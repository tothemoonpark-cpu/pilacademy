#!/usr/bin/env python3
"""반려동물 SNS 세트(posts.json)의 숫자·연구 인용·의학 사실을 API로 대조해 마크다운 표로 저장한다.

흐름(글 1편 단위):
  1) Claude(claude-sonnet-5-5)가 x·threads·ig 본문에서 검증 대상 주장을 추출
  2) 연구·의학 주장은 PubMed E-utilities(esearch→efetch, 키 불필요)로 PMID·초록 수집
  3) Claude가 주장별로 확인 / 불일치 / 근거 없음 판정

사용법은 tools/README_사실검수.md 참고.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MODEL = "claude-sonnet-5-5"
POST_BUDGET_SEC = 170          # 글 1편(시도 1회)이 끝나야 하는 상한
RETRIES = 1                    # 실패한 글 재시도 횟수
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
VERDICTS = ("확인", "불일치", "근거 없음")
PLATFORMS = ("x", "threads", "ig")
MAX_ABSTRACT_CHARS = 1800

CLAIM_SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "platform": {"type": "string", "enum": list(PLATFORMS)},
            "sentence": {"type": "string"},
            "kind": {"type": "string", "enum": ["숫자", "연구", "의학"]},
            "pubmed_query": {"type": "string"},
        },
        "required": ["platform", "sentence", "kind", "pubmed_query"],
        "additionalProperties": False,
    }}},
    "required": ["claims"],
    "additionalProperties": False,
}

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "verdict": {"type": "string", "enum": list(VERDICTS)},
            "source": {"type": "string"},
            "memo": {"type": "string"},
        },
        "required": ["index", "verdict", "source", "memo"],
        "additionalProperties": False,
    }}},
    "required": ["results"],
    "additionalProperties": False,
}

EXTRACT_SYSTEM = (
    "너는 반려동물(수의학) SNS 글의 사실검수 보조자다. 글에서 검증 가능한 주장만 뽑는다: "
    "숫자·통계, 연구/논문 인용, 의학·수의학 사실. 감상·의견·일화는 제외한다. "
    "sentence는 원문 문장을 그대로 옮긴다. 같은 문장이 여러 플랫폼에 있으면 플랫폼별로 따로 적는다. "
    "kind가 연구 또는 의학이면 pubmed_query에 PubMed 검색용 영어 키워드(필요시 연도·저자·저널)를 쓰고, "
    "숫자면 빈 문자열이다."
)

JUDGE_SYSTEM = (
    "너는 수의학 사실검수자다. 주어진 주장을 PubMed 초록(있는 경우)과 대조해 판정한다. "
    "확인: 초록 또는 명확한 공인 출처가 주장을 뒷받침. 불일치: 근거와 숫자·방향·결론이 다름. "
    "근거 없음: 제공된 자료로 판단할 수 없거나 출처를 댈 수 없음. "
    "초록에 없는 내용을 추측해 '확인'으로 판정하지 않는다. 논문 근거로 확인했다면 source에 PMID를 쓰고, "
    "논문 외 공인 출처(가이드라인 등)에 기댔다면 그 이름을 쓰되 memo에 초록 대조가 아님을 밝힌다. "
    "source가 없으면 빈 문자열. memo는 한 문장, 한국어. index는 입력 주장 번호를 그대로 쓴다."
)


# ---------------------------------------------------------------- 입력

def load_posts(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("posts", data) if isinstance(data, dict) else data
    posts = []
    for i, p in enumerate(items, 1):
        texts = {}
        for k in PLATFORMS:
            v = p.get(k, "")
            if isinstance(v, list):
                v = "\n".join(str(s) for s in v)
            texts[k] = str(v).strip()
        posts.append({"no": p.get("no", p.get("id", i)), "title": p.get("title", ""), "texts": texts})
    return posts


def post_prompt(post):
    parts = [f"[글 {post['no']}] {post['title']}".strip()]
    for k in PLATFORMS:
        if post["texts"][k]:
            parts.append(f"<{k}>\n{post['texts'][k]}\n</{k}>")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- PubMed

def _get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "pilacademy-factcheck/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def _eutils(endpoint, params, timeout):
    params = dict(params, tool="pilacademy_factcheck")
    if os.environ.get("NCBI_EMAIL"):
        params["email"] = os.environ["NCBI_EMAIL"]
    time.sleep(0.4)  # 키 없이 초당 3회 제한
    return _get(f"{EUTILS}/{endpoint}?{urllib.parse.urlencode(params)}", timeout)


def pubmed_lookup(query, retmax=3, timeout=15):
    """검색어 → [{pmid,title,year,abstract}]"""
    res = json.loads(_eutils("esearch.fcgi", {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax}, timeout))
    ids = res.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    root = ET.fromstring(_eutils("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}, timeout))
    out = []
    for art in root.iter("PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID") or ""
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        year = art.findtext(".//JournalIssue/PubDate/Year") or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
        abstract = " ".join("".join(a.itertext()) for a in art.iter("AbstractText"))
        out.append({"pmid": pmid, "title": title, "year": year, "abstract": abstract[:MAX_ABSTRACT_CHARS]})
    return out


# ---------------------------------------------------------------- Claude

_client = None


def _claude():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY 환경변수가 없습니다. (--dry 로는 키 없이 구조 시험 가능)")
        import anthropic  # 지연 import: --dry 에는 SDK 불필요
        _client = anthropic.Anthropic(max_retries=0)  # 재시도는 글 단위로 직접 관리
    return _client


def call_json(system, user, schema, deadline):
    remaining = deadline - time.monotonic()
    if remaining < 5:
        raise TimeoutError("글 단위 시간 예산(170초) 소진")
    resp = _claude().messages.create(
        model=MODEL,
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        timeout=min(remaining - 2, 120),
    )
    if resp.stop_reason != "end_turn":
        raise RuntimeError(f"비정상 종료: stop_reason={resp.stop_reason}")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


# ---------------------------------------------------------------- 처리

def check_post_live(post):
    deadline = time.monotonic() + POST_BUDGET_SEC
    claims = call_json(EXTRACT_SYSTEM, post_prompt(post), CLAIM_SCHEMA, deadline)["claims"]
    if not claims:
        return []
    evidence = {}
    for i, c in enumerate(claims):
        if c["kind"] != "숫자" and c["pubmed_query"].strip() and time.monotonic() < deadline - 40:
            try:
                evidence[i] = pubmed_lookup(c["pubmed_query"])
            except Exception as e:  # PubMed 장애는 해당 주장만 근거 없음으로 흘려보낸다
                evidence[i] = [{"error": str(e)}]
    lines = []
    for i, c in enumerate(claims):
        ev = evidence.get(i)
        if ev is None:
            ev_txt = "(PubMed 조회 안 함: 숫자 주장 또는 검색어 없음)"
        elif not ev:
            ev_txt = "(PubMed 검색 결과 없음)"
        elif "error" in ev[0]:
            ev_txt = f"(PubMed 조회 오류: {ev[0]['error']})"
        else:
            ev_txt = "\n".join(f"- PMID {e['pmid']} ({e['year']}) {e['title']}\n  초록: {e['abstract'] or '(초록 없음)'}" for e in ev)
        lines.append(f"[{i}] ({c['platform']}/{c['kind']}) {c['sentence']}\n근거 후보:\n{ev_txt}")
    judged = call_json(JUDGE_SYSTEM, "\n\n".join(lines), JUDGE_SCHEMA, deadline)["results"]
    by_idx = {r["index"]: r for r in judged}
    rows = []
    for i, c in enumerate(claims):
        r = by_idx.get(i, {"verdict": "근거 없음", "source": "", "memo": "판정 결과 누락"})
        rows.append({"no": post["no"], "platform": c["platform"], "sentence": c["sentence"],
                     "verdict": r["verdict"], "source": r["source"], "memo": r["memo"]})
    return rows


def check_post_dry(post):
    """네트워크·API 없이 구조만 시험: 숫자나 '연구'가 든 문장을 뽑아 고정 판정으로 채운다."""
    rows = []
    for k in PLATFORMS:
        for s in re.split(r"(?<=[.!?。])\s+|\n+", post["texts"][k]):
            if re.search(r"\d|연구|논문|%", s):
                rows.append({"no": post["no"], "platform": k, "sentence": s.strip(),
                             "verdict": "근거 없음", "source": "", "memo": "[dry] 실제 대조 안 함"})
    return rows


def run(posts, dry):
    rows, failed = [], []
    for post in posts:
        fn = check_post_dry if dry else check_post_live
        for attempt in range(RETRIES + 1):
            try:
                got = fn(post)
                rows += got
                print(f"글 {post['no']}: 주장 {len(got)}건", file=sys.stderr)
                break
            except Exception as e:
                print(f"글 {post['no']}: 시도 {attempt + 1} 실패 - {type(e).__name__}: {e}", file=sys.stderr)
                if attempt == RETRIES:
                    failed.append(post["no"])
                    rows.append({"no": post["no"], "platform": "-", "sentence": "(글 전체)", "verdict": "미판정(오류)",
                                 "source": "", "memo": f"{type(e).__name__}: {e}"[:200]})
    return rows, failed


# ---------------------------------------------------------------- 출력

def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def to_markdown(rows, src, dry):
    cnt = {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS + ("미판정(오류)",)}
    head = [f"# 사실검수 결과 ({os.path.basename(src)})", "",
            f"- 모드: {'dry(구조 시험, 판정 무의미)' if dry else MODEL + ' + PubMed E-utilities'}",
            "- " + " / ".join(f"{k} {v}" for k, v in cnt.items() if v or k in VERDICTS), "",
            "| 글 | 플랫폼 | 주장 문장 | 검증 결과 | 근거 PMID/출처 | 메모 |", "|---|---|---|---|---|---|"]
    body = [f"| {esc(r['no'])} | {r['platform']} | {esc(r['sentence'])} | {r['verdict']} | {esc(r['source'])} | {esc(r['memo'])} |"
            for r in rows]
    return "\n".join(head + body) + "\n"


def main():
    ap = argparse.ArgumentParser(description="posts.json 사실검수 (Anthropic API + PubMed)")
    ap.add_argument("posts", help="입력 posts.json 경로")
    ap.add_argument("-o", "--out", help="출력 .md 경로 (기본: 입력파일명_사실검수.md)")
    ap.add_argument("--dry", action="store_true", help="네트워크·API 없이 구조만 시험")
    a = ap.parse_args()
    posts = load_posts(a.posts)
    rows, failed = run(posts, a.dry)
    out = a.out or os.path.splitext(a.posts)[0] + "_사실검수.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(to_markdown(rows, a.posts, a.dry))
    print(f"저장: {out} (글 {len(posts)}편, 행 {len(rows)}건, 실패 {failed or '없음'})", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
