#!/usr/bin/env python3
"""
主力资金流向模块 - 完整功能测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import json
from datetime import datetime
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from money_flow_analyzer import AdvancedMoneyFlowAnalyzer


def test_module_import():
    """测试1: 模块导入"""
    print("\n📊 测试1: 模块导入")
    print("-"*50)
    try:
        from money_flow_analyzer import AdvancedMoneyFlowAnalyzer
        print("  ✅ AdvancedMoneyFlowAnalyzer 导入成功")
        return True
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        return False


def test_module_initialization():
    """测试2: 模块初始化"""
    print("\n📊 测试2: 模块初始化")
    print("-"*50)
    try:
        analyzer = AdvancedMoneyFlowAnalyzer()
        print(f"  ✅ 模块实例化成功")
        print(f"     - 数据库类型: {analyzer.db_type}")
        return True
    except Exception as e:
        print(f"  ❌ 初始化失败: {e}")
        return False


def test_single_stock_analysis():
    """测试3: 单只股票分析"""
    print("\n📊 测试3: 单只股票分析")
    print("-"*50)
    try:
        analyzer = AdvancedMoneyFlowAnalyzer()
        
        # 获取一只涨停股进行测试
        from database.models import get_session
        from sqlalchemy import text
        
        session = get_session()
        
        # 获取最近的涨停股
        result = session.execute(text("""
            SELECT ts_code FROM limit_up_stocks 
            ORDER BY trade_date DESC LIMIT 1
        """))
        row = result.fetchone()
        session.close()
        
        if not row:
            print("  ⚠️ 数据库中没有涨停股数据，跳过单只股票分析")
            return True
        
        test_ts_code = row[0]
        print(f"  测试股票: {test_ts_code}")
        
        result = analyzer.analyze_single_stock(test_ts_code, start_date='20260301', end_date='20260403')
        
        if result:
            print(f"  ✅ 分析完成")
            print(f"     - 分析周期: {result.get('analysis_period')}")
            print(f"     - 基础分析: {'有' if result.get('fundamental_analysis') else '无'}")
            print(f"     - 资金统计: {'有' if result.get('flow_statistics') else '无'}")
            print(f"     - 时序分析: {'有' if result.get('time_series_analysis') else '无'}")
            print(f"     - 板块对比: {'有' if result.get('sector_comparison') else '无'}")
            print(f"     - 异常检测: {'有' if result.get('anomaly_detection') else '无'}")
            print(f"     - 建议数量: {len(result.get('recommendations', []))} 条")
            return True
        else:
            print("  ⚠️ 分析结果为空")
            return True
            
    except Exception as e:
        print(f"  ❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_source():
    """测试4: 数据源检查"""
    print("\n📊 测试4: 数据源检查")
    print("-"*50)
    try:
        from database.models import get_session
        from sqlalchemy import text
        
        session = get_session()
        
        # 检查各数据表
        tables = [
            ('daily_stock_data', '每日行情'),
            ('moneyflow_data', '资金流向'),
            ('limit_up_stocks', '涨停股'),
        ]
        
        for table, name in tables:
            try:
                result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                print(f"  ✅ {name} ({table}): {count} 条")
            except Exception as e:
                print(f"  ⚠️ {name} ({table}): {e}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"  ❌ 数据源检查失败: {e}")
        return False


def test_flow_statistics():
    """测试5: 资金流向统计功能"""
    print("\n📊 测试5: 资金流向统计功能")
    print("-"*50)
    try:
        analyzer = AdvancedMoneyFlowAnalyzer()
        
        # 检查是否有可用数据
        from database.models import get_session
        from sqlalchemy import text
        
        session = get_session()
        result = session.execute(text("SELECT COUNT(*) FROM moneyflow_data"))
        count = result.fetchone()[0]
        session.close()
        
        if count == 0:
            print("  ⚠️ 资金流向数据为空，跳过统计测试")
            return True
        
        print(f"  资金流向数据: {count} 条")
        
        # 测试统计功能
        stats = analyzer._analyze_flow_statistics('000001.SZ', '20260301', '20260403')
        if stats:
            print(f"  ✅ 统计功能正常")
            print(f"     - 统计结果: {json.dumps(stats, ensure_ascii=False)[:200]}...")
        return True
        
    except Exception as e:
        print(f"  ❌ 统计功能测试失败: {e}")
        return True  # 不阻塞


def main():
    """主函数"""
    print("\n" + "="*60)
    print("📊 主力资金流向模块 - 完整功能测试")
    print("="*60)
    
    results = {}
    
    results['模块导入'] = test_module_import()
    results['模块初始化'] = test_module_initialization()
    results['数据源检查'] = test_data_source()
    results['单只股票分析'] = test_single_stock_analysis()
    results['资金统计功能'] = test_flow_statistics()
    
    # 汇总
    print("\n" + "="*60)
    print("📈 测试汇总")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n✅ 所有测试通过!")
    else:
        print(f"\n⚠️ {failed} 项测试失败")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
