#!/usr/bin/env python3
"""查看selection_results表结构"""
import sqlite3

conn = sqlite3.connect('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(selection_results)')
result = cursor.fetchall()
print('selection_results表结构:')
for row in result:
    print(f"  {row[1]} ({row[2]})")
conn.close()