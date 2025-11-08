#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MoodMend 后端服务
提供情绪分析、用户认证、数据存储等核心功能
"""

import os
import sys
import json
import logging
import sqlite3
import threading
import uuid
import hashlib
import time
import re
from datetime import datetime, timedelta

# 设置编码支持
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('moodmend.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('moodmend_backend')

# 导入Flask相关模块
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    logger.error("缺少Flask相关依赖，请运行: pip install flask flask-cors")
    sys.exit(1)

# 创建Flask应用实例
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # 用于生成会话令牌

# 配置静态文件服务，指向前端目录
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
app.static_folder = frontend_dir
app.static_url_path = '/static'

# 配置CORS，允许所有来源
CORS(app, origins='*', methods=['GET', 'POST', 'OPTIONS'], allow_headers=['*'])

# 处理Vite客户端请求，避免404错误
@app.route('/@vite/client')
def vite_client():
    return jsonify({"message": "Vite client not available"}), 404

# 主页路由，提供HTML文件
@app.route('/')
def serve_index():
    index_path = os.path.join(frontend_dir, 'index.html')
    if os.path.exists(index_path):
        return app.send_static_file('index.html')
    return jsonify({"message": "前端文件未找到"}), 404

# 提供Demo页面路由
@app.route('/moodmend_ui_demo.html')
def serve_demo():
    demo_path = os.path.join(frontend_dir, 'moodmend_ui_demo.html')
    if os.path.exists(demo_path):
        return app.send_static_file('moodmend_ui_demo.html')
    return jsonify({"message": "Demo页面未找到"}), 404

# 处理图标资源请求
@app.route('/icons/<path:filename>')
def serve_icon(filename):
    # 图标位于项目根目录的icons文件夹
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    icon_path = os.path.join(project_root, 'icons', filename)
    
    if os.path.exists(icon_path):
        with open(icon_path, 'rb') as f:
            content = f.read()
        
        # 设置正确的Content-Type
        if filename.endswith('.svg'):
            return app.response_class(content, mimetype='image/svg+xml')
        elif filename.endswith('.png'):
            return app.response_class(content, mimetype='image/png')
        return app.response_class(content)
    return jsonify({"message": "图标未找到"}), 404

# 提供service worker文件
@app.route('/sw.js')
def serve_sw():
    sw_path = os.path.join(frontend_dir, 'sw.js')
    if os.path.exists(sw_path):
        return app.send_static_file('sw.js')
    return jsonify({"message": "Service Worker未找到"}), 404

# 提供manifest.json文件
@app.route('/manifest.json')
def serve_manifest():
    manifest_path = os.path.join(frontend_dir, 'manifest.json')
    if os.path.exists(manifest_path):
        return app.send_static_file('manifest.json')
    # 尝试使用项目根目录的manifest.json
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    root_manifest = os.path.join(project_root, 'manifest.json')
    if os.path.exists(root_manifest):
        with open(root_manifest, 'rb') as f:
            return app.response_class(f.read(), mimetype='application/manifest+json')
    return jsonify({"message": "Manifest未找到"}), 404

# 处理JavaScript文件请求
@app.route('/<filename>.js')
def serve_js(filename):
    js_path = os.path.join(frontend_dir, f'{filename}.js')
    if os.path.exists(js_path):
        with open(js_path, 'rb') as f:
            return app.response_class(f.read(), mimetype='application/javascript')
    return jsonify({"message": f"JavaScript文件 {filename}.js 未找到"}), 404

# 处理assets目录下的资源
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    asset_path = os.path.join(frontend_dir, 'assets', filename)
    if os.path.exists(asset_path):
        with open(asset_path, 'rb') as f:
            content = f.read()
        
        # 设置正确的Content-Type
        if filename.endswith('.js'):
            return app.response_class(content, mimetype='application/javascript')
        elif filename.endswith('.css'):
            return app.response_class(content, mimetype='text/css')
        elif filename.endswith('.json'):
            return app.response_class(content, mimetype='application/json')
        return app.response_class(content)
    return jsonify({"message": f"资源 {filename} 未找到"}), 404

# 数据库配置
DB_NAME = 'moodmend.db'

# 数据库锁，用于线程安全
db_lock = threading.RLock()

# 情绪关键词定义（与前端保持一致）
EMOTION_KEYWORDS = {
    'happy': {
        'keywords': ['開心', '快樂', '高興', '愉快', '滿足', '興奮', '欣喜', '幸福', '喜悅', '歡樂', '愉悅', '狂喜', '慰問', '滿意', '樂乎', '樂', '爽'],
        'weight': 1
    },
    'sad': {
        'keywords': ['傷心', '難過', '悲傷', '憂傷', '沮喪', '抑鬱', '絕望', '悲痛', '悲哀', '難過', '傷心欲絕', '哀傷', '惆悵', '失落', '痛苦', '哭', '泣', '慘'],
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
}

# 情绪分类
NEGATIVE_EMOTIONS = ['sad', 'anxious', 'angry']
POSITIVE_EMOTIONS = ['happy']

# 建议内容
SUGGESTIONS = {
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
}

def init_db():
    """初始化数据库，创建必要的表"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # 检查表是否需要更新（如果表存在但结构不匹配）
            # 注意：生产环境中应该使用迁移工具，这里为了简化直接删除重建
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # 如果需要更新表结构，先删除旧表
            tables_to_recreate = ['users', 'logs', 'sync_queue']
            for table in tables_to_recreate:
                if table in existing_tables:
                    # 先删除索引
                    if table == 'logs':
                        cursor.execute("DROP INDEX IF EXISTS idx_logs_user_id")
                        cursor.execute("DROP INDEX IF EXISTS idx_logs_created_at")
                    elif table == 'sync_queue':
                        cursor.execute("DROP INDEX IF EXISTS idx_sync_queue_user_id")
                        cursor.execute("DROP INDEX IF EXISTS idx_sync_queue_synced")
                    # 删除表
                    cursor.execute(f"DROP TABLE {table}")
                    logger.info(f"已删除旧表: {table}")
            
            # 创建用户表
            create_users_sql = '''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    settings TEXT DEFAULT '{}'
                )
            '''
            cursor.execute(create_users_sql)
            logger.info("创建用户表成功")
            
            # 创建日志表（包含前端所需的所有字段）
            create_logs_sql = '''
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    input TEXT NOT NULL,
                    emotion TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    advice TEXT,
                    tags TEXT DEFAULT '[]',
                    location TEXT,
                    weather TEXT,
                    activity TEXT,
                    intensity INTEGER DEFAULT 5,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''
            cursor.execute(create_logs_sql)
            logger.info("创建日志表成功")
            
            # 创建数据同步表
            create_sync_queue_sql = '''
                CREATE TABLE sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''
            cursor.execute(create_sync_queue_sql)
            logger.info("创建同步表成功")
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX idx_logs_user_id ON logs(user_id)')
            cursor.execute('CREATE INDEX idx_logs_created_at ON logs(created_at)')
            cursor.execute('CREATE INDEX idx_sync_queue_user_id ON sync_queue(user_id)')
            cursor.execute('CREATE INDEX idx_sync_queue_synced ON sync_queue(synced)')
            logger.info("创建索引成功")
            
            conn.commit()
            conn.close()
            logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

