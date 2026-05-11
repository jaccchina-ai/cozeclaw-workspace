#!/usr/bin/env python3
"""检查数据库中的因子相关表"""
import sqlite3

conn = sqlite3.connect('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
cursor = conn.cursor()

# 查询所有因子相关表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%ic%' OR name LIKE '%factor%')")
tables = cursor.fetchall()

print('因子相关表:')
for table in tables:
    print(table[0])

conn.close()