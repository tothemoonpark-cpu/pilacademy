#!/usr/bin/env python3
"""3) 결과 수집기 — 끝난 배치의 결과를 편별 md 파일(drafts/<PMID>/<종류>.md)로 저장한다.

저장에 성공한 PMID 는 exclude_pmids.txt 에 자동으로 덧붙여 다음 후보에서 빠진다.
시험 모드: --test  → out/_test/mock_results.jsonl(제출기 시험 모드가 만든 가짜 결과)을 읽는다.
"""
import argparse
import json
import time

from common import (API_BASE, Paths, PipelineError, anthropic_headers, append_exclude, draft_path,
                    http, load_abstract, load_state, log, run_main, save_state, today)


def fetch_results(batch, paths, wait=False, interval=60):
    """끝난 배치의 결과 줄 목록을 돌려준다. 아직 처리 중이면 None."""
    if batch["test"]:
        if not paths.mock.exists():
            raise PipelineError("시험용 가짜 결과가 없습니다. batch_submit.py --test 를 먼저 실행하세요.")
        return [json.loads(l) for l in paths.mock.read_text(encoding="utf-8").splitlines() if l.strip()]
    while True:
        info = json.loads(http("GET", f"{API_BASE}/messages/batches/{batch['id']}", anthropic_headers()))
        if info.get("processing_status") == "ended":
            raw = http("GET", info["results_url"], anthropic_headers()).decode("utf-8")
            return [json.loads(l) for l in raw.splitlines() if l.strip()]
        c = info.get("request_counts", {})
        log(f"{batch['id']} 처리 중 (진행 {c.get('processing', '?')}건 남음)")
        if not wait:
            return None
        time.sleep(interval)


def save_draft(paths, batch, line, model=""):
    pmid, kind = line["custom_id"].split("-", 1)
    res = line["result"]
    if res["type"] != "succeeded":
        return None, f"{line['custom_id']}: {res['type']} {json.dumps(res.get('error', ''), ensure_ascii=False)[:200]}"
    msg = res["message"]
    text = "".join(b.get("text", "") for b in msg["content"] if b.get("type") == "text").strip()
    rec = load_abstract(paths, pmid) or {}
    meta = [("pmid", pmid), ("kind", kind), ("topic", rec.get("topic", "")), ("batch", batch["id"]),
            ("stop_reason", msg.get("stop_reason")), ("collected", today()),
            ("source", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")]
    p = draft_path(paths, pmid, kind)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\n" + "\n".join(f"{k}: {v}" for k, v in meta) + "\n---\n" + text + "\n", encoding="utf-8")
    note = " (분량 한도에서 잘림 — 검수 필요)" if msg.get("stop_reason") == "max_tokens" else ""
    return pmid, f"{p.relative_to(paths.base)}{note}"


def collect(paths, wait=False, batch_id=None):
    paths.ensure()
    state = load_state(paths)
    todo = [b for b in state["batches"] if not b["collected"] and (batch_id in (None, b["id"]))]
    if not todo:
        log("수집할 배치가 없습니다.")
        return 0
    saved, errors = 0, []
    for b in todo:
        lines = fetch_results(b, paths, wait)
        if lines is None:
            continue
        ok_pmids = set()
        for line in lines:
            pmid, msg = save_draft(paths, b, line)
            if pmid:
                ok_pmids.add(pmid)
                saved += 1
                log(f"저장: {msg}")
            else:
                errors.append(msg)
        b["collected"] = True
        n = append_exclude(paths, sorted(ok_pmids), f"초안 수집 {today()} ({b['id']})")
        log(f"배치 {b['id']}: 초안 {len(lines) - len(errors)}편 저장, 제외 목록에 PMID {n}건 추가")
    if errors:
        (paths.base / "collect_errors.md").write_text("# 수집 실패 목록\n\n" + "\n".join(f"- {e}" for e in errors) + "\n", encoding="utf-8")
        log(f"실패 {len(errors)}건 → {paths.base / 'collect_errors.md'}")
    save_state(paths, state)
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="시험 모드: 가짜 결과 파일을 읽는다")
    ap.add_argument("--wait", action="store_true", help="배치가 끝날 때까지 60초 간격으로 기다린다")
    ap.add_argument("--batch-id")
    a = ap.parse_args()
    collect(Paths(a.test), a.wait, a.batch_id)


if __name__ == "__main__":
    run_main(main)
