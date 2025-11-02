// 前端脚本，处理用户交互和离线数据存储

// 从db.js导入数据库操作函数
import { addLog } from './db.js';

// 初始化函数
export function initPage() {
  console.log('初始化前端脚本...');
  
  // 注册页面切换事件监听
  document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
  });
}

// 设置事件监听器
function setupEventListeners() {
  console.log('设置事件监听器...');
  
  // 监听Page3的任务完成按钮
  const completeTaskButtons = document.querySelectorAll('.complete-task-btn, [data-action="complete-task"]');
  completeTaskButtons.forEach(button => {
    button.addEventListener('click', handleTaskComplete);
  });
  
  // 监听网络状态变化
  window.addEventListener('online', handleNetworkOnline);
  window.addEventListener('offline', handleNetworkOffline);
}

// 处理任务完成事件
async function handleTaskComplete(event) {
  event.preventDefault();
  
  try {
    // 获取任务相关信息
    const taskElement = event.target.closest('[data-task-id], .task-item');
    const taskId = taskElement?.dataset.taskId || `task-${Date.now()}`;
    const taskName = taskElement?.dataset.taskName || taskElement?.querySelector('.task-name')?.textContent || '未知任务';
    const emotion = taskElement?.dataset.emotion || getCurrentEmotion();
    
    // 创建日志数据
    const logData = {
      emotion: emotion,
      task: taskName,
      taskId: taskId,
      completed: true,
      timestamp: new Date().toISOString(),
      userId: localStorage.getItem('currentUser') || 'anonymous'
    };
    
    // 保存日志到IndexedDB
    console.log('保存任务完成日志:', logData);
    const logId = await addLog(logData);
    
    // 显示成功提示
    showToast('任务已记录');
    
    // 如果离线，注册后台同步
    if (!navigator.onLine) {
      await registerBackgroundSync();
    }
    
    // 更新UI
    updateTaskUI(taskElement);
    
  } catch (error) {
    console.error('处理任务完成时出错:', error);
    showToast('保存任务失败，请重试');
  }
}

// 获取当前页面选择的情绪
function getCurrentEmotion() {
  const selectedEmotion = document.querySelector('.emotion-selected, [data-emotion-selected="true"]');
  return selectedEmotion?.dataset.emotion || 'neutral';
}

// 更新任务UI状态
function updateTaskUI(taskElement) {
  if (!taskElement) return;
  
  // 添加完成样式
  taskElement.classList.add('task-completed');
  taskElement.classList.remove('task-pending');
  
  // 更新完成状态图标
  const statusIcon = taskElement.querySelector('.task-status-icon');
  if (statusIcon) {
    statusIcon.textContent = '✓';
    statusIcon.style.color = '#4CAF50';
  }
  
  // 禁用完成按钮
  const completeButton = taskElement.querySelector('.complete-task-btn');
  if (completeButton) {
    completeButton.disabled = true;
    completeButton.textContent = '已完成';
  }
}

// 注册后台同步
async function registerBackgroundSync() {
  try {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-emotions');
      console.log('后台同步已注册');
      return true;
    } else {
      console.warn('浏览器不支持后台同步');
      return false;
    }
  } catch (error) {
    console.error('注册后台同步失败:', error);
    return false;
  }
}

// 网络恢复时处理
function handleNetworkOnline() {
  console.log('网络已连接');
  showToast('网络已恢复，正在同步数据...');
  
  // 尝试立即同步数据
  syncDataIfNeeded();
}

// 网络断开时处理
function handleNetworkOffline() {
  console.log('网络已断开，将使用离线模式');
  showToast('网络已断开，数据将在网络恢复后同步');
}

// 根据需要同步数据
async function syncDataIfNeeded() {
  try {
    // 检查是否有待同步的数据
    // 这里可以直接调用API服务或者注册后台同步
    await registerBackgroundSync();
  } catch (error) {
    console.error('尝试同步数据时出错:', error);
  }
}

// 显示提示消息
function showToast(message, duration = 3000) {
  // 检查是否已存在toast元素
  let toast = document.getElementById('toast-message');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-message';
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    toast.style.color = 'white';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '20px';
    toast.style.zIndex = '10000';
    toast.style.fontSize = '14px';
    toast.style.boxShadow = '0 2px 10px rgba(0,0,0,0.3)';
    toast.style.transition = 'opacity 0.3s ease';
    document.body.appendChild(toast);
  }
  
  // 重置显示
  clearTimeout(toast.timeoutId);
  toast.style.display = 'block';
  toast.style.opacity = '1';
  toast.textContent = message;
  
  // 设置自动隐藏
  toast.timeoutId = setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 300);
  }, duration);
}

// 导出全局方法
export function completeTask(taskData) {
  return addLog(taskData).then(logId => {
    if (!navigator.onLine) {
      return registerBackgroundSync().then(() => logId);
    }
    return logId;
  });
}

// 自动初始化
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    initPage();
  });
}