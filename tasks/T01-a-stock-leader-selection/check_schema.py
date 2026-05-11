from sqlalchemy import create_engine, inspect
from database.db_config import get_database_url, POSTGRES_CONFIG, SQLITE_DB_PATH

# 查询SQLite表结构
sqlite_engine = create_engine(get_database_url('sqlite'))
sqlite_inspect = inspect(sqlite_engine)
sqlite_columns = sqlite_inspect.get_columns('tracked_results')
print("SQLite Table Schema:")
for col in sqlite_columns:
    print(f"{col['name']}: {col['type']}")

# 查询PG表结构
pg_engine = create_engine(get_database_url('postgres'))
pg_inspect = inspect(pg_engine)
pg_columns = pg_inspect.get_columns('tracked_results')
print("\nPG Table Schema:")
for col in pg_columns:
    print(f"{col['name']}: {col['type']}")