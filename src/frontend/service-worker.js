// Service Worker Redirect to frontend sw.js
// 这个文件存在的目的是重定向service worker请求到正确的位置

// 立即安装并激活
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// 处理各种404错误请求
self.addEventListener('fetch', (event) => {
  const url = event.request.url;
  
  // 重要：不要拦截API请求，让它们直接发送到后端
  if (url.includes('/api/')) {
    return; // 不拦截API请求
  }
  
  // 处理SVG图标请求
  if (url.includes('/icons/') && url.endsWith('.svg')) {
    // 提取图标文件名
    const iconName = url.split('/').pop();
    // 构建正确的图标路径
    const correctIconPath = `../../icons/${iconName}`;
    
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
  
  // 处理/@vite/client请求，避免404错误
  if (url.includes('@vite/client')) {
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
  
  // 处理/favicon.ico请求
  if (url.includes('/favicon.ico')) {
    event.respondWith(
      fetch('./icons/icon-moodmend.svg')
        .then(response => {
          if (response.ok) {
            const modifiedResponse = new Response(response.body, response);
            modifiedResponse.headers.set('Content-Type', 'image/svg+xml');
            return modifiedResponse;
          }
          return new Response('Favicon Redirect', { status: 200 });
        })
        .catch(() => {
          return new Response('Favicon Redirect Fallback', { status: 200 });
        })
    );
    return;
  }
  
  // 对于HTML页面请求，检查是否为404路径
  if (event.request.headers.get('accept')?.includes('text/html')) {
    // 处理常见的错误路径重定向
    if (url.includes('/src/frontend/moodmend_ui_demo.html') || url.endsWith('/moodmend_ui_demo.html')) {
      event.respondWith(
        fetch('./moodmend_ui_demo.html')
          .then(response => {
            if (response.ok) {
              return response;
            }
            // 如果失败，尝试重定向到正确的路径
            return Response.redirect('./moodmend_ui_demo.html', 302);
          })
          .catch(() => {
            return new Response('Page Redirect', { 
              status: 200,
              headers: {
                'Content-Type': 'text/html',
                'Refresh': '0; url=./moodmend_ui_demo.html'
              }
            });
          })
      );
      return;
    }
  }
  
  // 对于其他请求，尝试加载前端目录中的实际service worker资源
  event.respondWith(
    fetch('./sw.js')
      .then(response => {
        if (response.ok) {
          return response;
        }
        return new Response('Service Worker Redirect', { status: 200 });
      })
      .catch(() => {
        return new Response('Service Worker Redirect Fallback', { status: 200 });
      })
  );
});