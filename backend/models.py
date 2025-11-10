#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库模型定义
包含用户、日志等数据模型
"""

import os
import sqlite3
import threading
import uuid
from datetime import datetime

# 数据库配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'moodmend.db')

# 数据库锁，用于线程安全
db_lock = threading.RLock()

def init_db():
    """初始化数据库，创建必要的表"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # 检查表是否需要更新
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
                    print(f"已删除旧表: {table}")
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nickname TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 创建情绪日志表
            cursor.execute('''
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    emotion TEXT NOT NULL,
                    intensity REAL,
                    thought TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    feedback TEXT,
                    suggestion TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX idx_logs_user_id ON logs (user_id)")
            cursor.execute("CREATE INDEX idx_logs_created_at ON logs (created_at)")
            
            # 创建同步队列表
            cursor.execute('''
                CREATE TABLE sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_id INTEGER,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0,
                    synced_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建索引
            cursor.execute("CREATE INDEX idx_sync_queue_user_id ON sync_queue (user_id)")
            cursor.execute("CREATE INDEX idx_sync_queue_synced ON sync_queue (synced)")
            
            conn.commit()
            print("数据库初始化成功")
            
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
    return conn

# 用户相关的辅助函数
def is_valid_email(email):
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def hash_password(password):
    """密码哈希处理"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
