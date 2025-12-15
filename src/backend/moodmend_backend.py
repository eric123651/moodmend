# MoodMend 后端服务 - 优化版
# 作者: AI Assistant
# 版本: 4.0
# 运行: python moodmend_backend.py

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from datetime import datetime, timedelta
import re
import json
import os
import logging
import uuid
import bcrypt
import sqlite3
import threading
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 配置日志
# 设置默认编码为UTF-8
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 创建自定义的StreamHandler，确保UTF-8编码
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # 尝试编码为系统默认编码，替换无法编码的字符
            msg = self.format(record)
            if hasattr(stream, 'encoding'):
                msg = msg.encode(stream.encoding, errors='replace').decode(stream.encoding)
            stream.write(msg + self.terminator)
            self.flush()

# Get log configuration from environment
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'moodmend.log')

logging.basicConfig(level=getattr(logging, LOG_LEVEL), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'),
                              UnicodeStreamHandler()])
logger = logging.getLogger('moodmend_backend')

# Flask应用配置
app = Flask(__name__)

# Get configuration from environment
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    logger.warning("SECRET_KEY not set in environment, using random key (not suitable for production)")
    SECRET_KEY = os.urandom(24)
else:
    SECRET_KEY = SECRET_KEY.encode('utf-8')

app.config['SECRET_KEY'] = SECRET_KEY

# CORS configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
CORS(app, origins=CORS_ORIGINS, methods=['GET', 'POST', 'OPTIONS'], allow_headers=['*'])

# 数据库配置
DB_NAME = os.getenv('DATABASE_PATH', 'moodmend.db')
logger.info(f"Using database: {DB_NAME}")

# 线程锁，用于并发安全
db_lock = threading.RLock()

# 模拟数据库（将在启动时从数据库加载）
users_db = {}
logs_db = []
user_last_emotion = {}

