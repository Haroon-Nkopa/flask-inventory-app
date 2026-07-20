const CACHE_NAME = 'stockwise-v3';

// 1. Core static structural assets AND HTML view routes from your layout tree
const STATIC_ASSETS = [
  '/',                     // Pre-caches your landing/dashboard route
  '/pos',                  // FIX: Pre-caches the actual POS HTML template so it loads offline
  '/manifest.json',
  '/static/css/bootstrap.min.css',
  '/static/css/style.css',
  '/static/icon/icon-512.png',
  '/static/screenshots/desktop.png',
  '/static/screenshots/mobile.png'
];

// 2. All specific JavaScript logic controllers found in your app/static/js folder
const JS_CONTROLLERS = [
  '/static/js/main.js',
  '/static/js/api.js',
  '/static/js/history.js',
  '/static/js/new_stock.js',
  '/static/js/pos.js',
  '/static/js/product.js',
  '/static/js/sales_history.js',
  '/static/js/stock_take.js',
  '/static/js/summary.js'
];

const ALL_ASSETS = [...STATIC_ASSETS, ...JS_CONTROLLERS];

// Install Event - Pre-caches all layout structure files immediately
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pre-caching all local static layouts and JS modules...');
      return cache.addAll(ALL_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event - Automatically clears older cache instances when version changes
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache layer:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Interception Strategy
self.addEventListener('fetch', (event) => {
  // Only handle same-origin assets
  if (!event.request.url.startsWith(self.location.origin)) return;

  // STRATEGY FOR API GET REQUESTS (Product list)
  if (event.request.url.includes('/api/pos/products') && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request)) // Fallback to cached product list offline
    );
    return;
  }

  // STRATEGY FOR API POST REQUESTS (Checkout API - let it fail so JS can catch it)
  if (event.request.url.includes('/api/pos/checkout')) {
    return; // Let frontend JavaScript catch the offline error and route to IndexedDB
  }

  // STRATEGY FOR HTML/CSS/JS ASSETS (Network-First)
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Only cache successful standard GET web server loads
        if (networkResponse.status === 200 && event.request.method === 'GET') {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
          
          // Generic HTML fallback screen if a specific navigate asset isn't matching
          if (event.request.mode === 'navigate') {
            return caches.match('/pos'); // Fallback straight to your working offline POS view
          }
        });
      })
  );
});


