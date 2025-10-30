// MoodMend PWA Service Worker

// 缓存名称和版本 - 增加版本号以确保更新
const CACHE_NAME = 'moodmend-v3';
const DYNAMIC_CACHE = 'moodmend-dynamic-v3';

// 需要缓存的核心资源
const STATIC_ASSETS = [
  '/',  // 根路径也需要缓存，确保离线时能访问
  './moodmend_ui_demo.html',
  './manifest.json',
  '../../icons/MoodMend_Logo_Option4.svg',
  '../../icons/MoodMend_Angry_Emotion.svg',
  '../../icons/MoodMend_Happy_Emotion.svg',
  '../../icons/MoodMend_Calm_Emotion.svg',
  '../../icons/MoodMend_Sad_Emotion.svg',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// 安装事件 - 预缓存核心资源
self.addEventListener('install', (event) => {
  console.log('Service Worker: 安裝中');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: 缓存核心資源');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// 激活事件 - 清理舊缓存  
  self.addEventListener('activate', (event) => {
    console.log('Service Worker: 激活中');
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // 清理所有旧版本的缓存
            if (cacheName !== CACHE_NAME && cacheName !== DYNAMIC_CACHE && cacheName.startsWith('moodmend-')) {
              console.log('Service Worker: 清理舊缓存', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }).then(() => {
        // 确保立即控制所有客户端
        return self.clients.claim();
      }).then(() => {
        // 向所有客户端发送消息，通知Service Worker已更新
        return self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({ type: 'SW_UPDATED' });
          });
        });
      })
    );
  });

// 资源请求策略：混合策略，优化离线体验
self.addEventListener('fetch', (event) => {
  // 对于HTML页面，使用网络优先但回退到缓存的策略
  if (event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(event.request.clone())
        .then(response => {
          console.log('Service Worker: 从网络获取HTML页面成功', event.request.url);
          return response;
        })
        .catch(error => {
          console.log('Service Worker: 网络请求失败，尝试从缓存获取', event.request.url, error);
          // 网络失败时，尝试从任一缓存获取
          return caches.match(event.request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                console.log('Service Worker: 从缓存返回HTML页面', event.request.url);
                return cachedResponse;
              }
              // 如果没有特定路径的缓存，返回主页
              console.log('Service Worker: 尝试返回主页作为后备');
              return caches.match('./src/frontend/moodmend_ui_demo.html');
            });
        })
    );
    return;
  }
  
  // 跳过API请求的缓存（让客户端处理离线逻辑）
  if (event.request.url.includes('api')) {
    return fetchWithNetworkFallback(event);
  }
  
  // 对于其他资源（CSS, JS, 图片等）使用缓存优先策略
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        // 如果找到缓存，返回缓存的响应
        if (cachedResponse) {
          return cachedResponse;
        }
        // 如果没有缓存，则从网络获取
        return fetch(event.request)
          .then((response) => {
            // 检查响应是否有效
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // 克隆响应以便缓存和返回
            const responseToCache = response.clone();
            
            // 将新获取的资源添加到动态缓存
            caches.open(DYNAMIC_CACHE)
              .then((cache) => {
                cache.put(event.request, responseToCache);
              });
            
            return response;
          })
          .catch(error => {
            console.error('Service Worker: 资源获取失败', event.request.url, error);
            // 对于图片请求，如果失败，返回一个空的占位符响应
            if (event.request.url.match(/\.(jpe?g|png|gif|svg)$/)) {
              return new Response('占位图片', { headers: { 'Content-Type': 'text/plain' } });
            }
            throw error;
          });
      })
  );
});

// 网络优先，缓存回退的请求处理函数
function fetchWithNetworkFallback(event) {
  return event.respondWith(
    fetch(event.request)
      .then(response => {
        // 对于API请求，可以选择性地缓存成功响应
        if (response && response.status === 200) {
          // 克隆响应
          const clonedResponse = response.clone();
          // 打开动态缓存并存储响应
          caches.open(DYNAMIC_CACHE)
            .then(cache => {
              cache.put(event.request, clonedResponse);
            });
        }
        return response;
      })
      .catch(() => {
        // 网络失败时尝试从缓存获取
        return caches.match(event.request);
      })
  );
}