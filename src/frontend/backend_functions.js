// 后端功能的前端实现版本

// 情绪关键词字典（从后端迁移）
const EMOTION_KEYWORDS = {
    'happy': {
                'keywords': ['開心', '快樂', '高興', '愉快', '滿足', '興奮', '欣喜', '幸福', '喜悅', '歡樂', '愉悅', '狂喜', '欣慰', '滿意', '樂乎', '樂', '爽'],
        'weight': 1
    },
    'sad': {'keywords': ['傷心', '難過', '悲傷', '憂傷', '沮喪', '抑鬱', '絕望', '悲痛', '悲哀', '難過', '傷心欲絕', '哀傷', '惆悵', '失落', '痛苦', '哭', '泣', '慘'],
        'weight': 1
    },
    'anxious': {
        'keywords': ['焦慮', '緊張', '不安', '擔憂', '害怕', '恐懼', '恐慌', '驚嚇', '擔憂', '焦慮不安', '心悸', '發抖', '哆嗦', '忐忑', '惴惴', '慌'],
        'weight': 1
    },
    'angry': {
        'keywords': ['生氣', '憤怒', '惱怒', '惱火', '氣憤', '暴躁', '暴怒', '火大', '發飆', '怒不可遏', '氣死', '冒火', '動怒', '怒火', '憤恨', '怒'],
        'weight': 1
    },
    'neutral': {
        'keywords': ['平靜', '平常', '一般', '普通', '淡定', '冷靜', '沉穩', '心平氣和', '無所謂', '還行', '可以', '不錯', '馬馬虎虎', '過得去'],
        'weight': 1
    }
};

// 情绪分类（从后端迁移）
const NEGATIVE_EMOTIONS = ['sad', 'anxious', 'angry'];
const POSITIVE_EMOTIONS = ['happy'];

// 建议模板（从后端迁移）
const SUGGESTIONS = {
    'happy': {
        'daily_task': '與朋友分享你的快樂，傳遞正能量。',
        'advice': '保持良好的作息和饮食习惯，延续快樂的狀態。',
        'resources': '推薦閱讀：《快樂競爭力》'
    },
    'sad': {
        'tips': '允許自己感受悲傷，但不要沉浸其中太久。',
        'daily_task': '進行一項讓自己休息的活動，如冥想或聽音樂。',
        'advice': '與信任的人交流你的感受，尋求支持。',
        'resources': '推薦APP：潮汐（冥想放松）'
    },
    'anxious': {
        'tips': '嘗試深呼吸練習，幫助缓解緊張情緒。',
        'daily_task': '進行15分鐘的身體活動，釋放壓力。',
        'advice': '將大問題分解成小步驟，逐一解決。',
        'resources': '推薦練習：4-7-8呼吸法'
    },
    'angry': {
        'tips': '先深呼吸，數到10再做決定。',
        'daily_task': '進行一項體育活動，釋放能量。',
        'advice': '嘗試從對方角度思考問題，尋求理解。',
        'resources': '推薦APP：Calm'
    },
    'neutral': {
        'tips': '探索新的興趣爱好，豐富生活體驗。',
        'daily_task': '學習一項新技能或知識。',
        'advice': '設定小目標，逐步提升生活滿意度。',
        'resources': '推薦平台：Coursera（線上學習）'
    }
};

// NFT徽章定义（从后端迁移）
const NFT_BADGES = {
    'happy': '快樂獎勵',
    'sad': '雨過天晴',
    'anxious': '平靜之心',
    'angry': '情緒掌控者',
    'neutral': '平衡大師'
};

// 本地情绪分析函数
function detectEmotionLocal(text) {
    const scores = {};
    
    // 初始化所有情绪分数为0
    Object.keys(EMOTION_KEYWORDS).forEach(emotion => {
        scores[emotion] = 0;
    });
    
    // 遍历每种情绪的关键词并计算得分
    Object.entries(EMOTION_KEYWORDS).forEach(([emotion, data]) => {
        const keywords = data.keywords;
        const weight = data.weight;
        
        keywords.forEach(keyword => {
            if (text.includes(keyword)) {
                scores[emotion] += weight;
            }
        });
    });
    
    // 找出得分最高的情绪
    let maxScore = 0;
    let detectedEmotion = 'neutral'; // 默认中性
    
    Object.entries(scores).forEach(([emotion, score]) => {
        if (score > maxScore) {
            maxScore = score;
            detectedEmotion = emotion;
        }
    });
    
    return detectedEmotion;
}

// 生成建议函数
function generateAdvice(emotion) {
    return SUGGESTIONS[emotion] || SUGGESTIONS.neutral;
}

