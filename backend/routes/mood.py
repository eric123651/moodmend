#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
情绪处理路由模块
提供情绪分析、处理等功能
"""

import os
import json
import logging
from datetime import datetime
from flask import request, jsonify, Blueprint
from backend.models import get_db, db_lock
from backend.utils.emotion import cloud_emotion_analysis, get_emotion_suggestion
from backend.utils.nft_generator import generate_emotion_nft

# 创建情绪处理蓝图
mood_bp = Blueprint('mood', __name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mood_routes')

def register_blueprint(app):
    """
    注册情绪处理相关路由
    
    Args:
        app: Flask应用实例
    """
    
@mood_bp.route('/api/process-emotion', methods=['POST'])
def process_emotion():
        """
        兼容前端调用格式，支持email或user_id参数
        
        请求体:
            {
                "thought": "今天心情很好",
                "user_id": 1  # 或 "email": "user@example.com"
            }
        
        响应:
            {
                "success": true,
                "emotion": "happy",
                "confidence": 0.95,
                "suggestion": "保持这份好心情！",
                "log_id": 123
            }
        """
        try:
            data = request.json
            
            # 验证请求参数
            if not data:
                return jsonify({
                    "success": False,
                    "message": "请求参数无效"
                }), 400
            
            thought = data.get('thought')
            user_id = data.get('user_id')
            email = data.get('email')
            
            # 基础验证
            if not thought:
                return jsonify({
                    "success": False,
                    "message": "思考内容不能为空"
                }), 400
            
            # 如果没有提供user_id但提供了email，则通过email查询user_id
            if not user_id and email:
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    result = cursor.fetchone()
                    if result:
                        user_id = result['id']
                    conn.close()
            
            # 如果仍然没有user_id，创建一个临时ID（仅用于非登录用户）
            if not user_id:
                logger.info("未提供有效用户ID，使用匿名模式处理")
                # 对于匿名用户，我们仍然进行情绪分析，但不保存到数据库
                # 进行情绪分析
                analysis_result = cloud_emotion_analysis(thought)
                emotion = analysis_result.get('emotion', 'neutral')
                confidence = analysis_result.get('confidence', 0.5)
                
                # 获取建议
                suggestion = get_emotion_suggestion(emotion, confidence)
                
                return jsonify({
                    "success": True,
                    "emotion": emotion,
                    "confidence": confidence,
                    "suggestion": suggestion,
                    "message": "使用匿名模式处理情绪"
                }), 200
            
            # 进行情绪分析
            analysis_result = cloud_emotion_analysis(thought)
            emotion = analysis_result.get('emotion', 'neutral')
            confidence = analysis_result.get('confidence', 0.5)
            
            # 获取建议
            suggestion = get_emotion_suggestion(emotion, confidence)
            
            # 保存到数据库
            log_id = None
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                
                # 检查用户是否存在
                cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                if cursor.fetchone():
                    # 插入情绪日志
                    cursor.execute(
                        "INSERT INTO logs (user_id, emotion, intensity, thought, suggestion) VALUES (?, ?, ?, ?, ?)",
                        (user_id, emotion, confidence, thought, suggestion)
                    )
                    log_id = cursor.lastrowid
                    
                    # 添加到同步队列
                    sync_data = {
                        'operation': 'create',
                        'table': 'logs',
                        'record_id': log_id,
                        'data': {
                            'emotion': emotion,
                            'intensity': confidence,
                            'thought': thought,
                            'suggestion': suggestion,
                            'created_at': datetime.now().isoformat()
                        }
                    }
                    cursor.execute(
                        "INSERT INTO sync_queue (user_id, operation, table_name, record_id, data) VALUES (?, ?, ?, ?, ?)",
                        (user_id, 'create', 'logs', log_id, str(sync_data))
                    )
                    
                    conn.commit()
                conn.close()
            
            # 生成情绪NFT（可选）
            # nft_path = generate_emotion_nft(emotion, user_id, thought[:20])
            
            logger.info(f"情绪处理完成: 用户 {user_id}, 情绪 {emotion}")
            
            return jsonify({
                "success": True,
                "emotion": emotion,
                "confidence": confidence,
                "suggestion": suggestion,
                "log_id": log_id
            }), 200
            
        except Exception as e:
            logger.error(f"情绪处理失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": "情绪处理失败，请稍后重试",
                "error": str(e)
            }), 500
    
@mood_bp.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
        """
        简单的情感分析接口
        
        请求体:
            {
                "text": "我今天很开心"
            }
        
        响应:
            {
                "success": true,
                "emotion": "happy",
                "confidence": 0.95
            }
        """
        try:
            data = request.json
            
            if not data or 'text' not in data:
                return jsonify({
                    "success": False,
                    "message": "缺少必要参数: text"
                }), 400
            
            text = data['text']
            
            # 调用情绪分析
            result = cloud_emotion_analysis(text)
            
            return jsonify({
                "success": True,
                "emotion": result.get('emotion', 'neutral'),
                "confidence": result.get('confidence', 0.5)
            }), 200
            
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": "情感分析失败",
                "error": str(e)
            }), 500
    
@mood_bp.route('/api/get-suggestions', methods=['GET'])
def get_suggestions():
        """
        获取情绪建议接口
        
        查询参数:
            ?emotion=happy&intensity=0.9
        
        响应:
            {
                "success": true,
                "suggestion": "保持这份好心情！"
            }
        """
        try:
            emotion = request.args.get('emotion', 'neutral')
            intensity = request.args.get('intensity', type=float)
            
            suggestion = get_emotion_suggestion(emotion, intensity)
            
            return jsonify({
                "success": True,
                "suggestion": suggestion
            }), 200
            
        except Exception as e:
            logger.error(f"获取建议失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": "获取建议失败",
                "error": str(e)
            }), 500
    
logger.info("情绪处理路由注册成功")
