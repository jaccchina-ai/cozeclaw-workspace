import json
import tushare as ts
import os

# 读取配置文件
config_path = os.path.join('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection', 'config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

token = config['tushare']['token']
print('Using token:', token)

# 初始化Tushare API
pro = ts.pro_api(token)

# 测试获取交易日历
trade_cal = pro.trade_cal(exchange='', start_date='20260424', end_date='20260424')
print('Trade calendar data:')
print(trade_cal)