def detect_emotion_local(text):
    """本地情绪检测算法"""
    if not text or not isinstance(text, str):
        return 'neutral', 0.0
    
    # 情绪得分统计
    emotion_scores = {}
    
    # 遍历每种情绪的关键词
    for emotion, config in EMOTION_KEYWORDS.items():
        score = 0
        keywords = config.get('keywords', [])
        weight = config.get('weight', 1)
        
        # 统计关键词出现次数
        for keyword in keywords:
            if keyword in text:
                score += text.count(keyword) * weight
        
        emotion_scores[emotion] = score
    
    # 找到得分最高的情绪
    if emotion_scores:
        max_emotion = max(emotion_scores, key=emotion_scores.get)
        max_score = emotion_scores[max_emotion]
        
        # 如果最高得分大于0，则返回对应的情绪，否则返回中性
        if max_score > 0:
            # 计算置信度（简单归一化）
            total_score = sum(emotion_scores.values())
            confidence = max_score / total_score if total_score > 0 else 0
            return max_emotion, confidence
    
    # 默认返回中性情绪
    return 'neutral', 0.5

def get_db():
    """获取数据库连接"""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问
        return conn
    except Exception as e:
        logger.error(f"获取数据库连接失败: {str(e)}")
        raise

def is_valid_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def hash_password(password):
    """密码哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

# API 路由定义

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        
        # 验证请求数据
        if not data:
            return jsonify({"success": False, "error": "无效的请求数据"}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        # 验证用户名长度
        if len(username) < 3 or len(username) > 20:
            return jsonify({"success": False, "error": "用户名长度应在3-20个字符之间"}), 400
        
        # 验证邮箱格式
        if not is_valid_email(email):
            return jsonify({"success": False, "error": "无效的邮箱格式"}), 400
        
        # 验证密码强度
        if len(password) < 6:
            return jsonify({"success": False, "error": "密码长度至少为6个字符"}), 400
        
        # 哈希密码
        password_hash = hash_password(password)
        
        # 插入用户数据
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"新用户注册成功: {username} (ID: {user_id})")
                
                return jsonify({
                    "success": True,
                    "message": "注册成功",
                    "user": {
                        "id": user_id,
                        "username": username,
                        "email": email
                    }
                }), 201
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "username" in str(e):
                    return jsonify({"success": False, "error": "用户名已存在"}), 400
                elif "email" in str(e):
                    return jsonify({"success": False, "error": "邮箱已被注册"}), 400
                else:
                    return jsonify({"success": False, "error": "注册失败，数据已存在"}), 400
            finally:
                conn.close()
                
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        return jsonify({"success": False, "error": "注册失败，请稍后重试"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        
        # 验证请求数据
        if not data:
            return jsonify({"success": False, "error": "无效的请求数据"}), 400
        
        # 支持邮箱或用户名登录
        identifier = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({"success": False, "error": "缺少用户名/邮箱或密码"}), 400
        
        # 哈希密码
        password_hash = hash_password(password)
        
        # 查询用户
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                # 尝试通过邮箱查询
                if '@' in identifier:
                    cursor.execute(
                        "SELECT id, username, email, password_hash FROM users WHERE email = ?",
                        (identifier,)
                    )
                else:
                    # 尝试通过用户名查询
                    cursor.execute(
                        "SELECT id, username, email, password_hash FROM users WHERE username = ?",
                        (identifier,)
                    )
                
                user = cursor.fetchone()
                
                # 测试账号支持
                if (identifier == 'test@example.com' or identifier == 'test') and password == 'password123':
                    # 如果是测试账号，返回测试用户信息
                    return jsonify({
                        "success": True,
                        "message": "登录成功",
                        "user": {
                            "id": 0,
                            "username": "测试用户",
                            "email": "test@example.com"
                        }
                    }), 200
                
                if not user or user['password_hash'] != password_hash:
                    return jsonify({"success": False, "error": "用户名/邮箱或密码错误"}), 401
                
                # 更新最后登录时间
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user['id'],)
                )
                conn.commit()
                
                logger.info(f"用户登录成功: {user['username']} (ID: {user['id']})")
                
                return jsonify({
                    "success": True,
                    "message": "登录成功",
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "email": user['email']
                    }
                }), 200
                
            finally:
                conn.close()
                
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        return jsonify({"success": False, "error": "登录失败，请稍后重试"}), 500

@app.route('/api/process-emotion', methods=['POST'])
def process_emotion():
    """情绪分析接口"""
    try:
        data = request.get_json()
        
        # 验证请求数据
        if not data:
            return jsonify({"success": False, "error": "无效的请求数据"}), 400
        
        user_id = data.get('user_id')
        text = data.get('input')
        
        if not user_id or not text:
            return jsonify({"success": False, "error": "缺少用户ID或输入内容"}), 400
        
        # 验证用户是否存在
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"success": False, "error": "用户不存在"}), 404
            conn.close()
        
        # 执行情绪检测
        emotion, confidence = detect_emotion_local(text)
        
        # 获取对应的建议
        suggestion = SUGGESTIONS.get(emotion, SUGGESTIONS['neutral'])
        
        # 准备日志数据
        log_data = {
            'user_id': user_id,
            'input': text,
            'emotion': emotion,
            'advice': json.dumps(suggestion) if suggestion else None,
            'tags': json.dumps([]),  # 默认空标签
            'intensity': int(confidence * 10)  # 转换置信度为强度值
        }
        
        # 可选字段
        if 'location' in data:
            log_data['location'] = data['location']
        if 'weather' in data:
            log_data['weather'] = data['weather']
        if 'activity' in data:
            log_data['activity'] = data['activity']
        if 'tags' in data:
            log_data['tags'] = json.dumps(data['tags'])
        if 'intensity' in data:
            log_data['intensity'] = data['intensity']
        
        # 保存到数据库
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "INSERT INTO logs (user_id, input, emotion, advice, tags, location, weather, activity, intensity) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (log_data['user_id'], log_data['input'], log_data['emotion'],
                     log_data['advice'], log_data['tags'], log_data.get('location'),
                     log_data.get('weather'), log_data.get('activity'), log_data['intensity'])
                )
                log_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"情绪分析结果已保存: 用户ID {user_id}, 情绪 {emotion}, 日志ID {log_id}")
                
            finally:
                conn.close()
        
        # 返回结果
        return jsonify({
            "success": True,
            "emotion": emotion,
            "confidence": confidence,
            "suggestion": suggestion,
            "log_id": log_id
        }), 200
        
    except Exception as e:
        logger.error(f"情绪分析失败: {str(e)}")
        return jsonify({"success": False, "error": "情绪分析失败，请稍后重试"}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取用户日志列表"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        # 获取分页参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        offset = (page - 1) * page_size
        
        # 查询日志
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            # 获取总数
            cursor.execute("SELECT COUNT(*) FROM logs WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            
            # 获取日志列表
            cursor.execute(
                "SELECT id, input, emotion, created_at, advice, tags, location, weather, activity, intensity "
                "FROM logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            )
            logs = cursor.fetchall()
            
            # 转换为字典列表
            log_list = []
            for log in logs:
                log_dict = dict(log)
                # 解析JSON字段
                if log_dict.get('advice'):
                    try:
                        log_dict['advice'] = json.loads(log_dict['advice'])
                    except:
                        log_dict['advice'] = {}
                if log_dict.get('tags'):
                    try:
                        log_dict['tags'] = json.loads(log_dict['tags'])
                    except:
                        log_dict['tags'] = []
                log_list.append(log_dict)
            
            conn.close()
        
        return jsonify({
            "success": True,
            "logs": log_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }), 200
        
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({"success": False, "error": "获取日志失败，请稍后重试"}), 500

@app.route('/api/logs/<int:log_id>', methods=['GET'])
def get_log_detail(log_id):
    """获取日志详情"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, input, emotion, created_at, advice, tags, location, weather, activity, intensity "
                "FROM logs WHERE id = ? AND user_id = ?",
                (log_id, user_id)
            )
            log = cursor.fetchone()
            
            if not log:
                conn.close()
                return jsonify({"success": False, "error": "日志不存在或无权访问"}), 404
            
            # 转换为字典
            log_dict = dict(log)
            # 解析JSON字段
            if log_dict.get('advice'):
                try:
                    log_dict['advice'] = json.loads(log_dict['advice'])
                except:
                    log_dict['advice'] = {}
            if log_dict.get('tags'):
                try:
                    log_dict['tags'] = json.loads(log_dict['tags'])
                except:
                    log_dict['tags'] = []
            
            conn.close()
        
        return jsonify({"success": True, "log": log_dict}), 200
        
    except Exception as e:
        logger.error(f"获取日志详情失败: {str(e)}")
        return jsonify({"success": False, "error": "获取日志详情失败，请稍后重试"}), 500

