const CACHE_NAME = 's3c-v2';
const ASSETS = [
  '/',
  '/static/img/logo_sekolah.png',
  '/static/js/three_bg.js'
];

// Install: Cache basic assets
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
  );
});

// Activate: Clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      );
    })
  );
  return self.clients.claim();
});

// Fetch: Network-first for main pages, Cache-first for images/others
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Network-first for navigation (HTML)
  if (event.request.mode === 'navigate' || ASSETS.includes(url.pathname)) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const resClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  } else {
    // Cache-first for other assets
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
  }
});
