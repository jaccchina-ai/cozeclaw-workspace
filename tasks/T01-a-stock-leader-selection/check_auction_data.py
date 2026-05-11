#!/usr/bin/env python3
"""
查询auction_results表中20260323的数据
"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.models import AuctionResult, session_scope

# 查询20260323的竞价选股结果
with session_scope() as session:
    results = session.query(AuctionResult).filter(AuctionResult.trade_date == '20260323').all()
    
    print(f"查询到 {len(results)} 条20260323的竞价选股结果")
    for result in results:
        print(f"股票代码: {result.ts_code}, 股票名称: {result.name}, 总分: {result.total_score}")
        
    # 检查表是否存在
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()
    print(f"\n数据库中的表: {tables}")
    
    # 如果auction_results表存在，查看表结构
    if 'auction_results' in tables:
        print("\nauction_results表结构:")
        columns = inspector.get_columns('auction_results')
        for column in columns:
            print(f"  {column['name']}: {column['type']}")