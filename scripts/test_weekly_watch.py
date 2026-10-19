#!/usr/bin/env python3
"""API 호출을 가짜 응답으로 바꿔 보고서 파일 생성만 확인한다. 키·네트워크 불필요."""
import datetime
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly_watch as w

calls = []


def fake_call_api(api_key, prompt):
    calls.append(prompt)
    return "## 가짜 본문\n- 시험 항목 https://example.com", 1234, 567


w.call_api = fake_call_api
now = datetime.datetime(2026, 10, 19, 9, 7, tzinfo=w.KST)

with tempfile.TemporaryDirectory() as tmp:
    w.REPORT_DIR = tmp
    # 키 없음: 파일을 만들지 않고 정상 종료
    assert w.run("공고", api_key="", now=now) is None
    assert os.listdir(tmp) == []
    for kind, name in (("공고", "261019_강사공고기회.md"), ("브리핑", "261019_콘텐츠브리핑.md")):
        path = w.run(kind, api_key="test-key", now=now)
        assert os.path.basename(path) == name, path
        text = open(path, encoding="utf-8").read()
        assert "토큰 사용량: 입력 1,234 · 출력 567" in text.splitlines()[-1], text
        assert "지난주에도 있음" not in calls[-1]
    # 다음 주: 지난 보고서가 프롬프트에 들어가는지
    w.run("공고", api_key="test-key", now=now + datetime.timedelta(days=7))
    assert "지난주에도 있음" in calls[-1] and "[261019_강사공고기회.md]" in calls[-1]
    print("파일:", sorted(os.listdir(tmp)))

# 실제 HTTP 경로: pause_turn → 이어받기, 토큰 합산, 429 재시도
import io
import json
import urllib.error

w.time.sleep = lambda s: None
responses = [
    urllib.error.HTTPError("u", 429, "rate", {}, io.BytesIO(b"{}")),
    {"stop_reason": "pause_turn", "content": [{"type": "text", "text": "중간"}],
     "usage": {"input_tokens": 100, "output_tokens": 10}},
    {"stop_reason": "end_turn", "content": [{"type": "text", "text": "최종 "}, {"type": "text", "text": "본문"}],
     "usage": {"input_tokens": 200, "output_tokens": 20}},
]


class FakeResp:
    def __init__(self, d): self.b = json.dumps(d).encode()
    def read(self, *a): return self.b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_urlopen(req, timeout=0):
    r = responses.pop(0)
    if isinstance(r, Exception):
        raise r
    return FakeResp(r)


import importlib
w2 = importlib.reload(w)
w2.time.sleep = lambda s: None
w2.urllib.request.urlopen = fake_urlopen
assert w2.call_api("k", "p") == ("최종 본문", 300, 30)
print("OK: HTTP 재시도·pause_turn 이어받기·토큰 합산 확인")
print("OK: 보고서 생성·토큰 줄·지난 보고서 반영 확인")