# 初始化数据库
def init_db():
    try:
        with db_lock, sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
            ''')
            
            # 检查并添加缺失的user_name列（兼容旧数据库）
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN user_name TEXT NOT NULL DEFAULT '用户'")
                conn.commit()
            except:
                # 如果列已存在，忽略错误
                pass
            # 创建日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email TEXT,
                    time TEXT,
                    emotion TEXT,
                    task TEXT,
                    nft TEXT,
                    completed BOOLEAN,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # 创建用户情绪表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_emotions (
                    user_id TEXT PRIMARY KEY,
                    last_emotion TEXT,
                    last_update TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            conn.commit()
        logger.info("資料庫初始化成功")
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {e}")

# 增强的情緒關鍵字字典 (包含强度权重)
EMOTION_KEYWORDS = {
    'anxious': [
        ('焦慮', 2), ('擔心', 1), ('壓力', 2), ('緊張', 1), ('不安', 1), 
        ('害怕', 2), ('恐慌', 3), ('慌張', 1), ('緊繃', 1), ('坐立不安', 2),
        ('忐忑', 1), ('煩憂', 1), ('煩惱', 1), ('憂慮', 1), ('焦慮不安', 2)
    ],
    'sad': [
        ('傷心', 2), ('難過', 2), ('沮喪', 2), ('孤單', 1), ('悲傷', 2), 
        ('失落', 1), ('絕望', 3), ('惆悵', 1), ('憂鬱', 2), ('傷感', 1),
        ('空虛', 2), ('鬱悶', 1), ('難受', 1), ('想哭', 1), ('寂寞', 1)
    ],
    'angry': [
        ('生氣', 2), ('憤怒', 3), ('煩躁', 1), ('氣憤', 2), ('不滿', 1),
        ('惱火', 2), ('惱怒', 2), ('暴跳如雷', 3), ('氣炸', 3), ('憤慨', 2),
        ('不悅', 1), ('不爽', 1), ('討厭', 1), ('厭煩', 1), ('惱恨', 2)
    ],
    'happy': [
        ('快樂', 2), ('開心', 2), ('興奮', 2), ('愉快', 1), ('滿足', 1),
        ('開朗', 1), ('欣喜', 2), ('高興', 2), ('歡喜', 1), ('雀躍', 2),
        ('愉悅', 1), ('欣慰', 1), ('幸福', 2), ('開懷', 1), ('喜悅', 2)
    ],
    'neutral': [
        ('平靜', 1), ('正常', 1), ('沒事', 1), ('ok', 1), ('一般', 1),
        ('平常', 1), ('普通', 1), ('淡定', 1), ('無感', 1), ('穩定', 1)
    ]
}

# 負面情緒定義 (用於轉移偵測)
NEGATIVE_EMOTIONS = {'anxious', 'sad', 'angry'}
POSITIVE_EMOTIONS = {'happy', 'neutral'}

# 調節建議模板 (基於情緒生成，新增daily_task)
SUGGESTIONS = {
    'anxious': {
        'tips': '深呼吸練習：吸氣4秒，憋氣4秒，吐氣4秒，重複5次。',
        'daily_task': '去做一件放鬆的事，例如聽音樂或散步。',
        'advice': '試著列出3件今天感恩的事，轉移焦點。',
        'resources': '資源連結：https://www.headspace.com/meditation/anxiety (免費冥想App)',
        'color': 'anxious'
    },
    'sad': {
        'tips': '聽一首喜歡的歌，或散步10分鐘接觸陽光。',
        'daily_task': '寫下3件讓你微笑的小事。',
        'advice': '寫日記：今天有什麼小事讓你微笑？',
        'resources': '資源連結：https://www.helpguide.org/articles/depression/coping-with-grief-and-loss.htm',
        'color': 'sad'
    },
    'angry': {
        'tips': '拳擊枕頭或快走5分鐘釋放能量。',
        'daily_task': '做5分鐘運動來釋放怒氣。',
        'advice': '問自己：這件事10年後還重要嗎？',
        'resources': '資源連結：https://www.mayoclinic.org/healthy-lifestyle/adult-health/in-depth/anger-management/art-20045434',
        'color': 'angry'
    },
    'happy': {
        'tips': '記錄這一刻，分享給朋友！',
        'daily_task': '計劃一個小慶祝活動。',
        'advice': '延續正面：計劃下一個小目標。',
        'resources': '資源連結：https://positivepsychology.com/happiness-activities-exercises-tools/',
        'color': 'happy'
    },
    'neutral': {
        'tips': '維持平衡：喝杯水，伸展身體。',
        'daily_task': '反思一天的正面時刻。',
        'advice': '反思一天：什麼讓你感覺好？',
        'resources': '資源連結：https://www.mind.org.uk/information-support/tips-for-everyday-living/wellbeing/',
        'color': 'neutral'
    }
}

# NFT徽章定義
NFT_BADGES = {
    'anxious': '🛡️ 勇者徽章 - 戰勝焦慮',
    'sad': '🌈 彩虹徽章 - 擁抱療癒',
    'angry': '🔥 鳳凰徽章 - 轉化怒火',
    'happy': '⭐ 星光徽章 - 喜悅守護',
    'neutral': '⚖️ 平衡徽章 - 平靜之源'
}

# 增强的情緒偵測函數
def detect_emotion(text):
    if not text or not isinstance(text, str):
        return 'neutral'
    
    text_lower = text.lower()
    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS}
    
    # 计算基础分数
    for emotion, keyword_list in EMOTION_KEYWORDS.items():
        for kw, weight in keyword_list:
            if kw.lower() in text_lower:
                scores[emotion] += weight
    
    # 计算总分数
    total_score = sum(scores.values())
    
    if total_score == 0:
        # 没有匹配到关键词，尝试二次分析
        # 检查否定词和程度词
        negations = ['不', '沒有', '不是', '並非', '不覺得']
        has_negation = any(neg in text_lower for neg in negations)
        
        # 检查情感词密集度
        emotion_words = []
        for emotion, keyword_list in EMOTION_KEYWORDS.items():
            emotion_words.extend([kw for kw, _ in keyword_list])
        
        # 计算文本长度和情感词数量
        char_count = len(text)
        emotion_word_count = sum(1 for word in emotion_words if word.lower() in text_lower)
        
        # 如果有否定词或者情感词密度很低，返回neutral
        if has_negation or (char_count > 20 and emotion_word_count == 0):
            return 'neutral'
        
        # 最后尝试一些常见的中性表达
        neutral_phrases = ['沒什麼', '還好', '一般般', '普通', '正常', '可以']
        for phrase in neutral_phrases:
            if phrase.lower() in text_lower:
                return 'neutral'
    
    # 返回得分最高的情绪
    dominant = max(scores, key=scores.get)
    return dominant if scores[dominant] > 0 else 'neutral'

# 生成基本NFT徽章
def generate_nft_badge(emotion):
    badge = NFT_BADGES.get(emotion, NFT_BADGES['neutral'])
    logger.info(f"生成NFT徽章: {badge} (情绪: {emotion})")
    return badge

# 增强的特殊轉移NFT
def generate_transition_nft(prev_emotion, current_emotion):
    # 从负面到正面的转移
    if prev_emotion in NEGATIVE_EMOTIONS and current_emotion in POSITIVE_EMOTIONS:
        transition_mapping = {
            ('anxious', 'happy'): '🌟 平復之星 - 從焦慮到喜悅的轉變',
            ('anxious', 'neutral'): '✨ 平靜之力 - 從焦慮到平靜的轉變',
            ('sad', 'happy'): '🌈 快樂重生 - 從傷心到喜悅的蛻變',
            ('sad', 'neutral'): '🌊 平靜如海 - 從傷心到平靜的治癒',
            ('angry', 'happy'): '🌞 和平使者 - 從憤怒到喜悅的轉化',
            ('angry', 'neutral'): '🌿 冷靜之心 - 從憤怒到平靜的掌控'
        }
        special_badge = transition_mapping.get((prev_emotion, current_emotion), 
                                              '🌟 成功緩和徽章 - 情緒管理的勝利')
        logger.info(f"生成特殊NFT: {special_badge} (从{prev_emotion}到{current_emotion})")
        return special_badge
    
    # 连续保持正面情绪的奖励
    if prev_emotion in POSITIVE_EMOTIONS and current_emotion in POSITIVE_EMOTIONS:
        return '🏆 持之以恆徽章 - 保持積極心態的成就'
    
    return None

# 工具函数: 验证邮箱格式
def is_valid_email(email):
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_pattern, email) is not None

# 工具函数: 获取数据库连接
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row  # Set row_factory to allow accessing columns by name
    return g.db

# API: 註冊
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        user_name = data.get('user_name')
        confirm_password = data.get('confirm_password')  # 获取确认密码
        
        # 验证输入
        if not email or not password or not user_name:
            return jsonify({
                'success': False,
                'message': '電子郵件、密碼和使用者名稱不能為空'
                }), 400
        
        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '請輸入有效的電子郵件地址'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': '密碼長度不能少於6位'
            }), 400
            
        if len(user_name) < 2 or len(user_name) > 20:
            return jsonify({
                'success': False,
                'message': '使用者名稱長度應在2-20個字符之間'
            }), 400
            
        # 验证确认密码
        if confirm_password is not None and password != confirm_password:
            return jsonify({
                'success': False,
                'message': '两次輸入的密碼不一致'
            }), 400
        
        # 检查邮箱是否已存在
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '該電子郵件已被註冊'
            }), 409
        
        # 密码加密
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        
        # 插入用户
        cursor.execute(
            'INSERT INTO users (user_id, email, password, user_name, created_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, email, hashed_password.decode('utf-8'), user_name, datetime.now().isoformat())
        )
        conn.commit()
        
        # 更新内存中的用户数据
        users_db[email] = {
            'user_id': user_id,
            'password': hashed_password.decode('utf-8'),
            'user_name': user_name
        }
        
        logger.info(f"新用戶註冊成功: {email}, 使用者名稱: {user_name}")
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'email': email,
            'user_name': user_name
        }), 201
        
    except Exception as e:
        logger.error(f"註冊失敗: {e}")
        return jsonify({
            'success': False,
            'message': '註冊失敗，請稍後重試'   
        }), 500

# API: 登錄
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # 验证输入
        if not email or not password:
            return jsonify({
                'success': False,
                'message': '電子郵件和密碼不能為空'
            }), 400
        
        # 优先处理测试账号
        if email == 'test@test.com' and password == '123':
            logger.info("演示用戶登錄成功")
            return jsonify({
                'success': True,
                'user_id': '1',
                'email': email,
                'user_name': '測試用戶',
                'message': '演示用戶登錄成功'
            })
        
        # 检查用户
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                'success': False,
                'message': '電子郵件或密碼錯誤'
            }), 401
        
        # 验证密码
        try:
            if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                return jsonify({
                    'success': False,
                    'message': '電子郵件或密碼錯誤'
                }), 401
        except Exception as e:
            logger.error(f"密碼驗證失敗: {e}")
            return jsonify({
                'success': False,
                'message': '密碼驗證失敗，請聯繫管理員'
            }), 500
        
        # 更新最後登錄時間
        cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?',
                      (datetime.now().isoformat(), user['user_id']))
        conn.commit()
        
        logger.info(f"用戶登錄成功: {email}, 用戶名稱: {user['user_name']}")
        
        return jsonify({
            'success': True,
            'user_id': user['user_id'],
            'email': user['email'],
            'user_name': user['user_name']
        })
        
    except Exception as e:
        logger.error(f"登錄失敗: {e}")
        return jsonify({
            'success': False,
            'message': '登錄失敗，請稍後重試'
        }), 500

# API: 處理情緒輸入
@app.route('/api/process-emotion', methods=['POST'])
def process_emotion():
    try:
        data = request.json
        user_input = data.get('input', '')
        email = data.get('email')
        task_completed = data.get('task_completed', False)
        
        # 增强的输入类型验证和处理
        # 确保data是字典
        if not isinstance(data, dict):
            data = {}
        
        # 重新获取user_input，确保正确的变量引用
        user_input = data.get('input', '')
        
        # 确保user_input是字符串 - 全面的类型处理
        if user_input is None:
            user_input = ''
        elif not isinstance(user_input, str):
            # 如果是字典，尝试各种方式提取字符串内容
            if isinstance(user_input, dict):
                # 1. 尝试获取text字段
                if 'text' in user_input:
                    user_input = user_input['text']
                # 2. 尝试获取第一个非空值
                elif user_input:
                    for key, value in user_input.items():
                        if isinstance(value, str) and value.strip():
                            user_input = value
                            break
                    # 如果没有找到合适的值，使用第一个值
                    else:
                        first_value = next(iter(user_input.values()), '')
                        user_input = str(first_value)
                else:
                    user_input = ''
            # 对于其他非字符串类型，转换为字符串
            else:
                try:
                    user_input = str(user_input)
                except:
                    user_input = ''
        
        # 去除首尾空白字符
        user_input = user_input.strip()
        
        # 验证输入
        if not user_input:
            return jsonify({
                'success': False,
                'message': '情緒描述不能為空'
            }), 400
        
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 偵測情緒
        emotion = detect_emotion(user_input)
        pkg = SUGGESTIONS.get(emotion, SUGGESTIONS['neutral'])
        
        # 生成基本NFT
        nft = generate_nft_badge(emotion)
        
        # 檢查情緒轉移
        transition_nft_str = ''
        conn = get_db()
        cursor = conn.cursor()
        
        # 从数据库获取上次情绪
        cursor.execute('SELECT last_emotion FROM user_emotions WHERE user_id = (SELECT user_id FROM users WHERE email = ?)', (email,))
        result = cursor.fetchone()
        prev_emotion = result[0] if result else None
        
        # 或者从内存中获取
        if not prev_emotion and email in user_last_emotion:
            prev_emotion = user_last_emotion[email]
        
        if prev_emotion and task_completed:
            transition_nft = generate_transition_nft(prev_emotion, emotion)
            if transition_nft:
                transition_nft_str = ' + ' + transition_nft
                nft += transition_nft_str
        
        # 更新数据库中的上次情绪
        user_id = None
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        user_result = cursor.fetchone()
        if user_result:
            user_id = user_result[0]
            cursor.execute(
                'INSERT OR REPLACE INTO user_emotions (user_id, last_emotion, last_update) VALUES (?, ?, ?)',
                (user_id, emotion, datetime.now().isoformat())
            )
            conn.commit()
        
        # 更新内存中的上次情绪
        user_last_emotion[email] = emotion
        
        logger.info(f"處理情緒成功: 用戶={email}, 輸入='{user_input[:30]}...', 檢測情緒={emotion}")
        
        return jsonify({
            'success': True,
            'emotion': emotion,
            'package': {
                'tips': pkg['tips'],
                'daily_task': pkg['daily_task'],
                'advice': pkg['advice'],
                'resources': pkg['resources'],
                'color': pkg['color']
            },
            'nft': nft,
            'transition_nft': transition_nft_str
        })
        
    except Exception as e:
        logger.error(f"處理情緒失敗: {e}")
        return jsonify({
            'success': False,
            'message': '處理情緒失敗，請稍後重試'
        }), 500

# API: 記錄日誌
@app.route('/api/add-log', methods=['POST'])
def add_log():
    try:
        data = request.json
        email = data.get('email')
        emotion = data.get('emotion')
        task = data.get('task')
        badge = data.get('nft')  # 从UI传过来的是nft
        completed = data.get('completed', False)
        
        # 验证输入
        if not all([email, emotion, task, badge]):
            return jsonify({
                'success': False,
                'message': '缺少必要的日誌信息'
            }), 400
        
        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 生成日誌ID和時間戳
        log_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 保存到数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        user_result = cursor.fetchone()
        
        if not user_result:
            return jsonify({
                'success': False,
                'message': '用戶不存在'
            }), 404
        
        user_id = user_result[0]
        
        cursor.execute(
            '''INSERT INTO logs 
               (log_id, user_id, email, time, emotion, task, nft, completed) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (log_id, user_id, email, timestamp, emotion, task, badge, completed)
        )
        conn.commit()
        
        # 更新内存中的日志（用于缓存）
        log_entry = {
            'log_id': log_id,
            'time': timestamp,
            'email': email,
            'emotion': emotion,
            'task': task,
            'nft': badge,
            'completed': completed
        }
        logs_db.append(log_entry)
        
        # 限制内存日志数量，避免内存泄漏
        if len(logs_db) > 1000:
            logs_db.pop(0)
        
        logger.info(f"日誌記錄成功: 用戶={email}, 情緒={emotion}")
        
        return jsonify({
            'success': True,
            'log': log_entry
        })
        
    except Exception as e:
        logger.error(f"記錄日誌失敗: {e}")
        return jsonify({
            'success': False,
            'message': '記錄日誌失敗，請稍後重試'
        }), 500

