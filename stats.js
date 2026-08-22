/* ============================================================
   박근필성장연구소 — 사이트 수치 단일 소스 (Single Source of Truth)
   ------------------------------------------------------------
   ⛔ 수치는 반드시 이 파일에서만 관리한다.
      각 페이지에 숫자를 직접 적지 말 것 (표류 사고 재발 방지).

   [사용법]
   1) 페이지 <head> 또는 </body> 앞에 넣는다:
        <script src="stats.js"></script>
   2) 숫자를 넣고 싶은 자리에 span을 둔다:
        <span data-stat="schools"></span>개교
        <span data-stat="books"></span>권
      → 페이지가 열릴 때 자동으로 채워진다.

   [학교 수는 자동 집계된다]
   아래 SCHOOL_HISTORY에 강연을 한 줄 추가하면
   사이트 전체의 "N개교"가 스스로 올라간다. 수동 수정 불필요.
     · (예정) 표기 항목 = 완료 수에서 자동 제외
     · 같은 학교 재방문 = 자동 중복 제거
     · 학교가 아닌 기관(자립지원관 등) = isSchool:false로 제외

   근거: 2026-08-08. 이전에는 수치가 6개 파일 18곳에 흩어져 있었고
        author.html이 "37개교"로 낡은 채 방치돼 있었다.
   ============================================================ */

