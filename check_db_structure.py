#!/usr/bin/env python3
"""查看数据库表结构"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.dual_db_manager import DualDBManager

def main():
    db = DualDBManager()
    print('Tables in database:')
    tables = db.execute_query('SELECT name FROM sqlite_master WHERE type=\'table\'')
    for table in tables:
        print(f"- {table[0]}")
    
    # 查看tracked_results表结构
    print("\ntracked_results表结构:")
    result = db.execute_query('PRAGMA table_info(tracked_results)')
    for row in result:
        print(f"  {row[1]} ({row[2]})")

if __name__ == "__main__":
    main()