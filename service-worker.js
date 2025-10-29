// MoodMend PWA Service Worker

// 缓存名称和版本 - 增加版本号以确保更新
const CACHE_NAME = 'moodmend-v3';
const DYNAMIC_CACHE = 'moodmend-dynamic-v3';

// 需要缓存的核心资源
const STATIC_ASSETS = [
  '/',  // 根路径也需要缓存，确保离线时能访问
  './moodmend_ui_demo.html',
  './manifest.json',
  './icon-192x192.svg',
  './icon-512x512.svg',
  './icon-1024x1024.svg',
  './icon-emotion.svg',
  './icon-history.svg',
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
              return caches.match('./moodmend_ui_demo.html');
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
        
        // 否则从网络获取
        return fetch(event.request)
          .then((networkResponse) => {
            // 只缓存成功的GET请求
            if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
              const responseToCache = networkResponse.clone();
              caches.open(DYNAMIC_CACHE)
                .then((cache) => {
                  // 设置合理的缓存过期时间
                  const headers = new Headers(responseToCache.headers);
                  headers.append('sw-fetched-on', new Date().getTime().toString());
                  
                  cache.put(event.request, responseToCache);
                })
                .catch(error => console.error('缓存资源失败:', error));
            }
            return networkResponse;
          })
          .catch(() => {
            // 对于SVG图标，确保有回退
            if (event.request.url.endsWith('.svg')) {
              return caches.match('./icon-192x192.svg');
            }
            // 对于Chart.js，尝试返回缓存
            if (event.request.url.includes('chart.js')) {
              return caches.match('https://cdn.jsdelivr.net/npm/chart.js');
            }
          });
      })
  );
});

// API请求的网络优先策略，失败时返回离线响应
function fetchWithNetworkFallback(event) {
  event.respondWith(
    fetch(event.request.clone())
      .then(response => {
        // 如果成功获取，缓存GET请求的响应（用于离线访问）
        if (response.ok && event.request.method === 'GET') {
          const responseToCache = response.clone();
          caches.open(DYNAMIC_CACHE)
            .then(cache => {
              cache.put(event.request, responseToCache);
            })
            .catch(error => console.error('缓存API响应失败:', error));
        }
        return response;
      })
      .catch(() => {
        // 对于POST请求，返回离线响应
        if (event.request.method === 'POST') {
          return new Response(JSON.stringify({
            success: false,
            offline: true,
            message: 'MoodMend 當前處於離線狀態，請稍後再試'
          }), {
            headers: {
              'Content-Type': 'application/json'
            }
          });
        }
        // 對於GET請求，嘗試從動態緩存獲取
        return caches.match(event.request)
          .then(cachedResponse => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // 如果没有缓存，返回离线响应
            return new Response(JSON.stringify({
              success: false,
              offline: true,
              message: 'MoodMend 當前處於離線狀態，且無緩存數據'
            }), {
              headers: {
                'Content-Type': 'application/json'
              }
            });
          });
      })
  );
}

// 後台同步事件 - 同步離線日誌
self.addEventListener('sync', (event) => {
  console.log('Service Worker: 後台同步', event.tag);
  if (event.tag === 'sync-logs') {
    event.waitUntil(syncOfflineLogs());
  }
});

// 同步离线日志到服务器
async function syncOfflineLogs() {
  const clients = await self.clients.matchAll();
  
  // 向客户端发送消息，通知開始同步
  clients.forEach(client => {
    client.postMessage({ type: 'SYNC_STARTED' });
  });
  
  try {
    // 由於Service Worker無法直接訪問localStorage，需要依賴客戶端完成實際的同步
    // 這裡我們向所有客戶端發送消息，請求它們執行同步
    clients.forEach(client => {
      client.postMessage({ type: 'SYNC_LOGS' });
    });
    
    console.log('Service Worker: 請求客戶端同步離線日誌');
  } catch (error) {
    console.error('Service Worker: 後台同步失敗', error);
  }
}

// 推送通知事件
self.addEventListener('push', (event) => {
  if (!event.data) return;
  
  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'MoodMend 有新的情緒建議等待查看',
      icon: './icon-192x192.svg',
      badge: './icon-192x192.svg',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || './moodmend_ui_demo.html'
      },
      actions: [
        {
          action: 'view',
          title: '查看詳情'
        },
        {
          action: 'close',
          title: '關閉'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'MoodMend提醒', options)
    );
  } catch (error) {
    console.error('處理推送消息失敗:', error);
  }
});

// 通知點擊事件 
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'view' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((clientList) => {
        const url = event.notification.data.url;
        
        // 如果已有窗口打开，切换到该窗口
        for (const client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        
        // 否则打开新窗口
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
    );
  }
});

// 周期性后台同步（实验性功能）
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'daily-sync') {
    event.waitUntil(syncOfflineLogs());
  }
});

// 消息事件 - 接收来自客户端的消息
self.addEventListener('message', (event) => {
  console.log('Service Worker: 收到消息', event.data);
  
  // 处理不同类型的消息
  if (event.data && event.data.type) {
    switch (event.data.type) {
      case 'SKIP_WAITING':
        self.skipWaiting();
        break;
      case 'CLIENTS_CLAIM':
        self.clients.claim();
        break;
      case 'SYNC_COMPLETED':
        // 通知所有客户端同步完成
        self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({ type: 'SYNC_COMPLETED', data: event.data.data });
          });
        });
        break;
      case 'REFRESH_CACHE':
        // 刷新缓存
        event.waitUntil(
          caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => {
              event.source.postMessage({ type: 'CACHE_REFRESHED' });
            })
            .catch(error => {
              event.source.postMessage({ type: 'CACHE_REFRESH_FAILED', error: error.message });
            })
        );
        break;
    }
  }
  
  // 总是回复消息，确认已收到
  event.source.postMessage({ type: 'MESSAGE_RECEIVED', timestamp: Date.now() });
});