# API: 获取日志列表
@app.route('/api/get-logs', methods=['GET'])
def get_logs():
    try:
        email = request.args.get('email')
        emotion_filter = request.args.get('emotion')
        date_filter = request.args.get('date')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # 验证输入
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        # 构建查詢
        conn = get_db()
        cursor = conn.cursor()
        
        # 基礎查詢
        query = '''SELECT log_id, time, emotion, task, nft, completed 
                  FROM logs 
                  WHERE email = ?''' 
        params = [email]
        
        # 添加過濾條件
        if emotion_filter:
            query += " AND emotion = ?"
            params.append(emotion_filter)
        
        if date_filter:
            query += " AND time LIKE ?"
            params.append(f"{date_filter}%")
            
        # Add date range filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            query += " AND time >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND time <= ?"
            params.append(end_date)
        
        # 添加排序和分页
        query += " ORDER BY time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(query, params)
        logs = []
        for row in cursor.fetchall():
            log = {
                'log_id': row[0],
                'time': row[1],
                'emotion': row[2],
                'task': row[3],
                'nft': row[4],
                'completed': row[5] == 1
            }
            logs.append(log)
        
        # 获取总数
        count_query = "SELECT COUNT(*) as count FROM logs WHERE email = ?"
        count_params = [email]
        
        if emotion_filter:
            count_query += " AND emotion = ?"
            count_params.append(emotion_filter)
        
        if date_filter:
            count_query += " AND time LIKE ?"
            count_params.append(f"{date_filter}%")
            
        if start_date:
            count_query += " AND time >= ?"
            count_params.append(start_date)
            
        if end_date:
            count_query += " AND time <= ?"
            count_params.append(end_date)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]  # 使用索引访问而不是字典访问，因为没有设置row_factory
        
        logger.info(f"查詢日誌成功: 用戶={email}, 數量={len(logs)}, 總數={total}")
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"查詢日誌失敗: {e}")
        return jsonify({
            'success': False,
            'message': '查詢日誌失敗，請稍後重試'
        }), 500

