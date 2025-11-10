#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MoodMend 后端主应用
整合所有路由和功能模块
"""

import os
import sys
import logging
import threading
import uuid
from datetime import datetime, timedelta

# 设置编码支持
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 定义基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志
log_file = os.path.join(BASE_DIR, 'moodmend.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('moodmend_app')

# 导入Flask相关模块
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    logger.error("缺少Flask相关依赖，请运行: pip install flask flask-cors")
    sys.exit(1)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据库模型和工具
from backend.models import init_db
from backend.routes import auth, mood, log

# 创建Flask应用实例
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # 用于生成会话令牌

# 配置静态文件服务，指向前端目录
frontend_dir = os.path.join(os.path.dirname(BASE_DIR), 'frontend')
if os.path.exists(frontend_dir):
    app.static_folder = frontend_dir
    app.static_url_path = ''  # 允许直接访问前端文件，不需要/static前缀
    logger.info(f"配置静态文件目录: {frontend_dir}")
else:
    logger.warning(f"前端目录不存在: {frontend_dir}")

# 配置CORS，允许所有来源
CORS(app, origins='*', methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'], allow_headers=['*'])

# 注册路由蓝图
auth.register_blueprint(app)
mood.register_blueprint(app)  # 调用函数，即使它为空
app.register_blueprint(log.log_bp)  # 直接注册log模块的蓝图

# 处理Vite客户端请求，避免404错误
@app.route('/@vite/client')
def vite_client():
    return jsonify({"message": "Vite client not available"}), 404

# 主页路由，提供HTML文件
@app.route('/')
@app.route('/index.html')
@app.route('/index.html/<path:anything>')
def serve_index(anything=None):
    index_path = os.path.join(frontend_dir, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
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
    project_root = os.path.dirname(BASE_DIR)
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
    project_root = os.path.dirname(BASE_DIR)
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

# API状态检查
@app.route('/api/status')
def api_status():
    """
    API状态检查接口
    """
    return jsonify({
        "success": True,
        "message": "MoodMend API 服务正常运行",
        "timestamp": datetime.now().isoformat()
    }), 200

# 同步数据接口
@app.route('/api/sync', methods=['POST'])
def sync_data():
    """
    数据同步接口
    
    请求体:
        {
            "user_id": 1
        }
    
    响应:
        {
            "success": true,
            "pending_sync": [],
            "message": "同步完成"
        }
    """
    try:
        data = request.json
        
        if not data or 'user_id' not in data:
            return jsonify({
                "success": False,
                "message": "缺少必要参数: user_id"
            }), 400
        
        user_id = data['user_id']
        
        # 这里应该实现完整的数据同步逻辑
        # 目前返回空的待同步列表
        return jsonify({
            "success": True,
            "pending_sync": [],
            "message": "同步完成"
        }), 200
        
    except Exception as e:
        logger.error(f"数据同步失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "数据同步失败",
            "error": str(e)
        }), 500

# 生成任务建议接口
@app.route('/api/generate-task-suggestion', methods=['POST'])
def generate_task_suggestion():
    """
    生成任务建议接口
    
    请求体:
        {
            "emotion": "happy",
            "thought": "今天心情很好"
        }
    
    响应:
        {
            "success": true,
            "suggestions": [
                "继续保持积极的心态",
                "记录下让你开心的事情"
            ]
        }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请求参数无效"
            }), 400
        
        emotion = data.get('emotion', 'neutral')
        
        # 根据情绪提供任务建议
        task_suggestions = {
            'happy': [
                "继续保持积极的心态",
                "记录下让你开心的事情",
                "与朋友分享你的快乐",
                "进行一些你喜欢的活动"
            ],
            'sad': [
                "给自己一些独处的时间",
                "听一些舒缓的音乐",
                "进行轻度的体育活动",
                "与信任的人交流感受"
            ],
            'angry': [
                "进行深呼吸练习",
                "暂时远离引起愤怒的环境",
                "进行体育锻炼释放压力",
                "尝试冥想或瑜伽"
            ],
            'anxious': [
                "进行渐进式肌肉放松练习",
                "专注于当下，练习正念",
                "将大问题分解成小步骤",
                "确保充足的休息和睡眠"
            ],
            'neutral': [
                "尝试新的爱好或活动",
                "设定今天的小目标",
                "反思最近的成就",
                "规划未来的积极行动"
            ]
        }
        
        suggestions = task_suggestions.get(emotion.lower(), task_suggestions['neutral'])
        
        return jsonify({
            "success": True,
            "suggestions": suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"生成任务建议失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": "生成任务建议失败",
            "error": str(e)
        }), 500

# 主函数
if __name__ == '__main__':
    try:
        # 初始化数据库
        init_db()
        logger.info("MoodMend 后端服务启动")
        
        # 启动Flask服务器
        # 注意：生产环境应该使用Gunicorn等WSGI服务器
        app.run(host='0.0.0.0', port=3000, debug=True)
        
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"服务启动失败: {str(e)}")
        sys.exit(1)
