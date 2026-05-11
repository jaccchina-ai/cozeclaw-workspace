from sqlalchemy import create_engine
import pandas as pd
from datetime import datetime, timedelta

# 初始化数据库连接
engine = create_engine('sqlite:////workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db')

# 检查因子IC值
try:
    # 读取factor_ic表（如果存在）
    try:
        df_ic = pd.read_sql('SELECT * FROM factor_ic ORDER BY trade_date DESC LIMIT 7', engine)
        if not df_ic.empty:
            print('近7天因子IC值:')
            for date, group in df_ic.groupby('trade_date'):
                print(f"\n日期: {date}")
                for _, row in group.iterrows():
                    print(f"  {row['factor_name']}: {row['ic_value']:.4f} (显著性: {row['p_value']:.4f})")
        else:
            print('factor_ic表无数据')
    except:
        # 如果factor_ic表不存在，检查stock_factor_scores表
        print('factor_ic表不存在，检查stock_factor_scores表...')
        df_scores = pd.read_sql('SELECT * FROM stock_factor_scores ORDER BY trade_date DESC LIMIT 100', engine)
        if not df_scores.empty:
            # 计算最近7天的因子IC值（简化版本）
            recent_days = df_scores['trade_date'].unique()[-7:] if len(df_scores['trade_date'].unique()) >=7 else df_scores['trade_date'].unique()
            print(f'最近{len(recent_days)}天的因子得分数据存在，但未预计算IC值')
            print(f'涉及因子: {df_scores.columns[3:-1].tolist()}')
        else:
            print('无因子得分数据')
except Exception as e:
    print(f'检查因子IC值时出错: {str(e)}')

# 检查是否有连续3天无选股告警
print("\n" + "="*50)
print('检查是否有连续3天无选股记录...')
try:
    # 读取selection_results表
    df_selection = pd.read_sql('SELECT trade_date, COUNT(*) as count FROM selection_results GROUP BY trade_date ORDER BY trade_date DESC', engine)
    if not df_selection.empty:
        # 将trade_date转换为datetime
        df_selection['trade_date'] = pd.to_datetime(df_selection['trade_date'], format='%Y%m%d')
        
        # 生成完整日期序列
        start_date = df_selection['trade_date'].min()
        end_date = df_selection['trade_date'].max()
        all_dates = pd.date_range(start=start_date, end=end_date, freq='B')  # B表示工作日
        
        # 找到无选股的日期
        selection_dates = set(df_selection['trade_date'])
        missing_dates = [date for date in all_dates if date not in selection_dates]
        
        if missing_dates:
            print(f'发现{len(missing_dates)}个工作日无选股记录:')
            for date in missing_dates:
                print(f"  {date.strftime('%Y-%m-%d')}")
            
            # 检查是否有连续3天的情况
            missing_dates_sorted = sorted(missing_dates)
            consecutive_count = 1
            has_consecutive_3 = False
            
            for i in range(1, len(missing_dates_sorted)):
                if (missing_dates_sorted[i] - missing_dates_sorted[i-1]).days == 1:
                    consecutive_count +=1
                    if consecutive_count >=3:
                        has_consecutive_3 = True
                        print(f"\n⚠️ 发现连续{consecutive_count}天无选股记录: {missing_dates_sorted[i-2].strftime('%Y-%m-%d')} 至 {missing_dates_sorted[i].strftime('%Y-%m-%d')}")
                else:
                    consecutive_count =1
            
            if not has_consecutive_3:
                print('\n✅ 无连续3天以上无选股记录')
        else:
            print('✅ 所有工作日均有选股记录')
    else:
        print('⚠️ selection_results表无数据')
except Exception as e:
    print(f'检查选股记录时出错: {str(e)}')