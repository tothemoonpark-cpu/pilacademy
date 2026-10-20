# -*- coding: utf-8 -*-
"""숨고 감시기. Playwright(chromium)로 저장된 로그인 상태(storage_state.json)를 써서

 (1) /pro/chats 목록에서 '마지막 말풍선이 고객 쪽인 방'이 새로 생기면 notify + results/soomgo_new.json
 (2) /requests/received 첫 화면 카드를 5조건으로 판정 → results/soomgo_scan.json, 통과 건은 notify

기본은 읽기 전용입니다. 견적을 보내는 방향의 동작은 --send 를 줄 때만 켜지며,
그때도 하루 상한(rules.json: send_daily_cap, 기본 3)·중복 방지를 지키고 '최종 제출'은 하지 않습니다.

  python soomgo_watch.py                  # 채팅+요청 1회 (5분마다 작업 스케줄러로 실행)
  python soomgo_watch.py --only chats
  python soomgo_watch.py --check-selectors   # 셀렉터가 몇 개 잡히는지 점검 + HTML/스크린샷 저장
  python soomgo_watch.py --html-dir 폴더     # 브라우저 없이 저장된 HTML 로 파서만 시험
"""
import argparse
import datetime
import os
import sys
import time

import dedupe
import soomgo_parser as P
from notify import notify

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
STATE = os.path.join(BASE, "state", "soomgo_state.json")


def load_cfg(name):
    return dedupe.load_json(os.path.join(BASE, "config", name))


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------- 순수 로직(브라우저 없이 시험 가능) ----------
def handle_chats(rooms, state, now_s, send=notify):
    """고객 차례 방 중 '처음 보는 상태'만 골라 알림·기록. 새 항목 리스트를 반환."""
    seen = state.setdefault("chat_seen", {})
    new = []
    for r in P.awaiting_reply(rooms):
        k = r.key()
        if k not in seen:
            seen[k] = now_s
            new.append({"room_id": r.room_id, "name": r.name, "last_text": r.last_text,
                        "found_at": now_iso()})
    # 오래된 키 정리(14일)
    dedupe.prune(seen, 14 * 24, now_s)
    if new:
        body = "\n".join("• %s: %s" % (n["name"] or n["room_id"], n["last_text"][:60]) for n in new[:8])
        send("숨고 채팅 답변 필요 %d건" % len(new), body, "alert")
    return new


def handle_requests(cards, rules, state, today, send=notify, do_send=False, opener=None):
    """카드 판정 → 통과 건 알림. 반환: scan 결과 리스트(전체 카드의 판정 포함)."""
    notified = state.setdefault("req_notified", {})
    send_log = state.setdefault("send_log", {})
    rows = []
    for card in cards:
        v = P.judge_card(card, rules)
        row = {"card_id": card.card_id, "title": card.title, "passed": v.passed,
               "conditions": {n: {"ok": ok, "why": why} for n, (ok, why) in v.conditions.items()},
               "action": "none"}
        if v.passed and card.card_id not in notified:
            notified[card.card_id] = time.time()
            send("숨고 요청 통과: %s" % (card.title or card.card_id), v.summary(), "alert")
            row["action"] = "notified"
            if do_send:
                ok, why = dedupe.can_send_quote(send_log, card.card_id, today, rules.get("send_daily_cap", 3))
                if not ok:
                    row["action"] = "send_refused: " + why
                elif opener is None:
                    row["action"] = "send_refused: 클릭 동작 없음"
                else:
                    msg = opener(card)  # 실제 클릭 시도(최종 제출 아님). 실패 사유 문자열 or ""
                    if msg:
                        row["action"] = "send_refused: " + msg
                    else:
                        send_log.setdefault(today, []).append(card.card_id)
                        row["action"] = "opened_for_quote"
        rows.append(row)
    dedupe.prune(notified, 14 * 24)
    return rows


def write_new(new):
    path = os.path.join(RESULTS, "soomgo_new.json")
    cur = dedupe.load_json(path, {"items": []})
    items = (new + cur.get("items", []))[:200]  # 최신순 200건 유지
    dedupe.save_json(path, {"updated": now_iso(), "items": items})


