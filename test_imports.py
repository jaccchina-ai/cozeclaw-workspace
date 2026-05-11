#!/usr/bin/env python3
import sys
import traceback
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

def test_imports():
    """测试各个模块的导入情况"""
    print("=== 模块导入测试 ===")
    
    # 测试1: 数据库模块
    try:
        from database.models import init_db, get_session
        print("✅ database.models 导入成功")
        init_db()
        print("✅ 数据库初始化成功")
        session = get_session()
        print("✅ 成功获取数据库会话")
        session.close()
    except Exception as e:
        print(f"❌ 数据库模块导入失败: {e}")
        traceback.print_exc()
    
    print("\n" + "="*50 + "\n")
    
    # 测试2: selection_engine 模块
    try:
        from selection_engine import TDaySelectionEngine, T1AuctionEngine
        print("✅ selection_engine 导入成功")
        print(f"   可用类: TDaySelectionEngine, T1AuctionEngine")
    except Exception as e:
        print(f"❌ selection_engine 导入失败: {e}")
        traceback.print_exc()
    
    print("\n" + "="*50 + "\n")
    
    # 测试3: data_fetcher 模块
    try:
        from data_fetcher import create_fetcher
        print("✅ data_fetcher 导入成功")
        fetcher = create_fetcher()
        print("✅ 成功创建数据获取器")
    except Exception as e:
        print(f"❌ data_fetcher 导入失败: {e}")
        traceback.print_exc()
    
    print("\n" + "="*50 + "\n")
    
    # 测试4: 尝试直接调用stk_auction接口
    try:
        from data_fetcher import create_fetcher
        fetcher = create_fetcher()
        print("✅ 测试 stk_auction 接口调用...")
        # 使用一个无效的股票代码测试
        result = fetcher.get_auction_data('000001.SZ', '20260508')
        print(f"✅ 接口调用成功，返回数据: {result}")
    except Exception as e:
        print(f"❌ stk_auction 接口调用失败: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    test_imports()