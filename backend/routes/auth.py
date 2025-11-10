#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用户认证路由模块
提供注册、登录等功能
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import request, jsonify, Blueprint
from backend.models import get_db, init_db, is_valid_email, hash_password, db_lock

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auth_routes')

def register_blueprint(app):
    """
    注册认证相关路由
    
    Args:
        app: Flask应用实例
    """
    
    @auth_bp.route('/api/register', methods=['POST'])
    def register():
        """
        用户注册接口
        
        请求体:
            {
                "email": "user@example.com",
                "password": "password123",
                "nickname": "用户名"
            }
        
        响应:
            {
                "success": true,
                "message": "注册成功",
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "nickname": "用户名"
                }
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
            
            email = data.get('email')
            password = data.get('password')
            nickname = data.get('nickname', '')
            
            # 基础验证
            if not email or not password:
                return jsonify({
                    "success": False,
                    "message": "邮箱和密码不能为空"
                }), 400
            
            # 邮箱格式验证
            if not is_valid_email(email):
                return jsonify({
                    "success": False,
                    "message": "邮箱格式不正确"
                }), 400
            
            # 密码长度验证
            if len(password) < 6:
                return jsonify({
                    "success": False,
                    "message": "密码长度至少为6位"
                }), 400
            
            # 哈希密码
            hashed_password = hash_password(password)
            
            # 保存到数据库
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                
                # 检查邮箱是否已存在
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    conn.close()
                    return jsonify({
                        "success": False,
                        "message": "该邮箱已被注册"
                    }), 409
                
                # 插入新用户
                cursor.execute(
                    "INSERT INTO users (email, password, nickname) VALUES (?, ?, ?)",
                    (email, hashed_password, nickname)
                )
                user_id = cursor.lastrowid
                conn.commit()
                conn.close()
            
            logger.info(f"新用户注册成功: {email}")
            
            return jsonify({
                "success": True,
                "message": "注册成功",
                "user": {
                    "id": user_id,
                    "email": email,
                    "nickname": nickname
                }
            }), 201
            
        except Exception as e:
            logger.error(f"注册失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": "注册失败，请稍后重试",
                "error": str(e)
            }), 500
    
    @auth_bp.route('/api/login', methods=['POST'])
    def login():
        """
        用户登录接口
        
        请求体:
            {
                "email": "user@example.com",
                "password": "password123"
            }
        
        响应:
            {
                "success": true,
                "message": "登录成功",
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "nickname": "用户名"
                },
                "token": "jwt_token_here"
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
            
            email = data.get('email')
            password = data.get('password')
            
            # 基础验证
            if not email or not password:
                return jsonify({
                    "success": False,
                    "message": "邮箱和密码不能为空"
                }), 400
            
            # 哈希密码用于验证
            hashed_password = hash_password(password)
            
            # 数据库查询
            with db_lock:
                conn = get_db()
                cursor = conn.cursor()
                
                # 查询用户
                cursor.execute(
                    "SELECT id, email, nickname, is_active FROM users WHERE email = ? AND password = ?",
                    (email, hashed_password)
                )
                user = cursor.fetchone()
                
                if user:
                    # 检查用户是否激活
                    if not user['is_active']:
                        conn.close()
                        return jsonify({
                            "success": False,
                            "message": "账号已被禁用"
                        }), 403
                    
                    # 更新最后登录时间
                    cursor.execute(
                        "UPDATE users SET last_login = ? WHERE id = ?",
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user['id'])
                    )
                    conn.commit()
                    conn.close()
                    
                    # 生成简单的会话token（实际项目中应使用JWT）
                    token = str(uuid.uuid4())
                    
                    logger.info(f"用户登录成功: {email}")
                    
                    return jsonify({
                        "success": True,
                        "message": "登录成功",
                        "user": {
                            "id": user['id'],
                            "email": user['email'],
                            "nickname": user['nickname']
                        },
                        "token": token
                    }), 200
                else:
                    conn.close()
                    return jsonify({
                        "success": False,
                        "message": "邮箱或密码错误"
                    }), 401
                    
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": "登录失败，请稍后重试",
                "error": str(e)
            }), 500
    
    logger.info("认证路由注册成功")
