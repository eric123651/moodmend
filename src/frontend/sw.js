// MoodMend PWA Service Worker

// 导入数据库工具函数
importScripts('assets/db.js');

// 缓存名称和版本 - 增加版本号以确保更新
const CACHE_NAME = 'moodmend-v4';
const DYNAMIC_CACHE = 'moodmend-dynamic-v4';

// 需要缓存的核心资源
const STATIC_ASSETS = [
  '/',  // 根路径也需要缓存，确保离线时能访问
  './moodmend_ui_demo.html',
  './manifest.json',
  './assets/script.js',
  './assets/db.js',
  // 同时缓存SVG和PNG格式的图标，确保兼容性
  '../../icons/MoodMend_Logo_Option4.svg',
  '../../icons/MoodMend_Logo_Option4.png',
  '../../icons/MoodMend_Angry_Emotion.svg',
  '../../icons/MoodMend_Happy_Emotion.svg',
  '../../icons/MoodMend_Calm_Emotion.svg',
  '../../icons/MoodMend_Sad_Emotion.svg',
  '../../icons/MoodMend_Voice_Button_Simple.svg',
  '../../icons/MoodMend_End_Call_Button.svg',
  '../../icons/icon-moodmend.svg',
  '../../icons/icon-emotion.svg',
  '../../icons/icon-emotion.png',
  '../../icons/icon-history.svg',
  '../../icons/icon-history.png',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// 安装事件 - 预缓存核心资源
self.addEventListener('install', (event) => {
  console.log('Service Worker: 安裝中');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: 缓存核心資源');
        // 使用Promise.all处理缓存失败的情况，确保单个资源失败不会导致整个安装失败
        return Promise.all(
          STATIC_ASSETS.map(url => {
            return cache.add(url).catch(error => {
              console.warn('Service Worker: 缓存失败:', url, error);
              // 继续处理其他资源
              return true;
            });
          })
        );
      })
      .then(() => self.skipWaiting())
  );
});

// 后台同步功能，用于离线时保存数据
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-emotions') {
    event.waitUntil(syncEmotionData());
  }
});

// 实现后台同步逻辑
async function syncEmotionData() {
  try {
    // 获取待同步的数据
    console.log('开始同步情绪数据到服务器...');
    const unsyncedData = await self.getUnsyncedData();
    
    if (unsyncedData.length === 0) {
      console.log('没有需要同步的数据');
      const clients = await self.clients.matchAll();
      clients.forEach(client => {
        client.postMessage({ 
          type: 'SYNC_COMPLETED',
          timestamp: Date.now(),
          success: true,
          message: '没有需要同步的数据'
        });
      });
      return;
    }
    
    // 同步每条数据到服务器
    const syncedIds = [];
    for (const record of unsyncedData) {
      try {
        // 发送数据到服务器
        const response = await fetch('/api/emotions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(record)
        });
        
        if (response.ok) {
          syncedIds.push(record.id);
          console.log(`数据 ${record.id} 同步成功`);
        } else {
          console.error(`数据 ${record.id} 同步失败:`, await response.text());
        }
      } catch (syncError) {
        console.error(`同步单条数据失败:`, syncError);
        // 继续尝试同步其他数据
      }
    }
    
    // 标记已同步的数据
    if (syncedIds.length > 0) {
      await self.markAsSynced(syncedIds);
      console.log(`成功同步并标记 ${syncedIds.length} 条数据`);
    }
    
    // 通知所有客户端同步完成
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({ 
        type: 'SYNC_COMPLETED',
        timestamp: Date.now(),
        success: true,
        syncedCount: syncedIds.length,
        totalCount: unsyncedData.length,
        message: `成功同步 ${syncedIds.length}/${unsyncedData.length} 条数据`
      });
    });
  } catch (error) {
    console.error('后台同步失败:', error);
    // 通知客户端同步失败
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({ 
        type: 'SYNC_FAILED',
        timestamp: Date.now(),
        error: error.message || '未知错误'
      });
    });
  }
}

// 推送通知功能
self.addEventListener('push', (event) => {
  if (!event.data) return;
  
  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'MoodMend提醒',
      icon: '../../icons/MoodMend_Logo_Option4.png',
      badge: '../../icons/MoodMend_Logo_Option4.png',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || './moodmend_ui_demo.html'
      },
      actions: [
        { action: 'view', title: '查看详情' },
        { action: 'close', title: '关闭' }
      ],
      timestamp: Date.now(),
      renotify: true
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'MoodMend', options)
    );
  } catch (error) {
    console.error('处理推送消息失败:', error);
    try {
      event.waitUntil(
        self.registration.showNotification('MoodMend', {
          body: '您有一条新消息',
          icon: '../../icons/MoodMend_Logo_Option4.png',
          badge: '../../icons/MoodMend_Logo_Option4.png'
        })
      );
    } catch (notifyError) {
      console.error('显示通知失败:', notifyError);
    }
  }
});

// 点击通知事件
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(windowClients => {
      for (const client of windowClients) {
        if (client.url.includes('./moodmend_ui_demo.html') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});

// 周期性后台同步（需要浏览器支持）
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'daily-summary') {
    event.waitUntil(sendDailySummary());
  }
});

// 发送每日总结
async function sendDailySummary() {
  console.log('执行每日总结同步');
}

// 激活事件 - 清理舊缓存
self.addEventListener('activate', (event) => {
  console.log('Service Worker: 激活中');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== DYNAMIC_CACHE && cacheName.startsWith('moodmend-')) {
            console.log('Service Worker: 清理舊缓存', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    }).then(() => {
      return self.clients.matchAll().then(clients => {
        clients.forEach(client => {
          client.postMessage({ type: 'SW_UPDATED' });
        });
      });
    })
  );
}

