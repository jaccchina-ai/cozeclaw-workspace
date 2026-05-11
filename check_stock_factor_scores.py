#!/usr/bin/env python3
"""检查stock_factor_scores表的结构和数据"""
import sqlite3

conn = sqlite3.connect('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
cursor = conn.cursor()

# 查看表结构
cursor.execute('PRAGMA table_info(stock_factor_scores)')
columns = cursor.fetchall()
print('stock_factor_scores表结构:')
for col in columns:
    print(f'{col[1]} ({col[2]})')

# 查询最近5条数据
cursor.execute('SELECT * FROM stock_factor_scores ORDER BY trade_date DESC LIMIT 5')
rows = cursor.fetchall()
print('\n最近5条因子数据:')
for row in rows:
    print(f'日期: {row[1]}, 股票: {row[2]}, 总得分: {row[3]}')

# 检查因子得分是否为0
cursor.execute('SELECT COUNT(*) FROM stock_factor_scores WHERE total_score = 0')
zero_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM stock_factor_scores')
total_count = cursor.fetchone()[0]
print(f'\n因子得分统计:')
print(f'总记录数: {total_count}')
print(f'总得分=0的记录数: {zero_count}')
if total_count > 0:
    print(f'总得分=0的比例: {zero_count/total_count*100:.2f}%')

conn.close()