(function (global) {
  'use strict';

  /* ── 1. 강연 이력 (학교 수 자동 집계의 원천) ───────────────
     새 강연은 해당 연도 배열 맨 앞에 추가하면 된다.
     형식: "26.7.13 학산여자중학교 (전교생 306명)"
           { text: "...", url: "후기 링크" }
           { text: "...", isSchool: false }   ← 학교가 아닌 기관
  */
  var SCHOOL_HISTORY = [
    {
      year: '2026년',
      schools: [
        '26.12.9 남도여자중학교 (전교생 210명, 1시간 북콘서트) (예정)',
        '26.11.11 김해중앙여자고등학교 (김해진로교육지원센터 「학교로 찾아가는 직업체험」, 1차시 특강 2회) (예정)',
        '26.7.16 내성중학교',
        '26.7.15 김해 대청고등학교',
        { text: '26.7.13 학산여자중학교 (전교생 306명, 1시간 40분 진로 토크 콘서트)', url: 'https://blog.naver.com/tothemoon_park/224349752613' },
        { text: '26.7.10 윤중중학교 (3학년 137명, 1시간 40분)', url: 'https://blog.naver.com/tothemoon_park/224347773934' },
        { text: '26.7.9 부일고등학교', url: 'https://blog.naver.com/tothemoon_park/224341514365' },
        '26.7.8 동현중학교',
        { text: '26.7.7 남성여자고등학교 (1·2학년 210여 명, 1시간)', url: 'https://blog.naver.com/tothemoon_park/224346558264' },
        '26.7.2 좌삼초등학교',
        { text: '26.6.30 당리중학교 진로 콘서트 (1학년 135명, 1시간 동기 부여 강연)', url: 'https://blog.naver.com/tothemoon_park/224332038136' },
        '26.6.24 오륙도중학교',
        '26.6.18 양산 서창중학교',
        { text: '26.6.12 유락여자중학교 (2·3학년 550명, 각 1시간)', url: 'https://blog.naver.com/tothemoon_park/224321173600' },
        { text: '26.6.10 부산영상예술고등학교 (전교생 414명, 1시간 30분)', url: 'https://blog.naver.com/tothemoon_park/224320635555' },
        '26.6.5 상당중학교',
        '26.5.29 양산 성산초등학교',
        '26.5.20 해운대여자중학교',
        '26.5.14 신양초등학교',
        '26.5.13 대명여자고등학교',
        '26.5.13 명호고등학교',
        '26.4.29 사송고등학교',
        '26.4.28 양산초등학교',
        { text: '26.4.25 부산시청소년자립지원관 진로 특강', url: 'https://www.youtube.com/watch?v=yXY0kf-uTdw&t=73s', isSchool: false },
        '26.4.24 신곡중학교',
        '26.4.21 김해 수남중학교',
        '26.4.7 부산여중'
      ]
    },
    {
      year: '2025년',
      schools: [
        '25.12.9 금정중',
        { text: '25.12.1 인천 계양중학교', url: 'https://blog.naver.com/tothemoon_park/224096489803' },
        '25.11.3 금양중',
        '25.10.29 개금고등학교',
        '25.10.22 김해 제일고등학교',
        '25.9.9 금사중',
        '25.9.8 부곡여중',
        '25.7.14 사직고등학교',
        '25.7.14 부산 부일외국어고등학교',
        '25.7.4 양산고등학교',
        '25.6.26 동래여중',
        '25.6.2 김해 수남중학교',
        '25.5.21 부산 대명여고',
        '25.4.30 브니엘예중',
        '25.4.9 부산여중'
      ]
    },
    {
      year: '2024년',
      schools: [
        '24.7 신도고등학교',
        '24.7 내성고등학교'
      ]
    }
  ];

  /* ── 2. 자동 집계 로직 ────────────────────────────────── */

  // 항목에서 순수 학교명만 뽑아 비교용으로 정규화한다.
  //  "26.5.13 대명여자고등학교"  → "대명여고"
  //  "25.5.21 부산 대명여고"      → "대명여고"  (동일 학교로 인식)
  function normalizeName(raw) {
    var s = String(raw);
    s = s.replace(/^\d{2}\.\d{1,2}(\.\d{1,2})?\s*/, ''); // 앞 날짜 제거
    s = s.replace(/\([^)]*\)/g, '');                      // 괄호 설명 제거
    s = s.replace(/(진로|직업)?\s*(토크\s*)?(콘서트|특강|강연|북콘서트).*$/, '');
    s = s.trim();
    s = s.replace(/^(부산|김해|양산|인천|서울|경남)\s+/, ''); // 지역 접두어(띄어쓴 경우만)
    s = s.replace(/여자중학교/g, '여중')
         .replace(/여자고등학교/g, '여고')
         .replace(/고등학교/g, '고')
         .replace(/중학교/g, '중')
         .replace(/초등학교/g, '초');
    return s.replace(/\s+/g, '').trim();
  }

  function itemText(item) {
    return (item && typeof item === 'object') ? item.text : item;
  }
  function isSchoolItem(item) {
    return !(item && typeof item === 'object' && item.isSchool === false);
  }
  function isUpcoming(item) {
    return /\(예정\)/.test(itemText(item));
  }

  function computeSchoolStats() {
    var totalEvents = 0, completedEvents = 0, upcoming = 0;
    var uniqueCompleted = {};

    SCHOOL_HISTORY.forEach(function (y) {
      y.schools.forEach(function (item) {
        if (!isSchoolItem(item)) return;   // 학교가 아닌 기관은 학교 수에서 제외
        totalEvents++;
        if (isUpcoming(item)) { upcoming++; return; }
        completedEvents++;
        uniqueCompleted[normalizeName(itemText(item))] = true;
      });
    });

    return {
      totalEvents: totalEvents,                          // 학교 강연 총 건수(예정 포함)
      completedEvents: completedEvents,                  // 완료 건수
      upcomingEvents: upcoming,                          // 예정 건수
      uniqueSchools: Object.keys(uniqueCompleted).length // ★ 대외 표기용 = 완료 유니크 개교
    };
  }

  var schoolStats = computeSchoolStats();

  /* ── 3. 인터뷰 인원 (「N여 명」 표기 자동 산출) ────────────
     피플인사이트는 매월 늘어난다. "62명"이라고 적으면 곧 63명이 되어
     사이트 전체가 낡는다. 그래서 표기는 **10단위 내림 + '여 명'** 으로 고정한다.
       · interviewsExact = 실제 최신 인원 (여기 한 곳만 고친다)
       · interviews      = 대외 표기용 (자동 산출: 62 → 60, 70 → 70)
     70번째 인터뷰가 올라오는 순간 사이트 전 페이지가 스스로 「70여 명」이 된다.
     ⛔ HTML에 숫자를 직접 적지 말 것. <span data-stat="interviews"></span>여 명 형태만 사용.
     ------------------------------------------------------------ */
  var interviewsExact = 62;   // 2026-08-15 기준 (브런치 「예순두 번째 인터뷰이」 확인)
  var interviewsRounded = Math.floor(interviewsExact / 10) * 10;

  /* ── 4. 나머지 수치 (수동 관리 — 바뀌면 여기만 고친다) ──── */
  var SITE_STATS = {
    // 자동 집계
    schools: schoolStats.uniqueSchools,        // 완료 유니크 개교 (자동)
    schoolEvents: schoolStats.completedEvents, // 완료 강연 건수 (자동)
    interviews: interviewsRounded,             // 대외 표기용 「N여 명」 (자동)
    interviewsExact: interviewsExact,          // 정확 인원이 필요한 자리용

    // 수동 관리
    books: 5,               // 출간 저서 (집필 중 제외)
    columnOutlets: 25,      // 칼럼 연재 매체 수
    pressBook: 31,          // 신간 출간 보도 매체 수
    pressLecture: 23,       // 자립지원관 특강 보도 매체 수
    followers: '2.6만',     // SNS 팔로워
    vodCount: 5,            // 자체 VOD 강좌 수

    asOf: '2026.8'          // 기준 시점 (수치 옆에 함께 노출)
  };

  /* ── 4. 페이지 자동 반영 ──────────────────────────────── */
  function applyStats() {
    var nodes = document.querySelectorAll('[data-stat]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-stat');
      if (SITE_STATS[key] !== undefined) nodes[i].textContent = SITE_STATS[key];
    }
  }

  global.SITE_STATS = SITE_STATS;
  global.SCHOOL_HISTORY = SCHOOL_HISTORY;
  global.SCHOOL_STATS = schoolStats;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyStats);
  } else {
    applyStats();
  }
})(window);
