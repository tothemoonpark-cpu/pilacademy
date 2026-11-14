/* fold.js — 긴 섹션을 접어 스크롤을 줄인다 (2026-11-14)
   · 내용은 지우지 않고 화면에서만 가린다(검색 엔진·AI가 읽는 HTML은 그대로).
   · 스크립트가 꺼져 있으면 전부 펼쳐진 채로 보인다.
   · 쓰는 법: 페이지에 <script src="fold.js" defer></script> 한 줄.
     섹션에 data-toc="짧은 이름" 을 주면 맨 위 목차에 들어간다. data-fold="off" 면 접지 않는다. */
(function () {
  if (window.__pilFold) return; window.__pilFold = 1;
  var css = '.pf-toc-sp{display:block}.pf-toc{display:block;box-sizing:border-box;width:100%;max-width:none;margin:0;padding:0;position:fixed;left:0;right:0;top:var(--pf-top,0px);z-index:45;background:#1f5c4d;box-shadow:0 2px 10px rgba(0,0,0,.14)}' +
    '.pf-toc-in{display:flex;align-items:center;gap:14px;box-sizing:border-box;max-width:1240px;margin:0 auto;padding:9px 20px}' +
    '.pf-toc-t{flex:none;display:inline-block;width:auto;margin:0;color:#fff;font-size:.98rem;font-weight:800;white-space:nowrap}' +
    '.pf-toc-l{display:flex;flex:1 1 auto;min-width:0;flex-wrap:nowrap;gap:8px;margin:0;padding:2px 0;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}.pf-toc-l::-webkit-scrollbar{display:none}' +
    '.pf-toc-l a{flex:none;display:inline-block;padding:8px 14px;border-radius:999px;background:#fff;color:#1f5c4d;font-size:.95rem;font-weight:800;text-decoration:none;line-height:1.3;white-space:nowrap}' +
    '.pf-toc-l a:hover,.pf-toc-l a:focus{background:#d9efe7}.pf-toc-l a.pf-on{background:#ffd76a;color:#1c1c1c}' +
    '@media(max-width:640px){.pf-toc-in{gap:10px;padding:8px 12px}.pf-toc-t{font-size:.88rem}.pf-toc-l a{padding:7px 12px;font-size:.9rem}}' +
    '.pf-clip{position:relative;overflow:hidden}.pf-clip:after{content:"";position:absolute;left:0;right:0;bottom:0;height:120px;pointer-events:none;background:linear-gradient(to bottom,rgba(255,255,255,0),var(--pf-bg,#fff))}' +
    '.pf-bar{display:flex;justify-content:center;padding:14px 20px 4px}.pf-btn{appearance:none;border:1.5px solid #2f7d68;background:#fff;color:#1f5c4d;font:inherit;font-weight:700;font-size:1rem;padding:12px 26px;border-radius:999px;cursor:pointer;line-height:1.3}' +
    '.pf-btn:hover,.pf-btn:focus{background:#e9f5f0}@media print{.pf-clip{max-height:none!important;overflow:visible}.pf-clip:after,.pf-bar,.pf-toc,.pf-toc-sp{display:none!important}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  function bgOf(el) { while (el && el !== document.documentElement) { var c = getComputedStyle(el).backgroundColor; if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; el = el.parentElement; } return '#fff'; }
  function run() {
    var secs = [].slice.call(document.querySelectorAll('main section, body > section')).filter(function (s) { return !s.closest('header,footer,nav'); });
    if (!secs.length) return;
    var vh = window.innerHeight || 800, limit = Math.max(480, Math.round(vh * 0.6)), folds = [];
    secs.forEach(function (s, i) {
      if (i === 0 || s.getAttribute('data-fold') === 'off' || s.querySelector('form')) return;
      var box = s.querySelector(':scope > .wrap') || s;
      if (box.scrollHeight < Math.max(1000, vh * 1.15)) return;
      var id = s.id || (s.id = 'pf-sec-' + i), h = s.querySelector('h2,h3'), name = s.getAttribute('data-toc') || (h ? h.textContent.trim() : '이 부분');
      box.classList.add('pf-clip'); box.style.maxHeight = limit + 'px'; box.style.setProperty('--pf-bg', bgOf(s));
      var bar = document.createElement('div'); bar.className = 'pf-bar';
      var b = document.createElement('button'); b.type = 'button'; b.className = 'pf-btn'; b.setAttribute('aria-expanded', 'false');
      if (!box.id) box.id = id + '-body'; b.setAttribute('aria-controls', box.id);
      var label = '이어서 보기'; b.textContent = label; b.setAttribute('aria-label', name + ' — 이어서 보기');
      bar.appendChild(b); box.parentNode.insertBefore(bar, box.nextSibling);
      function open(noScroll) { if (b.getAttribute('aria-expanded') === 'true') return; box.classList.remove('pf-clip'); box.style.maxHeight = ''; box.scrollTop = 0; b.setAttribute('aria-expanded', 'true'); b.textContent = '접기'; b.setAttribute('aria-label', name + ' — 접기'); }
      function close() { box.classList.add('pf-clip'); box.style.maxHeight = limit + 'px'; b.setAttribute('aria-expanded', 'false'); b.textContent = label; b.setAttribute('aria-label', name + ' — 이어서 보기'); s.scrollIntoView({ block: 'start' }); }
      b.addEventListener('click', function () { b.getAttribute('aria-expanded') === 'true' ? close() : open(); });
      box.addEventListener('scroll', function () { if (box.scrollTop > 0) open(); });          /* 찾기(Ctrl+F)·탭 이동으로 가려진 곳에 닿으면 펼친다 */
      box.addEventListener('focusin', function (e) { if (b.getAttribute('aria-expanded') !== 'true' && e.target.getBoundingClientRect().top > box.getBoundingClientRect().top + limit - 40) open(); });
      folds.push({ s: s, box: box, open: open });
    });
    function toHash() { var h = decodeURIComponent(location.hash || '').slice(1); if (!h) return; var t = document.getElementById(h); if (!t) return; folds.forEach(function (f) { if (f.box.contains(t) && t !== f.s) { f.open(); setTimeout(function () { t.scrollIntoView({ block: 'start' }); }, 30); } }); }
    window.addEventListener('hashchange', toHash); toHash();
    document.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a) return; setTimeout(toHash, 0); });
    var named = secs.filter(function (s) { return s.getAttribute('data-toc'); });
    if (named.length >= 3 && !document.querySelector('.pf-toc')) {
      var nav = document.createElement('div'); nav.className = 'pf-toc'; nav.setAttribute('role', 'navigation'); nav.setAttribute('aria-label', '이 페이지에서 볼 것');
      var inn = document.createElement('div'); inn.className = 'pf-toc-in';
      var t = document.createElement('span'); t.className = 'pf-toc-t'; t.textContent = '바로 가기'; inn.appendChild(t);
      var ul = document.createElement('div'); ul.className = 'pf-toc-l'; var links = [];
      named.forEach(function (s, i) { if (!s.id) s.id = 'pf-toc-' + i; var a = document.createElement('a'); a.href = '#' + s.id; a.textContent = s.getAttribute('data-toc'); ul.appendChild(a); links.push(a); });
      inn.appendChild(ul); nav.appendChild(inn); var sp = document.createElement('div'); sp.className = 'pf-toc-sp'; secs[0].parentNode.insertBefore(sp, secs[0]); document.body.appendChild(nav);
      /* 위에 붙어 있는 사이트 메뉴가 있으면 그 아래에 붙인다 */
      var topH = 0; [].slice.call(document.querySelectorAll('header, body > nav, .site-nav, .pil-nav')).forEach(function (h) { if (h === nav || h.contains(nav)) return; var p = getComputedStyle(h).position; if (p === 'sticky' || p === 'fixed') { var r = h.getBoundingClientRect(); if (r.top <= 2 && r.height < 200) topH = Math.max(topH, Math.round(r.bottom)); } });
      nav.style.setProperty('--pf-top', topH + 'px');
      sp.style.height = nav.offsetHeight + 'px'; var off = topH + nav.offsetHeight + 12;
      named.forEach(function (s) { s.style.scrollMarginTop = off + 'px'; });
      function mark() { var cur = null, y = off + 24; named.forEach(function (s, i) { if (s.getBoundingClientRect().top <= y) cur = i; }); links.forEach(function (a, i) { var on = i === cur; if (on !== a.classList.contains('pf-on')) { a.classList.toggle('pf-on', on); if (on) { a.setAttribute('aria-current', 'true'); var l = a.offsetLeft - ul.clientWidth / 2 + a.offsetWidth / 2; ul.scrollLeft = Math.max(0, l); } else a.removeAttribute('aria-current'); } }); }
      var tk = 0; window.addEventListener('scroll', function () { if (tk) return; tk = 1; requestAnimationFrame(function () { tk = 0; mark(); }); }, { passive: true }); mark();
    }
  }
  if (document.readyState === 'complete') run(); else window.addEventListener('load', run);
})();
