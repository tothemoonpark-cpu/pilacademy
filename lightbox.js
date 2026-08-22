/* lightbox.js — 본문 이미지를 클릭하면 크게 보여 준다
 *
 * 왜 만들었나 (2026-08-22 작가님 지적)
 * ------------------------------------
 * "사진이 작아서 내 얼굴, 텍스트 안 보여. 클릭하면 사진 확대되는 기능 넣어."
 * 전북대 강연 포스터를 카드 안에 240px 로 넣었더니 포스터 안의 글자가 읽히지 않았다.
 * 후기 캡처·프로필 사진·책 표지도 같은 문제를 안고 있었다.
 *
 * ⭐ 한 곳만 고치지 않는다
 * 이 파일 하나를 각 페이지가 읽어 가므로, 앞으로 넣는 이미지도 자동으로 확대된다.
 * (전역지침: "한 곳만 고치면 나머지는 따라온다" / "이걸 앞으로 누가 갱신하나?")
 *
 * 무엇이 대상인가 — 「축소되어 보이는 이미지」만
 * ------------------------------------------
 * 원본 해상도가 화면 표시 폭보다 1.25배 이상 크면 = 클릭해서 더 볼 것이 있는 이미지.
 * 로고·아이콘·장식 이미지는 원본이 표시 크기와 비슷하므로 자동으로 빠진다.
 * 강제로 빼려면 <img data-nozoom>, 강제로 넣으려면 <img data-zoom>.
 */
