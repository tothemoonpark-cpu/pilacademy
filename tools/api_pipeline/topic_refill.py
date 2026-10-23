#!/usr/bin/env python3
"""1) 주제 후보 자동 보충기 — PubMed(esearch·efetch)에서 최근 2년 논문을 찾아 후보 md 로 저장한다.

이미 쓴 PMID(exclude_pmids.txt)는 거르고, 주제(강아지·고양이·펫로스)별로 미사용 후보가
목표 개수보다 모자랄 때만 채운다.  시험 모드: --test (결과는 out/_test/ 에만 저장, 소량만 조회).
"""
import argparse
from datetime import datetime

from common import (Paths, load_pool, load_queue, log, read_exclude, run_main, pubmed_fetch,
                    pubmed_search, save_abstract)

MIN_ABSTRACT_CHARS = 200


def refill(queue, paths, test=False, target=None):
    paths.ensure()
    cfg = queue["topics"]
    target = target or (1 if test else cfg.get("pool_per_topic", 6))
    excluded = read_exclude(paths)
    pool = {r["pmid"]: r for r in load_pool(paths)}
    added_total = 0
    for key, tcfg in cfg["queries"].items():
        unused = [r for r in pool.values() if r.get("topic") == key and r["pmid"] not in excluded]
        need = target - len(unused)
        if need <= 0:
            log(f"[{key}] 미사용 후보 {len(unused)}건 — 보충 불필요")
            continue
        retmax = min(8, need * 4 + 4) if test else min(200, need * 6 + 10)
        ids = pubmed_search(tcfg["query"], retmax, cfg.get("years", 2) * 365)
        ids = [i for i in ids if i not in excluded and i not in pool]
        log(f"[{key}] 검색 {len(ids)}건(제외·중복 거른 뒤), {need}건 보충 시도")
        got = 0
        for i in range(0, len(ids), 20):
            for rec in pubmed_fetch(ids[i:i + 20]):
                if got >= need:
                    break
                if len(rec["abstract"]) < MIN_ABSTRACT_CHARS:
                    continue
                rec.update(topic=key, added=datetime.now().isoformat(timespec="seconds"))
                save_abstract(paths, rec)
                pool[rec["pmid"]] = rec
                got += 1
            if got >= need:
                break
        added_total += got
        log(f"[{key}] {got}건 추가")
    write_candidates_md(queue, paths, pool, excluded)
    return added_total


def write_candidates_md(queue, paths, pool, excluded):
    labels = {k: v.get("label", k) for k, v in queue["topics"]["queries"].items()}
    lines = [f"# 주제 후보 ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"- 제외 목록(이미 쓴 PMID): {len(excluded)}건 · 검색 범위: 최근 {queue['topics'].get('years', 2)}년",
             "- 초록 원문은 아래 인용문 그대로입니다. 초안·검수는 이 초록만 근거로 합니다.", ""]
    for key, label in labels.items():
        items = [r for r in pool.values() if r.get("topic") == key and r["pmid"] not in excluded]
        lines += [f"## {label} ({len(items)}건)", ""]
        for n, r in enumerate(items, 1):
            lines += [f"### {n}. PMID {r['pmid']}", f"- 제목: {r['title']}",
                      f"- 저널/연도: {r['journal']} / {r['year']}",
                      f"- 링크: https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/", ""]
            lines += [f"> {ln}" for ln in r["abstract"].splitlines()] + [""]
    paths.candidates.write_text("\n".join(lines), encoding="utf-8")
    log(f"후보 md 저장: {paths.candidates}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", default="queue.json")
    ap.add_argument("--test", action="store_true", help="시험 모드: out/_test/ 에 소량만 저장")
    ap.add_argument("--target", type=int, help="주제별 미사용 후보 목표 개수")
    a = ap.parse_args()
    n = refill(load_queue(a.queue), Paths(a.test), a.test, a.target)
    log(f"완료: 새 후보 {n}건")


if __name__ == "__main__":
    run_main(main)
