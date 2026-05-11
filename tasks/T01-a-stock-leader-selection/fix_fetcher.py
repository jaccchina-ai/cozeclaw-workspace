#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解决fetcher模块依赖问题
"""

import os
import sys

# 创建fetcher模块
fetcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础fetcher模块，提供数据获取功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import tushare as ts

class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        self.ts_api = ts.pro_api()
    
    def get_previous_trade_date(self):
        """
        获取前一交易日
        """
        try:
            # 从tushare获取交易日历
            df = self.ts_api.trade_cal(exchange='SSE', start_date='20230101', end_date=datetime.now().strftime('%Y%m%d'))
            trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()
            today = datetime.now().strftime('%Y%m%d')
            
            # 找到前一个交易日
            if today in trade_dates:
                idx = trade_dates.index(today)
                if idx > 0:
                    return trade_dates[idx-1]
                else:
                    return trade_dates[0]
            else:
                # 如果今天不是交易日，找到最近的交易日
                while today not in trade_dates:
                    today = (datetime.strptime(today, '%Y%m%d') - timedelta(days=1)).strftime('%Y%m%d')
                return today
                
        except Exception as e:
            print(f"获取交易日历失败，使用简单模式: {e}")
            # 简单模式
            today = datetime.now()
            while True:
                today -= timedelta(days=1)
                if today.weekday() < 5:
                    return today.strftime('%Y%m%d')


def get_previous_trade_date():
    """
    获取前一交易日的便捷函数
    """
    fetcher = DataFetcher()
    return fetcher.get_previous_trade_date()


if __name__ == '__main__':
    print("测试DataFetcher:")
    fetcher = DataFetcher()
    print(f"前一交易日: {fetcher.get_previous_trade_date()}")
'''

# 保存fetcher模块
with open('fetcher.py', 'w') as f:
    f.write(fetcher_content)

print("✅ 已创建fetcher模块")

# 测试导入
try:
    sys.path.insert(0, os.path.abspath('.'))
    import fetcher
    print("✅ fetcher模块可正常导入")
    
    # 测试功能
    trade_date = fetcher.get_previous_trade_date()
    print(f"✅ 前一交易日获取成功: {trade_date}")
except Exception as e:
    print(f"❌ fetcher模块测试失败: {e}")
