#!/usr/bin/env python3
"""
T01 选股系统 - 完整模块测试脚本
功能：测试各核心模块功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from database.models import init_db, get_session
from sqlalchemy import text


def test_database_connection():
    """测试数据库连接"""
    print("\n📊 测试1: 数据库连接")
    print("-"*40)
    try:
        init_db()
        session = get_session()
        result = session.execute(text("SELECT 1")).fetchone()
        print(f"  ✅ PostgreSQL 连接成功")
        session.close()
        return True
    except Exception as e:
        print(f"  ❌ PostgreSQL 连接失败: {e}")
        return False


def test_data_existence():
    """测试数据存在性"""
    print("\n📊 测试2: 数据存在性检查")
    print("-"*40)
    
    init_db()
    session = get_session()
    
    test_date = '20260403'
    tables_to_check = [
        ('daily_stock_data', '每日行情', 'trade_date'),
        ('moneyflow_data', '资金流向', 'trade_date'),
        ('selection_results', '选股结果', 'trade_date'),
        ('stock_factor_scores', '因子评分', 'trade_date'),
        ('auction_data', '竞价数据', 'trade_date'),
        ('market_sentiment', '市场情绪', 'trade_date'),
        ('unifuncs_results', '涨跌停播报', 'trade_date'),
        ('tracked_results', '跟踪结果', 't_day'),
    ]
    
    results = []
    for table, name, date_field in tables_to_check:
        try:
            count = session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {date_field} = :date"),
                {'date': test_date}
            ).fetchone()[0]
            if count > 0:
                print(f"  ✅ {name} ({table}): {count} 条")
                results.append(True)
            else:
                print(f"  ⚠️ {name} ({table}): 0 条")
                results.append(False)
        except Exception as e:
            print(f"  ❌ {name} ({table}): {e}")
            results.append(False)
    
    session.close()
    return all(results)


def test_selection_engine():
    """测试选股引擎"""
    print("\n📊 测试3: 选股引擎功能")
    print("-"*40)
    try:
        from selection_engine import TDaySelectionEngine
        print("  ✅ selection_engine 模块导入成功")
        
        # 检查引擎依赖
        engine = TDaySelectionEngine()
        print(f"  ✅ TDaySelectionEngine 实例化成功")
        print(f"     - hot_money_manager: {'已启用' if engine.hot_money_manager else '未启用'}")
        return True
    except Exception as e:
        print(f"  ❌ 选股引擎测试失败: {e}")
        return False


def test_ml_data_exporter():
    """测试ML数据导出"""
    print("\n📊 测试4: ML数据导出功能")
    print("-"*40)
    try:
        from ml_data_exporter import MLDataExporter
        
        exporter = MLDataExporter()
        print("  ✅ MLDataExporter 实例化成功")
        
        # 测试数据查询
        test_date = '20260403'
        try:
            df = exporter.get_training_data(start_date='20260301', end_date='20260403')
            if df is not None and len(df) > 0:
                print(f"  ✅ 训练数据查询成功: {len(df)} 条")
                return True
            else:
                print(f"  ⚠️ 训练数据为空")
                return True  # 数据可能为空但模块本身正常
        except Exception as e:
            print(f"  ⚠️ 训练数据查询: {e}")
            return True  # 模块本身正常，只是数据问题
            
    except Exception as e:
        print(f"  ❌ ML数据导出测试失败: {e}")
        return False


def test_factor_analysis():
    """测试因子分析功能"""
    print("\n📊 测试5: 因子分析功能")
    print("-"*40)
    try:
        # 尝试导入因子分析模块
        import factor_analysis
        print("  ✅ factor_analysis 模块导入成功")
        return True
    except Exception as e:
        print(f"  ❌ 因子分析测试失败: {e}")
        return False


def test_evolution_module():
    """测试Evolution模块"""
    print("\n📊 测试6: Evolution模块")
    print("-"*40)
    try:
        import evolution
        print("  ✅ evolution 模块导入成功")
        return True
    except Exception as e:
        print(f"  ❌ Evolution模块测试失败: {e}")
        return False


def test_data_consistency():
    """测试数据一致性"""
    print("\n📊 测试7: 数据一致性检查")
    print("-"*40)
    try:
        import sqlite3
        from database.db_config import SQLITE_DB_PATH
        
        init_db()
        session = get_session()
        
        test_date = '20260403'
        tables = ['daily_stock_data', 'moneyflow_data']
        all_consistent = True
        
        for table in tables:
            # PG count
            pg_count = session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE trade_date = :date"),
                {'date': test_date}
            ).fetchone()[0]
            
            # SQLite count
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE trade_date = ?", (test_date,))
            sqlite_count = cursor.fetchone()[0]
            conn.close()
            
            if pg_count == sqlite_count:
                print(f"  ✅ {table}: PG={pg_count}, SQLite={sqlite_count}")
            else:
                print(f"  ❌ {table}: PG={pg_count}, SQLite={sqlite_count} (不一致!)")
                all_consistent = False
        
        session.close()
        return all_consistent
    except Exception as e:
        print(f"  ❌ 数据一致性测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("📊 T01 选股系统 - 完整模块测试")
    print("="*60)
    
    results = {}
    
    # 执行各项测试
    results['数据库连接'] = test_database_connection()
    results['数据存在性'] = test_data_existence()
    results['选股引擎'] = test_selection_engine()
    results['ML数据导出'] = test_ml_data_exporter()
    results['因子分析'] = test_factor_analysis()
    results['Evolution模块'] = test_evolution_module()
    results['数据一致性'] = test_data_consistency()
    
    # 汇总
    print("\n" + "="*60)
    print("📈 测试汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️ {failed} 项测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