# ---------- 브라우저 부분 ----------
def snapshot_failure(page, tag):
    """실패 시 스크린샷+HTML 을 results/ 에 남긴다(셀렉터 수정 근거)."""
    os.makedirs(RESULTS, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    try:
        page.screenshot(path=os.path.join(RESULTS, "fail_%s_%s.png" % (tag, stamp)), full_page=True)
        with open(os.path.join(RESULTS, "fail_%s_%s.html" % (tag, stamp)), "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception as e:
        print("[soomgo] 스냅샷 저장 실패: %s" % type(e).__name__, file=sys.stderr)


def fetch_html(page, section, tag, timeout_ms=20000):
    """페이지를 열고 목록이 뜰 때까지 기다린 뒤 HTML 반환. 실패하면 스냅샷 후 예외."""
    page.goto(section["url"], wait_until="domcontentloaded", timeout=30000)
    if "login" in page.url:
        snapshot_failure(page, tag + "_login")
        raise RuntimeError("로그인 만료: storage_state.json 을 다시 만드세요")
    try:
        page.wait_for_selector(section["wait_for"], timeout=timeout_ms)
    except Exception:
        snapshot_failure(page, tag)
        raise
    return page.content()


def check_selectors(page, sel):
    """각 셀렉터가 실제 화면에서 몇 개 잡히는지 출력."""
    for name in ("chats", "requests"):
        sec = sel[name]
        try:
            fetch_html(page, sec, "check_" + name)
        except Exception as e:
            print("[%s] 페이지 열기/대기 실패: %s (results/ 의 스냅샷 확인)" % (name, type(e).__name__))
            continue
        for k, v in sec.items():
            if k in ("url", "id_regex", "room_id_regex") or not v or k.startswith("_"):
                continue
            print("[%s] %-16s %-3d  %s" % (name, k, len(page.query_selector_all(v)), v))


def make_opener(page, sel):
    """--send: 카드 상세를 열고 open_button 만 클릭. 최종 제출 버튼은 정의조차 하지 않는다."""
    btn = (sel.get("send") or {}).get("open_button", "")

    def opener(card):
        if not btn:
            return "selectors.json send.open_button 미설정 → 클릭하지 않음"
        try:
            page.goto(card.link if card.link.startswith("http") else "https://soomgo.com" + card.link)
            page.click(btn, timeout=10000)
            return ""
        except Exception as e:
            snapshot_failure(page, "send")
            return "클릭 실패 %s" % type(e).__name__
    return opener


def run_browser(args, sel, rules):
    from playwright.sync_api import sync_playwright  # 지연 임포트(테스트 환경엔 없어도 됨)
    state = dedupe.load_json(STATE)
    now_s = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        ctx = browser.new_context(storage_state=args.storage_state)
        page = ctx.new_page()
        try:
            if args.check_selectors:
                check_selectors(page, sel)
                return 0
            errors = 0
            if args.only in ("all", "chats"):
                try:
                    rooms = P.parse_chat_rooms(fetch_html(page, sel["chats"], "chats"), sel["chats"])
                    new = handle_chats(rooms, state, now_s)
                    if new:
                        write_new(new)
                    print("[soomgo] 채팅 %d방 / 답변 필요 %d / 새로 %d" % (
                        len(rooms), len(P.awaiting_reply(rooms)), len(new)))
                except Exception as e:
                    errors += report_error("chats", e)
            if args.only in ("all", "requests"):
                try:
                    cards = P.parse_request_cards(fetch_html(page, sel["requests"], "requests"), sel["requests"])
                    opener = make_opener(page, sel) if args.send else None
                    rows = handle_requests(cards, rules, state, datetime.date.today().isoformat(),
                                           do_send=args.send, opener=opener)
                    dedupe.save_json(os.path.join(RESULTS, "soomgo_scan.json"),
                                     {"updated": now_iso(), "send_mode": args.send, "cards": rows})
                    print("[soomgo] 요청 %d건 / 통과 %d" % (len(rows), sum(r["passed"] for r in rows)))
                except Exception as e:
                    errors += report_error("requests", e)
            return 1 if errors else 0
        finally:
            dedupe.save_json(STATE, state)
            browser.close()


def report_error(where, e):
    """오류는 4시간에 한 번만 경보(5분마다 같은 오류가 쏟아지지 않게)."""
    msg = "%s: %s %s" % (where, type(e).__name__, str(e).splitlines()[0][:120] if str(e) else "")
    print("[soomgo] 오류 " + msg, file=sys.stderr)
    st = dedupe.load_json(STATE)
    gate = st.setdefault("error_gate", {})
    if dedupe.should_send(gate, where + type(e).__name__, 4):
        dedupe.mark_sent(gate, where + type(e).__name__)
        notify("숨고 감시 오류", msg + "\n(results/ 의 fail_* 스냅샷 확인)", "warn")
        dedupe.save_json(STATE, st)
    return 1


def run_offline(args, sel, rules):
    """--html-dir: chats.html / requests.html 로 파서만 시험(알림은 콘솔 출력)."""
    fake = lambda t, b, l="info": print("[알림:%s] %s | %s" % (l, t, b))
    state = {}
    cp = os.path.join(args.html_dir, "chats.html")
    rp = os.path.join(args.html_dir, "requests.html")
    if os.path.exists(cp):
        rooms = P.parse_chat_rooms(open(cp, encoding="utf-8").read(), sel["chats"])
        print("채팅 %d방, 새로 %d" % (len(rooms), len(handle_chats(rooms, state, time.time(), fake))))
    if os.path.exists(rp):
        cards = P.parse_request_cards(open(rp, encoding="utf-8").read(), sel["requests"])
        for r in handle_requests(cards, rules, state, "offline", fake):
            print(r["card_id"], "통과" if r["passed"] else "탈락", r["title"])
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--storage-state", default=os.path.join(BASE, "storage_state.json"))
    ap.add_argument("--only", choices=["all", "chats", "requests"], default="all")
    ap.add_argument("--send", action="store_true", help="견적 방향 동작 활성화(기본 꺼짐, 하루 상한·중복 방지)")
    ap.add_argument("--check-selectors", action="store_true")
    ap.add_argument("--headed", action="store_true", help="브라우저 창 보이기(디버그)")
    ap.add_argument("--html-dir", help="저장된 HTML 폴더로 오프라인 시험")
    args = ap.parse_args(argv)
    sel, rules = load_cfg("selectors.json"), load_cfg("rules.json")
    if args.html_dir:
        return run_offline(args, sel, rules)
    if not os.path.exists(args.storage_state):
        print("storage_state.json 이 없습니다. install_windows.md 의 '로그인 상태 만들기'를 먼저 하세요.", file=sys.stderr)
        return 2
    return run_browser(args, sel, rules)


if __name__ == "__main__":
    sys.exit(main())