(function () {
  'use strict';

  var RATIO = 1.25;                       // 이 배율 이상 축소돼 있으면 확대 대상
  var MINW = 120;                          // 이보다 작게 그려진 것은 아이콘으로 본다
  var SKIP = /logo|favicon|icon|qr|배지|badge|sprite/i;

  var overlay, imgEl, capEl, lastFocus;

  function build() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'pz-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', '이미지 확대 보기');
    overlay.innerHTML =
      '<button class="pz-close" type="button" aria-label="닫기">&times;</button>' +
      '<figure class="pz-figure">' +
        '<img class="pz-img" alt="">' +
        '<figcaption class="pz-cap"></figcaption>' +
      '</figure>';
    document.body.appendChild(overlay);
    imgEl = overlay.querySelector('.pz-img');
    capEl = overlay.querySelector('.pz-cap');

    overlay.addEventListener('click', function (e) {
      // 사진 자체를 눌러도 닫힌다(모바일에서 닫기 버튼을 찾기 어렵다)
      if (e.target === overlay || e.target.closest('.pz-close') || e.target === imgEl) close();
    });
    document.addEventListener('keydown', function (e) {
      if (!overlay.classList.contains('on')) return;
      if (e.key === 'Escape') close();
    });
  }

  function open(img) {
    build();
    lastFocus = document.activeElement;
    imgEl.src = img.currentSrc || img.src;
    imgEl.alt = img.alt || '';
    capEl.textContent = img.alt || '';
    capEl.style.display = img.alt ? '' : 'none';
    overlay.classList.add('on');
    document.documentElement.style.overflow = 'hidden';
    overlay.querySelector('.pz-close').focus();
  }

  function close() {
    if (!overlay) return;
    overlay.classList.remove('on');
    document.documentElement.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* 확대할 값이 있는 이미지인가
   * ⛔ 2026-08-22 수리 — 처음엔 페이지 로드 직후 크기를 재서 판정했는데,
   *    필북 후기 73장·프로필 사진이 **접힌 아코디언 안**에 있어 clientWidth 가 0 이었고,
   *    loading="lazy" 이미지는 아직 내려받지도 않아 naturalWidth 가 0 이었다.
   *    → 그 순간에는 판정할 수 없다. **클릭하는 순간 판정**한다(그때는 반드시 보이고 로드돼 있다). */
  function worth(img) {
    if (img.dataset.nozoom !== undefined) return false;
    if (SKIP.test(img.getAttribute('src') || '')) return false;
    if (img.dataset.zoom !== undefined) return true;
    var shown = img.clientWidth;
    if (shown && shown < MINW) return false;            // 아이콘 크기로 그려진 것
    if (!img.naturalWidth) return false;
    if (img.naturalWidth < 400) return false;           // 원본이 작으면 확대해도 볼 게 없다
    if (!shown) return true;                            // 아직 크기를 모르면 일단 허용
    return img.naturalWidth >= shown * RATIO;
  }

  /* 클릭은 문서 하나에만 건다(위임) — 나중에 생기거나 펼쳐지는 이미지까지 전부 걸린다 */
  function delegate() {
    document.addEventListener('click', function (e) {
      var img = e.target.closest && e.target.closest('img');
      if (!img) return;
      if (img.closest('a')) return;                     // 링크 안의 이미지는 링크가 우선
      if (!worth(img)) return;
      e.preventDefault();
      open(img);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var img = document.activeElement;
      if (!img || img.tagName !== 'IMG' || !worth(img)) return;
      e.preventDefault();
      open(img);
    });
  }

  /* 커서·툴팁은 보이는 이미지에만 붙인다(있으면 클릭할 수 있다는 신호) */
  function mark(img) {
    if (img.dataset.pzOn || img.closest('a') || !worth(img)) return;
    img.dataset.pzOn = '1';
    img.style.cursor = 'zoom-in';
    img.setAttribute('role', 'button');
    img.setAttribute('tabindex', '0');
    if (!img.title) img.title = '클릭하면 크게 볼 수 있습니다';
  }

  function scan() {
    var list = document.querySelectorAll('img:not([data-pz-on])');
    for (var i = 0; i < list.length; i++) {
      var im = list[i];
      if (im.complete) mark(im);
      else im.addEventListener('load', function () { mark(this); }, { once: true });
    }
  }

  function init() {
    delegate();
    scan();
    // 접힌 영역이 펼쳐지거나 지연 이미지가 내려오면 그때 표시를 붙인다
    if (window.MutationObserver) {
      var mo = new MutationObserver(function () {
        clearTimeout(init._t);
        init._t = setTimeout(scan, 150);
      });
      mo.observe(document.body, { childList: true, subtree: true, attributes: true,
                                  attributeFilter: ['src', 'style', 'class', 'hidden'] });
    }
    setTimeout(scan, 1200);
    window.addEventListener('resize', function () { clearTimeout(init._r); init._r = setTimeout(scan, 250); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // 스타일은 이 파일이 직접 넣는다 — 페이지마다 CSS 를 복사하면 반드시 어긋난다
  var css = document.createElement('style');
  css.textContent =
    // z-index 는 최대값 — 사이트 헤더가 fixed 로 3000 까지 쓰고 있어 9999 로는 헤더가 위에 떴다(2026-08-22 실측)
    '.pz-overlay{position:fixed;inset:0;z-index:2147483000;display:none;align-items:center;' +
      'justify-content:center;background:rgba(22,24,29,.96);padding:24px;cursor:zoom-out}' +
    '.pz-overlay.on{display:flex}' +
    '.pz-figure{margin:0;max-width:100%;max-height:100%;display:flex;flex-direction:column;' +
      'align-items:center;gap:12px}' +
    '.pz-img{max-width:min(1100px,94vw);max-height:82vh;width:auto;height:auto;' +
      'border-radius:8px;background:#fff;box-shadow:0 12px 40px rgba(0,0,0,.45)}' +
    '.pz-cap{color:#fff;font-size:.88rem;line-height:1.5;text-align:center;max-width:min(1100px,94vw);' +
      'opacity:.85}' +
    '.pz-close{position:absolute;top:14px;right:18px;width:42px;height:42px;border:0;border-radius:50%;' +
      'background:rgba(255,255,255,.14);color:#fff;font-size:26px;line-height:1;cursor:pointer}' +
    '.pz-close:hover{background:rgba(255,255,255,.26)}' +
    '@media(max-width:640px){.pz-overlay{padding:12px}.pz-img{max-height:76vh}}';
  document.head.appendChild(css);
})();