// 生成NFT徽章函数
function generateNftBadge(emotion, taskCompleted) {
    if (taskCompleted) {
        return `${NFT_BADGES[emotion]} - 任务达人`;
    }
    return NFT_BADGES[emotion];
}

// 检查情绪转移函数
async function checkEmotionTransition(currentEmotion, email) {
    // 从IndexedDB获取最近的情绪记录
    const recentRecords = await getRecentEmotions(email, 2);
    
    if (recentRecords.length >= 1) {
        const lastEmotion = recentRecords[0].emotion;
        
        // 检查是否从负面情绪转为正面情绪
        if (NEGATIVE_EMOTIONS.includes(lastEmotion) && POSITIVE_EMOTIONS.includes(currentEmotion)) {
            return {
                hasTransition: true,
                transitionType: 'negative_to_positive',
                previousEmotion: lastEmotion,
                currentEmotion: currentEmotion
            };
        }
    }
    
    return {
        hasTransition: false
    };
}

// 生成转换NFT徽章函数
function generateTransitionNft(transitionInfo) {
    if (transitionInfo.hasTransition && transitionInfo.transitionType === 'negative_to_positive') {
        return `情绪蜕变 - 从${getEmotionLabel(transitionInfo.previousEmotion)}到${getEmotionLabel(currentEmotion)}`;
    }
    return null;
}

// 获取情绪标签（中文显示）
function getEmotionLabel(emotion) {
    const labels = {
        'happy': '快樂',
        'sad': '悲傷',
        'anxious': '焦慮',
        'angry': '怒氣',
        'neutral': '平靜'
    };
    return labels[emotion] || emotion;
}

// 获取情绪颜色
function getEmotionColor(emotion) {
    const colors = {
        'happy': '#FFD93D',
        'sad': '#6BCF7F',
        'anxious': '#6BCF7F',
        'angry': '#FF6B6B',
        'neutral': '#6BCF7F'
    };
    return colors[emotion] || '#6BCF7F';
}

// 初始化数据库
async function initDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('MoodMendDB', 1);
        
        request.onerror = event => {
            console.error('打開數據庫失敗:', event.target.error);
            reject(event.target.error);
        };
        
        request.onsuccess = event => {
            const db = event.target.result;
            console.log('数据库连接成功');
            resolve(db);
        };
        
        request.onupgradeneeded = event => {
            const db = event.target.result;
            
            // 创建情绪记录表
            if (!db.objectStoreNames.contains('emotions')) {
                const emotionStore = db.createObjectStore('emotions', {
                    keyPath: 'id',
                    autoIncrement: true
                });
                emotionStore.createIndex('date', 'date', { unique: false });
                emotionStore.createIndex('synced', 'synced', { unique: false });
                emotionStore.createIndex('email', 'email', { unique: false });
            }
            
            // 创建用户表
            if (!db.objectStoreNames.contains('users')) {
                const userStore = db.createObjectStore('users', {
                    keyPath: 'email'
                });
            }
        };
    });
}

