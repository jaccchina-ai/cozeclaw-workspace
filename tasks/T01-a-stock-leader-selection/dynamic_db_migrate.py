"""
T01 动态数据库迁移工具

支持根据因子配置自动创建/更新数据库表结构
"""

import os
import sys
from typing import List, Tuple
from sqlalchemy import Column, Float, String, inspect
from sqlalchemy.exc import OperationalError

sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.models import (
    Base, StockFactorScore, AuctionData, init_db, get_session
)
from factor_config import factor_manager, FactorType


def get_existing_columns(table_name: str) -> List[str]:
    """获取表现有字段"""
    engine = init_db()
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]


def column_exists(table_name: str, column_name: str) -> bool:
    """检查字段是否存在"""
    return column_name in get_existing_columns(table_name)


def add_column(table_name: str, column_name: str, column_type: str = 'Float'):
    """添加字段到表"""
    from sqlalchemy import text
    engine = init_db()
    
    type_mapping = {
        'Float': 'FLOAT',
        'String': 'VARCHAR(50)',
        'Integer': 'INTEGER',
    }
    
    sql_type = type_mapping.get(column_type, 'FLOAT')
    
    try:
        with engine.connect() as conn:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"
            conn.execute(text(sql))
            conn.commit()
        return True
    except OperationalError as e:
        if "duplicate column name" in str(e).lower():
            return True  # 已存在
        print(f"添加字段失败: {e}")
        return False


def sync_factor_table(category: str, table_name: str, model_class):
    """
    同步因子表结构
    
    Args:
        category: 因子类别 (t_day_factors / auction_factors)
        table_name: 表名
        model_class: 模型类
    """
    print(f"\n【同步 {table_name} 表】")
    
    # 获取配置中的字段
    required_fields = factor_manager.get_database_fields(category)
    print(f"配置要求字段数: {len(required_fields)}")
    
    # 获取现有字段
    existing = get_existing_columns(table_name)
    print(f"现有字段数: {len(existing)}")
    
    # 找出需要添加的字段
    to_add = []
    for field_name, field_type, comment in required_fields:
        if field_name not in existing:
            to_add.append((field_name, field_type))
    
    if not to_add:
        print(f"✅ {table_name} 表结构已是最新")
        return 0
    
    # 添加缺失的字段
    print(f"需要添加字段数: {len(to_add)}")
    added = 0
    for field_name, field_type in to_add:
        if add_column(table_name, field_name, field_type):
            print(f"  ✅ 添加字段: {field_name}")
            added += 1
        else:
            print(f"  ❌ 添加失败: {field_name}")
    
    return added


def create_dynamic_factor_table(category: str, table_name: str) -> bool:
    """
    创建动态因子表（如果不存在）
    
    用于创建新的因子数据表
    """
    from sqlalchemy import Table, Column, Integer, String, Float, DateTime
    from database.models import Base, DATABASE_URL
    from sqlalchemy import create_engine
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    # 检查表是否存在
    if inspect(engine).has_table(table_name):
        return True
    
    # 获取字段定义
    fields = factor_manager.get_database_fields(category)
    
    # 动态创建表
    columns = [
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('ts_code', String(12), index=True),
        Column('trade_date', String(8), index=True),
    ]
    
    for field_name, field_type, _ in fields:
        col_type = Float if field_type == 'Float' else String(50)
        columns.append(Column(field_name, col_type, default=0 if field_type == 'Float' else None))
    
    columns.append(Column('created_at', DateTime))
    
    # 创建表
    table = Table(table_name, Base.metadata, *columns)
    table.create(engine)
    
    print(f"✅ 创建表: {table_name}")
    return True


def validate_database_schema():
    """验证数据库结构完整性"""
    print("=" * 60)
    print("数据库结构验证")
    print("=" * 60)
    
    issues = []
    
    # 检查 StockFactorScore 表
    print("\n【检查 StockFactorScore 表】")
    existing = set(get_existing_columns('stock_factor_scores'))
    required = set(name for name, _, _ in factor_manager.get_database_fields('t_day_factors'))
    
    missing = required - existing
    if missing:
        print(f"⚠️ 缺失字段: {missing}")
        issues.extend([(f"stock_factor_scores.{f}", "缺失") for f in missing])
    else:
        print("✅ 所有必需字段已存在")
    
    # 检查 AuctionData 表
    print("\n【检查 AuctionData 表】")
    existing = set(get_existing_columns('auction_data'))
    required = set(name for name, _, _ in factor_manager.get_database_fields('auction_factors'))
    
    missing = required - existing
    if missing:
        print(f"⚠️ 缺失字段: {missing}")
        issues.extend([(f"auction_data.{f}", "缺失") for f in missing])
    else:
        print("✅ 所有必需字段已存在")
    
    if issues:
        print(f"\n⚠️ 发现 {len(issues)} 个问题")
        return False, issues
    else:
        print("\n✅ 数据库结构完整")
        return True, []


def migrate_database():
    """执行数据库迁移"""
    print("=" * 60)
    print("T01 动态数据库迁移")
    print("=" * 60)
    
    # 同步 T日因子表
    t_day_added = sync_factor_table('t_day_factors', 'stock_factor_scores', StockFactorScore)
    
    # 同步 竞价因子表
    auction_added = sync_factor_table('auction_factors', 'auction_data', AuctionData)
    
    print("\n" + "=" * 60)
    print("迁移完成")
    print("=" * 60)
    print(f"T日因子表新增字段: {t_day_added}")
    print(f"竞价因子表新增字段: {auction_added}")
    
    # 验证
    valid, issues = validate_database_schema()
    
    return valid


def generate_orm_model_code(category: str, class_name: str) -> str:
    """
    生成ORM模型代码
    
    用于生成更新后的 models.py 代码
    """
    fields = factor_manager.get_database_fields(category)
    
    code_lines = [f"class {class_name}(Base):"]
    code_lines.append(f'    """{category} 动态生成"""')
    code_lines.append(f"    __tablename__ = '{class_name.lower()}'")
    code_lines.append("")
    code_lines.append("    id = Column(Integer, primary_key=True, autoincrement=True)")
    code_lines.append("    ts_code = Column(String(12), index=True)")
    code_lines.append("    trade_date = Column(String(8), index=True)")
    code_lines.append("")
    
    for field_name, field_type, comment in fields:
        col_type = 'Float' if field_type == 'Float' else 'String(50)'
        default = ', default=0' if field_type == 'Float' else ''
        code_lines.append(f"    {field_name} = Column({col_type}{default})  # {comment}")
    
    code_lines.append("")
    code_lines.append("    created_at = Column(DateTime, default=datetime.now)")
    
    return '\n'.join(code_lines)


if __name__ == '__main__':
    # 执行迁移
    success = migrate_database()
    
    if success:
        print("\n✅ 数据库迁移成功!")
    else:
        print("\n⚠️ 数据库结构不完整，请手动修复")
