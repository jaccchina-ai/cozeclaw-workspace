#!/usr/bin/env python3
"""
数据一致性检查工具
用于验证 PostgreSQL 和 SQLite 数据库之间的数据一致性，并自动同步差异

使用方法:
    python3 database/consistency_checker.py                    # 检查所有表
    python3 database/consistency_checker.py --table selection_results  # 检查特定表
    python3 database/consistency_checker.py --sync              # 自动同步差异
"""

import os
import sys
import json
import argparse
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.db_config import DB_TYPE, SQLITE_DB_PATH
from database.models import init_db, get_session


# 需要检查一致性的表列表
# 注意：SQLAlchemy 模型名可能与数据库表名不同
# key: 模型名, pg_table: PG表名, sqlite_table: SQLite表名
TABLE_MAPPING = {
    'selection_results': {'pg_table': 'selection_results', 'sqlite_table': 'selection_results'},
    'factor_scores': {'pg_table': 'stock_factor_scores', 'sqlite_table': 'stock_factor_scores'},
    'auction_data': {'pg_table': 'auction_data', 'sqlite_table': 'auction_data'},
    'market_sentiment': {'pg_table': 'market_sentiment', 'sqlite_table': 'market_sentiment'},
    'unifuncs_results': {'pg_table': 'unifuncs_results', 'sqlite_table': 'unifuncs_results'},
    'tracked_results': {'pg_table': 'tracked_results', 'sqlite_table': 'tracked_results'},
    'ml_training_records': {'pg_table': 'ml_training_records', 'sqlite_table': 'ml_training_records'},
}

TABLES_TO_CHECK = list(TABLE_MAPPING.keys())


def get_pg_count(session, table: str) -> int:
    """获取 PostgreSQL 表记录数"""
    try:
        from sqlalchemy import text
        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return result.fetchone()[0]
    except Exception as e:
        print(f"  ⚠️ PG 查询失败: {e}")
        return -1


