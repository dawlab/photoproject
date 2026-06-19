const CACHE_VERSION = 'v1';
const STATIC_CACHE = `photo365-static-${CACHE_VERSION}`;
const API_CACHE    = `photo365-api-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/galerie',
  '/nastroje',
  '/static/css/main.css',
  '/static/js/header.js',
  '/static/js/utils.js',
  '/static/js/moods.js',
  '/static/favicon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// ─── Install ────────────────────────────────────────────────────────────────

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ─── Activate ───────────────────────────────────────────────────────────────

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith('photo365-') && k !== STATIC_CACHE && k !== API_CACHE)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ─── Fetch ──────────────────────────────────────────────────────────────────

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin
  if (request.method !== 'GET' || url.origin !== location.origin) return;

  // Admin panel: network-first (always fresh)
  if (url.pathname.startsWith('/new-day')) {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }

  // API: network-first with cache fallback (stale-while-revalidate)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(staleWhileRevalidate(request, API_CACHE));
    return;
  }

  // Uploaded photos / thumbnails: cache-first (immutable)
  if (url.pathname.startsWith('/uploads/') || url.pathname.startsWith('/thumbnails/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Pages: network-first
  event.respondWith(networkFirst(request, STATIC_CACHE));
});

// ─── Strategies ─────────────────────────────────────────────────────────────

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response('Brak połączenia', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);
  return cached || await networkPromise || new Response('{}', { status: 503 });
}
