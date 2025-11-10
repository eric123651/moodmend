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
import base64
from datetime import datetime, timedelta

# 导入阿里云服务
from aliyun_services import get_nlp_service, get_nls_service, get_qwen_service

# 设置编码支持
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 定义基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志 - 使用固定的绝对路径
log_file = os.path.join(BASE_DIR, 'moodmend.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
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

# 初始化阿里云服务实例
nlp_service = get_nlp_service()
nls_service = get_nls_service()
qwen_service = get_qwen_service()

# 注意：不再使用本地情绪检测，完全依赖阿里云AI服务

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

# 数据库配置 - 使用固定的绝对路径避免路径歧义
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'moodmend.db')

# 数据库锁，用于线程安全
db_lock = threading.RLock()

# 情绪分类（仅用于参考，实际分析使用阿里云AI）
NEGATIVE_EMOTIONS = ['sad', 'anxious', 'angry']
POSITIVE_EMOTIONS = ['happy']

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

# 注意：不再使用本地情绪检测函数，完全依赖阿里云AI服务

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
    """情绪分析接口（兼容前端调用格式，支持email或user_id参数）"""
    try:
        data = request.get_json()
        
        # 验证请求数据
        if not data:
            return jsonify({"success": False, "error": "无效的请求数据"}), 400
        
        # 支持前端使用email参数的调用方式
        email = data.get('email')
        user_id = data.get('user_id')
        text = data.get('input')
        task_completed = data.get('task_completed', False)
        is_voice_input = False
        
        # 如果提供了email但没有user_id，通过email查找用户ID
        if email and not user_id:
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                user = cursor.fetchone()
                conn.close()
            
            user_id = user[0] if user else str(uuid.uuid4())  # 如果找不到用户，生成临时ID
        
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
        
        # 处理语音输入
        if 'audio_data' in data and not text:
            is_voice_input = True
            logger.info(f"处理语音输入: 用户ID {user_id}")
            
            # 检查语音服务是否可用
            if nls_service:
                # 调用语音识别服务
                format_type = data.get('format', 'wav')
                sample_rate = data.get('sample_rate', 16000)
                
                speech_result = nls_service.recognize_speech(
                    data['audio_data'], 
                    format_type, 
                    sample_rate
                )
                
                if speech_result.get('success'):
                    text = speech_result['text']
                    logger.info(f"语音识别成功: {text[:30]}...")
                else:
                    logger.error(f"语音识别失败: {speech_result.get('error', '未知错误')}")
                    return jsonify({"success": False, "error": "语音识别失败"}), 400
            else:
                logger.warning("语音识别服务不可用，回退到本地处理")
                return jsonify({"success": False, "error": "语音识别服务不可用"}), 503
        
        # 验证文本内容
        if not text:
            return jsonify({"success": False, "error": "缺少输入内容"}), 400
        
        # 执行情绪检测 - 仅使用阿里云NLP服务
        emotion = 'neutral'
        confidence = 0.5
        detect_method = 'alicloud'
        
        # 必须使用阿里云NLP服务
        if nlp_service:
            logger.info(f"使用阿里云NLP服务进行情绪分析: 用户ID {user_id}")
            nlp_result = nlp_service.analyze_sentiment(text)
            
            if nlp_result:
                emotion = nlp_result['emotion']
                confidence = nlp_result['confidence']
                logger.info(f"阿里云NLP分析结果: 情绪={emotion}, 置信度={confidence}")
            else:
                logger.error("阿里云NLP服务分析失败")
                return jsonify({"success": False, "error": "情绪分析服务暂时不可用，请稍后重试"}), 503
        else:
            logger.error("阿里云NLP服务不可用")
            return jsonify({"success": False, "error": "情绪分析服务未配置，请检查系统设置"}), 503
        
        # 生成个性化建议 - 仅使用通义千问服务
        suggestion = None
        suggestion_method = 'alicloud'
        
        # 必须使用通义千问服务
        if qwen_service:
            logger.info(f"使用通义千问生成个性化建议: 用户ID {user_id}, 情绪={emotion}")
            
            # 获取用户历史数据作为上下文
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT emotion, input FROM logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
                    (user_id,)
                )
                recent_moods = cursor.fetchall()
                conn.close()
            
            # 构建用户上下文
            user_context = {
                'recent_moods': [dict(mood) for mood in recent_moods],
                'current_input': text[:100]  # 限制上下文长度
            }
            
            # 调用通义千问生成建议
            qwen_result = qwen_service.generate_task_suggestion(emotion, user_context)
            
            if qwen_result.get('success'):
                suggestion = qwen_result['suggestion']
                logger.info("通义千问成功生成个性化建议")
            else:
                logger.error(f"通义千问生成建议失败: {qwen_result.get('error', '未知错误')}")
                return jsonify({"success": False, "error": "建议生成服务暂时不可用，请稍后重试"}), 503
        else:
            logger.error("通义千问服务不可用")
            return jsonify({"success": False, "error": "建议生成服务未配置，请检查系统设置"}), 503
        
        # 准备日志数据
        log_data = {
            'user_id': user_id,
            'input': text,
            'emotion': emotion,
            'advice': json.dumps({
                'content': suggestion,
                'method': suggestion_method
            }) if suggestion else None,
            'tags': json.dumps([]),  # 默认空标签
            'intensity': int(confidence * 10),  # 转换置信度为强度值
            'location': data.get('location'),
            'weather': data.get('weather'),
            'activity': data.get('activity')
        }
        
        # 可选字段
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
                
                logger.info(f"情绪分析结果已保存: 用户ID {user_id}, 情绪 {emotion}, 日志ID {log_id}, "
                          f"检测方法 {detect_method}, 建议方法 {suggestion_method}")
                
            finally:
                conn.close()
        
        # 返回结果
        return jsonify({
            "success": True,
            "emotion": emotion,
            "confidence": confidence,
            "suggestion": suggestion,
            "log_id": log_id,
            "detect_method": detect_method,
            "suggestion_method": suggestion_method,
            "is_voice_input": is_voice_input
        }), 200
        
    except Exception as e:
        logger.error(f"情绪分析失败: {str(e)}", exc_info=True)
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
        
        # 如果更新了输入内容，使用阿里云服务重新分析情绪
        if 'input' in data:
            if nlp_service:
                logger.info(f"使用阿里云NLP服务重新分析情绪: 日志ID {log_id}")
                nlp_result = nlp_service.analyze_sentiment(data['input'])
                
                if nlp_result:
                    emotion = nlp_result['emotion']
                    update_fields.append("emotion = ?")
                    update_values.append(emotion)
                    
                    # 使用通义千问生成新建议
                    if qwen_service:
                        # 构建最小上下文
                        user_context = {
                            'recent_moods': [],
                            'current_input': data['input'][:100]
                        }
                        qwen_result = qwen_service.generate_task_suggestion(emotion, user_context)
                        
                        if qwen_result.get('success'):
                            suggestion = qwen_result['suggestion']
                            update_fields.append("advice = ?")
                            update_values.append(json.dumps({
                                'content': suggestion,
                                'method': 'alicloud'
                            }))
                else:
                    logger.error("阿里云NLP服务重新分析失败")
                    return jsonify({"success": False, "error": "情绪重新分析失败，请稍后重试"}), 503
            else:
                logger.error("阿里云NLP服务不可用")
                return jsonify({"success": False, "error": "情绪分析服务未配置"}), 503
        
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