def get_sqlite_count(table: str) -> int:
    """获取 SQLite 表记录数"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        # 表可能不存在
        return -1


def check_table_consistency(pg_session, table: str) -> Dict:
    """检查单个表的一致性"""
    # 获取实际表名
    mapping = TABLE_MAPPING.get(table, {'pg_table': table, 'sqlite_table': table})
    pg_table = mapping['pg_table']
    sqlite_table = mapping['sqlite_table']
    
    result = {
        'table': table,
        'pg_table': pg_table,
        'sqlite_table': sqlite_table,
        'pg_count': -1,
        'sqlite_count': -1,
        'consistent': False,
        'pg_only_count': 0,
        'sqlite_only_count': 0,
        'status': 'unknown'
    }
    
    try:
        # 1. 比较记录数
        result['pg_count'] = get_pg_count(pg_session, pg_table)
        result['sqlite_count'] = get_sqlite_count(sqlite_table)
        
        if result['pg_count'] == -1 or result['sqlite_count'] == -1:
            result['errors'] = ["无法获取至少一个数据库的记录数"]
            result['status'] = 'error'
            return result
        
        result['consistent'] = (result['pg_count'] == result['sqlite_count'])
        
        # 2. 获取主键列表
        pk_fields = get_primary_key_fields(table)
        pk_list = ', '.join(pk_fields)
        
        # 3. 查询 PG 独有的记录数
        try:
            pg_only = pg_session.execute(text(f"""
                SELECT COUNT(*) FROM {table} t
                WHERE NOT EXISTS (
                    SELECT 1 FROM sqlite_{table} s 
                    WHERE {' AND '.join([f"t.{pk} = s.{pk}" for pk in pk_fields])}
                )
            """))
            result['pg_only_count'] = 0  # 假设表名不同，需要特殊处理
        except:
            pass
        
        # 4. 简单比较
        if result['pg_count'] == result['sqlite_count'] == 0:
            result['status'] = 'empty'
        elif result['pg_count'] == result['sqlite_count']:
            result['status'] = 'consistent'
        else:
            result['status'] = 'inconsistent'
            # 估算差异
            result['pg_only_count'] = max(0, result['pg_count'] - result['sqlite_count'])
            result['sqlite_only_count'] = max(0, result['sqlite_count'] - result['pg_count'])
        
    except Exception as e:
        result['errors'] = [str(e)]
        result['status'] = 'error'
    
    return result


def get_primary_key_fields(table: str) -> List[str]:
    """获取表的主键字段"""
    pk_map = {
        'selection_results': ['trade_date', 'ts_code', 'selection_type'],
        'factor_scores': ['trade_date', 'ts_code'],
        'auction_data': ['trade_date', 'ts_code'],
        'market_sentiment': ['trade_date'],
        'unifuncs_results': ['trade_date', 'task_id'],
        'tracked_results': ['trade_date', 'ts_code'],
        'ml_training_records': ['id'],
    }
    return pk_map.get(table, ['id'])


def print_report(results: List[Dict], verbose: bool = False) -> Tuple[bool, List[Dict]]:
    """打印检查报告，返回(是否全部一致, 需要同步的表列表)"""
    print("\n" + "="*80)
    print("📊 数据一致性检查报告")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    consistent_count = 0
    inconsistent_count = 0
    error_count = 0
    tables_to_sync = []  # 需要同步的表
    
    for r in results:
        status = r.get('status', 'unknown')
        
        if status == 'consistent' or status == 'empty':
            consistent_count += 1
            icon = "✅" if status == 'consistent' else "📭"
            print(f"\n{icon} {r['table']}: {'一致' if status == 'consistent' else '空表'}")
            print(f"   PG: {r['pg_count']} 条 | SQLite: {r['sqlite_count']} 条")
            
        elif status == 'inconsistent':
            inconsistent_count += 1
            tables_to_sync.append(r)  # 添加到同步列表
            print(f"\n❌ {r['table']}: 不一致")
            print(f"   PG: {r['pg_count']} 条 | SQLite: {r['sqlite_count']} 条")
            if r.get('pg_only_count'):
                print(f"   PG 独有: {r['pg_only_count']} 条")
            if r.get('sqlite_only_count'):
                print(f"   SQLite 独有: {r['sqlite_only_count']} 条")
            print(f"   → 需要从 {'PG' if r['pg_count'] > r['sqlite_count'] else 'SQLite'} 同步到 {'SQLite' if r['pg_count'] > r['sqlite_count'] else 'PG'}")
            
        elif status == 'error':
            error_count += 1
            print(f"\n⚠️ {r['table']}: 检查出错")
            for err in r.get('errors', []):
                print(f"   - {err}")
    
    # 汇总
    print("\n" + "-"*80)
    print(f"📈 汇总:")
    print(f"   ✅ 一致: {consistent_count} 个表")
    print(f"   ❌ 不一致: {inconsistent_count} 个表")
    print(f"   ⚠️ 错误: {error_count} 个表")
    
    return inconsistent_count == 0 and error_count == 0, tables_to_sync


def sync_table_data(pg_session, table_info: Dict) -> Dict:
    """同步单个表的数据，从数据条数多的同步到数据条数少的"""
    table = table_info['table']
    pg_table = table_info['pg_table']
    sqlite_table = table_info['sqlite_table']
    pg_count = table_info['pg_count']
    sqlite_count = table_info['sqlite_count']
    
    result = {
        'table': table,
        'synced': 0,
        'errors': []
    }
    
    # 确定同步方向：谁多谁作为源
    if pg_count > sqlite_count:
        source = 'pg'
        target = 'sqlite'
        source_count = pg_count
        print(f"\n🔄 同步 {table}: PG({pg_count}) → SQLite({sqlite_count})")
    else:
        source = 'sqlite'
        target = 'pg'
        source_count = sqlite_count
        print(f"\n🔄 同步 {table}: SQLite({sqlite_count}) → PG({pg_count})")
    
    try:
        if source == 'pg':
            # 从 PG 同步到 SQLite
            result = sync_pg_to_sqlite(pg_session, pg_table, sqlite_table, result)
        else:
            # 从 SQLite 同步到 PG
            result = sync_sqlite_to_pg(pg_session, pg_table, sqlite_table, result)
        
    except Exception as e:
        result['errors'].append(str(e))
        print(f"   ❌ 同步失败: {e}")
        pg_session.rollback()
    
    return result


def sync_pg_to_sqlite(pg_session, pg_table: str, sqlite_table: str, result: Dict) -> Dict:
    """从 PostgreSQL 同步数据到 SQLite"""
    # 获取 PG 列信息
    col_info = pg_session.execute(text(f"""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = '{pg_table}'
    """)).fetchall()
    col_type_map = {col[0]: col[1] for col in col_info}
    pg_columns = [col[0] for col in col_info]
    
    # 获取 PG 数据
    pg_data = pg_session.execute(text(f"SELECT {', '.join(pg_columns)} FROM {pg_table}")).fetchall()
    
    # 连接 SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ', '.join(['?' for _ in pg_columns])
    insert_sql = f"INSERT OR REPLACE INTO {sqlite_table} ({', '.join(pg_columns)}) VALUES ({placeholders})"
    
    for row_idx, row in enumerate(pg_data):
        try:
            values = []
            # 将行转换为字典，统一按列名取值
            row_dict = dict(zip(pg_columns, row))
            
            for col in pg_columns:
                val = row_dict[col]
                # PostgreSQL 布尔值转换为 SQLite 整数
                if col_type_map.get(col) == 'boolean' and val is not None:
                    val = 1 if val else 0
                # PostgreSQL timestamp 转换为 SQLite 字符串
                elif 'timestamp' in str(col_type_map.get(col, '')) and val:
                    val = str(val)
                values.append(val)
            
            cursor.execute(insert_sql, values)
            result['synced'] += 1
        except Exception as e:
            error_msg = f"PG→SQLite 行 {row_idx+1} 错误: {e}"
            print(f"   ⚠️ {error_msg}")
            result['errors'].append(error_msg)
    
    conn.commit()
    conn.close()
    pg_session.commit()
    
    print(f"   ✅ 已同步 {result['synced']} 条到 SQLite")
    return result


def sync_sqlite_to_pg(pg_session, pg_table: str, sqlite_table: str, result: Dict) -> Dict:
    """从 SQLite 同步数据到 PostgreSQL"""
    # 连接 SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({sqlite_table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    # 获取所有数据
    cursor.execute(f"SELECT * FROM {sqlite_table}")
    rows = cursor.fetchall()
    conn.close()
    
    # 获取 PG 列类型
    col_info = pg_session.execute(text(f"""
        SELECT column_name, data_type FROM information_schema.columns 
        WHERE table_name = '{pg_table}'
    """)).fetchall()
    col_type_map = {col[0]: col[1] for col in col_info}
    
    # 构建 INSERT 语句
    placeholders = ', '.join([f":{col}" for col in columns])
    insert_sql = text(f"""
        INSERT INTO {pg_table} ({', '.join(columns)}) 
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """)
    
    for row in rows:
        try:
            data = dict(zip(columns, row))
            # SQLite 整数转换为 PostgreSQL 布尔值
            for col, col_type in col_type_map.items():
                if col_type == 'boolean' and col in data and data[col] is not None:
                    data[col] = bool(data[col])
                # timestamp 转换
                elif 'timestamp' in str(col_type) and col in data and data[col]:
                    data[col] = str(data[col])
            
            pg_session.execute(insert_sql, data)
            result['synced'] += 1
        except Exception as e:
            result['errors'].append(f"SQLite→PG: {e}")
    
    pg_session.commit()
    
    print(f"   ✅ 已同步 {result['synced']} 条到 PG")
    return result


def main():
    parser = argparse.ArgumentParser(description='数据一致性检查工具')
    parser.add_argument('--table', '-t', help='指定检查的表名')
    parser.add_argument('--sync', '-s', action='store_true', help='自动同步差异（从数据多的同步到数据少的）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    args = parser.parse_args()
    
    print(f"数据库类型: {DB_TYPE}")
    
    # 初始化数据库连接
    init_db()
    
    # 获取 PG 连接
    pg_session = get_session()
    
    # 确定要检查的表
    tables = [args.table] if args.table else TABLES_TO_CHECK
    
    results = []
    
    try:
        for table in tables:
            print(f"\n🔍 检查表: {table}...")
            result = check_table_consistency(pg_session, table)
            results.append(result)
            
            # 遇到错误时回滚事务，避免影响后续查询
            pg_session.rollback()
        
        # 打印报告
        all_ok, tables_to_sync = print_report(results, verbose=args.verbose)
        
        # 自动同步
        if args.sync and tables_to_sync:
            print("\n" + "="*80)
            print("🔄 开始自动同步...")
            print("="*80)
            
            sync_results = []
            for table_info in tables_to_sync:
                sync_result = sync_table_data(pg_session, table_info)
                sync_results.append(sync_result)
                pg_session.rollback()  # 每表事务后回滚
                
            print("\n" + "="*80)
            print("📊 同步结果汇总")
            print("="*80)
            total_synced = sum(r['synced'] for r in sync_results)
            total_errors = sum(len(r['errors']) for r in sync_results)
            for r in sync_results:
                status = "✅" if r['errors'] else "⚠️"
                print(f"   {status} {r['table']}: 同步 {r['synced']} 条, 错误 {len(r['errors'])} 个")
            print(f"\n总计: 同步 {total_synced} 条, 错误 {total_errors} 个")
            
            # 重新检查一致性
            print("\n" + "="*80)
            print("🔍 同步后重新检查...")
            print("="*80)
            
            results = []
            for table in tables:
                result = check_table_consistency(pg_session, table)
                results.append(result)
                pg_session.rollback()
            
            all_ok, _ = print_report(results, verbose=False)
        
        # 保存详细报告
        report_file = f"consistency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📄 详细报告已保存: {report_file}")
        
        return 0 if all_ok else 1
        
    finally:
        pg_session.close()


if __name__ == '__main__':
    sys.exit(main())
