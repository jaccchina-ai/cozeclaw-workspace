#!/usr/bin/env python3
"""查看数据库表结构"""
import sqlite3
import os

def main():
    db_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db'
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print('Tables in database:')
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')
    tables = cursor.fetchall()
    for table in tables:
        print(f"- {table[0]}")
    
    # 查看tracked_results表结构
    print("\ntracked_results表结构:")
    cursor.execute('PRAGMA table_info(tracked_results)')
    result = cursor.fetchall()
    for row in result:
        print(f"  {row[1]} ({row[2]})")
    
    conn.close()

if __name__ == "__main__":
    main()