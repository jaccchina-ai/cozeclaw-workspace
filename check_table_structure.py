from sqlalchemy import create_engine, inspect

engine = create_engine('sqlite:////workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
inspector = inspect(engine)

# 查看所有表
print("数据库中的表:")
tables = inspector.get_table_names()
for table in tables:
    print(f"  - {table}")

# 查看tracked_results表结构
if 'tracked_results' in tables:
    print("\ntracked_results表字段:")
    columns = inspector.get_columns('tracked_results')
    for col in columns:
        print(f"  {col['name']}: {col['type']}")