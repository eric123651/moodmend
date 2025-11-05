// MoodMend PWA Service Worker

// 缓存名称和版本 - 增加版本号以确保更新
const CACHE_NAME = 'moodmend-v3';
const DYNAMIC_CACHE = 'moodmend-dynamic-v3';

// 需要缓存的核心资源
const STATIC_ASSETS = [
  '/',  // 根路径也需要缓存，确保离线时能访问
  './moodmend_ui_demo.html',
  './manifest.json',
  '/icons/MoodMend_Logo_Option4.svg',
  '/icons/MoodMend_Angry_Emotion.svg',
  '/icons/MoodMend_Happy_Emotion.svg',
  '/icons/MoodMend_Calm_Emotion.svg',
  '/icons/MoodMend_Sad_Emotion.svg',
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
  const url = event.request.url;
  
  // 处理SVG图标请求
  if (url.includes('/icons/') && url.endsWith('.svg')) {
    // 提取图标文件名
    const iconName = url.split('/').pop();
    // 构建正确的图标路径
    const correctIconPath = `/icons/${iconName}`;
    
    event.respondWith(
      fetch(correctIconPath)
        .then(response => {
          if (response.ok) {
            return response;
          }
          console.error('SVG图标未找到:', correctIconPath);
          return new Response('SVG图标未找到', { status: 404 });
        })
        .catch(error => {
          console.error('获取SVG图标失败:', error);
          return new Response('获取SVG图标失败', { status: 500 });
        })
    );
    return;
  }
  
  // 拦截favicon.ico请求，重定向到我们的SVG图标
  if (url.includes('favicon.ico')) {
    event.respondWith(
      caches.match('/icons/icon-moodmend.svg')
        .then(cachedResponse => {
          if (cachedResponse) return cachedResponse;
          return fetch('/icons/icon-moodmend.svg')
            .catch(() => {
              // 如果都失败，返回一个基本的响应
              return new Response('Not Found', { status: 404 });
            });
        })
    );
    return;
  }
  
  // 处理/@vite/client请求，避免404错误
  if (event.request.url.includes('@vite/client')) {
    event.respondWith(
      new Response('Vite Client Not Available in Production', {
        status: 200,
        headers: {
          'Content-Type': 'application/javascript'
        }
      })
    );
    return;
  }
  
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
        .catch(error => {
          console.log('Service Worker: API请求失败，尝试从缓存获取', event.request.url, error);
          return caches.match(event.request)
            .then(cachedResponse => {
              if (cachedResponse) {
                console.log('Service Worker: 从缓存返回API响应', event.request.url);
                return cachedResponse;
              }
              // API请求失败且无缓存时，返回503离线状态
              return new Response(JSON.stringify({ error: '您当前处于离线状态' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
              });
            });
        })
    );
  }

// 处理后台同步事件
self.addEventListener('sync', (event) => {
  console.log('Service Worker: 后台同步触发', event.tag);
  if (event.tag === 'sync-offline-data') {
    event.waitUntil(syncOfflineLogs());
  }
});

// 同步离线日志数据
async function syncOfflineLogs() {
  try {
    // 从IndexedDB获取离线存储的日志
    const offlineLogs = await getOfflineLogs();
    
    if (offlineLogs && offlineLogs.length > 0) {
      console.log('Service Worker: 开始同步', offlineLogs.length, '条离线日志');
      
      // 逐条同步日志
      for (const log of offlineLogs) {
        try {
          const response = await fetch('http://localhost:5000/api/add-log', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(log)
          });
          
          if (response.ok) {
            console.log('Service Worker: 离线日志同步成功');
            // 同步成功后删除离线日志
            await deleteOfflineLog(log.id);
          }
        } catch (error) {
          console.error('Service Worker: 单条日志同步失败', error);
        }
      }
      
      console.log('Service Worker: 离线日志同步完成');
      // 发送同步完成通知给客户端
      const clients = await self.clients.matchAll();
      clients.forEach(client => {
        client.postMessage({ type: 'SYNC_COMPLETED' });
      });
    }
  } catch (error) {
    console.error('Service Worker: 离线日志同步失败', error);
  }
}

// 获取离线日志（模拟函数，实际应使用IndexedDB）
function getOfflineLogs() {
  return new Promise((resolve) => {
    // 这里应该从IndexedDB获取数据
    // 由于没有实际的IndexedDB实现，这里返回空数组
    resolve([]);
  });
}

// 删除离线日志（模拟函数）
function deleteOfflineLog(logId) {
  return new Promise((resolve) => {
    // 这里应该从IndexedDB删除数据
    resolve();
  });
}

// 处理推送通知
self.addEventListener('push', (event) => {
  if (!event.data) return;
  
  try {
    const data = event.data.json();
    const options = {
      body: data.body || '您有新的情绪建议',
      icon: '/icons/MoodMend_Logo_Option4.svg',
      badge: '/icons/MoodMend_Logo_Option4.svg',
      data: {
        url: data.url || '/',
        timestamp: Date.now()
      },
      vibrate: [100, 50, 100],
      actions: data.actions || [
        {
          action: 'view',
          title: '查看详情'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'MoodMend', options)
    );
  } catch (error) {
    console.error('Service Worker: 推送通知处理失败', error);
  }
});

// 处理通知点击事件
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      const url = event.notification.data.url;
      
      // 如果已经有打开的窗口，则切换到该窗口
      for (const client of clientList) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // 否则打开新窗口
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

// 实现推送订阅
self.addEventListener('pushsubscriptionchange', (event) => {
  console.log('Service Worker: 推送订阅已更改');
  event.waitUntil(
    // 重新订阅推送服务
    self.registration.pushManager.subscribe(event.oldSubscription.options)
      .then((newSubscription) => {
        // 将新的订阅信息发送到服务器
        return fetch('http://localhost:5000/api/update-push-subscription', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(newSubscription)
        });
      })
  );
});

// 定期缓存更新（可选）
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// 实现内容安全策略兼容
self.addEventListener('contentsecuritypolicyviolation', (event) => {
  console.warn('Service Worker: 内容安全策略违规', event);
});