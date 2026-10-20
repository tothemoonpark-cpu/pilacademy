# -*- coding: utf-8 -*-
"""숨고 화면 HTML 파서·판정 함수. 브라우저/네트워크 없이 HTML 문자열만 다룹니다.

셀렉터는 코드에 박지 않고 config/selectors.json 에서 받습니다.
"""
import hashlib
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


# ---------- 공통 헬퍼 ----------
def _text(el, css):
    """el 안에서 css 로 찾은 첫 요소의 텍스트. css 가 비었거나 못 찾으면 ''."""
    if not css or el is None:
        return ""
    found = el.select_one(css)
    return found.get_text(" ", strip=True) if found else ""


def _hit(el, css):
    """el 자신이 css 에 해당하거나, 그 안에 해당 요소가 있으면 True."""
    if not css or el is None:
        return False
    return bool(el.css.match(css) or el.select_one(css))


def _id_from(el, regex, fallback_text):
    href = el.get("href", "") if hasattr(el, "get") else ""
    m = re.search(regex, href) if regex and href else None
    if m:
        return m.group(1)
    return "h" + hashlib.sha1(fallback_text.encode("utf-8")).hexdigest()[:12]


# ---------- 채팅 ----------
@dataclass
class ChatRoom:
    room_id: str
    name: str
    last_text: str
    last_side: str  # "customer" | "pro" | "unknown"

    def key(self):
        """같은 방의 같은 마지막 메시지면 같은 키 → 새 메시지가 오면 키가 바뀐다."""
        return "%s|%s" % (self.room_id, hashlib.sha1(self.last_text.encode("utf-8")).hexdigest()[:10])


def last_side(room_el, sel):
    """마지막 말풍선(없으면 방 항목 자체)의 보낸 쪽을 마커 셀렉터로 판정."""
    target = room_el
    if sel.get("bubble"):
        bubbles = room_el.select(sel["bubble"])
        if bubbles:
            target = bubbles[-1]
    cust = _hit(target, sel.get("customer_marker"))
    pro = _hit(target, sel.get("pro_marker"))
    if cust and not pro:
        return "customer"
    if pro and not cust:
        return "pro"
    return "unknown"  # 둘 다/둘 다 아님 → 오탐 방지를 위해 알림 대상에서 제외


def parse_chat_rooms(html, sel):
    soup = BeautifulSoup(html, "html.parser")
    rooms = []
    for el in soup.select(sel["room"]):
        name = _text(el, sel.get("name"))
        last = _text(el, sel.get("last_text"))
        rid = _id_from(el, sel.get("room_id_regex"), name + last)
        rooms.append(ChatRoom(rid, name, last, last_side(el, sel)))
    return rooms


def awaiting_reply(rooms):
    """마지막 말풍선이 고객 쪽인 방(= 내가 답해야 할 방)."""
    return [r for r in rooms if r.last_side == "customer"]


# ---------- 받은 요청 ----------
@dataclass
class RequestCard:
    card_id: str
    title: str = ""
    category: str = ""
    body: str = ""
    quote_text: str = ""
    elapsed_text: str = ""
    usage_text: str = ""
    link: str = ""
    raw_text: str = ""


def parse_request_cards(html, sel):
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for el in soup.select(sel["card"]):
        title = _text(el, sel.get("title"))
        body = _text(el, sel.get("body"))
        raw = el.get_text(" ", strip=True)
        cards.append(RequestCard(
            card_id=_id_from(el, sel.get("id_regex"), title + body),
            title=title,
            category=_text(el, sel.get("category")),
            body=body,
            quote_text=_text(el, sel.get("quote_count")),
            elapsed_text=_text(el, sel.get("elapsed")),
            usage_text=_text(el, sel.get("client_usage")),
            link=el.get("href", "") if hasattr(el, "get") else "",
            raw_text=raw,
        ))
    return cards


# ---------- 5조건 판정 ----------
def parse_elapsed_minutes(text):
    """'방금 전' → 0, '12분 전' → 12, '2시간 전' → 120, '3일 전' → 4320. 모르면 None."""
    t = (text or "").strip()
    if not t:
        return None
    if "방금" in t or "금방" in t:
        return 0
    for unit, mult in (("분", 1), ("시간", 60), ("일", 1440), ("주", 10080)):
        m = re.search(r"(\d+)\s*%s\s*전" % unit, t)
        if m:
            return int(m.group(1)) * mult
    return None


def parse_quote_count(text):
    """'견적 보낸 고수 1명' → 1, '아직 없음' → 0. 모르면 None(→ 판정 보수적으로 탈락)."""
    t = (text or "").strip()
    if not t:
        return None
    m = re.search(r"(\d+)\s*명", t)
    if m:
        return int(m.group(1))
    if re.search(r"없", t):
        return 0
    return None


def parse_usage_count(text):
    m = re.search(r"이용\s*(\d+)\s*회", text or "")
    return int(m.group(1)) if m else None


@dataclass
class Verdict:
    passed: bool
    conditions: dict = field(default_factory=dict)  # 이름 -> (통과 여부, 근거)

    def summary(self):
        return " / ".join("%s %s(%s)" % ("✅" if ok else "❌", n, why)
                          for n, (ok, why) in self.conditions.items())


def judge_card(card, rules):
    """5조건을 모두 만족해야 통과. 정보를 읽지 못한 조건은 통과시키지 않는다(보수적)."""
    c = {}
    blob = " ".join([card.category, card.title, card.body])

    q = parse_quote_count(card.quote_text)
    c["견적≤%d명" % rules["max_quotes"]] = (
        q is not None and q <= rules["max_quotes"], "읽은 값=%s" % q)

    hit = [k for k in rules["video_keywords"] if k in blob]
    c["영상 편집"] = (bool(hit), "키워드=%s" % (hit[:2] or "없음"))

    found = [name for name, pats in rules["specifics"].items()
             if any(re.search(p, blob, re.I) for p in pats)]
    c["구체 정보≥%d" % rules["min_specifics"]] = (
        len(found) >= rules["min_specifics"], "발견=%s" % (found or "없음"))

    el = parse_elapsed_minutes(card.elapsed_text)
    c["%d분 이내" % rules["max_elapsed_minutes"]] = (
        el is not None and el <= rules["max_elapsed_minutes"], "경과=%s분" % el)

    usage = parse_usage_count(card.usage_text or card.raw_text)
    body_len = len((card.body or "").strip())
    ok5 = (usage is not None and usage >= rules["min_usage_count"]) or body_len >= rules["min_body_chars"]
    c["이용%d회 또는 본문%d자" % (rules["min_usage_count"], rules["min_body_chars"])] = (
        ok5, "이용=%s회, 본문=%d자" % (usage, body_len))

    return Verdict(all(ok for ok, _ in c.values()), c)
