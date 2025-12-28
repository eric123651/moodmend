const CACHE_NAME = 'moodmend-v1.1';
const ASSETS_TO_CACHE = [
  '/',
  './moodmend_ui_demo.html',
  './manifest.json',
  './icons/icon-moodmend.png',
  './icons/icon-moodmend.svg',
  './icons/MoodMend_Angry_Emotion.svg',
  './icons/MoodMend_Happy_Emotion.svg',
  './icons/MoodMend_Calm_Emotion.svg',
  './icons/MoodMend_Anxious_Emotion.png',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Service Worker: Caching Assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing Old Cache');
            return caches.delete(cache);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match('./moodmend_ui_demo.html');
        }
      });
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});