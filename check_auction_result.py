import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from strategy.auction_strategy import AuctionStrategy
from data.data_provider import DataProvider

dp = DataProvider()
data = dp.get_auction_data('20260422')
print('获取竞价数据条数: %s' % (len(data) if data else 0))

if data:
    strategy = AuctionStrategy()
    results = strategy.select_stocks(data)
    print('选股结果条数: %s' % len(results))
    if not results:
        print('所有股票均未通过过滤条件')
        # 检查过滤原因
        for stock in data:
            reasons = strategy.get_filter_reasons(stock)
            if reasons:
                print(f"股票 {stock['ts_code']} 未通过过滤: {reasons}")