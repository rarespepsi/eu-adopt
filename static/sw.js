/**
 * Service Worker – EU Adopt
 * Cache static assets; navigare network-first.
 */

const CACHE_NAME = 'euadopt-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;

  // Pagini / navigare: mereu rețea, fallback la cache
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((res) => res)
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match('/')))
    );
    return;
  }

  // Static (CSS, JS, imagini): cache-first
  if (/\.(css|js|woff2?|png|jpe?g|gif|ico|svg|webp)(\?.*)?$/i.test(url.pathname)) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return res;
        });
      })
    );
    return;
  }

  // Restul: rețea
  event.respondWith(fetch(event.request));
});
