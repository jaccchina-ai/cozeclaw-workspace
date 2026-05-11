#!/usr/bin/env python3
"""
查询20260323的竞价选股结果
"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.models import AuctionData, SelectionResult, get_session

# 获取会话
session = get_session()

try:
    print("=== 查询AuctionData表 ===")
    auction_data = session.query(AuctionData).filter(AuctionData.trade_date == '20260323').all()
    print(f"查询到 {len(auction_data)} 条20260323的竞价数据")
    
    if auction_data:
        first_data = auction_data[0]
        print(f"示例数据: 股票代码={first_data.ts_code}, 名称={first_data.name}, 总分={first_data.total_score}")
    
    print("\n=== 查询SelectionResult表 ===")
    selection_results = session.query(SelectionResult).filter(SelectionResult.trade_date == '20260323').all()
    print(f"查询到 {len(selection_results)} 条20260323的选股结果")
    
    if selection_results:
        first_result = selection_results[0]
        print(f"示例数据: 股票代码={first_result.ts_code}, 名称={first_result.name}, 策略类型={first_result.strategy_type}")
        
finally:
    # 关闭会话
    session.close()