// 保存情绪日志
async function saveEmotionLog(logData) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readwrite');
        const store = transaction.objectStore('emotions');
        
        const record = {
            ...logData,
            date: new Date().toISOString(),
            synced: navigator.onLine,
            offlineId: Date.now().toString()
        };
        
        const request = store.add(record);
        
        request.onsuccess = () => {
            console.log('情绪日志保存成功');
            resolve(request.result);
        };
        
        request.onerror = event => {
            console.error('保存情绪日志失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 获取未同步的数据
async function getUnsyncedData() {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readonly');
        const store = transaction.objectStore('emotions');
        const index = store.index('synced');
        const request = index.getAll(false); // 获取所有未同步的数据
        
        request.onsuccess = () => {
            console.log(`找到 ${request.result.length} 条未同步数据`);
            resolve(request.result);
        };
        
        request.onerror = event => {
            console.error('获取未同步数据失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 将数据标记为已同步
async function markAsSynced(id) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readwrite');
        const store = transaction.objectStore('emotions');
        const request = store.get(id);
        
        request.onsuccess = () => {
            if (request.result) {
                const record = request.result;
                record.synced = true;
                
                const updateRequest = store.put(record);
                updateRequest.onsuccess = () => {
                    console.log(`记录 ${id} 已标记为已同步`);
                    resolve(true);
                };
                
                updateRequest.onerror = event => {
                    console.error('标记数据为已同步失败:', event.target.error);
                    reject(event.target.error);
                };
            } else {
                reject(new Error('记录不存在'));
            }
        };
        
        request.onerror = event => {
            console.error('查找记录失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 获取最近的情绪记录
async function getRecentEmotions(email, limit = 10) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readonly');
        const store = transaction.objectStore('emotions');
        // 直接获取所有记录，然后在内存中排序和筛选
        const request = store.getAll();
        
        request.onsuccess = () => {
            // 筛选出当前用户的记录并按日期倒序排列 - 优先使用time字段
            const records = request.result
                .filter(record => record.email === email)
                .sort((a, b) => {
                    const aTime = a.time || a.date;
                    const bTime = b.time || b.date;
                    return new Date(bTime) - new Date(aTime);
                })
                .slice(0, limit); // 限制返回数量
            
            resolve(records);
        };
        
        request.onerror = event => {
            console.error('获取情绪记录失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 获取所有情绪日志（用于分页）
async function getAllEmotionLogs(email, page = 1, pageSize = 10, emotionFilter = null, dateFilter = null, periodFilter = null) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readonly');
        const store = transaction.objectStore('emotions');
        const request = store.getAll();
        
        request.onsuccess = () => {
            let allRecords = request.result
                .filter(record => record.email === email);
            
            // 应用过滤条件
            if (emotionFilter) {
                allRecords = allRecords.filter(record => record.emotion === emotionFilter);
            }
            
            if (dateFilter) {
                allRecords = allRecords.filter(record => {
                    // 优先使用time字段，兼容date字段
                    const recordDateTime = record.time || record.date;
                    const recordDate = new Date(recordDateTime).toISOString().split('T')[0];
                    return recordDate.includes(dateFilter);
                });
            }
            
            if (periodFilter) {
                const now = new Date();
                let startTime = new Date();
                
                switch (periodFilter) {
                    case 'week':
                        startTime.setDate(now.getDate() - 7);
                        break;
                    case 'month':
                        startTime.setMonth(now.getMonth() - 1);
                        break;
                    case 'year':
                        startTime.setFullYear(now.getFullYear() - 1);
                        break;
                    case '6month':
                        startTime.setMonth(now.getMonth() - 6);
                        break;
                    case 'day':
                        startTime.setHours(0, 0, 0, 0);
                        break;
                }
                
                allRecords = allRecords.filter(record => {
                    // 优先使用time字段，兼容date字段
                    const recordDateTime = record.time || record.date;
                    return new Date(recordDateTime) >= startTime;
                });
            }
            
            // 按日期倒序排列 - 优先使用time字段，兼容date字段
            allRecords.sort((a, b) => {
                const aTime = a.time || a.date;
                const bTime = b.time || b.date;
                return new Date(bTime) - new Date(aTime);
            });
            
            // 分页处理
            const start = (page - 1) * pageSize;
            const end = start + pageSize;
            const pagedRecords = allRecords.slice(start, end);
            
            resolve({
                success: true,
                logs: pagedRecords,
                total: allRecords.length,
                page: page,
                pageSize: pageSize
            });
        };
        
        request.onerror = event => {
            console.error('获取所有情绪日志失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 获取统计数据
async function getStats(email) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['emotions'], 'readonly');
        const store = transaction.objectStore('emotions');
        const request = store.getAll();
        
        request.onsuccess = () => {
            const userRecords = request.result.filter(record => record.email === email);
            
            // 计算完成率
            const totalTasks = userRecords.length;
            const completedTasks = userRecords.filter(record => record.completed).length;
            const completionRate = totalTasks > 0 ? (completedTasks / totalTasks * 100) : 0;
            
            // 计算情绪转移次数
            let transitionCount = 0;
            for (let i = 1; i < userRecords.length; i++) {
                if (NEGATIVE_EMOTIONS.includes(userRecords[i-1].emotion) && 
                    POSITIVE_EMOTIONS.includes(userRecords[i].emotion)) {
                    transitionCount++;
                }
            }
            
            // 计算情绪分布
            const emotionDistribution = {};
            Object.keys(EMOTION_KEYWORDS).forEach(emotion => {
                emotionDistribution[emotion] = 0;
            });
            
            userRecords.forEach(record => {
                emotionDistribution[record.emotion] = (emotionDistribution[record.emotion] || 0) + 1;
            });
            
            // 计算连续打卡天数
            const sortedRecords = [...userRecords].sort((a, b) => new Date(a.date) - new Date(b.date));
            let streak = 0;
            let currentStreak = 0;
            let lastDate = null;
            
            sortedRecords.forEach(record => {
                const recordDate = new Date(record.date);
                recordDate.setHours(0, 0, 0, 0);
                
                if (!lastDate) {
                    currentStreak = 1;
                } else {
                    const diffTime = Math.abs(recordDate - lastDate);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    
                    if (diffDays === 1) {
                        currentStreak++;
                    } else if (diffDays > 1) {
                        currentStreak = 1;
                    }
                }
                
                streak = Math.max(streak, currentStreak);
                lastDate = recordDate;
            });
            
            resolve({
                completion_rate: completionRate,
                transition_count: transitionCount,
                emotion_distribution: emotionDistribution,
                streak: streak
            });
        };
        
        request.onerror = event => {
            console.error('获取统计数据失败:', event.target.error);
            reject(event.target.error);
        };
    });
}

// 注册用户
async function registerUser(userData) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['users'], 'readwrite');
        const store = transaction.objectStore('users');
        
        // 先检查用户是否已存在
        const checkRequest = store.get(userData.email);
        
        checkRequest.onsuccess = () => {
            if (checkRequest.result) {
                reject({ success: false, message: '邮箱已被注册' });
                return;
            }
            
            // 创建新用户（简化版，实际应用中应该加密密码）
            const newUser = {
                email: userData.email,
                password: userData.password, // 注意：实际应用中应该加密存储
                user_name: userData.user_name,
                created_at: new Date().toISOString()
            };
            
            const addRequest = store.add(newUser);
            
            addRequest.onsuccess = () => {
                resolve({ success: true, email: userData.email, user_name: userData.user_name });
            };
            
            addRequest.onerror = event => {
                console.error('注册用户失败:', event.target.error);
                reject({ success: false, message: '注册失败，请稍后重试' });
            };
        };
        
        checkRequest.onerror = event => {
            console.error('检查用户是否存在失败:', event.target.error);
            reject({ success: false, message: '注册失败，请稍后重试' });
        };
    });
}

// 用户登录
async function loginUser(email, password) {
    const db = await initDatabase();
    
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['users'], 'readonly');
        const store = transaction.objectStore('users');
        const request = store.get(email);
        
        request.onsuccess = () => {
            const user = request.result;
            
            if (!user) {
                // 检查是否是测试账号
                if (email === 'test@example.com' && password === 'password123') {
                    resolve({ success: true, email: email, user_name: '测试用户' });
                    return;
                }
                reject({ success: false, message: '用户不存在' });
                return;
            }
            
            // 简化版密码验证（实际应用中应该使用密码加密和验证）
            if (user.password === password) {
                resolve({ success: true, email: user.email, user_name: user.user_name });
            } else {
                reject({ success: false, message: '密码错误' });
            }
        };
        
        request.onerror = event => {
            console.error('登录失败:', event.target.error);
            reject({ success: false, message: '登录失败，请稍后重试' });
        };
    });
}

