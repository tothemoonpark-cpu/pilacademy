#!/bin/bash
# ============================================================
# 박근필성장연구소 전체 사이트 무결성 체크
# 모든 작업 전·후 반드시 실행
# ============================================================

OK=0; FAIL=0
check() {
  local label="$1"; local file="$2"; local pattern="$3"; local min="$4"
  local count=$(grep -c "$pattern" "$file" 2>/dev/null || echo 0)
  if [ "$count" -ge "$min" ]; then
    echo "✅ $label: ${count}건"
    OK=$((OK+1))
  else
    echo "❌ $label: ${count}건 (최소 ${min}건 필요) ← 누락!"
    FAIL=$((FAIL+1))
  fi
}

echo "====== 박근필성장연구소 전체 사이트 무결성 체크 ======"
echo ""

# ── author.html ─────────────────────────────────────────────
echo "[author.html - 소장이력]"
check "트레바리" /mnt/project/author.html "trevari" 1
check "부산시청소년자립지원관" /mnt/project/author.html "자립지원관" 1
check "두피디아" /mnt/project/author.html "Doopedia" 1
check "계양중" /mnt/project/author.html "계양중" 1
check "부산시청강연" /mnt/project/author.html "1cA7WuT" 1

echo ""
echo "[author.html - 인터뷰]"
check "뉴스테이션인터뷰" /mnt/project/author.html "7380" 1
check "뉴스앤잡인터뷰" /mnt/project/author.html "32467" 1
check "한국강사신문인터뷰" /mnt/project/author.html "197706" 1
check "커리어온인터뷰" /mnt/project/author.html "473344" 1
check "미디어파인인터뷰" /mnt/project/author.html "75486" 1
check "대한민국교육인터뷰" /mnt/project/author.html "390683" 1
check "뉴스클레임인터뷰" /mnt/project/author.html "3056718" 1
check "BookNews인터뷰" /mnt/project/author.html "booknews" 1
check "SLICE인터뷰" /mnt/project/author.html "myslice" 1
check "월간리더스인터뷰" /mnt/project/author.html "kleadersforum" 1
check "CEO저널인터뷰" /mnt/project/author.html "ceojhn" 1

echo ""
echo "[author.html - 칼럼 29개 매체]"
check "한국인공지능신문" /mnt/project/author.html "k-ainews" 1
check "뉴스테이션칼럼" /mnt/project/author.html "7442" 1
check "한국강사신문칼럼" /mnt/project/author.html "200825" 1
check "학생과청소년" /mnt/project/author.html "3736" 1
check "출판교육문화뉴스" /mnt/project/author.html "editbiznews" 1
check "캐어유뉴스" /mnt/project/author.html "9407" 1
check "호남교육신문" /mnt/project/author.html "252501" 1
check "코스미안뉴스" /mnt/project/author.html "cosmiannews" 1
check "미디어파인칼럼" /mnt/project/author.html "75653" 1
check "이로운넷" /mnt/project/author.html "eroun.net" 1
check "아웃소싱타임즈" /mnt/project/author.html "outsourcing.co.kr" 1
check "PPSS" /mnt/project/author.html "ppss.kr" 1
check "뉴스후플러스" /mnt/project/author.html "newswhoplus" 1
check "이모작뉴스" /mnt/project/author.html "emozak" 1
check "독서신문" /mnt/project/author.html "readersnews" 1
check "커리어온칼럼" /mnt/project/author.html "475494" 1
check "키즈맘" /mnt/project/author.html "kizmom" 1
check "경인미래교육신문" /mnt/project/author.html "ki-edu" 1
check "더에듀" /mnt/project/author.html "te.co.kr" 1
check "경인열린신문" /mnt/project/author.html "kiyln" 1
check "교육플러스" /mnt/project/author.html "edpl.co.kr" 1
check "뉴스프리존" /mnt/project/author.html "newsfreezone" 1
check "대한민국교육칼럼" /mnt/project/author.html "395878" 1
check "뉴스클레임칼럼" /mnt/project/author.html "3057134" 1
check "뉴스앤잡칼럼" /mnt/project/author.html "32725" 1
check "에듀진" /mnt/project/author.html "edujin" 1
check "데일리개원" /mnt/project/author.html "dailygaewon" 1
check "데일리벳" /mnt/project/author.html "dailyvet" 1
check "한국독서교육신문" /mnt/project/author.html "readingnews" 1

