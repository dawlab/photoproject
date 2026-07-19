(async function initHeader(isAdmin) {
  const placeholder = document.getElementById('header-placeholder');
  if (!placeholder) return;

  placeholder.outerHTML = `
<header class="site-header">
  <a href="index.html" class="logo">Projekt&nbsp;<span class="logo-accent">Lepiej</span></a>
  <nav class="site-nav" id="siteNav"></nav>
  <button class="hamburger" id="hamburger" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
</header>
<div class="nav-overlay" id="navOverlay">
  <button class="nav-overlay__close" id="navClose" aria-label="Zamknij">✕</button>
  <nav class="nav-overlay__links" id="navOverlayLinks"></nav>
</div>`;

  const { data: links } = await sb.from('nav_links').select('*').order('position');
  const cur = location.pathname.split('/').pop() || 'index.html';

  const nav = document.getElementById('siteNav');
  nav.innerHTML = (links || []).map(l =>
    `<a href="${l.url}" class="nav-link${cur === l.url ? ' active' : ''}">${l.title}</a>`
  ).join('');

  const overlay = document.getElementById('navOverlayLinks');
  overlay.innerHTML = (links || []).map(l =>
    `<a href="${l.url}" class="nav-overlay__link${cur === l.url ? ' active' : ''}">${l.title}</a>`
  ).join('');

  const ham   = document.getElementById('hamburger');
  const box   = document.getElementById('navOverlay');
  const close = document.getElementById('navClose');
  const closeMenu = () => { box.classList.remove('open'); ham.classList.remove('open'); document.body.style.overflow = ''; };
  ham.addEventListener('click', () => { box.classList.add('open'); ham.classList.add('open'); document.body.style.overflow = 'hidden'; });
  close.addEventListener('click', closeMenu);
  box.addEventListener('click', e => { if (e.target === box) closeMenu(); });

  // ── Footer (wspólna dla wszystkich stron) ──
  if (!document.querySelector('.site-footer')) {
    const footer = document.createElement('footer');
    footer.className = 'site-footer';
    footer.innerHTML = `
      <span class="site-footer__brand">Projekt Lepiej © ${new Date().getFullYear()}</span>
      <a href="polityka-prywatnosci.html" class="site-footer__link">Polityka prywatności</a>`;
    document.body.appendChild(footer);
  }
})();
