import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta

engine = create_engine('sqlite:////workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')
df = pd.read_sql('SELECT * FROM tracked_results', engine)

if len(df) > 0:
    # 处理日期字段，t_day是YYYYMMDD格式的字符串
    df['t_day'] = pd.to_datetime(df['t_day'], format='%Y%m%d')
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_df = df[df['t_day'] >= seven_days_ago]
    
    if len(recent_df) > 0:
        # 使用is_win字段统计盈利数，或者用final_profit > 0
        wins = len(recent_df[recent_df['is_win'] == True])
        # 或者用final_profit: wins = len(recent_df[recent_df['final_profit'] > 0])
        total = len(recent_df)
        print(f'本周交易总数: {total}, 盈利数: {wins}, 胜率: {wins/total*100:.2f}%')
        # 打印具体交易信息
        print('\n本周交易详情:')
        for idx, row in recent_df.iterrows():
            profit = row['final_profit'] if row['final_profit'] is not None else row['return_pct']
            print(f"  {row['stock_name']}({row['ts_code']}): 盈利={profit:.2f}% {'✅' if row['is_win'] else '❌'}")
    else:
        print('本周无交易数据')
else:
    print('无交易数据')