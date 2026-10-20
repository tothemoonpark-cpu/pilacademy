# -*- coding: utf-8 -*-
"""설정 JSON 의 명령들을 주기대로 실행하고, 출력에 경보 패턴이 있으면 notify 로 보낸다.

  python watch_runner.py --config config/watch.json          # 도래한 작업만 1회 실행(작업 스케줄러용)
  python watch_runner.py --config config/watch.json --loop    # 상주 실행(1분마다 점검)
  python watch_runner.py --config config/watch.json --force   # 주기 무시하고 전부 실행

같은 경보 줄은 dedupe_hours(기본 4시간) 안에 한 번만 보냅니다(state/watch_state.json).
"""
import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time

import dedupe
from notify import notify

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATTERNS = ["⛔", "🔴", "ALERT:"]
_TS = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?|\d{2}:\d{2}:\d{2}")


def find_alert_lines(output, patterns):
    """패턴 중 하나라도 들어 있는 줄을 순서대로 돌려준다(정규식)."""
    regs = [re.compile(p) for p in patterns]
    return [ln.strip() for ln in output.splitlines()
            if ln.strip() and any(r.search(ln) for r in regs)]


def alert_key(job_name, line):
    """시각 문자열을 지워 '같은 경보'가 매번 다른 키가 되지 않게 한다."""
    norm = _TS.sub("", line)
    norm = re.sub(r"\s+", " ", norm).strip()
    return job_name + "|" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def run_command(cmd, workdir, timeout):
    """(returncode, 합쳐진 출력). 실행 불가/시간초과는 returncode 를 -1 로."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd, posix=(os.name != "nt"))
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        p = subprocess.run(cmd, cwd=workdir or None, capture_output=True,
                           timeout=timeout, env=env)
        out = (p.stdout or b"") + b"\n" + (p.stderr or b"")
        return p.returncode, out.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return -1, "ALERT: 시간 초과(%ss)" % timeout
    except OSError as e:
        return -1, "ALERT: 실행 실패 %s" % type(e).__name__


def process_job(job, cfg, state, alerts_state, now, runner=run_command, send=notify):
    """작업 1개 실행 → 새(중복 아닌) 경보를 묶어 발송. 보낸 줄 수를 반환."""
    window = float(cfg.get("dedupe_hours", 4))
    patterns = cfg.get("patterns") or DEFAULT_PATTERNS
    code, out = runner(job["cmd"], cfg.get("workdir"), job.get("timeout_sec", 600))
    lines = find_alert_lines(out, patterns)
    if code != 0 and not lines:  # 비정상 종료인데 패턴 줄이 없으면 그 자체를 경보로
        lines = ["ALERT: %s 비정상 종료(코드 %s)" % (job["name"], code)]
    fresh = []
    for ln in lines:
        k = alert_key(job["name"], ln)
        if dedupe.should_send(alerts_state, k, window, now):
            fresh.append(ln)
            dedupe.mark_sent(alerts_state, k, now)
    if fresh:
        body = "\n".join(fresh[:15])
        if len(fresh) > 15:
            body += "\n… 외 %d줄" % (len(fresh) - 15)
        send("[감시] %s" % job["name"], body, "alert")
    state.setdefault("last_run", {})[job["name"]] = now
    return len(fresh)


def run_once(cfg, state_path, force=False, now=None, runner=run_command, send=notify):
    now = time.time() if now is None else now
    state = dedupe.load_json(state_path)
    alerts = state.setdefault("alerts", {})
    sent = 0
    for job in cfg.get("jobs", []):
        last = state.get("last_run", {}).get(job["name"])
        due = force or last is None or (now - last) >= job.get("interval_minutes", 60) * 60
        if due:
            sent += process_job(job, cfg, state, alerts, now, runner, send)
    dedupe.prune(alerts, float(cfg.get("dedupe_hours", 4)), now)
    dedupe.save_json(state_path, state)
    return sent


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(BASE, "config", "watch.json"))
    ap.add_argument("--state", default=os.path.join(BASE, "state", "watch_state.json"))
    ap.add_argument("--loop", action="store_true", help="상주 실행(60초마다 도래 여부 점검)")
    ap.add_argument("--force", action="store_true", help="주기 무시하고 전부 실행")
    args = ap.parse_args(argv)
    cfg = dedupe.load_json(args.config)
    if not cfg.get("jobs"):
        print("설정에 jobs 가 없습니다: %s" % args.config, file=sys.stderr)
        return 2
    while True:
        n = run_once(cfg, args.state, force=args.force)
        print("[watch] 새 경보 %d줄 발송" % n)
        if not args.loop:
            return 0
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())
