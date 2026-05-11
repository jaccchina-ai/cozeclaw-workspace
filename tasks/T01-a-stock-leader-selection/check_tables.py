import sqlite3
from database.db_config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 检查表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('dragon_tiger_records', 'dragon_tiger_details');")
tables = cursor.fetchall()

if tables:
    print('✅ 龙虎榜数据库表已创建成功:')
    for table in tables:
        print(f'  - {table[0]}')
else:
    print('❌ 龙虎榜数据库表不存在')

cursor.close()
conn.close()
