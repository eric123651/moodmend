#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本：验证数据库文件位置和内容
"""

import os
import sqlite3
import sys

# 打印当前工作目录
print(f"当前工作目录: {os.getcwd()}")

# 测试数据库文件路径
db_name = 'moodmend.db'
print(f"数据库文件相对路径: {db_name}")
print(f"数据库文件绝对路径: {os.path.abspath(db_name)}")

# 检查文件是否存在
if os.path.exists(db_name):
    print(f"数据库文件存在，大小: {os.path.getsize(db_name)} 字节")
    
    # 连接数据库并查看表结构
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 查看每个表的记录数
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"表 {table_name} 中有 {count} 条记录")
            
        conn.close()
    except Exception as e:
        print(f"读取数据库失败: {e}")
else:
    print("数据库文件不存在")
