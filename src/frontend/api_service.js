// 统一API服务层 - 智能模式切换机制
// 根据网络状态自动在后端API和前端本地实现之间切换

// 确保window.apiService对象存在
window.apiService = window.apiService || {};

// 后端API基础URL
const API_BASE_URL = 'http://localhost:3000/api';

// 网络状态检测函数
window.apiService.isOnline = function() {
    return navigator.onLine;
}

// 显示提示信息
function showToast(message) {
    if (window.showToast) {
        window.showToast(message);
    } else {
        console.log('Toast:', message);
        // 如果没有showToast函数，创建临时提示
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.padding = '10px 20px';
        toast.style.backgroundColor = '#333';
        toast.style.color = 'white';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '9999';
        toast.style.opacity = '0';
        document.body.appendChild(toast);
        
        // 淡入淡出动画
        setTimeout(() => toast.style.opacity = '1', 10);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// 监听网络状态变化
window.apiService.setupNetworkListeners = function() {
    window.addEventListener('online', () => {
        console.log('网络已连接，切换到在线模式');
        showToast('已切换到在线模式，使用Google Cloud服务');
        // 网络恢复时尝试同步数据
        window.apiService.syncPendingData();
    });

    window.addEventListener('offline', () => {
        console.log('网络已断开，切换到离线模式');
        showToast('已切换到离线模式，使用本地功能');
    });
}

// 统一的情绪处理API
window.apiService.processEmotion = async function(input, email, taskCompleted = false) {
    // 根据网络状态选择实现方式
    if (window.apiService.isOnline()) {
        try {
            // 优先尝试后端API
            return await window.apiService.processEmotionOnline(input, email, taskCompleted);
        } catch (error) {
            console.log('后端API调用失败，回退到本地实现:', error);
            // 失败时回退到本地实现
            return await window.backendFunctions.processEmotionLocal(input, email, taskCompleted);
        }
    } else {
        // 离线状态直接使用本地实现
        return await window.backendFunctions.processEmotionLocal(input, email, taskCompleted);
    }
}

// 在线模式：调用后端API处理情绪
window.apiService.processEmotionOnline = async function(input, email, taskCompleted = false) {
    const response = await fetch(`${API_BASE_URL}/process-emotion`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email,
            input: input,
            task_completed: taskCompleted
        })
    });
    
    if (!response.ok) {
        throw new Error('后端API调用失败');
    }
    
    return await response.json();
}

// 统一的登录接口
window.apiService.login = async function(email, password) {
    if (window.apiService.isOnline()) {
        try {
            return await window.apiService.loginOnline(email, password);
        } catch (error) {
            console.log('后端登录失败，尝试本地登录:', error);
            return await window.backendFunctions.loginUser(email, password);
        }
    } else {
        return await window.backendFunctions.loginUser(email, password);
    }
}

// 在线模式：调用后端登录API
window.apiService.loginOnline = async function(email, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email,
            password: password
        })
    });
    
    if (!response.ok) {
        throw new Error('后端登录API调用失败');
    }
    
    return await response.json();
}

// 统一的注册接口
window.apiService.register = async function(userData) {
    if (window.apiService.isOnline()) {
        try {
            return await window.apiService.registerOnline(userData);
        } catch (error) {
            console.log('后端注册失败，尝试本地注册:', error);
            return await window.backendFunctions.registerUser(userData);
        }
    } else {
        return await window.backendFunctions.registerUser(userData);
    }
}

// 在线模式：调用后端注册API
window.apiService.registerOnline = async function(userData) {
    const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    });
    
    if (!response.ok) {
        throw new Error('后端注册API调用失败');
    }
    
    return await response.json();
}

// 统一的获取日志接口 - 支持多种参数格式
window.apiService.getLogs = async function(...args) {
    // 支持两种调用格式：
    // 1. getLogs(page, filters)
    // 2. getLogs(email, page, pageSize, emotionFilter, dateFilter, periodFilter)
    
    let email, page, pageSize, emotionFilter, dateFilter, periodFilter;
    
    if (args.length === 2 && typeof args[1] === 'object') {
        // 格式1: getLogs(page, filters)
        page = args[0];
        const filters = args[1];
        email = window.currentUser?.email || window.currentUser;
        pageSize = 10;
        emotionFilter = filters.emotion;
        dateFilter = filters.date;
        periodFilter = filters.period;
    } else {
        // 格式2: getLogs(email, page, pageSize, emotionFilter, dateFilter, periodFilter)
        email = args[0];
        page = args[1] || 1;
        pageSize = args[2] || 10;
        emotionFilter = args[3];
        dateFilter = args[4];
        periodFilter = args[5];
    }
    
    if (window.apiService.isOnline()) {
        try {
            return await window.apiService.getLogsOnline(page, {
                emotion: emotionFilter,
                date: dateFilter,
                period: periodFilter
            });
        } catch (error) {
            console.log('获取在线日志失败，使用本地数据:', error);
            return await window.backendFunctions.getAllEmotionLogs(
                email,
                page,
                pageSize,
                emotionFilter,
                dateFilter,
                periodFilter
            );
        }
    } else {
        return await window.backendFunctions.getAllEmotionLogs(
            email,
            page,
            pageSize,
            emotionFilter,
            dateFilter,
            periodFilter
        );
    }
}

