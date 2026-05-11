#!/usr/bin/env python3
"""
数据库模型修复脚本
修复重复索引创建问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, Index
from sqlalchemy.exc import ProgrammingError
from database.models import Base, DATABASE_URL, get_engine_kwargs

def fix_duplicate_indexes():
    """修复重复索引问题"""
    try:
        engine = create_engine(DATABASE_URL, **get_engine_kwargs())
        
        # 检查并删除已存在的重复索引
        indexes_to_check = [
            'idx_limit_trade_date',
            'idx_limit_ts_code_date', 
            'idx_limit_type',
            'idx_step_ts_code_date',
            'idx_step_time'
        ]
        
        with engine.connect() as conn:
            for index_name in indexes_to_check:
                try:
                    # 检查索引是否存在
                    result = conn.execute(
                        text("""
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name
                        """),
                        {'index_name': index_name}
                    )
                    
                    if result.fetchone():
                        print(f"删除已存在的索引: {index_name}")
                        conn.execute(
                            text(f"DROP INDEX {index_name}")
                        )
                        conn.commit()
                        
                except Exception as e:
                    print(f"处理索引{index_name}时出错: {e}")
                    conn.rollback()
        
        print("索引修复完成")
        return True
        
    except Exception as e:
        print(f"修复索引时出错: {e}")
        return False

def update_model_definitions():
    """更新模型定义，移除重复索引"""
    try:
        # 读取并修改models.py文件
        models_path = os.path.join(os.path.dirname(__file__), 'database', 'models.py')
        
        with open(models_path, 'r') as f:
            content = f.read()
        
        # 移除重复的idx_limit_trade_date索引定义
        if 'Index(\'idx_limit_trade_date\', \'trade_date\'),' in content:
            content = content.replace(
                'Index(\'idx_limit_trade_date\', \'trade_date\'),',
                ''
            )
            print("已移除重复的idx_limit_trade_date索引定义")
        
        # 保存修改
        with open(models_path, 'w') as f:
            f.write(content)
        
        print("模型定义更新完成")
        return True
        
    except Exception as e:
        print(f"更新模型定义时出错: {e}")
        return False

def reinit_database():
    """重新初始化数据库"""
    try:
        engine = create_engine(DATABASE_URL, **get_engine_kwargs())
        
        # 重新创建所有表（忽略已存在的表）
        Base.metadata.create_all(engine, checkfirst=True)
        
        print("数据库重新初始化完成")
        return True
        
    except Exception as e:
        print(f"重新初始化数据库时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== 数据库模型修复脚本 ===\n")
    
    # 步骤1: 修复重复索引
    print("步骤1: 修复重复索引...")
    if not fix_duplicate_indexes():
        print("索引修复失败")
        return 1
    
    # 步骤2: 更新模型定义
    print("\n步骤2: 更新模型定义...")
    if not update_model_definitions():
        print("模型定义更新失败")
        return 1
    
    # 步骤3: 重新初始化数据库
    print("\n步骤3: 重新初始化数据库...")
    if not reinit_database():
        print("数据库重新初始化失败")
        return 1
    
    print("\n✅ 所有修复操作完成")
    return 0

if __name__ == '__main__':
    sys.exit(main())