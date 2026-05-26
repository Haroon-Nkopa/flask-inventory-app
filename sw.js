const CACHE_NAME = 'stockwise-v1';
const ASSETS = [
  '/static/css/style.css',   // Fixed: removed the extra 's'
  '/static/manifest.json'
];

// Install Service Worker and cache essential files safely
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Using map allows valid assets to cache even if one fails
      return Promise.all(
        ASSETS.map(url => {
          return cache.add(url).catch(err => console.warn('Failed to cache:', url, err));
        })
      );
    })
  );
});

// Serve cached content when offline
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request).catch(() => {
        // Optional: return a fallback offline message if fetch fails entirely
      });
    })
  );
});
