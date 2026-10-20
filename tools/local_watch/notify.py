# -*- coding: utf-8 -*-
"""알림 발송기. ntfy.sh / 텔레그램 봇 / (설정 없을 때) Windows 토스트.

사용:  from notify import notify;  notify("제목", "본문", "alert")
level: info | warn | alert  (ntfy 우선순위 3 / 4 / 5)

설정: config/notify.json (config/notify.example.json 참고). 환경변수
LOCAL_WATCH_CONFIG_DIR 로 설정 폴더를 바꿀 수 있습니다.
비밀값(토큰·토픽)은 로그에 절대 찍지 않습니다.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
LEVELS = {"info": 3, "warn": 4, "alert": 5}
TELEGRAM_MAX = 4000  # 텔레그램 한 통 4096자 제한보다 약간 작게


def config_dir():
    return os.environ.get("LOCAL_WATCH_CONFIG_DIR") or os.path.join(BASE, "config")


def load_config(path=None):
    path = path or os.path.join(config_dir(), "notify.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _post_json(url, payload, timeout=15):
    """JSON POST. 성공이면 True. 예외 메시지에 URL(토큰 포함)이 섞이지 않게 요약만 남긴다."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print("[notify] HTTP 오류 %s" % e.code, file=sys.stderr)
    except Exception as e:  # 네트워크 단절 등
        print("[notify] 전송 실패: %s" % type(e).__name__, file=sys.stderr)
    return False


def send_ntfy(cfg, title, body, level):
    topic = (cfg or {}).get("topic", "").strip()
    if not (cfg or {}).get("enabled", True) or not topic:
        return None  # 미설정
    server = (cfg.get("server") or "https://ntfy.sh").rstrip("/")
    # JSON 발행 방식: 헤더가 아니라 본문에 담으므로 한글 제목도 안전합니다.
    payload = {"topic": topic, "title": title, "message": body,
               "priority": LEVELS.get(level, 3)}
    return _post_json(server, payload)


def send_telegram(cfg, title, body, level):
    token = (cfg or {}).get("token", "").strip()
    chat_id = str((cfg or {}).get("chat_id", "")).strip()
    if not (cfg or {}).get("enabled", True) or not token or not chat_id:
        return None
    icon = {"alert": "🔴 ", "warn": "🟠 "}.get(level, "")
    text = ("%s%s\n%s" % (icon, title, body))[:TELEGRAM_MAX]
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    return _post_json(url, {"chat_id": chat_id, "text": text})


def send_toast(title, body):
    """Windows 토스트. win10toast → plyer 순서로 시도, 둘 다 없으면 콘솔 출력."""
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, body[:250], duration=8, threaded=True)
        return True
    except Exception:
        pass
    try:
        from plyer import notification
        notification.notify(title=title, message=body[:250], timeout=8)
        return True
    except Exception:
        pass
    print("[알림] %s\n%s" % (title, body))
    return False


def notify(title, body, level="info", config=None):
    """모든 설정된 채널로 보낸다. 하나도 성공/설정되지 않으면 토스트로 대체.

    반환: {"ntfy": True/False/None, "telegram": ..., "toast": ...} (None = 미설정)
    """
    cfg = load_config() if config is None else config
    level = level if level in LEVELS else "info"
    result = {
        "ntfy": send_ntfy(cfg.get("ntfy"), title, body, level),
        "telegram": send_telegram(cfg.get("telegram"), title, body, level),
    }
    if not any(v is True for v in result.values()):
        result["toast"] = send_toast(title, body)
    return result


if __name__ == "__main__":
    # 점검용: python notify.py "제목" "본문" alert
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:] + ["테스트 알림", "local_watch 알림 점검", "info"][len(sys.argv[1:]):]
    print(notify(a[0], a[1], a[2]))
