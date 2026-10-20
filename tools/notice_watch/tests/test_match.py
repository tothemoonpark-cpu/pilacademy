# -*- coding: utf-8 -*-
"""네트워크 없이 추출·키워드 매칭·diff·인코딩 감지를 시험한다."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import notice_watch as nw

HTML = """<ul>
<li><a href="/v?id=1">[공모] 2027 글쓰기 강사 모집</a></li>
<li><a href="javascript:view(2)">직원 식당 조리원 채용</a></li>
<li><a href="#">공모</a></li>
<li><a href="/v?id=3">평생학습   <b>프로그램</b> 안내</a></li>
</ul><script>var a='<a href="x">강사 모집 스크립트</a>';</script>"""
KW = ["강사", "모집", "공모", "평생학습"]


class MatchTest(unittest.TestCase):
    def test_extract(self):
        items = nw.extract_items(HTML, "https://a.kr/list")
        titles = [t for t, _ in items]
        self.assertIn("[공모] 2027 글쓰기 강사 모집", titles)
        self.assertIn("평생학습 프로그램 안내", titles)
        self.assertNotIn("강사 모집 스크립트", titles)
        self.assertEqual(dict(items)["[공모] 2027 글쓰기 강사 모집"], "https://a.kr/v?id=1")

    def test_match_and_diff(self):
        items = nw.extract_items(HTML, "https://a.kr/list")
        new, keys = nw.find_new("테스트", items, KW, set())
        self.assertEqual(len(new), 2)
        self.assertEqual(new[0]["키워드"], ["강사", "모집", "공모"])
        new2, _ = nw.find_new("테스트", items, KW, set(keys))
        self.assertEqual(new2, [])
        items.append(("신규 독서 강사 공모", ""))
        new3, _ = nw.find_new("테스트", items, KW, set(keys))
        self.assertEqual([n["제목"] for n in new3], ["신규 독서 강사 공모"])

    def test_cp949(self):
        raw = "<html><body>강사 모집</body></html>".encode("cp949")
        self.assertEqual(nw.decode(raw, "text/html"), "<html><body>강사 모집</body></html>")
        raw2 = '<meta charset="euc-kr">강사'.encode("cp949")
        self.assertIn("강사", nw.decode(raw2))

    def test_season(self):
        src = {"계절": [3, 4]}
        self.assertTrue(nw.in_season(src, {"계절_적용": False}, 10))
        self.assertFalse(nw.in_season(src, {"계절_적용": True}, 10))
        self.assertTrue(nw.in_season(src, {"계절_적용": True}, 3))


if __name__ == "__main__":
    unittest.main()
