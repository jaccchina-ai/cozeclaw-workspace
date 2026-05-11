import sqlite3

# 连接数据库
conn = sqlite3.connect('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
cursor = conn.cursor()

# 查看现有表结构
print("现有 tracked_results 表结构:")
cursor.execute("PRAGMA table_info(tracked_results)")
columns = cursor.fetchall()
for col in columns:
    print(col)

# 添加新字段
print("\n添加新字段...")
try:
    # 添加 shares_held 字段
    cursor.execute("ALTER TABLE tracked_results ADD COLUMN shares_held FLOAT DEFAULT 1.0")
    print("✅ 成功添加 shares_held 字段")
    
    # 添加 sell_history 字段
    cursor.execute("ALTER TABLE tracked_results ADD COLUMN sell_history TEXT DEFAULT '[]'")
    print("✅ 成功添加 sell_history 字段")
    
    # 添加 final_profit 字段
    cursor.execute("ALTER TABLE tracked_results ADD COLUMN final_profit FLOAT")
    print("✅ 成功添加 final_profit 字段")
    
    conn.commit()
    print("\n✅ 所有字段添加成功！")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️ 字段已存在，跳过添加")
    else:
        raise e
finally:
    # 关闭连接
    conn.close()