@app.route('/api/logs/<int:log_id>', methods=['PUT'])
def update_log(log_id):
    """更新日志"""
    try:
        data = request.get_json()
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        if not data:
            return jsonify({"success": False, "error": "无效的请求数据"}), 400
        
        # 准备更新数据
        update_fields = []
        update_values = []
        
        if 'input' in data:
            update_fields.append("input = ?")
            update_values.append(data['input'])
        if 'tags' in data:
            update_fields.append("tags = ?")
            update_values.append(json.dumps(data['tags']))
        if 'location' in data:
            update_fields.append("location = ?")
            update_values.append(data['location'])
        if 'weather' in data:
            update_fields.append("weather = ?")
            update_values.append(data['weather'])
        if 'activity' in data:
            update_fields.append("activity = ?")
            update_values.append(data['activity'])
        if 'intensity' in data:
            update_fields.append("intensity = ?")
            update_values.append(data['intensity'])
        
        if not update_fields:
            return jsonify({"success": False, "error": "没有可更新的字段"}), 400
        
        # 如果更新了输入内容，重新分析情绪
        if 'input' in data:
            emotion, confidence = detect_emotion_local(data['input'])
            update_fields.append("emotion = ?")
            update_values.append(emotion)
            
            # 更新建议
            suggestion = SUGGESTIONS.get(emotion, SUGGESTIONS['neutral'])
            update_fields.append("advice = ?")
            update_values.append(json.dumps(suggestion))
        
        # 添加WHERE条件的参数
        update_values.extend([log_id, user_id])
        
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                # 执行更新
                sql = f"UPDATE logs SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
                cursor.execute(sql, update_values)
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "error": "日志不存在或无权更新"}), 404
                
                conn.commit()
                conn.close()
                
                logger.info(f"日志已更新: 日志ID {log_id}, 用户ID {user_id}")
                
                return jsonify({"success": True, "message": "日志更新成功"}), 200
                
            except Exception as e:
                conn.rollback()
                conn.close()
                raise
                
    except Exception as e:
        logger.error(f"更新日志失败: {str(e)}")
        return jsonify({"success": False, "error": "更新日志失败，请稍后重试"}), 500

