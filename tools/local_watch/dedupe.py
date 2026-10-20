# -*- coding: utf-8 -*-
"""중복 억제·상태 파일 유틸. 표준 라이브러리만 사용(네트워크·브라우저 없음).

상태 파일은 {키: 마지막 발송 epoch초} 형태의 JSON 입니다.
"""
import json
import os
import tempfile
import time


def load_json(path, default=None):
    """JSON 을 읽는다. 없거나 깨졌으면 default(없으면 {})를 돌려준다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def save_json(path, data):
    """임시 파일에 쓴 뒤 교체(쓰다 꺼져도 파일이 깨지지 않게)."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def should_send(state, key, window_hours, now=None):
    """같은 key 를 window_hours 안에 이미 보냈으면 False."""
    now = time.time() if now is None else now
    last = state.get(key)
    return last is None or (now - float(last)) >= window_hours * 3600


def mark_sent(state, key, now=None):
    state[key] = time.time() if now is None else now


def prune(state, window_hours, now=None):
    """창(window)보다 오래된 항목을 지워 상태 파일이 커지지 않게 한다."""
    now = time.time() if now is None else now
    for k in [k for k, v in state.items() if (now - float(v)) >= window_hours * 3600]:
        del state[k]


def can_send_quote(send_log, card_id, today, cap):
    """--send 일일 상한·중복 방지. send_log = {"YYYY-MM-DD": [card_id, ...]}.

    중복은 날짜와 무관하게 이미 처리한 건이면 거부한다.
    """
    done = {cid for ids in send_log.values() for cid in ids}
    if card_id in done:
        return False, "이미 처리한 건"
    if len(send_log.get(today, [])) >= cap:
        return False, "오늘 상한(%d건) 도달" % cap
    return True, "ok"
