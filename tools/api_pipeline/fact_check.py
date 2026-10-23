#!/usr/bin/env python3
"""4) 사실검수기 — 초안의 숫자·약 이름·용량·연구 주장을 PubMed 초록 원문과 대조해 어긋난 곳만 목록으로 만든다.

기본 검사(API 불필요, 결정적):
  숫자 — 초안의 숫자가 초록에 없으면 표시.  용량 — '숫자+단위' 조합이 초록에 없으면 표시.
  약 이름 — drug_terms.txt·영문 약 접미사에 걸리는 이름이 초록에 없으면 표시.
  강한 단정 — 관찰·설문 연구인데 '증명·입증' 같은 단정 표현이 있으면 표시.
선택 검사: --llm  초안의 연구 주장 문장을 Claude 가 초록과 대조(동기 Messages API 호출, ANTHROPIC_API_KEY 필요).
시험 모드: --test  → 내장 시험 문서로 탐지·비탐지를 검증하고 out/_test/ 의 시험 초안도 검사한다(API 호출 없음).
"""
import argparse
import json
import re
from decimal import Decimal, InvalidOperation

from common import (API_BASE, ROOT, Paths, PipelineError, anthropic_headers, fetch_abstract_cached, http,
                    load_queue, log, run_main, split_front_matter, today)

NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
UNITS = r"mg/kg|mcg/kg|μg/kg|µg/kg|mg|mcg|μg|µg|ml|IU|kg|㎎|㎖|밀리그램|마이크로그램|밀리리터|cc|g"
DOSE_RE = re.compile(rf"(\d+(?:,\d{{3}})*(?:\.\d+)?)\s*({UNITS})(?![A-Za-z])", re.I)
UNIT_CANON = {"㎎": "mg", "밀리그램": "mg", "μg": "mcg", "µg": "mcg", "마이크로그램": "mcg", "㎖": "ml", "밀리리터": "ml",
              "cc": "ml", "μg/kg": "mcg/kg", "µg/kg": "mcg/kg"}
DRUG_SUFFIX = re.compile(r"\b[a-z]{4,}(?:cillin|mycin|oxacin|azole|pril|sartan|olol|statin|caine|barbital|profen|coxib|"
                         r"zepam|zolam|pram|tine|zine|mab|nib|dipine|idone|afil|sone|solone)\b", re.I)
STRONG = ["증명", "입증", "확정했", "원인이 됩니다", "원인입니다", "완치", "반드시", "100%", "틀림없"]
WEAK_DESIGN = re.compile(r"cross-sectional|survey|questionnaire|observational|retrospective|associat|correlat|interview", re.I)
RCT = re.compile(r"randomi[sz]ed|placebo|controlled trial", re.I)


def norm_num(tok):
    try:
        d = Decimal(tok.replace(",", ""))
    except InvalidOperation:
        return tok
    return format(d.normalize(), "f")


def dose_key(num, unit):
    u = UNIT_CANON.get(unit, UNIT_CANON.get(unit.lower(), unit.lower()))
    return f"{norm_num(num)}{u}"


def abstract_sets(abstract):
    nums = {norm_num(t) for t in NUM_RE.findall(abstract)}
    doses = {dose_key(n, u) for n, u in DOSE_RE.findall(abstract)}
    return nums, doses


def clean_line(line):
    line = re.sub(r"https?://\S+", " ", line)
    line = re.sub(r"PMID\s*\d+", " ", line, flags=re.I)
    line = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", line)            # 타임코드
    line = re.sub(r"#\S+", " ", line)                                     # 해시태그
    line = re.sub(r"^[#>\s\-\*\[\(]*\d+\s*/\s*\d+\b", " ", line)          # 줄머리 순번 1/9
    line = re.sub(r"\(\d+\s*/\s*\d+\)", " ", line)
    line = re.sub(r"^\s*\d+[.)]\s", " ", line)                            # 목록 번호
    return line


def load_drugs():
    groups = []
    for ln in (ROOT / "drug_terms.txt").read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.startswith("#"):
            groups.append([t.strip().lower() for t in ln.split("|") if t.strip()])
    return groups


def check_draft(body, rec):
    """어긋난 곳 목록 [(줄번호, 구분, 문장 일부, 이유)] 을 돌려준다."""
    abstract = rec["abstract"]
    a_low = abstract.lower()
    a_nums, a_doses = abstract_sets(abstract)
    allowed = {norm_num(str(rec["pmid"])), norm_num(str(rec.get("year") or "x"))}
    drugs = load_drugs()
    found = []
    for no, raw in enumerate(body.splitlines(), 1):
        line = clean_line(raw)
        snippet = raw.strip()[:70]
        spans = []
        for m in DOSE_RE.finditer(line):
            spans.append(m.span())
            key = dose_key(m.group(1), m.group(2))
            if key not in a_doses:
                why = "초록에 같은 숫자는 있으나 단위·조합이 다릅니다" if norm_num(m.group(1)) in a_nums else "초록에 없는 용량입니다"
                found.append((no, "용량", snippet, f"'{m.group(0)}' — {why}"))
        rest = "".join(c if not any(s <= i < e for s, e in spans) else " " for i, c in enumerate(line))
        for tok in NUM_RE.findall(rest):
            n = norm_num(tok)
            if n not in a_nums and n not in allowed:
                found.append((no, "숫자", snippet, f"'{tok}' 가 초록에 없습니다"))
        low = raw.lower()
        for g in drugs:
            if any(t in low for t in g) and g[0] not in a_low:
                found.append((no, "약 이름", snippet, f"'{g[0]}' 이(가) 초록에 없습니다"))
        for w in DRUG_SUFFIX.findall(raw):
            if w.lower() not in a_low and not any(w.lower() in f[3].lower() for f in found if f[0] == no):
                found.append((no, "약 이름", snippet, f"'{w}' 이(가) 초록에 없습니다(영문 약 접미사 규칙)"))
        if WEAK_DESIGN.search(abstract) and not RCT.search(abstract):
            for w in STRONG:
                if w in raw:
                    found.append((no, "강한 단정", snippet, f"관찰·설문 연구인데 '{w}' 표현을 썼습니다"))
    return found