# API: 获取统计数据
@app.route('/api/get-stats', methods=['GET'])
def get_stats():
    try:
        email = request.args.get('email')
        period = request.args.get('period', 'all')  # all, week, month
        
        # 验证输入
        if not email or not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': '無效的用戶信息'
            }), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 构建時間過濾條件
        time_filter = ""
        params = [email]
        
        if period == 'week':
            # 过去7天
            time_filter = " AND time >= ?"
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            params.append(week_ago)
        elif period == 'month':
            # 过去30天
            time_filter = " AND time >= ?"
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            params.append(month_ago)
        
        # 查询总数和完成数
        query = f"""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM logs 
            WHERE email = ? {time_filter}
        """
        cursor.execute(query, params)
        result = cursor.fetchone()
        total = result[0] or 0
        completed = result[1] or 0
        
        # 查询情绪转移数
        transition_query = f"""
            SELECT COUNT(*) as count 
            FROM logs 
            WHERE email = ? AND nft LIKE ? {time_filter}
        """
        cursor.execute(transition_query, params + ['%成功緩和%'])
        transitions = cursor.fetchone()[0]
        
        # 查询情绪分布
        emotion_query = f"""
            SELECT emotion, COUNT(*) as count 
            FROM logs 
            WHERE email = ? {time_filter}
            GROUP BY emotion
        """
        cursor.execute(emotion_query, params)
        
        chart_data = {
            'anxious': 0,
            'sad': 0,
            'neutral': 0,
            'happy': 0,
            'angry': 0
        }
        
        for row in cursor.fetchall():
            if row[0] in chart_data:
                chart_data[row[0]] = row[1]
        
        # 计算完成率
        completion_rate = round((completed/total)*100) if total > 0 else 0
        
        # 获取连续打卡天数
        streak_query = f"""
            SELECT DISTINCT date(time) as log_date 
            FROM logs 
            WHERE email = ? AND completed = 1 
            ORDER BY log_date DESC
        """
        cursor.execute(streak_query, [email])
        dates = [row[0] for row in cursor.fetchall()]
        
        streak = 0
        current_date = datetime.now().date()
        
        for log_date_str in dates:
            log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
            if (current_date - log_date).days == streak:
                streak += 1
            else:
                break
        
        logger.info(f"查詢統計數據成功: 用戶={email}, 完成率={completion_rate}%, 轉移次數={transitions}")
        
        return jsonify({
            'success': True,
            'completion_rate': completion_rate,
            'transitions': transitions,
            'chart_data': chart_data,
            'total_logs': total,
            'streak': streak,
            'period': period
        })
        
    except Exception as e:
        logger.error(f"查詢統計數據失敗: {e}")
        return jsonify({
            'success': False,
            'message': '查詢統計數據失敗，請稍後重試'
        }), 500

