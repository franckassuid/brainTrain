/**
 * BrainTrain - Service Worker PWA pour mode 100% hors-ligne
 */

const CACHE_NAME = 'braintrain-cache-v1';

const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './favicon.svg',
  './css/style.css',
  './css/sudoku.css',
  './css/mastermind.css',
  './css/nonogram.css',
  './css/hashi.css',
  './css/compte_est_bon.css',
  './css/cross_math.css',
  './js/app.js',
  './js/api.js',
  './js/timer.js',
  './js/sudoku.js',
  './js/mastermind.js',
  './js/nonogram.js',
  './js/hashi.js',
  './js/compte_est_bon.js',
  './js/cross_math.js',
  './data/puzzles.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Pour les requêtes locales / statiques
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // En arrière-plan, rafraîchit le cache si le réseau est dispo
        fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, networkResponse);
            });
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return response;
      }).catch(() => {
        // Si hors-ligne et requête de page html
        if (event.request.mode === 'navigate') {
          return caches.match('./index.html');
        }
      });
    })
  );
});
