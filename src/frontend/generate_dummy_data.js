// 生成模拟情绪记录数据并添加到IndexedDB
async function generateAndAddDummyData() {
    // 初始化数据库连接
    let db;
    await new Promise((resolve, reject) => {
        const request = indexedDB.open('MoodMendDB', 1);
        
        request.onerror = event => {
            console.error('打开数据库失败:', event.target.error);
            reject(event.target.error);
        };
        
        request.onsuccess = event => {
            db = event.target.result;
            console.log('数据库连接成功');
            resolve();
        };
        
        request.onupgradeneeded = event => {
            db = event.target.result;
            
            // 创建情绪记录表（如果不存在）
            if (!db.objectStoreNames.contains('emotions')) {
                const emotionStore = db.createObjectStore('emotions', {
                    keyPath: 'id',
                    autoIncrement: true
                });
                emotionStore.createIndex('date', 'date', { unique: false });
                emotionStore.createIndex('synced', 'synced', { unique: false });
            }
        };
    });

    // 情绪类型
    const emotions = ['happy', 'sad', 'anxious', 'neutral', 'angry'];
    
    // 任务类型
    const tasks = ['冥想', '锻炼', '阅读', '写日记', '社交活动', '听音乐', '散步'];
    
    // NFT/徽章类型
    const nfts = ['宁静之心', '活力四射', '思考者', '平衡大师', '情绪掌控者', '阳光明媚', '内心平静'];
    
    // 生成30条模拟记录，覆盖过去30天
    const dummyRecords = [];
    const now = new Date();
    
    for (let i = 0; i < 30; i++) {
        // 生成过去30天内的随机日期
        const recordDate = new Date(now);
        recordDate.setDate(now.getDate() - Math.floor(Math.random() * 30));
        recordDate.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60));
        
        // 随机选择情绪、任务和徽章
        const emotion = emotions[Math.floor(Math.random() * emotions.length)];
        const task = tasks[Math.floor(Math.random() * tasks.length)];
        const nft = nfts[Math.floor(Math.random() * nfts.length)];
        
        // 随机决定任务是否完成
        const completed = Math.random() > 0.3;
        
        // 创建记录
        dummyRecords.push({
            emotion: emotion,
            task: task,
            completed: completed,
            nft: nft,
            date: recordDate.toISOString(),
            synced: true,
            offlineId: Date.now().toString() + i,
            time: recordDate.toLocaleString('zh-TW') // 格式化为台湾地区时间
        });
    }

    // 批量添加记录到IndexedDB
    await new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readwrite');
        const store = transaction.objectStore('emotions');
        
        dummyRecords.forEach(record => {
            const request = store.add(record);
            request.onsuccess = () => {
                console.log(`已添加模拟记录: ${record.emotion} - ${record.task}`);
            };
            request.onerror = event => {
                console.error('添加模拟记录失败:', event.target.error);
            };
        });
        
        transaction.oncomplete = () => {
            console.log('所有模拟数据添加完成，共', dummyRecords.length, '条记录');
            resolve();
        };
        
        transaction.onerror = event => {
            console.error('批量添加数据失败:', event.target.error);
            reject(event.target.error);
        };
    });

    return dummyRecords.length;
}

// 执行数据生成
if (typeof window !== 'undefined') {
    // 在浏览器环境中执行
    generateAndAddDummyData().then(count => {
        console.log(`成功添加${count}条模拟情绪记录数据`);
    }).catch(error => {
        console.error('生成模拟数据失败:', error);
    });
} else {
    // 导出函数供其他模块使用
    module.exports = { generateAndAddDummyData };
}
