import sqlite3
import os

# 连接数据库
db_path = os.path.join('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection', 'database/t01_stocks.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库表列表:')
for table in tables:
    print(f'- {table[0]}')

# 关闭连接
conn.close()