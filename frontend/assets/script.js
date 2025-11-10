// MoodMend 前端核心脚本

// API 基础URL
const API_BASE_URL = 'http://localhost:3000/api';

// 登录功能
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            // 注意：后端API期望email参数，而不是username
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email: username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // 保存token
                localStorage.setItem('token', data.token);
                // 跳转到互动页面
                window.location.href = 'interact.html';
            } else {
                alert('登录失败: ' + data.message);
            }
        } catch (error) {
            console.error('登录错误:', error);
            alert('登录时发生错误，请稍后重试');
        }
    });
}

// 互动页面功能
if (document.getElementById('voiceButton')) {
    const voiceButton = document.getElementById('voiceButton');
    const statusText = document.getElementById('statusText');
    const resultContainer = document.getElementById('resultContainer');
    const emotionBadge = document.getElementById('emotionBadge');
    const analysisText = document.getElementById('analysisText');
    
    let recognition = null;
    
    // 初始化语音识别
    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.lang = 'zh-CN';
            recognition.interimResults = false;
            
            recognition.onstart = () => {
                statusText.textContent = '正在聆听...';
                voiceButton.style.transform = 'scale(1.2)';
            };
            
            recognition.onresult = async (event) => {
                const transcript = event.results[0][0].transcript;
                statusText.textContent = '正在分析...';
                
                // 处理语音内容
                await processEmotion(transcript);
            };
            
            recognition.onend = () => {
                voiceButton.style.transform = 'scale(1)';
                if (statusText.textContent === '正在聆听...') {
                    statusText.textContent = '点击开始录音';
                }
            };
            
            recognition.onerror = (event) => {
                console.error('语音识别错误:', event.error);
                statusText.textContent = '识别出错，请重试';
                voiceButton.style.transform = 'scale(1)';
            };
        } else {
            statusText.textContent = '浏览器不支持语音识别';
            voiceButton.disabled = true;
        }
    }
    
    // 处理情绪分析
    async function processEmotion(text) {
        try {
            const response = await fetch(`${API_BASE_URL}/process-emotion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ text })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // 显示分析结果
                resultContainer.classList.remove('hidden');
                emotionBadge.textContent = getEmotionText(data.emotion);
                emotionBadge.className = `emotion-badge ${data.emotion}`;
                analysisText.textContent = `你现在的情绪是${getEmotionText(data.emotion)}，置信度: ${(data.confidence * 100).toFixed(1)}%`;
                
                // 2秒后自动跳转到日志页面
                setTimeout(() => {
                    window.location.href = 'log.html';
                }, 2000);
            } else {
                statusText.textContent = '分析失败，请重试';
            }
        } catch (error) {
            console.error('情绪分析错误:', error);
            statusText.textContent = '分析时发生错误';
        }
    }
    
    // 获取情绪文本
    function getEmotionText(emotion) {
        const emotionMap = {
            'happy': '开心',
            'sad': '难过',
            'angry': '生气',
            'calm': '平静',
            'neutral': '中性'
        };
        return emotionMap[emotion] || '未知';
    }
    
    // 绑定按钮事件
    voiceButton.addEventListener('click', () => {
        if (!recognition) {
            initSpeechRecognition();
        }
        recognition.start();
    });
}

// 日志页面功能
if (document.getElementById('emotionChart')) {
    // 获取日志数据并显示
    async function loadLogs() {
        try {
            const response = await fetch(`${API_BASE_URL}/get-logs`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                renderChart(data.logs);
                renderLogsList(data.logs);
            } else {
                console.error('获取日志失败:', data.message);
            }
        } catch (error) {
            console.error('获取日志错误:', error);
        }
    }
    
    // 渲染图表
    function renderChart(logs) {
        const ctx = document.getElementById('emotionChart').getContext('2d');
        
        // 提取数据
        const labels = logs.map(log => new Date(log.timestamp).toLocaleString());
        const emotions = ['happy', 'sad', 'angry', 'calm', 'neutral'];
        
        // 创建图表数据
        const datasets = emotions.map(emotion => ({
            label: getEmotionText(emotion),
            data: logs.map(log => log.emotion === emotion ? log.confidence : 0),
            borderColor: getEmotionColor(emotion),
            backgroundColor: getEmotionColor(emotion, 0.2),
            tension: 0.1
        }));
        
        // 创建图表
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '情绪变化趋势'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                }
            }
        });
    }
    
    // 渲染日志列表
    function renderLogsList(logs) {
        const logsContainer = document.getElementById('logsContainer');
        logsContainer.innerHTML = '';
        
        logs.forEach(log => {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            entry.innerHTML = `
                <span class="emotion">${getEmotionText(log.emotion)}</span>
                <span class="timestamp">${new Date(log.timestamp).toLocaleString()}</span>
            `;
            
            logsContainer.appendChild(entry);
        });
    }
    
    // 获取情绪文本
    function getEmotionText(emotion) {
        const emotionMap = {
            'happy': '开心',
            'sad': '难过',
            'angry': '生气',
            'calm': '平静',
            'neutral': '中性'
        };
        return emotionMap[emotion] || '未知';
    }
    
    // 获取情绪颜色
    function getEmotionColor(emotion, alpha = 1) {
        const colorMap = {
            'happy': `rgba(255, 217, 61, ${alpha})`,
            'sad': `rgba(107, 207, 246, ${alpha})`,
            'angry': `rgba(255, 107, 107, ${alpha})`,
            'calm': `rgba(149, 225, 211, ${alpha})`,
            'neutral': `rgba(248, 181, 0, ${alpha})`
        };
        return colorMap[emotion] || `rgba(128, 128, 128, ${alpha})`;
    }
    
    // 加载日志
    loadLogs();
}

// 页面初始化检查登录状态
function checkAuth() {
    // 如果不是登录页面且没有token，则跳转到登录页面
    if (!window.location.pathname.includes('index.html') && !localStorage.getItem('token')) {
        window.location.href = 'index.html';
    }
}

// 页面加载完成后执行
window.addEventListener('DOMContentLoaded', checkAuth);