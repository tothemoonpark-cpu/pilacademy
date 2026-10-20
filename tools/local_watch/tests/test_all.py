# -*- coding: utf-8 -*-
"""네트워크·브라우저 없이 도는 단위 테스트.  실행: python -m unittest discover -s tests -v"""
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import dedupe  # noqa: E402
import notify as N  # noqa: E402
import soomgo_parser as P  # noqa: E402
import soomgo_watch as W  # noqa: E402
import watch_runner as R  # noqa: E402

def _load(name):
    with open(os.path.join(ROOT, "config", name), encoding="utf-8") as f:
        return json.load(f)


RULES = _load("rules.json")
# 합성 샘플용 셀렉터(실제 selectors.json 은 미검증이므로 테스트는 자체 셀렉터를 쓴다)
SEL_CHAT = {"room": "a.room", "room_id_regex": "/pro/chats/(\\d+)", "name": ".name",
            "last_text": ".last-message", "bubble": "",
            "customer_marker": ".received", "pro_marker": ".sent"}
SEL_REQ = {"card": "a.card", "id_regex": "/requests/(\\d+)", "title": ".title", "category": ".category",
           "body": ".content", "quote_count": ".quote", "elapsed": "time", "client_usage": ".usage"}


def fx(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


def card(**kw):
    base = dict(card_id="1", title="유튜브 영상 편집", category="영상 편집",
                body="유튜브용 10분 분량, 3일 이내 납기 부탁드려요. 자막 포함 컷편집 필요합니다. 참고 영상 첨부.",
                quote_text="견적 보낸 고수 1명", elapsed_text="12분 전", usage_text="숨고 이용 5회")
    base.update(kw)
    return P.RequestCard(**base)


class TestJudge(unittest.TestCase):
    def test_pass(self):
        v = P.judge_card(card(), RULES)
        self.assertTrue(v.passed, v.summary())

    def test_each_condition_fails_alone(self):
        cases = {
            "quote": card(quote_text="견적 보낸 고수 2명"),
            "video": card(category="", title="로고 디자인", body="로고 디자인 10분 3일 이내 유튜브 용 " * 3),
            "elapsed": card(elapsed_text="31분 전"),
            "unreadable_elapsed": card(elapsed_text=""),
            "unreadable_quote": card(quote_text=""),
        }
        for name, c in cases.items():
            self.assertFalse(P.judge_card(c, RULES).passed, name)

    def test_specifics_need_two(self):
        c = card(title="영상 편집", category="영상 편집", body="영상 편집 해주세요 " * 8, usage_text="숨고 이용 4회")
        self.assertFalse(P.judge_card(c, RULES).passed)

    def test_fifth_condition_either_branch(self):
        short_but_veteran = card(body="유튜브용 10분 3일 이내 영상 편집", usage_text="숨고 이용 3회")
        self.assertTrue(P.judge_card(short_but_veteran, RULES).passed)
        newbie_long = card(usage_text="숨고 이용 1회", body="유튜브용 10분 분량 3일 이내 납기 영상 편집 요청드립니다. " * 3)
        self.assertGreaterEqual(len(newbie_long.body), 60)
        self.assertTrue(P.judge_card(newbie_long, RULES).passed)  # 본문 60자 이상
        newbie_short = card(body="유튜브용 10분 3일 이내 영상 편집", usage_text="숨고 이용 1회")
        self.assertFalse(P.judge_card(newbie_short, RULES).passed)

    def test_elapsed_parse(self):
        f = P.parse_elapsed_minutes
        self.assertEqual((f("방금 전"), f("30분 전"), f("2시간 전"), f("어제")), (0, 30, 120, None))
        self.assertTrue(P.judge_card(card(elapsed_text="30분 전"), RULES).passed)  # 경계 포함


class TestParser(unittest.TestCase):
    def test_chat_sides(self):
        rooms = P.parse_chat_rooms(fx("chats.html"), SEL_CHAT)
        self.assertEqual([r.last_side for r in rooms], ["customer", "pro", "unknown"])
        self.assertEqual([r.room_id for r in P.awaiting_reply(rooms)], ["1001"])

    def test_request_cards_fixture(self):
        cards = P.parse_request_cards(fx("requests.html"), SEL_REQ)
        self.assertEqual([c.card_id for c in cards], ["9001", "9002"])
        res = [P.judge_card(c, RULES).passed for c in cards]
        self.assertEqual(res, [True, False])

    def test_default_selectors_json_is_loadable(self):
        sel = _load("selectors.json")
        self.assertIn("room", sel["chats"])
        self.assertFalse(sel["send"]["open_button"])  # 기본은 비활성


class TestChatNew(unittest.TestCase):
    def test_notify_once_then_again_on_new_message(self):
        sent, state = [], {}
        send = lambda t, b, l="info": sent.append(t)
        rooms = P.parse_chat_rooms(fx("chats.html"), SEL_CHAT)
        self.assertEqual(len(W.handle_chats(rooms, state, 1000, send)), 1)
        self.assertEqual(len(W.handle_chats(rooms, state, 1300, send)), 0)  # 5분 뒤 같은 상태 → 조용
        rooms[0].last_text = "답이 없으시네요"
        self.assertEqual(len(W.handle_chats(rooms, state, 1600, send)), 1)  # 새 메시지 → 다시
        self.assertEqual(len(sent), 2)


class TestRequestsAndSend(unittest.TestCase):
    def setUp(self):
        self.cards = P.parse_request_cards(fx("requests.html"), SEL_REQ)

    def test_notify_pass_once_and_no_click_by_default(self):
        sent, state = [], {}
        opener = mock.Mock(return_value="")
        send = lambda t, b, l="info": sent.append(t)
        rows = W.handle_requests(self.cards, RULES, state, "2026-10-20", send, do_send=False, opener=opener)
        self.assertEqual(rows[0]["action"], "notified")
        opener.assert_not_called()
        W.handle_requests(self.cards, RULES, state, "2026-10-20", send)
        self.assertEqual(len(sent), 1)  # 같은 건 재알림 없음

    def test_send_cap_and_dedupe(self):
        ok, _ = dedupe.can_send_quote({"d": ["a", "b", "c"]}, "x", "d", 3)
        self.assertFalse(ok)  # 상한
        ok, _ = dedupe.can_send_quote({"old": ["x"]}, "x", "d", 3)
        self.assertFalse(ok)  # 다른 날이라도 중복
        ok, _ = dedupe.can_send_quote({"d": ["a"]}, "x", "d", 3)
        self.assertTrue(ok)

    def test_send_mode_calls_opener_and_logs(self):
        state, opener = {}, mock.Mock(return_value="")
        rows = W.handle_requests(self.cards, RULES, state, "d", lambda *a: None, do_send=True, opener=opener)
        self.assertEqual(rows[0]["action"], "opened_for_quote")
        self.assertEqual(state["send_log"]["d"], ["9001"])

    def test_send_refused_when_opener_not_configured(self):
        rows = W.handle_requests(self.cards, RULES, {}, "d", lambda *a: None, do_send=True,
                                 opener=lambda c: "open_button 미설정")
        self.assertTrue(rows[0]["action"].startswith("send_refused"))


class TestDedupe(unittest.TestCase):
    def test_window(self):
        s = {}
        self.assertTrue(dedupe.should_send(s, "k", 4, now=0))
        dedupe.mark_sent(s, "k", now=0)
        self.assertFalse(dedupe.should_send(s, "k", 4, now=3 * 3600 + 3599))
        self.assertTrue(dedupe.should_send(s, "k", 4, now=4 * 3600))

    def test_prune(self):
        s = {"old": 0, "new": 100000}
        dedupe.prune(s, 4, now=100000)
        self.assertEqual(list(s), ["new"])


class TestWatchRunner(unittest.TestCase):
    def test_find_lines(self):
        out = "ok\n⛔ 링크 깨짐 3건\n🔴 세트 누락\nALERT: x\n평범"
        self.assertEqual(len(R.find_alert_lines(out, R.DEFAULT_PATTERNS)), 3)

    def test_key_ignores_timestamps(self):
        a = R.alert_key("j", "⛔ 실패 2026-10-20 10:00:01 링크")
        b = R.alert_key("j", "⛔ 실패 2026-10-20 14:30:09 링크")
        self.assertEqual(a, b)

    def test_four_hour_suppression_and_resend(self):
        sent = []
        send = lambda t, b, l="info": sent.append(b)
        cfg = {"patterns": R.DEFAULT_PATTERNS, "dedupe_hours": 4,
               "jobs": [{"name": "J", "cmd": ["x"], "interval_minutes": 10}]}
        runner = lambda cmd, wd, to: (0, "⛔ 문제 발생\n정상")
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, "s.json")
            self.assertEqual(R.run_once(cfg, sp, now=0, runner=runner, send=send), 1)
            self.assertEqual(R.run_once(cfg, sp, now=3600, runner=runner, send=send), 0)       # 1시간 뒤 억제
            self.assertEqual(R.run_once(cfg, sp, now=300, runner=runner, send=send), 0)        # 주기 미도래
            self.assertEqual(R.run_once(cfg, sp, now=4 * 3600 + 1, runner=runner, send=send), 1)  # 4시간 후 재발송
        self.assertEqual(len(sent), 2)

    def test_nonzero_exit_without_pattern_alerts(self):
        sent = []
        cfg = {"jobs": [{"name": "J", "cmd": ["x"]}]}
        R.process_job(cfg["jobs"][0], cfg, {}, {}, 0, runner=lambda *a: (1, "traceback"),
                      send=lambda t, b, l="info": sent.append(b))
        self.assertIn("비정상 종료", sent[0])


