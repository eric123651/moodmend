// IndexedDB 工具函数，用于离线数据存储和同步

// 打开数据库连接
export async function openDB() {
  return new Promise((resolve, reject) => {
    // 打开MoodMendDB数据库，版本号为1
    const request = indexedDB.open('MoodMendDB', 1);
    
    request.onerror = event => {
      console.error('打开数据库失败:', event.target.error);
      reject(event.target.error);
    };
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      
      // 创建情绪记录表，如果不存在
      if (!db.objectStoreNames.contains('emotions')) {
        const emotionStore = db.createObjectStore('emotions', {
          keyPath: 'id',
          autoIncrement: true
        });
        // 创建索引以便快速查询
        emotionStore.createIndex('date', 'date', { unique: false });
        emotionStore.createIndex('synced', 'synced', { unique: false });
        emotionStore.createIndex('email', 'email', { unique: false });
      }
    };
    
    request.onsuccess = event => {
      const db = event.target.result;
      console.log('数据库连接成功');
      
      // 监听数据库版本变化，需要重新连接
      db.onversionchange = () => {
        db.close();
        console.warn('数据库版本已更改，需要重新连接');
      };
      
      resolve(db);
    };
  });
}

// 添加日志到数据库
export async function addLog(logData) {
  try {
    const db = await openDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['emotions'], 'readwrite');
      const store = transaction.objectStore('emotions');
      
      // 创建记录对象，添加必要的字段
      const record = {
        ...logData,
        date: new Date().toISOString(),
        synced: navigator.onLine,
        offlineId: Date.now().toString() + Math.random().toString(36).substr(2, 9)
      };
      
      const request = store.add(record);
      
      request.onsuccess = () => {
        console.log('情绪日志保存成功，ID:', request.result);
        resolve(request.result);
      };
      
      request.onerror = event => {
        console.error('保存情绪日志失败:', event.target.error);
        reject(event.target.error);
      };
      
      transaction.oncomplete = () => {
        db.close();
      };
      
      transaction.onerror = () => {
        console.error('事务失败:', transaction.error);
      };
    });
  } catch (error) {
    console.error('添加日志时发生错误:', error);
    throw error;
  }
}

// 获取所有未同步的数据
export async function getUnsyncedData() {
  try {
    const db = await openDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['emotions'], 'readonly');
      const store = transaction.objectStore('emotions');
      const syncedIndex = store.index('synced');
      
      // 获取所有未同步的数据
      const request = syncedIndex.getAll(false);
      
      request.onsuccess = () => {
        console.log('获取未同步数据成功，共', request.result.length, '条');
        resolve(request.result);
      };
      
      request.onerror = event => {
        console.error('获取未同步数据失败:', event.target.error);
        reject(event.target.error);
      };
      
      transaction.oncomplete = () => {
        db.close();
      };
    });
  } catch (error) {
    console.error('获取未同步数据时发生错误:', error);
    throw error;
  }
}

// 标记数据为已同步
export async function markAsSynced(recordIds) {
  try {
    const db = await openDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['emotions'], 'readwrite');
      const store = transaction.objectStore('emotions');
      let updatedCount = 0;
      
      // 标记每条记录为已同步
      recordIds.forEach(id => {
        const request = store.get(id);
        
        request.onsuccess = () => {
          if (request.result) {
            const record = request.result;
            record.synced = true;
            record.syncedAt = new Date().toISOString();
            
            const updateRequest = store.put(record);
            
            updateRequest.onsuccess = () => {
              updatedCount++;
              console.log('数据已标记为同步:', id);
              
              // 检查是否所有记录都已更新
              if (updatedCount === recordIds.length) {
                resolve(updatedCount);
              }
            };
            
            updateRequest.onerror = event => {
              console.error('标记数据同步失败:', id, event.target.error);
              reject(event.target.error);
            };
          } else {
            updatedCount++;
            console.warn('要标记的记录不存在:', id);
            
            // 即使记录不存在，也要继续处理其他记录
            if (updatedCount === recordIds.length) {
              resolve(updatedCount);
            }
          }
        };
        
        request.onerror = event => {
          console.error('获取记录失败:', id, event.target.error);
          reject(event.target.error);
        };
      });
      
      transaction.oncomplete = () => {
        db.close();
      };
      
      transaction.onerror = () => {
        console.error('标记同步事务失败:', transaction.error);
      };
    });
  } catch (error) {
    console.error('标记数据同步时发生错误:', error);
    throw error;
  }
}

// 导出db.js中的函数到全局作用域，以便在service worker中使用
if (typeof self !== 'undefined') {
  self.openDB = openDB;
  self.addLog = addLog;
  self.getUnsyncedData = getUnsyncedData;
  self.markAsSynced = markAsSynced;
}