// 在线模式：调用后端获取日志API
window.apiService.getLogsOnline = async function(page = 1, filters = {}) {
    const queryParams = new URLSearchParams();
    queryParams.append('page', page);
    queryParams.append('email', window.currentUser?.email || window.currentUser);
    
    if (filters.emotion) queryParams.append('emotion', filters.emotion);
    if (filters.date) queryParams.append('date', filters.date);
    if (filters.period) queryParams.append('period', filters.period);
    
    const response = await fetch(`${API_BASE_URL}/get-logs?${queryParams}`);
    
    if (!response.ok) {
        throw new Error('后端获取日志API调用失败');
    }
    
    return await response.json();
}

// 获取统计数据
window.apiService.getStats = async function(email) {
    if (window.apiService.isOnline()) {
        try {
            return await window.apiService.getStatsOnline(email);
        } catch (error) {
            console.log('获取在线统计数据失败，使用本地数据:', error);
            return await window.backendFunctions.getStats(email);
        }
    } else {
        return await window.backendFunctions.getStats(email);
    }
}

// 在线模式：获取统计数据
window.apiService.getStatsOnline = async function(email) {
    const response = await fetch(`${API_BASE_URL}/get-stats?email=${email}`);
    
    if (!response.ok) {
        throw new Error('后端获取统计数据API调用失败');
    }
    
    return await response.json();
}

// 数据同步函数
window.apiService.syncPendingData = async function() {
    if (!window.apiService.isOnline()) {
        console.log('当前离线，无法同步数据');
        return;
    }
    
    try {
        // 获取未同步的本地数据
        const pendingData = await window.backendFunctions.getUnsyncedData();
        
        if (pendingData && pendingData.length > 0) {
            showToast(`正在同步 ${pendingData.length} 条数据到服务器...`);
            
            // 逐条同步
            let syncedCount = 0;
            for (const data of pendingData) {
                try {
                    await syncSingleRecord(data);
                    // 同步成功后更新本地状态
                    await window.backendFunctions.markAsSynced(data.id);
                    syncedCount++;
                } catch (error) {
                    console.error('单条数据同步失败:', error);
                }
            }
            
            if (syncedCount > 0) {
                showToast(`成功同步 ${syncedCount} 条数据`);
                // 通知UI更新
                if (window.updateUIAfterSync) {
                    window.updateUIAfterSync();
                }
            }
        }
    } catch (error) {
        console.error('数据同步失败:', error);
    }
}

// 同步单条记录到后端
window.apiService.syncSingleRecord = async function(record) {
    // 根据记录类型选择不同的同步端点
    if (record.emotion && record.input) {
        // 情绪日志记录
        await fetch(`${API_BASE_URL}/add-log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(record)
        });
    }
    // 可以根据需要添加其他类型记录的同步逻辑
}

// 初始化API服务
window.apiService.initApiService = function() {
    // 设置网络监听器
    window.apiService.setupNetworkListeners();
    
    // 检查初始网络状态
    const initialStatus = window.apiService.isOnline() ? '在线' : '离线';
    console.log(`应用已启动，当前网络状态: ${initialStatus}`);
    
    // 立即尝试同步未同步的数据（如果在线）
    if (window.apiService.isOnline()) {
        setTimeout(window.apiService.syncPendingData, 1000);
    }
}

// 确保API服务已正确初始化到全局作用域
if (typeof window !== 'undefined') {
    // 所有方法已经通过window.apiService.xxx方式定义，无需重新赋值
    console.log('API服务已正确注册到window.apiService');
    
    // 确保switchPage函数在全局可用
    if (typeof window.switchPage !== 'function') {
        window.switchPage = function(id, event = null) {
            // 先关闭所有菜单
            const menus = document.querySelectorAll('.menu-dropdown');
            if (menus.length > 0) {
                menus.forEach(menu => {
                    menu.classList.remove('show');
                });
            }
            
            // 隐藏所有页面
            const pages = document.querySelectorAll('.page');
            if (pages.length > 0) {
                pages.forEach(p => {
                    p.classList.remove('active');
                });
            }
            
            // 显示目标页面
            const targetPage = document.getElementById(id);
            if (targetPage) {
                targetPage.classList.add('active');
            }
            
            // 当切换到page4时，尝试刷新日志
            if (id === 'page4' && typeof window.loadLogs === 'function') {
                setTimeout(() => {
                    window.loadLogs(1);
                }, 100);
            }
        };
    }
}