# 从数据库加载用户数据
def load_users_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, email, password, user_name FROM users')
        rows = cursor.fetchall()
        for row in rows:
            if row[0]:  # Only load users with valid user_id
                users_db[row[1]] = {
                    'user_id': row[0],
                    'password': row[2],
                    'user_name': row[3]
                }
        conn.close()
        logger.info(f"从数据库加载用户成功，共{len(users_db)}个用户")
    except Exception as e:
        logger.error(f"從數據庫加載用戶數據失敗: {e}")
        
# 從數據庫加載最近的日誌
def load_recent_logs_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # 只加載最近100條日誌到內存
        cursor.execute('SELECT log_id, time, email, emotion, task, nft, completed FROM logs ORDER BY time DESC LIMIT 100')
        for row in cursor.fetchall():
            log_entry = {
                'log_id': row[0],
                'time': row[1],
                'email': row[2],
                'emotion': row[3],
                'task': row[4],
                'nft': row[5],
                'completed': row[6] == 1
            }
            logs_db.append(log_entry)
        conn.close()
        logger.info(f"從數據庫加載日誌成功，共{len(logs_db)}條")
    except Exception as e:
        logger.error(f"加載日誌數據失敗: {e}")

# 從數據庫加載用戶情緒數據
def load_user_emotions_from_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ue.user_id, u.email, ue.last_emotion 
            FROM user_emotions ue 
            JOIN users u ON ue.user_id = u.user_id
        ''')
        for row in cursor.fetchall():
            user_last_emotion[row[1]] = row[2]
        conn.close()
        logger.info(f"從資料庫載入使用者情緒資料成功，共{len(user_last_emotion)}條")
    except Exception as e:
        logger.error(f"從數據庫加載用戶情緒資料失敗: {e}")

# 定期清理过期的內存緩存
def cleanup_memory_cache():
    try:
        # 限制內存中的日誌數量
        global logs_db
        if len(logs_db) > 500:
            # 只保留最近的300條
            logs_db = logs_db[:300]
        
        # 清理長時間未活動的用戶情緒資料
        global user_last_emotion
        # 這裡可以根據需要實現更複雜的清理邏輯
        
        logger.info(f"內存緩存清理完成，當前日誌數: {len(logs_db)}, 用戶情緒資料數: {len(user_last_emotion)}")  
    except Exception as e:
        logger.error(f"清理內存緩存失敗: {e}")

# 應用上下文處理器
@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

# 根路徑
@app.route('/')
def index():
    return "MoodMend 後端服務正在運行"  

# 健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': 'V1.0.4'
        })
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# 數據庫備份端點
@app.route('/api/backup-db', methods=['POST'])
def backup_database():
    try:
        # 簡單的數據庫備份邏輯
        backup_file = f'moodmend_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        import shutil
        shutil.copy2(DB_NAME, backup_file)
        
        logger.info(f"數據庫備份成功: {backup_file}")
        
        return jsonify({
            'success': True,
            'message': '數據庫備份成功',
            'backup_file': backup_file
        })
    except Exception as e:
        logger.error(f"數據庫備份失敗: {e}")
        return jsonify({
            'success': False,
            'message': '數據庫備份失敗'
        }), 500

# 定时任务初始化
import atexit
from threading import Timer

def schedule_cleanup():
    # 每小时执行一次内存清理
    cleanup_memory_cache()
    t = Timer(3600, schedule_cleanup)
    t.daemon = True
    t.start()

# API: Health Check (for monitoring)
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring service status"""
    try:
        # Check database connectivity
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM logs')
        log_count = cursor.fetchone()[0]
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'users': user_count,
            'logs': log_count,
            'version': '1.2.1'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

if __name__ == '__main__':
    try:
        # 初始化数据库
        init_db()
        
        # 加载数据
        load_users_from_db()
        load_recent_logs_from_db()
        load_user_emotions_from_db()
        
        # 启动定时任务
        schedule_cleanup()
        
        # 注册程序退出时的清理函数
        atexit.register(cleanup_memory_cache)
        
        logger.info("MoodMend後端服務啟動")
        
        # 在生產環境中，應該使用適當的WSGI服務器
        # 這裡為了演示，使用Flask的開發服務器
        app.run(debug=True, port=3000, host='0.0.0.0')
        
    except Exception as e:
        logger.critical(f"服務啟動失敗: {e}")
        raise e