def parse_llm_claims(text):
    a, b = text.find("["), text.rfind("]")
    if a < 0 or b < a:
        raise PipelineError("LLM 검수 응답에서 JSON 목록을 찾지 못했습니다.")
    return [c for c in json.loads(text[a:b + 1]) if isinstance(c, dict) and c.get("quote")]


def llm_check(body, rec, model):
    system = ("당신은 논문 초록과 초안을 대조하는 사실검수자입니다. 초안에서 연구 결과·연구 대상·연구 설계에 관한 문장 중 "
              "초록과 어긋나거나 초록에 근거가 없는 것만 골라 JSON 목록으로만 답합니다. "
              '형식: [{"quote": "초안 문장", "issue": "어긋난 이유"}]. 어긋남이 없으면 []. 설명·머리말 금지.')
    user = f"[논문 초록]\n{rec['abstract']}\n\n[초안]\n{body}"
    resp = json.loads(http("POST", f"{API_BASE}/messages", anthropic_headers(), {
        "model": model, "max_tokens": 1500, "temperature": 0, "system": system,
        "messages": [{"role": "user", "content": user}]}))
    return parse_llm_claims("".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text"))


def run(paths, pmid=None, use_llm=False, model=None, fetch=True):
    paths.ensure()
    files = sorted(paths.drafts.glob(f"{pmid or '*'}/*.md"))
    sections, total, checked = [], 0, 0
    for f in files:
        meta, body = split_front_matter(f.read_text(encoding="utf-8"))
        if body.lstrip().startswith("[작성 보류]"):
            continue
        rec = fetch_abstract_cached(paths, meta["pmid"]) if fetch else None
        if rec is None:
            sections.append(f"## {f.relative_to(paths.drafts)}\n- 초록을 받지 못해 검사하지 못했습니다.\n")
            continue
        checked += 1
        issues = [(n, k, s, w) for n, k, s, w in check_draft(body, rec)]
        if use_llm:
            for c in llm_check(body, rec, model):
                issues.append((0, "연구 주장", c["quote"][:70], c.get("issue", "")))
        if meta.get("stop_reason") == "max_tokens":
            issues.append((0, "잘림", "", "분량 한도에서 끊긴 초안입니다"))
        if issues:
            total += len(issues)
            rows = "\n".join(f"- {('줄 ' + str(n)) if n else '전체'} · **{k}** · {w}" + (f"\n  - `{s}`" if s else "") for n, k, s, w in issues)
            sections.append(f"## {f.relative_to(paths.drafts)} (PMID {meta['pmid']} · https://pubmed.ncbi.nlm.nih.gov/{meta['pmid']}/)\n{rows}\n")
    head = f"# 사실검수 보고 ({today()})\n\n검사 {checked}편 · 어긋난 곳 {total}건 (어긋난 곳만 적습니다)\n"
    body_md = head + ("\n" + "\n".join(sections) if sections else "\n어긋난 곳이 없습니다.\n")
    out = paths.factcheck / f"report_{today()}.md"
    out.write_text(body_md, encoding="utf-8")
    log(f"검사 {checked}편, 어긋난 곳 {total}건 → {out}")
    return total, out


def selftest(paths):
    rec = {"pmid": "1", "year": "2024", "abstract":
           "In this cross-sectional survey of 120 dog owners, 23.5% reported grief. Carprofen use was rare."}
    clean = "### 1/2\n120명의 보호자를 설문한 연구입니다. 23.5%가 슬픔을 보고했습니다. 카프로펜 사용은 드물었습니다. #펫로스\n출처: J, 2024, PMID 1"
    bad = "37.5%가 달라졌습니다.\n가바펜틴 5mg/kg을 쓰면 됩니다.\n120mg 이 연구가 증명했습니다.\nmeloxicam 보다 낫습니다."
    assert check_draft(clean, rec) == [], check_draft(clean, rec)
    kinds = {(k, w.split("'")[1]) for _, k, _, w in check_draft(bad, rec)}
    expect = {("숫자", "37.5"), ("용량", "5mg/kg"), ("약 이름", "gabapentin"), ("용량", "120mg"),
              ("강한 단정", "증명"), ("약 이름", "meloxicam")}
    assert expect <= kinds, f"탐지 누락: {expect - kinds}"
    assert parse_llm_claims('설명 [{"quote":"a","issue":"b"}] 끝')[0]["quote"] == "a"
    assert parse_llm_claims("[]") == []
    log("내장 시험 통과: 정상 문서 0건, 틀린 문서에서 숫자·용량·약 이름·단정 6종 모두 탐지, LLM 응답 파서 정상")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", default="queue.json")
    ap.add_argument("--test", action="store_true", help="시험 모드: 내장 시험 + out/_test 초안 검사")
    ap.add_argument("--llm", action="store_true", help="연구 주장 대조를 Claude 로 추가 수행(유료 호출)")
    ap.add_argument("--pmid", help="이 PMID 의 초안만 검사")
    a = ap.parse_args()
    paths = Paths(a.test)
    if a.test:
        selftest(paths)
    run(paths, a.pmid, a.llm and not a.test, load_queue(a.queue)["model"])


if __name__ == "__main__":
    run_main(main)
