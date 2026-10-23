#!/usr/bin/env python3
"""5) 큐 실행기 — queue.json 하나로 1~4 단계(보충 → 제출 → 수집 → 검수)를 이어 돌린다.

다시 실행해도 안전하다: 아직 처리 중인 배치가 있으면 새로 제출하지 않고 수집만 시도한다.
  python3 run_queue.py                 # 보충 → (진행 중 배치 없으면) 제출 → 수집 시도 → 검수
  python3 run_queue.py --wait          # 배치가 끝날 때까지 기다렸다가 수집·검수까지
  python3 run_queue.py --steps collect,factcheck
  python3 run_queue.py --test          # 키 없이 전체 흐름 시험(PubMed 는 실제 조회, Claude 는 가짜 결과)
"""
import argparse

from batch_collect import collect
from batch_submit import submit
from common import Paths, load_queue, load_state, log, run_main
from fact_check import run as factcheck_run
from topic_refill import refill

STEPS = ["refill", "submit", "collect", "factcheck"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", default="queue.json")
    ap.add_argument("--steps", default=",".join(STEPS), help="쉼표로 구분: " + ",".join(STEPS))
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--llm", action="store_true", help="검수에 Claude 주장 대조 추가")
    a = ap.parse_args()
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    bad = [s for s in steps if s not in STEPS]
    if bad:
        raise SystemExit(f"알 수 없는 단계: {bad}")
    paths, queue = Paths(a.test), load_queue(a.queue)
    if "refill" in steps:
        log("== 1/4 주제 후보 보충 ==")
        refill(queue, paths, a.test)
    if "submit" in steps:
        log("== 2/4 배치 제출 ==")
        if any(not b["collected"] for b in load_state(paths)["batches"]):
            log("아직 수집하지 않은 배치가 있어 새로 제출하지 않습니다.")
        else:
            submit(queue, paths, a.test)
    if "collect" in steps:
        log("== 3/4 결과 수집 ==")
        collect(paths, a.wait)
    if "factcheck" in steps:
        log("== 4/4 사실검수 ==")
        factcheck_run(paths, use_llm=a.llm and not a.test, model=queue["model"])


if __name__ == "__main__":
    run_main(main)
