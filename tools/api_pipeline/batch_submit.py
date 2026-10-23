#!/usr/bin/env python3
"""2) 초안 배치 제출기 — Anthropic Message Batches API(50% 할인)로 종류별 프롬프트를 한꺼번에 제출한다.

prompts/_rules.md 가 system 으로, prompts/<종류>.md 가 사용자 프롬프트로 들어간다.
키는 환경변수 ANTHROPIC_API_KEY 에서만 읽는다.
시험 모드: --test  → API 를 부르지 않고 요청 본문만 만들어 보여 주고, 수집기·검수기 시험용 가짜 결과를
out/_test/mock_results.jsonl 에 만든다(가짜 결과에는 일부러 틀린 숫자·약 용량이 섞여 있다).
"""
import argparse
import json
import re
from datetime import datetime

from common import (API_BASE, ROOT, Paths, PipelineError, anthropic_headers, http, load_pool,
                    load_queue, load_state, log, read_exclude, run_main, save_state)


def load_prompt(kind):
    p = ROOT / "prompts" / f"{kind}.md"
    if not p.exists():
        raise PipelineError(f"프롬프트 파일이 없습니다: {p}")
    return p.read_text(encoding="utf-8")


def fill(template, rec, topic_label):
    vals = {"TOPIC_LABEL": topic_label, "TITLE": rec["title"], "JOURNAL": rec["journal"],
            "YEAR": rec["year"], "PMID": rec["pmid"], "ABSTRACT": rec["abstract"]}
    for k, v in vals.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template


def interleave(pool, topic_order):
    groups = [[r for r in pool if r.get("topic") == t] for t in topic_order]
    out = []
    for i in range(max((len(g) for g in groups), default=0)):
        out += [g[i] for g in groups if i < len(g)]
    return out


def pick_pmids(queue, paths, state, take):
    blocked = read_exclude(paths) | set(state.get("submitted_pmids", []))
    if queue.get("items"):
        return [str(i["pmid"] if isinstance(i, dict) else i) for i in queue["items"]
                if str(i["pmid"] if isinstance(i, dict) else i) not in blocked][:take]
    pool = [r for r in load_pool(paths) if r["pmid"] not in blocked]
    return [r["pmid"] for r in interleave(pool, list(queue["topics"]["queries"]))][:take]


def build_requests(queue, paths, pmids):
    rules = (ROOT / "prompts" / "_rules.md").read_text(encoding="utf-8")
    labels = {k: v.get("label", k) for k, v in queue["topics"]["queries"].items()}
    pool = {r["pmid"]: r for r in load_pool(paths)}
    reqs = []
    for pmid in pmids:
        rec = pool.get(pmid)
        if rec is None:
            raise PipelineError(f"PMID {pmid} 의 초록이 없습니다. 먼저 topic_refill.py 를 실행하세요.")
        for kind in queue["kinds"]:
            prompt = fill(load_prompt(kind["name"]), rec, labels.get(rec.get("topic"), rec.get("topic", "")))
            cid = f"{pmid}-{kind['name']}"
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cid):
                raise PipelineError(f"custom_id 형식 오류: {cid}")
            reqs.append({"custom_id": cid, "params": {
                "model": queue["model"], "max_tokens": kind.get("max_tokens", 3000),
                "system": rules, "messages": [{"role": "user", "content": prompt}]}})
    return reqs