// 资源请求策略：混合策略，优化离线体验
self.addEventListener('fetch', (event) => {
  const url = event.request.url;
  
  // 重要：不要拦截API请求，让它们直接发送到后端
  if (url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match(event.request).then(cachedResponse => {
            return cachedResponse || new Response(JSON.stringify({ 
              error: '网络连接不可用，无法获取数据',
              offline: true 
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }
  
  // 处理图标请求（SVG和PNG）
  if (url.includes('/icons/') && (url.endsWith('.svg') || url.endsWith('.png'))) {
    const iconName = url.split('/').pop();
    const correctIconPath = `../../icons/${iconName}`;
    
    event.respondWith(
      caches.match(correctIconPath)
        .then(cachedResponse => {
          if (cachedResponse) return cachedResponse;
          return fetch(correctIconPath)
            .then(response => {
              if (response.ok) {
                const responseToCache = response.clone();
                caches.open(DYNAMIC_CACHE)
                  .then(cache => cache.put(correctIconPath, responseToCache))
                  .catch(err => console.warn('缓存图标失败:', err));
                return response;
              }
              const altFormat = url.endsWith('.svg') ? url.replace('.svg', '.png') : url.replace('.png', '.svg');
              const altIconName = altFormat.split('/').pop();
              const altIconPath = `../../icons/${altIconName}`;
              
              return caches.match(altIconPath)
                .then(altCachedResponse => {
                  if (altCachedResponse) return altCachedResponse;
                  return fetch(altIconPath)
                    .catch(() => {
                      return caches.match('../../icons/MoodMend_Logo_Option4.png')
                        .then(defaultPngIcon => {
                          if (defaultPngIcon) return defaultPngIcon;
                          return caches.match('../../icons/MoodMend_Logo_Option4.svg')
                            .then(defaultSvgIcon => defaultSvgIcon || new Response('获取图标失败', { status: 404 }));
                        });
                    });
                });
            })
            .catch(error => {
              return caches.match('../../icons/MoodMend_Logo_Option4.png')
                .then(defaultPngIcon => {
                  if (defaultPngIcon) return defaultPngIcon;
                  return caches.match('../../icons/MoodMend_Logo_Option4.svg')
                    .then(defaultSvgIcon => defaultSvgIcon || new Response('获取图标失败', { status: 500 }));
                });
            });
        })
    );
    return;
  }
  
  // 拦截favicon.ico请求，优先使用PNG图标
  if (url.includes('favicon.ico')) {
    event.respondWith(
      caches.match('../../icons/MoodMend_Logo_Option4.png')
        .then(cachedResponse => {
          if (cachedResponse) return cachedResponse;
          return caches.match('../../icons/MoodMend_Logo_Option4.svg')
            .then(svgCachedResponse => {
              if (svgCachedResponse) return svgCachedResponse;
              return fetch('../../icons/MoodMend_Logo_Option4.png')
                .catch(() => fetch('../../icons/MoodMend_Logo_Option4.svg'))
                .catch(() => {
                  return new Response('Not Found', { status: 404 });
                });
            });
        })
    );
    return;
  }
  
  // 对于HTML页面请求，优先使用缓存优先策略，确保离线可用
  if (event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      caches.match(event.request)
        .then(cachedResponse => {
          if (cachedResponse) {
            fetch(event.request)
              .then(networkResponse => {
                if (networkResponse.ok) {
                  caches.open(DYNAMIC_CACHE)
                    .then(cache => cache.put(event.request, networkResponse))
                    .catch(err => console.warn('后台更新HTML缓存失败:', err));
                }
              })
              .catch(() => console.warn('后台更新HTML缓存失败'));
            return cachedResponse;
          }
          
          return fetch(event.request)
            .then(response => {
              if (response.ok) {
                const responseToCache = response.clone();
                caches.open(DYNAMIC_CACHE)
                  .then(cache => cache.put(event.request, responseToCache))
                  .catch(err => console.warn('缓存HTML页面失败:', err));
                return response;
              }
              return caches.match('./moodmend_ui_demo.html')
                .then(fallbackPage => fallbackPage || new Response('无法加载页面', { status: 503 }));
            })
            .catch(() => {
              return caches.match('./moodmend_ui_demo.html')
                .then(fallbackPage => fallbackPage || new Response('您当前处于离线状态', { 
                  status: 503,
                  headers: { 'Content-Type': 'text/html' }
                }));
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

  // 对于其他资源（CSS, JS, 图片等）使用缓存优先策略
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request)
          .then((response) => {
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            const responseToCache = response.clone();
            
            caches.open(DYNAMIC_CACHE)
              .then((cache) => {
                cache.put(event.request, responseToCache);
              })
              .catch(err => console.warn('缓存响应失败:', err));
            
            return response;
          })
          .catch(error => {
            if (event.request.url.match(/\.(jpe?g|png|gif|svg)$/)) {
              return new Response('占位图片', { headers: { 'Content-Type': 'text/plain' } });
            }
            return new Response('网络错误，无法加载资源', { status: 503 });
          });
      })
  );
}

// 网络优先，缓存回退的请求处理函数
function fetchWithNetworkFallback(event) {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response && response.status === 200) {
          const clonedResponse = response.clone();
          caches.open(DYNAMIC_CACHE)
            .then(cache => {
              cache.put(event.request, clonedResponse);
            })
            .catch(err => console.warn('缓存响应失败:', err));
        }
        return response;
      })
      .catch(() => {
        // 网络失败时尝试从缓存获取
        return caches.match(event.request).then(cachedResponse => {
          return cachedResponse || new Response('网络错误，无法加载资源', { status: 503 });
        });
      })
  );
}