@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """删除日志"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "DELETE FROM logs WHERE id = ? AND user_id = ?",
                    (log_id, user_id)
                )
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "error": "日志不存在或无权删除"}), 404
                
                conn.commit()
                conn.close()
                
                logger.info(f"日志已删除: 日志ID {log_id}, 用户ID {user_id}")
                
                return jsonify({"success": True, "message": "日志删除成功"}), 200
                
            except Exception as e:
                conn.rollback()
                conn.close()
                raise
                
    except Exception as e:
        logger.error(f"删除日志失败: {str(e)}")
        return jsonify({"success": False, "error": "删除日志失败，请稍后重试"}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取用户统计数据"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            # 获取总体统计
            cursor.execute(
                "SELECT COUNT(*) as total_logs, "
                "COUNT(DISTINCT DATE(created_at)) as active_days "
                "FROM logs WHERE user_id = ?",
                (user_id,)
            )
            stats = dict(cursor.fetchone())
            
            # 获取情绪分布
            cursor.execute(
                "SELECT emotion, COUNT(*) as count "
                "FROM logs WHERE user_id = ? "
                "GROUP BY emotion",
                (user_id,)
            )
            emotion_dist = {row['emotion']: row['count'] for row in cursor.fetchall()}
            
            # 获取最近7天的情绪趋势
            cursor.execute(
                "SELECT DATE(created_at) as date, emotion, COUNT(*) as count "
                "FROM logs WHERE user_id = ? AND created_at >= date('now', '-7 days') "
                "GROUP BY date, emotion "
                "ORDER BY date",
                (user_id,)
            )
            trends_data = cursor.fetchall()
            
            # 整理趋势数据
            trends = {}
            for row in trends_data:
                date = row['date']
                if date not in trends:
                    trends[date] = {}
                trends[date][row['emotion']] = row['count']
            
            conn.close()
        
        return jsonify({
            "success": True,
            "total_logs": stats['total_logs'],
            "active_days": stats['active_days'],
            "emotion_distribution": emotion_dist,
            "weekly_trends": trends
        }), 200
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        return jsonify({"success": False, "error": "获取统计数据失败，请稍后重试"}), 500

@app.route('/api/sync', methods=['POST'])
def sync_data():
    """数据同步接口"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        # 验证用户是否存在
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"success": False, "error": "用户不存在"}), 404
            conn.close()
        
        # 处理同步操作
        sync_results = {
            "sent_logs": [],
            "received_logs": []
        }
        
        # 如果有本地日志需要同步
        if 'logs' in data and isinstance(data['logs'], list):
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                
                try:
                    for log in data['logs']:
                        # 检查日志是否已存在
                        cursor.execute(
                            "SELECT id FROM logs WHERE user_id = ? AND created_at = ? AND input = ?",
                            (user_id, log['created_at'], log['input'])
                        )
                        
                        if not cursor.fetchone():
                            # 插入新日志
                            cursor.execute(
                                "INSERT INTO logs (user_id, input, emotion, created_at, advice, tags, location, weather, activity, intensity) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (user_id, log.get('input'), log.get('emotion', 'neutral'),
                                 log.get('created_at'), log.get('advice'), log.get('tags', '[]'),
                                 log.get('location'), log.get('weather'), log.get('activity'),
                                 log.get('intensity', 5))
                            )
                            new_log_id = cursor.lastrowid
                            sync_results['sent_logs'].append(new_log_id)
                    
                    conn.commit()
                    
                finally:
                    conn.close()
        
        # 返回服务器上的最新日志
        last_sync_time = data.get('last_sync_time', '1970-01-01')
        
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, input, emotion, created_at, advice, tags, location, weather, activity, intensity "
                "FROM logs WHERE user_id = ? AND created_at > ? "
                "ORDER BY created_at DESC",
                (user_id, last_sync_time)
            )
            
            new_logs = cursor.fetchall()
            for log in new_logs:
                log_dict = dict(log)
                # 解析JSON字段
                if log_dict.get('advice'):
                    try:
                        log_dict['advice'] = json.loads(log_dict['advice'])
                    except:
                        log_dict['advice'] = {}
                if log_dict.get('tags'):
                    try:
                        log_dict['tags'] = json.loads(log_dict['tags'])
                    except:
                        log_dict['tags'] = []
                sync_results['received_logs'].append(log_dict)
            
            conn.close()
        
        return jsonify({
            "success": True,
            "sync_results": sync_results,
            "current_time": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"数据同步失败: {str(e)}")
        return jsonify({"success": False, "error": "数据同步失败，请稍后重试"}), 500

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """获取情绪建议列表"""
    try:
        emotion = request.args.get('emotion')
        
        if emotion and emotion in SUGGESTIONS:
            suggestions = SUGGESTIONS[emotion]
        else:
            suggestions = SUGGESTIONS
        
        return jsonify({
            "success": True,
            "suggestions": suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"获取建议失败: {str(e)}")
        return jsonify({"success": False, "error": "获取建议失败，请稍后重试"}), 500

# 主入口
if __name__ == '__main__':
    try:
        # 初始化数据库
        init_db()
        logger.info("MoodMend 后端服务启动")
        # 启动服务器
        app.run(host='0.0.0.0', port=3000, debug=True)
    except Exception as e:
        logger.critical(f"服务启动失败: {str(e)}")
        sys.exit(1)
