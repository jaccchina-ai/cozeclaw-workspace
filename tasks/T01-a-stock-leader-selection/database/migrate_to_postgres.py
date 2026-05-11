#!/usr/bin/env python3
"""
T01 选股系统 - SQLite 到 PostgreSQL 数据迁移脚本

用法:
    python3 migrate_to_postgres.py
"""

import os
import sys

# 安装 psycopg2
try:
    import psycopg2
except ImportError:
    print("安装 psycopg2-binary...")
    os.system(f"{sys.executable} -m pip install psycopg2-binary -q")
    import psycopg2

try:
    import psycopg2.extras
except ImportError:
    pass

import sqlite3

# SQLite 路径
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 't01_stocks.db')

# PostgreSQL 连接配置
PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'database': os.environ.get('PG_DATABASE', 't01_stocks'),
    'user': os.environ.get('PG_USER', 't01_user'),
    'password': os.environ.get('PG_PASSWORD', 't01_pass_2026')
}


def get_sqlite_connection():
    """获取 SQLite 连接"""
    return sqlite3.connect(SQLITE_PATH)


def get_postgres_connection():
    """获取 PostgreSQL 连接"""
    return psycopg2.connect(**PG_CONFIG)


def get_pg_table_columns(pg_conn, table_name):
    """获取 PostgreSQL 表的列名"""
    cursor = pg_conn.cursor()
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = [row[0] for row in cursor.fetchall()]
    # 排除 id 和 created_at/updated_at
    return [c for c in columns if c not in ('id', 'created_at', 'updated_at')]


def get_sqlite_table_columns(sqlite_conn, table_name):
    """获取 SQLite 表的列名"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def convert_value(val, pg_col_name):
    """
    转换值类型以适配 PostgreSQL
    
    SQLite 使用 0/1 表示 boolean，PostgreSQL 使用 true/false
    """
    if val is None:
        return None
    
    # 布尔类型列名
    bool_columns = [
        'is_open', 'is_weak_to_strong', 'is_selected', 'is_filtered',
        'unifuncs_recommended', 'is_success', 'is_win', 'is_active', 'is_primary'
    ]
    
    if pg_col_name in bool_columns:
        if isinstance(val, int):
            return bool(val)
        elif isinstance(val, str):
            return val.lower() in ('true', '1', 'yes')
        return bool(val)
    
    # 字符串处理
    if isinstance(val, str):
        if val == '':
            return None
        return val
    
    return val


def migrate_table(sqlite_conn, pg_conn, table_name):
    """
    迁移单个表
    
    使用 PostgreSQL 表结构作为目标结构
    """
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # 获取 PostgreSQL 表结构
    pg_columns = get_pg_table_columns(pg_conn, table_name)
    
    if not pg_columns:
        print(f"  ⚠️ 表 {table_name} 在 PostgreSQL 中不存在")
        return 0
    
    # 获取 SQLite 表结构
    sqlite_columns = get_sqlite_table_columns(sqlite_conn, table_name)
    
    # 找出两边共有的列（用于迁移）
    common_columns = [c for c in pg_columns if c in sqlite_columns]
    
    if not common_columns:
        print(f"  ℹ️ 表 {table_name} 无共有列可迁移")
        return 0
    
    # 获取 SQLite 数据
    try:
        col_str = ', '.join(common_columns)
        sqlite_cursor.execute(f"SELECT {col_str} FROM {table_name}")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  ⚠️ 表 {table_name} 读取失败: {e}")
        return 0
    
    if not rows:
        print(f"  ℹ️ 表 {table_name} 无数据 (0 条记录)")
        return 0
    
    # 处理数据类型转换
    processed_rows = []
    for row in rows:
        processed_row = []
        for i, val in enumerate(row):
            col_name = common_columns[i]
            converted = convert_value(val, col_name)
            processed_row.append(converted)
        processed_rows.append(tuple(processed_row))
    
    # 构建插入语句
    col_str = ', '.join(common_columns)
    placeholders = ', '.join(['%s'] * len(common_columns))
    insert_sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
    
    # 插入数据
    try:
        psycopg2.extras.execute_batch(pg_cursor, insert_sql, processed_rows)
        pg_conn.commit()
        print(f"  ✅ {table_name}: 迁移 {len(rows)} 条记录")
        return len(rows)
    except Exception as e:
        pg_conn.rollback()
        print(f"  ❌ {table_name}: 迁移失败 - {e}")
        return 0


def main():
    print("=" * 60)
    print("T01 数据迁移: SQLite -> PostgreSQL")
    print("=" * 60)
    
    # 检查 SQLite 文件
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ SQLite 文件不存在: {SQLITE_PATH}")
        return
    
    print(f"\nSQLite 文件: {SQLITE_PATH}")
    print(f"PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    
    # 连接数据库
    try:
        sqlite_conn = get_sqlite_connection()
        print("✅ SQLite 连接成功")
    except Exception as e:
        print(f"❌ SQLite 连接失败: {e}")
        return
    
    try:
        pg_conn = get_postgres_connection()
        print("✅ PostgreSQL 连接成功")
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
        return
    
    # 获取 PostgreSQL 中所有表
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in pg_cursor.fetchall()]
    
    print("\n" + "-" * 60)
    print("开始迁移数据...")
    print("-" * 60)
    
    total_migrated = 0
    for table_name in tables:
        count = migrate_table(sqlite_conn, pg_conn, table_name)
        total_migrated += count
    
    print("-" * 60)
    print(f"\n✅ 迁移完成，共迁移 {total_migrated} 条记录")
    
    # 验证迁移结果
    print("\n验证迁移结果:")
    for table_name in tables:
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = pg_cursor.fetchone()[0]
        if count > 0:
            print(f"  - {table_name}: {count} 条记录")
    
    # 关闭连接
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n数据库连接已关闭")


if __name__ == '__main__':
    main()