// 处理情绪输入的主函数
async function processEmotionLocal(input, email, taskCompleted = false) {
    try {
        // 1. 检测情绪
        const emotion = detectEmotionLocal(input);
        
        // 2. 生成建议
        const suggestions = generateAdvice(emotion);
        
        // 3. 生成NFT徽章
        let nft = generateNftBadge(emotion, taskCompleted);
        
        // 4. 检查情绪转移
        const transitionInfo = await checkEmotionTransition(emotion, email);
        if (transitionInfo.hasTransition) {
            const transitionNft = generateTransitionNft(transitionInfo);
            if (transitionNft) {
                nft = transitionNft;
            }
        }
        
        // 5. 保存日志
        await saveEmotionLog({
            email: email,
            emotion: emotion,
            input: input,
            task: suggestions.daily_task,
            completed: taskCompleted,
            nft: nft
        });
        
        // 6. 返回结果
        return {
            success: true,
            emotion: getEmotionLabel(emotion),
            package: {
                tips: suggestions.tips,
                daily_task: suggestions.daily_task,
                advice: suggestions.advice,
                resources: suggestions.resources,
                color: getEmotionColor(emotion)
            },
            nft: nft
        };
    } catch (error) {
        console.error('处理情绪失败:', error);
        return {
            success: false,
            message: '处理情绪失败，请稍后重试'
        };
    }
}

// 导出所有函数供前端使用
if (typeof window !== 'undefined') {
    // 浏览器环境
    window.backendFunctions = {
        detectEmotionLocal,
        generateAdvice,
        generateNftBadge,
        checkEmotionTransition,
        generateTransitionNft,
        getEmotionLabel,
        getEmotionColor,
        initDatabase,
        saveEmotionLog,
        getRecentEmotions,
        getAllEmotionLogs,
        getStats,
        registerUser,
        loginUser,
        processEmotionLocal,
        getUnsyncedData,
        markAsSynced
    };
} else {
    // Node.js环境（如果需要）
    module.exports = {
        detectEmotionLocal,
        generateAdvice,
        generateNftBadge,
        checkEmotionTransition,
        generateTransitionNft,
        getEmotionLabel,
        getEmotionColor,
        initDatabase,
        saveEmotionLog,
        getRecentEmotions,
        getAllEmotionLogs,
        getStats,
        registerUser,
        loginUser,
        processEmotionLocal,
        getUnsyncedData,
        markAsSynced
    };
}
