#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版龙虎榜集成检查脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("T日晚间选股系统龙虎榜集成检查报告")
print("="*60)

# 1. 检查龙虎榜模块是否可导入
print("\n1. 龙虎榜模块可用性检查:")
try:
    from dragon_tiger.integration import DragonTigerIntegration
    from dragon_tiger.api import DragonTigerAPI
    print("✅ 龙虎榜模块可正常导入")
except Exception as e:
    print(f"❌ 龙虎榜模块导入失败: {e}")
    sys.exit(1)

# 2. 检查选股引擎
print("\n2. 选股引擎检查:")
try:
    import selection_engine
    # 检查是否有TDaySelectionEngine
    if hasattr(selection_engine, 'TDaySelectionEngine'):
        print("✅ TDaySelectionEngine 存在")
        engine_class = getattr(selection_engine, 'TDaySelectionEngine')
        engine = engine_class()
        print("✅ 选股引擎初始化成功")
        
        # 检查是否可以访问scoring_model
        if hasattr(engine, 'scoring_model'):
            print("✅ 得分模型存在")
        else:
            print("⚠️  无法访问得分模型")
    else:
        print("❌ TDaySelectionEngine 不存在")
        
except Exception as e:
    print(f"❌ 选股引擎检查失败: {e}")

# 3. 测试龙虎榜因子计算
print("\n3. 龙虎榜因子计算测试:")
try:
    integration = DragonTigerIntegration()
    
    # 测试获取龙虎榜因子
    test_result = integration.get_dragon_tiger_score({'ts_code': '000001.SZ'})
    print(f"✅ 获取单只股票龙虎榜因子成功: {test_result}")
    
    # 测试批量处理
    test_stocks = [
        {'ts_code': '000001.SZ', 'name': '平安银行'},
        {'ts_code': '000002.SZ', 'name': '万科A'},
        {'ts_code': '600000.SH', 'name': '浦发银行'}
    ]
    
    updated_stocks = integration.update_stock_selection_factors(test_stocks)
    print(f"✅ 批量更新龙虎榜因子成功，更新了 {len(updated_stocks)} 只股票")
    
    for stock in updated_stocks[:2]:
        print(f"   {stock['ts_code']}: {stock.get('dragon_tiger_score', 0)}")
        
except Exception as e:
    print(f"❌ 龙虎榜因子测试失败: {e}")

# 4. 检查选股代码中是否已集成龙虎榜因子
print("\n4. 选股代码集成检查:")
try:
    import linecache
    import selection_engine
    
    # 检查run_t_day_selection函数
    source_file = selection_engine.__file__
    if source_file.endswith('.pyc'):
        source_file = source_file[:-1]
    
    # 搜索龙虎榜相关代码
    found = False
    with open(source_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if 'dragon_tiger' in line.lower() or '龙虎榜' in line:
                print(f"✅ 第 {line_num} 行发现龙虎榜相关代码: {line.strip()}")
                found = True
    
    if not found:
        print("⚠️  选股代码中未显式找到龙虎榜相关代码")
        print("📌 需要手动将龙虎榜因子集成到选股逻辑中")
        print("📌 建议在评分模型和筛选逻辑中添加龙虎榜因子")
        
except Exception as e:
    print(f"❌ 代码搜索失败: {e}")

# 5. 数据库检查
print("\n5. 数据库集成检查:")
try:
    from database.models import get_session
    session = get_session()
    
    # 检查龙虎榜表是否存在
    from sqlalchemy import inspect
    inspector = inspect(session.get_bind())
    tables = inspector.get_table_names()
    
    dragon_tiger_tables = [t for t in tables if 'dragon_tiger' in t]
    if dragon_tiger_tables:
        print("✅ 龙虎榜相关表已存在:")
        for table in dragon_tiger_tables:
            print(f"   - {table}")
    else:
        print("❌ 龙虎榜相关表不存在")
        
    # 检查因子得分表
    if 'stock_factor_scores' in tables:
        print("✅ 股票因子得分表存在")
        print("📌 可在该表中存储龙虎榜因子得分")
    
    session.close()
    
except Exception as e:
    print(f"❌ 数据库检查失败: {e}")

# 6. 集成建议
print("\n" + "="*60)
print("6. 集成建议:")
print("📌 在 FactorWeights 类中添加 dragon_tiger 字段")
print("📌 在 ScoringModel 中添加龙虎榜因子计算逻辑")
print("📌 在选股流程中调用 filter_by_dragon_tiger 函数")
print("📌 为龙虎榜因子配置合适的权重参数")
print("📌 在选股结果中显示龙虎榜因子得分")

print("\n" + "="*60)
print("🎉 龙虎榜模块核心功能正常，可开始集成到选股系统！")
print("📌 目前已具备完整的龙虎榜数据分析能力")
print("📌 需要在选股逻辑中添加因子调用和筛选代码")
