"""api_pipeline 공용 모듈 — 경로, HTTP, PubMed, 큐/상태 파일 도우미 (표준 라이브러리만 사용)."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PipelineError(Exception):
    pass


class Paths:
    """실제 모드는 out/, 시험 모드는 out/_test/ 에만 쓴다."""

    def __init__(self, test=False):
        self.test = test
        self.base = ROOT / "out" / ("_test" if test else "")
        self.abstracts = self.base / "abstracts"
        self.drafts = self.base / "drafts"
        self.factcheck = self.base / "factcheck"
        self.candidates = self.base / "candidates.md"
        self.state = self.base / "state.json"
        self.mock = self.base / "mock_results.jsonl"
        self.exclude = self.base / "exclude_pmids.txt" if test else ROOT / "exclude_pmids.txt"
        self.real_exclude = ROOT / "exclude_pmids.txt"

    def ensure(self):
        for d in (self.abstracts, self.drafts, self.factcheck):
            d.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(msg, flush=True)


# ---------- 키 / HTTP ----------

def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise PipelineError("환경변수 ANTHROPIC_API_KEY 가 없습니다. 실제 모드에서는 이 환경변수로만 키를 읽습니다. (키 없이 확인하려면 --test)")
    return key


def http(method, url, headers=None, data=None, retries=4, timeout=90):
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    last = None
    for i in range(retries + 1):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            last = PipelineError(f"HTTP {e.code} {method} {url.split('?')[0]} — {detail}")
            if e.code not in (429, 500, 502, 503, 529) or i == retries:
                raise last
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = PipelineError(f"연결 실패 {method} {url.split('?')[0]} — {e}")
            if i == retries:
                raise last
        time.sleep(2 ** (i + 1))
    raise last


def anthropic_headers(extra=None):
    h = {"x-api-key": get_api_key(), "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}
    h.update(extra or {})
    return h


# ---------- PubMed ----------

_last_call = [0.0]


def _eutils(endpoint, params):
    params = dict(params, tool="pilacademy_api_pipeline")
    if os.environ.get("NCBI_API_KEY"):  # 선택 사항(없어도 동작, 초당 3회 제한 준수)
        params["api_key"] = os.environ["NCBI_API_KEY"]
    gap = 0.12 if "api_key" in params else 0.4
    wait = gap - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    url = f"{EUTILS}/{endpoint}?{urllib.parse.urlencode(params)}"
    out = http("GET", url)
    _last_call[0] = time.time()
    return out


def pubmed_search(query, retmax, reldate=730):
    raw = _eutils("esearch.fcgi", {
        "db": "pubmed", "term": query, "retmax": retmax, "retmode": "json",
        "sort": "pub_date", "datetype": "pdat", "reldate": reldate,
    })
    return json.loads(raw)["esearchresult"].get("idlist", [])


def pubmed_fetch(pmids):
    if not pmids:
        return []
    raw = _eutils("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    return parse_pubmed_xml(raw)


def parse_pubmed_xml(raw):
    out = []
    for art in ET.fromstring(raw).findall(".//PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID")
        t = art.find(".//ArticleTitle")
        title = "".join(t.itertext()).strip() if t is not None else ""
        parts = []
        for at in art.findall(".//Abstract/AbstractText"):
            text = "".join(at.itertext()).strip()
            label = at.get("Label")
            parts.append(f"{label}: {text}" if label else text)
        year = (art.findtext(".//JournalIssue/PubDate/Year")
                or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
                or art.findtext(".//ArticleDate/Year") or "")
        out.append({
            "pmid": pmid, "title": title, "journal": art.findtext(".//Journal/Title") or "",
            "year": year, "abstract": "\n".join(parts),
        })
    return out


def save_abstract(paths, rec):
    paths.abstracts.mkdir(parents=True, exist_ok=True)
    (paths.abstracts / f"{rec['pmid']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")


def load_abstract(paths, pmid):
    for p in (paths.abstracts / f"{pmid}.json", ROOT / "out" / "abstracts" / f"{pmid}.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def fetch_abstract_cached(paths, pmid):
    rec = load_abstract(paths, pmid)
    if rec is None:
        got = pubmed_fetch([pmid])
        if not got:
            return None
        rec = got[0]
        save_abstract(paths, rec)
    return rec


# ---------- 제외 목록 / 풀 / 큐 / 상태 ----------

def read_exclude(paths):
    seen = set()
    for f in {paths.real_exclude, paths.exclude}:
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*(\d{4,10})\b", line)
                if m:
                    seen.add(m.group(1))
    return seen


def append_exclude(paths, pmids, note):
    have = read_exclude(paths)
    new = [p for p in pmids if p not in have]
    if not new:
        return 0
    paths.exclude.parent.mkdir(parents=True, exist_ok=True)
    if not paths.exclude.exists():
        paths.exclude.write_text("", encoding="utf-8")
    with paths.exclude.open("a", encoding="utf-8") as f:
        for p in new:
            f.write(f"{p}  # {note}\n")
    return len(new)


def load_pool(paths):
    pool = []
    if paths.abstracts.exists():
        for p in paths.abstracts.glob("*.json"):
            pool.append(json.loads(p.read_text(encoding="utf-8")))
    pool.sort(key=lambda r: (r.get("added", ""), r["pmid"]))
    return pool


def load_queue(path):
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8"))


def load_state(paths):
    if paths.state.exists():
        return json.loads(paths.state.read_text(encoding="utf-8"))
    return {"batches": [], "submitted_pmids": []}


def save_state(paths, state):
    paths.state.parent.mkdir(parents=True, exist_ok=True)
    paths.state.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- 초안 md ----------

def draft_path(paths, pmid, kind):
    return paths.drafts / str(pmid) / f"{kind}.md"


def split_front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


def today():
    return date.today().isoformat()


def run_main(fn):
    try:
        sys.exit(fn() or 0)
    except PipelineError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(2)
