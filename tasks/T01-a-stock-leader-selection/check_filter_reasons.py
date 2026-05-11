#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from strategy.auction_strategy import AuctionStrategy
from data.data_provider import DataProvider

def main():
    dp = DataProvider()
    data = dp.get_auction_data('20260422')
    strategy = AuctionStrategy()

    print('=== 20260422竞价选股过滤详情 ===')
    for i, stock in enumerate(data[:5]):  # 只看前5只进入评估的股票
        print('\n股票 %d: %s - %s' % (i+1, stock['ts_code'], stock['name']))
        print('  竞价涨幅: %.2f%%' % stock['auction_change'])
        print('  竞价成交量: %.2f万手' % (stock['auction_vol']/10000))
        print('  封单金额: %.2f万元' % (stock['seal_amount']/10000))
        print('  封单比率: %.2f%%' % stock['seal_ratio'])
        print('  连板数: %d' % stock['continuous_up'])
        
        reasons = strategy.get_filter_reasons(stock)
        if reasons:
            print('  未通过原因: %s' % reasons)
        else:
            print('  ✅ 通过所有过滤条件')

if __name__ == '__main__':
    main()