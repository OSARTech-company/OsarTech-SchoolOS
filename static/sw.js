const SW_VERSION = 'school-result-pwa-v3';
const STATIC_CACHE = `${SW_VERSION}-static`;
const OFFLINE_URL = '/static/offline.html';

// Cache only safe public/static resources.
const SAFE_SHELL_PATHS = ['/', '/login', '/terms-privacy', OFFLINE_URL];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(SAFE_SHELL_PATHS)).catch(() => Promise.resolve())
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isStaticAsset =
    req.destination === 'style' ||
    req.destination === 'script' ||
    req.destination === 'image' ||
    req.destination === 'font' ||
    url.pathname.startsWith('/static/');

  if (isStaticAsset) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(req, copy)).catch(() => {});
          }
          return res;
        });
      })
    );
    return;
  }

  // Navigation requests: do not cache authenticated/dynamic pages.
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => {
        // Offline fallback page only.
        return caches.match(OFFLINE_URL);
      })
    );
    return;
  }
});