echo ""
echo "[author.html - JS 렌더링 구조]"
check "history-activities" /mnt/project/author.html "history-activities" 1
check "history-interviews" /mnt/project/author.html "history-interviews" 1
check "column-section-3" /mnt/project/author.html "column-section-3" 1
check "columnData" /mnt/project/author.html "columnData" 1
check "historyData" /mnt/project/author.html "historyData" 1

echo ""
echo "── newsletter.html ─────────────────────────────────────"
check "필레터1호" /mnt/project/newsletter.html "필레터 정규 1호" 1
check "필레터5호" /mnt/project/newsletter.html "필레터 정규 5호" 1
check "필레터10호" /mnt/project/newsletter.html "필레터 정규 10호" 1
check "필레터15호" /mnt/project/newsletter.html "필레터 정규 15호" 1
check "필레터16호" /mnt/project/newsletter.html "필레터 정규 16호" 1
check "필레터18호" /mnt/project/newsletter.html "필레터 정규 18호" 1
check "필레터19호" /mnt/project/newsletter.html "필레터 정규 19호" 1
check "필레터20호" /mnt/project/newsletter.html "필레터 정규 20호" 1
check "newsletter-manifest" /mnt/project/newsletter.html "newsletterManifest" 1

echo ""
echo "── philbook.html ───────────────────────────────────────"
check "필북4기" /mnt/project/philbook.html "필북 4기" 1
check "필북5기" /mnt/project/philbook.html "필북 5기" 1
check "필북6기" /mnt/project/philbook.html "필북 6기" 1
check "필북신청마감" /mnt/project/philbook.html "신청_마감" 1

echo ""
echo "── index.html ──────────────────────────────────────────"
check "독저팅섹션" /mnt/project/index.html "id=\"dokjeoting\"" 1
check "VOD섹션" /mnt/project/index.html "id=\"vod\"" 1
check "필북섹션" /mnt/project/index.html "id=\"philbook\"" 1
check "필레터섹션" /mnt/project/index.html "newsletter" 1
check "피플인사이트섹션" /mnt/project/index.html "people-insight" 1
check "저서섹션" /mnt/project/index.html "id=\"books\"" 1
check "필북6기마감" /mnt/project/index.html "신청_마감" 1

echo ""
echo "── books.html ──────────────────────────────────────────"
check "저서1(수의사니까)" /mnt/project/books.html "book1.jpg" 1
check "저서2(두번출근)" /mnt/project/books.html "book2.jpg" 1
check "저서3(마흔)" /mnt/project/books.html "book3.jpg" 1
check "저서4(방구석)" /mnt/project/books.html "book4.jpg" 1

echo ""
echo "── vod.html ────────────────────────────────────────────"
check "VOD미리보기1" /mnt/project/vod.html "preview1Container" 1
check "VOD미리보기2" /mnt/project/vod.html "preview2Container" 1
check "VOD미리보기3" /mnt/project/vod.html "preview3Container" 1
check "VOD미리보기4" /mnt/project/vod.html "preview4Container" 1
check "VOD미리보기5" /mnt/project/vod.html "preview5Container" 1

echo ""
echo "── dokjeoting.html ─────────────────────────────────────"
check "독저팅소개" /mnt/project/dokjeoting.html "독저팅" 1
check "독저팅신청" /mnt/project/dokjeoting.html "contact\|신청\|kakao" 1

echo ""
echo "── people-insight.html ─────────────────────────────────"
check "피플인사이트유튜브" /mnt/project/people-insight.html "PL9gDAK_kh9BJl6wyOhDCvexqOSXNTKitH" 1
check "피플인사이트소개" /mnt/project/people-insight.html "매월 한 분" 1

echo ""
echo "── phillife.html ───────────────────────────────────────"
check "필라이프소개" /mnt/project/phillife.html "필라이프" 1
check "필라이프코칭" /mnt/project/phillife.html "코칭" 1

echo ""
echo "── notice.html ─────────────────────────────────────────"
check "공지1번" /mnt/project/notice.html "notice-item" 4
check "오픈카카오" /mnt/project/notice.html "open.kakao" 1

echo ""
echo "======================================================"
echo "✅ 정상: ${OK}건 / ❌ 누락: ${FAIL}건"
if [ "$FAIL" -gt "0" ]; then
  echo "⚠️  누락 항목 발견! 즉시 복구 필요."
else
  echo "🎉 전체 이상 없음."
fi
echo "======================================================"
