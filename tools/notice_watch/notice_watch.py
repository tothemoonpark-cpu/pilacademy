# -*- coding: utf-8 -*-
"""공고 감시기 (AI 없음, 표준 라이브러리만).

흐름: 설정 읽기 → 소스별 GET/POST → 본문에서 링크 항목 추출 → 키워드 매칭
      → state.json 과 비교해 새 항목만 결과 파일 맨 위에 추가 → 윈도우 토스트.
Windows 작업 스케줄러에서 `python notice_watch.py` 한 줄로 돈다.
"""
import concurrent.futures as cf
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config", "sources.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) notice_watch/1.0"


# ---------- 가져오기 ----------
def detect_charset(raw, header_ct=""):
    """응답 헤더 → meta → utf-8 시도 → cp949 순으로 인코딩을 정한다."""
    m = re.search(r"charset=([\w-]+)", header_ct or "", re.I)
    if m:
        return m.group(1)
    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:4096], re.I)
    if m:
        return m.group(1).decode("ascii", "ignore")
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp949"


def decode(raw, header_ct=""):
    cs = detect_charset(raw, header_ct)
    if cs.lower() in ("euc-kr", "ks_c_5601-1987"):
        cs = "cp949"
    try:
        return raw.decode(cs, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def fetch(url, timeout, data=None):
    """GET(data 없음) 또는 POST(data=dict). 본문 문자열을 돌려준다."""
    body = urllib.parse.urlencode(data).encode("ascii") if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return decode(r.read(2_000_000), r.headers.get("Content-Type", ""))


# ---------- 추출·매칭 ----------
def extract_items(page, base_url=""):
    """HTML 에서 (제목, 링크) 목록을 뽑는다. 링크 없는 목록은 제목 텍스트만."""
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    items = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", page):
        title = clean(m.group(2))
        if len(title) < 4:
            continue
        h = re.search(r"""href\s*=\s*["']([^"']*)["']""", m.group(1), re.I)
        href = h.group(1).strip() if h else ""
        if href.lower().startswith("javascript") or href.startswith("#"):
            href = ""
        items.append((title, urllib.parse.urljoin(base_url, html.unescape(href)) if href else ""))
    return items


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip()


def match_keywords(title, keywords):
    return [k for k in keywords if k and k in title]


def item_key(source_name, title, link):
    return hashlib.sha1(f"{source_name}|{title}|{link}".encode("utf-8")).hexdigest()[:16]


def find_new(source_name, items, keywords, seen):
    """키워드에 걸린 항목 중 seen 에 없는 것만 반환. (새 항목, 걸린 전체 키 목록)"""
    hits, keys, new = set(), [], []
    for title, link in items:
        kw = match_keywords(title, keywords)
        if not kw:
            continue
        key = item_key(source_name, title, link)
        if key in hits:
            continue
        hits.add(key)
        keys.append(key)
        if key not in seen:
            new.append({"제목": title, "링크": link, "키워드": kw})
    return new, keys


def in_season(src, settings, month):
    if not settings.get("계절_적용"):
        return True
    months = src.get("계절")
    return not months or month in months


# ---------- 소스 처리 ----------
def check_source(src, settings):
    """한 소스에서 (키워드에 걸린 항목 목록)을 얻는다. 실패하면 예외."""
    timeout = settings.get("타임아웃_초", 15)
    keywords = list(settings.get("공통키워드", [])) + list(src.get("추가키워드", []))
    url = src.get("url")
    items = []
    if src.get("방식", "GET").upper() == "POST":
        # 검색어마다 POST. 하나라도 성공하면 사용, 모두 실패하면 GET 목록으로 되돌아간다.
        post_url = src.get("post_url") or url
        ok = False
        if post_url and src.get("검색파라미터"):
            for term in src.get("검색어", []):
                form = dict(src.get("폼", {}))
                form[src["검색파라미터"]] = term
                try:
                    items += extract_items(fetch(post_url, timeout, form), post_url)
                    ok = True
                except Exception:
                    break
        if ok:
            keywords += src.get("검색어", [])
        elif not url:
            raise RuntimeError("POST 실패, GET url 없음")
        else:
            items = extract_items(fetch(url, timeout), url)
    else:
        items = extract_items(fetch(url, timeout), url)
    return items, keywords


def run_source(src, settings):
    items, keywords = check_source(src, settings)
    return items, keywords


# ---------- 결과·상태 ----------
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def render_block(now, new_by_source, failed, baseline):
    lines = [f"## {now:%Y-%m-%d %H:%M} 실행", ""]
    for name, items in new_by_source.items():
        lines.append(f"### {name}")
        for it in items:
            link = f" — {it['링크']}" if it["링크"] else ""
            lines.append(f"- {it['제목']}{link}  `{', '.join(it['키워드'])}`")
        lines.append("")
    for name in baseline:
        lines.append(f"- 첫 확인(기준선 저장, 알림 없음): {name}")
    for name in failed:
        lines.append(f"- 확인 실패: {name}")
    return "\n".join(lines).rstrip() + "\n\n"


def prepend_result(path, block):
    """제목 줄 아래, 기존 기록 맨 위에 새 블록을 끼워 넣는다."""
    head = "# 새 공고 감시 결과\n\n"
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
        if old.startswith(head):
            old = old[len(head):]
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + block + old)