def submit(queue, paths, test=False, take=None, dry=False):
    paths.ensure()
    state = load_state(paths)
    pmids = pick_pmids(queue, paths, state, take or (1 if test else queue.get("take", 3)))
    if not pmids:
        log("제출할 PMID 가 없습니다. topic_refill.py 로 후보를 보충하거나 queue.json 의 items 를 채워 주세요.")
        return None
    reqs = build_requests(queue, paths, pmids)
    log(f"요청 {len(reqs)}건 (PMID {', '.join(pmids)} × 종류 {len(queue['kinds'])})")
    if test or dry:
        r0 = reqs[0]
        log("--- 시험 모드: API 를 부르지 않습니다. 첫 요청 미리보기 ---")
        log(f"custom_id={r0['custom_id']} model={r0['params']['model']} max_tokens={r0['params']['max_tokens']}")
        log("system(앞 120자): " + r0["params"]["system"][:120].replace("\n", " "))
        log("user(앞 160자): " + r0["params"]["messages"][0]["content"][:160].replace("\n", " "))
        batch_id = "msgbatch_TEST_" + datetime.now().strftime("%H%M%S")
        if test:
            write_mock_results(paths, reqs)
    else:
        resp = json.loads(http("POST", f"{API_BASE}/messages/batches", anthropic_headers(), {"requests": reqs}))
        batch_id = resp["id"]
        log(f"배치 제출 완료: {batch_id} (상태 {resp.get('processing_status')})")
    if not dry:
        state["batches"].append({
            "id": batch_id, "created": datetime.now().isoformat(timespec="seconds"), "test": test,
            "pmids": pmids, "custom_ids": [r["custom_id"] for r in reqs], "collected": False})
        state["submitted_pmids"] = sorted(set(state.get("submitted_pmids", [])) | set(pmids))
        save_state(paths, state)
    return batch_id


# ---------- 시험용 가짜 결과 ----------

def _unused_number(abstract):
    present = set(re.findall(r"\d+(?:\.\d+)?", abstract))
    for cand in ("37.5", "88.8", "41.3"):
        if cand not in present:
            return cand
    return "9999"


def write_mock_results(paths, reqs):
    pool = {r["pmid"]: r for r in load_pool(paths)}
    lines = []
    for i, rq in enumerate(reqs):
        pmid, kind = rq["custom_id"].split("-", 1)
        rec = pool[pmid]
        real = re.findall(r"\d+(?:\.\d+)?", rec["abstract"])
        real_num = real[0] if real else None
        fact = f"이 연구에서 확인된 수치는 {real_num}입니다." if real_num else "이 연구는 수치보다 경향을 살펴봤습니다."
        src = f"출처: {rec['journal']}, {rec['year']}, PMID {pmid}"
        if kind == "sns_set":
            body = f"### 1/2\n{fact} #반려동물\n\n### 2/2\n보호자의 마음을 먼저 살피는 연구입니다. #펫로스\n\n{src}"
        elif kind == "petloss_blog":  # 일부러 틀린 숫자와 약 용량을 섞는다
            body = (f"# 시험용 블로그\n\n{fact}\n\n이 연구에서는 {_unused_number(rec['abstract'])}%가 달라졌다고 합니다. "
                    f"또 가바펜틴 5mg/kg을 쓰면 편안해진다고 이 연구가 증명했습니다.\n\n{src}")
        elif kind == "petlus_news":
            body = f"# 시험용 기사\n\n{fact}\n\n{src}"
        else:
            body = f"{fact}\n보호자님의 마음을 헤아리는 연구입니다.\n{src}"
        if i == len(reqs) - 1 and len(reqs) > 3:  # 오류 경로 시험: 마지막 요청은 실패 처리
            lines.append({"custom_id": rq["custom_id"], "result": {"type": "errored",
                          "error": {"type": "error", "error": {"type": "overloaded_error", "message": "mock"}}}})
            continue
        lines.append({"custom_id": rq["custom_id"], "result": {"type": "succeeded", "message": {
            "content": [{"type": "text", "text": body}], "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0}}}})
    paths.mock.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n", encoding="utf-8")
    log(f"시험용 가짜 결과 저장: {paths.mock}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", default="queue.json")
    ap.add_argument("--test", action="store_true", help="시험 모드: API 호출 없이 요청 구성 + 가짜 결과 생성")
    ap.add_argument("--dry-run", action="store_true", help="실제 풀로 요청만 구성해 보고 제출·기록은 하지 않음")
    ap.add_argument("--take", type=int, help="이번에 제출할 PMID 수")
    a = ap.parse_args()
    paths = Paths(a.test)
    queue = load_queue(a.queue)
    if a.test and not load_pool(paths):
        from topic_refill import refill
        log("시험 풀이 비어 있어 PubMed 에서 소량 보충합니다.")
        refill(queue, paths, test=True)
    submit(queue, paths, a.test, a.take, a.dry_run)


if __name__ == "__main__":
    run_main(main)