class TestNotify(unittest.TestCase):
    def test_no_channel_falls_back_to_toast(self):
        with mock.patch.object(N, "send_toast", return_value=True) as t:
            r = N.notify("제목", "본문", "alert", config={})
        t.assert_called_once()
        self.assertTrue(r["toast"])

    def test_ntfy_payload(self):
        with mock.patch.object(N, "_post_json", return_value=True) as p, \
             mock.patch.object(N, "send_toast") as t:
            r = N.notify("제목", "본문", "alert", config={"ntfy": {"topic": "abc"}})
        url, payload = p.call_args[0]
        self.assertEqual(url, "https://ntfy.sh")
        self.assertEqual((payload["topic"], payload["priority"]), ("abc", 5))
        t.assert_not_called()
        self.assertTrue(r["ntfy"])

    def test_telegram_and_failed_ntfy_falls_back(self):
        calls = []
        def fake_post(url, payload, timeout=15):
            calls.append(url)
            return "telegram" in url
        cfg = {"ntfy": {"topic": "abc"}, "telegram": {"token": "T", "chat_id": "1"}}
        with mock.patch.object(N, "_post_json", side_effect=fake_post), mock.patch.object(N, "send_toast") as t:
            N.notify("a", "b", "info", config=cfg)
        self.assertEqual(len(calls), 2)
        t.assert_not_called()  # 텔레그램 성공 → 토스트 불필요

    def test_disabled_channel_skipped(self):
        self.assertIsNone(N.send_ntfy({"enabled": False, "topic": "x"}, "t", "b", "info"))


if __name__ == "__main__":
    unittest.main()
