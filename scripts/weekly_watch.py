#!/usr/bin/env python3
"""주간 감시·브리핑: Anthropic Messages API + web_search 로 보고서를 만든다.

사용법: python scripts/weekly_watch.py 공고|브리핑
표준 라이브러리만 사용한다. 비밀값은 환경변수 ANTHROPIC_API_KEY 로만 받는다.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5-5"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 15}
MAX_CONTINUES = 6
KST = datetime.timezone(datetime.timedelta(hours=9))

REPORT_DIR = os.environ.get(
    "REPORT_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "weekly"),
)

RULES = (
    "규칙: 사실·마감일·주소(URL)는 웹 검색 결과에 실제로 나온 것만 쓰고, "
    "검색 결과에서 확인되지 않는 항목은 추측하지 말고 「확인 필요」라고 적는다. "
    "출처 주소가 없는 항목은 넣지 않는다. 한국어 마크다운으로, 군더더기 없이 쓴다."
)

KINDS = {
    "공고": {
        "file": "강사공고기회",
        "title": "강사 공고·기회 감시",
        "task": (
            "오늘 날짜는 {today}(한국시간)다. 아래 두 부분을 웹 검색으로 조사해 보고서를 쓴다.\n\n"
            "## (가) 강사 공고\n"
            "국민연금공단 전문강사, 그리고 도서관·평생학습관·교육청의 외부 강사 모집 중 "
            "주제가 진로·독서·글쓰기·펫로스인 것. 마감일이 오늘부터 2주(14일) 이상 남은 공고만 넣는다. "
            "마감일이 확인되지 않으면 「마감일 확인 필요」로 표시하고 따로 모은다. "
            "항목마다: 기관, 공고명, 마감일, 주제, 주소.\n\n"
            "## (나) 기회\n"
            "반려동물·펫로스·진로독서와 관련된 공모, 기고(칼럼) 모집, 방송 출연 모집. "
            "항목마다: 주최, 내용, 마감일, 주소.\n\n"
            "해당 항목이 없으면 「이번 주 해당 없음」이라고 쓴다."
        ),
    },
    "브리핑": {
        "file": "콘텐츠브리핑",
        "title": "콘텐츠 브리핑",
        "task": (
            "오늘 날짜는 {today}(한국시간)다. 지난 7일 안에 나온 반려동물 건강 관련 연구·뉴스 중 "
            "숏폼 영상과 블로그 글의 소재가 될 만한 것 5개를 웹 검색으로 골라 보고서를 쓴다. "
            "항목마다: 소재 제목, 한두 문장 요약, 숏폼으로 풀 한 줄 아이디어, 출처 주소(필수). "
            "출처 주소가 없거나 발행일이 지난 7일 밖이면 넣지 않는다. 5개를 못 채우면 채운 만큼만 쓰고 이유를 적는다."
        ),
    },
}


def previous_reports(kind_file, today_stamp, limit=2, cap=6000):
    """같은 종류의 지난 보고서(오늘 것 제외) 최근 limit개 본문."""
    try:
        names = sorted(
            n for n in os.listdir(REPORT_DIR)
            if n.endswith(f"_{kind_file}.md") and not n.startswith(today_stamp)
        )
    except FileNotFoundError:
        return ""
    chunks = []
    for name in names[-limit:]:
        with open(os.path.join(REPORT_DIR, name), encoding="utf-8") as f:
            chunks.append(f"[{name}]\n{f.read()[:cap]}")
    return "\n\n".join(chunks)


def build_prompt(kind, today, prev):
    spec = KINDS[kind]
    parts = [spec["task"].format(today=today), RULES]
    if prev:
        parts.append(
            "아래는 지난 보고서다. 여기에 이미 있는 공고·기회는 상세 내용을 다시 쓰지 말고 "
            "제목 뒤에 「(지난주에도 있음)」만 붙인다.\n\n" + prev
        )
    parts.append(
        "응답은 보고서 본문만 쓴다. 맨 위 제목 줄과 토큰 사용량 줄은 쓰지 않는다(시스템이 붙인다)."
    )
    return "\n\n".join(parts)


def call_api(api_key, prompt):
    """Messages API 호출. pause_turn 이면 이어서 호출. (본문, 입력토큰, 출력토큰) 반환."""
    messages = [{"role": "user", "content": prompt}]
    in_tok = out_tok = 0
    for _ in range(MAX_CONTINUES + 1):
        body = json.dumps({
            "model": MODEL,
            "max_tokens": 16000,
            "tools": [WEB_SEARCH_TOOL],
            "messages": messages,
        }).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=body, method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"API 오류 {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
        usage = data.get("usage", {})
        in_tok += usage.get("input_tokens", 0)
        out_tok += usage.get("output_tokens", 0)
        if data.get("stop_reason") == "pause_turn":
            messages.append({"role": "assistant", "content": data["content"]})
            continue
        text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        if data.get("stop_reason") == "refusal" and not text.strip():
            raise RuntimeError("모델이 응답을 거절했습니다(refusal).")
        return text.strip(), in_tok, out_tok
    raise RuntimeError("pause_turn 이어받기 횟수를 초과했습니다.")


def run(kind, api_key=None, now=None):
    """보고서를 만들어 저장하고 경로를 반환. 키가 없으면 None."""
    api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("키 없음: ANTHROPIC_API_KEY 가 설정되지 않아 보고서를 만들지 않고 정상 종료합니다.")
        return None
    spec = KINDS[kind]
    now = now or datetime.datetime.now(KST)
    stamp = now.strftime("%y%m%d")
    today = now.strftime("%Y-%m-%d")
    prev = previous_reports(spec["file"], stamp)
    text, in_tok, out_tok = call_api(api_key, build_prompt(kind, today, prev))
    report = (
        f"# {spec['title']} ({today})\n\n{text}\n\n---\n"
        f"토큰 사용량: 입력 {in_tok:,} · 출력 {out_tok:,} (모델 {MODEL})\n"
    )
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"{stamp}_{spec['file']}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"저장: {path}")
    return path


def main(argv):
    if len(argv) != 2 or argv[1] not in KINDS:
        print(f"사용법: weekly_watch.py {'|'.join(KINDS)}", file=sys.stderr)
        return 2
    try:
        run(argv[1])
    except RuntimeError as e:
        print(f"실패: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