# 阿里云AI服务API端点
@app.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
    """使用阿里云NLP服务进行情感分析"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        text = data.get('text', '').strip()
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        if not text:
            return jsonify({"success": False, "error": "请提供要分析的文本"}), 400
        
        # 检查NLP服务是否可用
        if not nlp_service:
            # 如果服务不可用，回退到本地情绪检测
            emotion, confidence = detect_emotion_local(text)
            return jsonify({
                "success": True,
                "emotion": emotion,
                "confidence": confidence,
                "method": "local"
            })
        
        # 调用NLP服务进行情感分析
        result = nlp_service.analyze_sentiment(text)
        
        if result:
            # 记录分析结果到数据库
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO logs (user_id, input, emotion, created_at, intensity) VALUES (?, ?, ?, ?, ?)",
                    (user_id, text, result['emotion'], datetime.now(), int(result['confidence'] * 10))
                )
                conn.commit()
                conn.close()
                
            return jsonify({
                "success": True,
                "emotion": result['emotion'],
                "confidence": result['confidence'],
                "details": result.get('details', {}),
                "method": "alicloud"
            })
        else:
            # 失败时回退到本地检测
            emotion, confidence = detect_emotion_local(text)
            return jsonify({
                "success": True,
                "emotion": emotion,
                "confidence": confidence,
                "method": "local_fallback"
            })
            
    except Exception as e:
        logger.error(f"情感分析过程中发生错误: {str(e)}")
        return jsonify({"success": False, "error": "处理请求时发生错误"}), 500

# 保留原始的process_emotion函数，已经在文件上方定义

@app.route('/api/recognize-speech', methods=['POST'])
def recognize_speech():
    """语音识别接口（增强版）"""
    try:
        # 支持JSON和FormData两种格式
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 处理文件上传
            file = request.files.get('audio_file')
            if not file:
                return jsonify({"success": False, "error": "缺少音频文件"}), 400
            
            # 读取文件内容并进行Base64编码
            audio_bytes = file.read()
            audio_data = base64.b64encode(audio_bytes).decode('utf-8')
            
            # 获取其他参数
            user_id = request.form.get('user_id')
            format_type = request.form.get('format', 'wav')
            sample_rate = int(request.form.get('sample_rate', 16000))
            
            logger.info(f"处理文件上传的语音识别请求，用户ID: {user_id}, 格式: {format_type}")
        else:
            # 处理JSON请求
            data = request.get_json()
            
            if not data:
                return jsonify({"success": False, "error": "无效的请求数据"}), 400
            
            user_id = data.get('user_id')
            audio_data = data.get('audio_data')
            format_type = data.get('format', 'wav')
            sample_rate = data.get('sample_rate', 16000)
            
            logger.info(f"处理JSON格式的语音识别请求，用户ID: {user_id}, 格式: {format_type}")
        
        # 验证必要参数
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
            
        if not audio_data:
            return jsonify({"success": False, "error": "请提供音频数据"}), 400
        
        # 检查服务可用性
        if not nls_service:
            logger.warning("语音识别服务不可用")
            return jsonify({"success": False, "error": "语音识别服务暂不可用"}), 503
        
        # 支持的音频格式
        supported_formats = ['wav', 'mp3', 'opus', 'pcm']
        if format_type.lower() not in supported_formats:
            return jsonify({
                "success": False, 
                "error": f"不支持的音频格式，请使用以下格式之一: {', '.join(supported_formats)}"
            }), 400
        
        # 验证音频数据长度
        if len(audio_data) > 5 * 1024 * 1024:  # 5MB限制
            return jsonify({"success": False, "error": "音频文件过大，请控制在5MB以内"}), 413
        
        # 调用语音服务进行识别
        logger.info(f"开始语音识别处理，用户ID: {user_id}")
        result = nls_service.recognize_speech(audio_data, format_type, sample_rate)
        
        # 处理识别结果
        if result.get('success'):
            # 对识别结果进行基本的文本清理
            recognized_text = result['text'].strip()
            
            # 可选：如果识别到文本，自动进行情绪分析
            emotion_result = None
            if recognized_text and nlp_service:
                try:
                    emotion_analysis = nlp_service.analyze_sentiment(recognized_text)
                    if emotion_analysis:
                        emotion_result = {
                            'emotion': emotion_analysis['emotion'],
                            'confidence': emotion_analysis['confidence']
                        }
                except Exception as e:
                    logger.warning(f"自动情绪分析失败: {str(e)}")
            
            # 记录语音识别结果到日志表
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO logs (user_id, input, emotion, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, recognized_text, emotion_result['emotion'] if emotion_result else 'neutral', datetime.now())
                )
                conn.commit()
                conn.close()
            
            response = {
                "success": True,
                "text": recognized_text,
                "confidence": result.get('confidence', 0),
                "format": format_type,
                "sample_rate": sample_rate,
                "audio_size": len(audio_data)
            }
            
            # 如果有情绪分析结果，添加到响应中
            if emotion_result:
                response['emotion_analysis'] = emotion_result
            
            logger.info(f"用户 {user_id} 语音识别成功，识别文本长度: {len(recognized_text)} 字符")
            return jsonify(response), 200
        else:
            error_message = result.get('error', '语音识别失败')
            error_code = result.get('error_code')
            logger.error(f"语音识别失败，用户ID: {user_id}, 错误: {error_message}, 错误码: {error_code}")
            
            # 提供更具体的错误信息
            detailed_error = error_message
            if error_code == 'INVALID_AUDIO':
                detailed_error = "音频数据格式无效，请检查音频文件是否正确"
            elif error_code == 'SERVICE_BUSY':
                detailed_error = "服务暂时繁忙，请稍后重试"
            
            return jsonify({
                "success": False,
                "error": detailed_error,
                "error_code": error_code,
                "format": format_type
            }), 500
            
    except ValueError as e:
        logger.error(f"语音识别参数错误: {str(e)}")
        return jsonify({"success": False, "error": f"参数错误: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"语音识别处理失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "处理请求时发生错误，请稍后重试"}), 500

@app.route('/api/generate-task-suggestion', methods=['POST'])
def generate_task_suggestion():
    """使用通义千问生成个性化任务建议（增强版）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        emotion = data.get('emotion', 'neutral')
        current_input = data.get('input', '')
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        # 构建丰富的用户上下文
        user_context = {
            'current_input': current_input,
            'recent_moods': []
        }
        
        # 获取用户最近的情绪记录作为上下文
        try:
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                # 获取最近5条记录，并设置row_factory以便于访问
                cursor.row_factory = sqlite3.Row
                cursor.execute(
                    "SELECT emotion, input, created_at FROM logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
                    (user_id,)
                )
                recent_moods = cursor.fetchall()
                conn.close()
            
            # 转换为字典列表
            user_context['recent_moods'] = [dict(row) for row in recent_moods]
            logger.info(f"为用户 {user_id} 获取了 {len(user_context['recent_moods'])} 条历史情绪记录")
        except Exception as e:
            logger.warning(f"获取用户历史记录失败: {str(e)}")
            # 继续处理，即使没有历史记录
        
        # 检查通义千问服务是否可用
        if not qwen_service:
            logger.warning("通义千问服务不可用，使用本地预设建议")            # 如果服务不可用，回退到预设建议
            fallback_suggestion = SUGGESTIONS.get(emotion, SUGGESTIONS['neutral'])
            return jsonify({
                "success": True,
                "suggestion": fallback_suggestion,
                "method": "local"
            })
        
        # 获取用户历史数据作为上下文
        with db_lock:
            conn = get_db()
            cursor = conn.cursor()
            
            # 获取用户最近的情绪记录
            cursor.execute(
                "SELECT emotion, input FROM logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
                (user_id,)
            )
            recent_moods = cursor.fetchall()
            conn.close()
        
        # 构建用户上下文
        enhanced_context = {
            'recent_moods': [dict(mood) for mood in recent_moods],
            'additional_context': user_context
        }
        
        # 调用通义千问生成任务建议
        result = qwen_service.generate_task_suggestion(emotion, enhanced_context)
        
        if result.get('success'):
            # 记录任务建议生成
            logger.info(f"为用户 {user_id} 生成任务建议，情绪: {emotion}")
            return jsonify({
                "success": True,
                "suggestion": result['suggestion'],
                "method": "alicloud"
            })
        else:
            # 失败时回退到预设建议
            fallback_suggestion = SUGGESTIONS.get(emotion, SUGGESTIONS['neutral'])
            return jsonify({
                "success": True,
                "suggestion": fallback_suggestion,
                "method": "local_fallback"
            })
            
    except Exception as e:
        logger.error(f"生成任务建议过程中发生错误: {str(e)}")
        return jsonify({"success": False, "error": "处理请求时发生错误"}), 500

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
