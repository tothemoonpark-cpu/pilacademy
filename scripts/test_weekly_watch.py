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
    assert w.run("공고", api_key="", now=now) is None or os.environ.get("ANTHROPIC_API_KEY")
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
print("OK: 보고서 생성·토큰 줄·지난 보고서 반영 확인")
