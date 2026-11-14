/* fold.js — 긴 섹션을 접어 스크롤을 줄인다 (2026-11-14)
   · 내용은 지우지 않고 화면에서만 가린다(검색 엔진·AI가 읽는 HTML은 그대로).
   · 스크립트가 꺼져 있으면 전부 펼쳐진 채로 보인다.
   · 쓰는 법: 페이지에 <script src="fold.js" defer></script> 한 줄.
     섹션에 data-toc="짧은 이름" 을 주면 맨 위 목차에 들어간다. data-fold="off" 면 접지 않는다. */
(function () {
  if (window.__pilFold) return; window.__pilFold = 1;
  var css = '.pf-toc{display:block;max-width:1160px;margin:0 auto;padding:18px 20px 6px}.pf-toc-t{display:block;width:100%}.pf-toc-t{font-size:.86rem;font-weight:700;color:#5b6b66;margin:0 0 10px}' +
    '.pf-toc-l{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none}.pf-toc-l a{display:inline-block;padding:8px 14px;border:1px solid #cfe3dc;border-radius:999px;background:#fff;color:#1f5c4d;font-size:.92rem;font-weight:700;text-decoration:none;line-height:1.3}' +
    '.pf-toc-l a:hover,.pf-toc-l a:focus{background:#e9f5f0}' +
    '.pf-clip{position:relative;overflow:hidden}.pf-clip:after{content:"";position:absolute;left:0;right:0;bottom:0;height:120px;pointer-events:none;background:linear-gradient(to bottom,rgba(255,255,255,0),var(--pf-bg,#fff))}' +
    '.pf-bar{display:flex;justify-content:center;padding:14px 20px 4px}.pf-btn{appearance:none;border:1.5px solid #2f7d68;background:#fff;color:#1f5c4d;font:inherit;font-weight:700;font-size:1rem;padding:12px 26px;border-radius:999px;cursor:pointer;line-height:1.3}' +
    '.pf-btn:hover,.pf-btn:focus{background:#e9f5f0}@media print{.pf-clip{max-height:none!important;overflow:visible}.pf-clip:after,.pf-bar,.pf-toc{display:none}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  function bgOf(el) { while (el && el !== document.documentElement) { var c = getComputedStyle(el).backgroundColor; if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; el = el.parentElement; } return '#fff'; }
  function run() {
    var secs = [].slice.call(document.querySelectorAll('main section, body > section')).filter(function (s) { return !s.closest('header,footer,nav'); });
    if (!secs.length) return;
    var vh = window.innerHeight || 800, limit = Math.max(520, Math.round(vh * 0.7)), folds = [];
    secs.forEach(function (s, i) {
      if (i === 0 || s.getAttribute('data-fold') === 'off' || s.querySelector('form')) return;
      var box = s.querySelector(':scope > .wrap') || s;
      if (box.scrollHeight < Math.max(1300, vh * 1.5)) return;
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
      var nav = document.createElement('nav'); nav.className = 'pf-toc'; nav.setAttribute('aria-label', '이 페이지에서 볼 것');
      var t = document.createElement('p'); t.className = 'pf-toc-t'; t.textContent = '이 페이지에서 볼 것'; nav.appendChild(t);
      var ul = document.createElement('ul'); ul.className = 'pf-toc-l';
      named.forEach(function (s, i) { if (!s.id) s.id = 'pf-toc-' + i; var li = document.createElement('li'), a = document.createElement('a'); a.href = '#' + s.id; a.textContent = s.getAttribute('data-toc'); li.appendChild(a); ul.appendChild(li); });
      nav.appendChild(ul); secs[0].parentNode.insertBefore(nav, secs[0].nextSibling);
    }
  }
  if (document.readyState === 'complete') run(); else window.addEventListener('load', run);
})();