def toast(title, msg):
    """PowerShell WinRT 토스트. Windows 가 아니면 조용히 건너뛴다."""
    if os.name != "nt":
        return
    esc = lambda s: html.escape(s, quote=True).replace("'", "''")
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null;"
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f"$x.LoadXml('<toast><visual><binding template=\"ToastText02\"><text id=\"1\">{esc(title)}</text><text id=\"2\">{esc(msg)}</text></binding></visual></toast>');"
        "$t = New-Object Windows.UI.Notifications.ToastNotification $x;"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($t)"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=20,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


# ---------- 메인 ----------
def main():
    cfg = load_json(CONFIG, None)
    if not cfg:
        print("설정을 읽지 못했습니다:", CONFIG)
        return 1
    settings = cfg.get("설정", {})
    now = datetime.datetime.now()
    result_path = os.path.join(BASE, settings.get("결과파일", "_notice_watch_새공고.md"))
    state_path = os.path.join(BASE, settings.get("상태파일", "state.json"))
    state = load_json(state_path, {})

    targets = [s for s in cfg.get("소스", [])
               if s.get("url") and s.get("사용", True) and in_season(s, settings, now.month)]
    new_by_source, failed, baseline = {}, [], []

    pool = cf.ThreadPoolExecutor(max_workers=settings.get("동시_접속", 6))
    futs = {pool.submit(run_source, s, settings): s for s in targets}
    done = set()
    try:
        for fut in cf.as_completed(futs, timeout=settings.get("전체_제한_초", 100)):
            done.add(fut)
            src = futs[fut]
            name = src["이름"]
            try:
                items, keywords = fut.result()
            except Exception:
                failed.append(name)
                continue
            first = name not in state
            new, keys = find_new(name, items, keywords, set(state.get(name, [])))
            # 사라진 항목이 다시 올라와도 새 공고로 보지 않도록 기존 키를 합친다.
            state[name] = sorted(set(state.get(name, [])) | set(keys))
            if first and not settings.get("첫실행_알림"):
                baseline.append(name)
            elif new:
                new_by_source[name] = new
    except cf.TimeoutError:
        pass
    for fut, src in futs.items():
        if fut not in done:
            failed.append(src["이름"])
    pool.shutdown(wait=False, cancel_futures=True)

    if new_by_source or failed or baseline:
        prepend_result(result_path, render_block(now, new_by_source, failed, baseline))
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    total = sum(len(v) for v in new_by_source.values())
    if total and settings.get("토스트", True):
        names = ", ".join(list(new_by_source)[:3])
        toast(f"새 공고 {total}건", names)
    print(f"새 공고 {total}건, 실패 {len(failed)}곳, 기준선 {len(baseline)}곳")
    sys.stdout.flush()
    os._exit(0)  # 시간 초과로 남은 접속 스레드가 있어도 바로 종료


if __name__ == "__main__":
    sys.exit(main())
