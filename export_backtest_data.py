import pandas as pd
from sqlalchemy import create_engine
import os

# 创建SQLite连接
db_path = 'sqlite:////workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db'
engine = create_engine(db_path)

# 获取过去三个月的完整数据
data_tables = {
    '初选结果': '''
        SELECT * FROM selection_results 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC, total_score DESC
    ''',
    '竞价精选': '''
        SELECT * FROM auction_data 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC, final_score DESC
    ''',
    '市场情绪': '''
        SELECT * FROM market_sentiment 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC
    ''',
    '因子评分': '''
        SELECT * FROM stock_factor_scores 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC, ts_code
    ''',
    '跟踪结果': '''
        SELECT * FROM tracked_results 
        WHERE t1_day >= date('now', '-3 months')
        ORDER BY t1_day DESC
    ''',
    '龙虎榜数据': '''
        SELECT * FROM dragon_tiger_records 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC
    ''',
    '资金流向': '''
        SELECT * FROM moneyflow_data 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC, ts_code
    ''',
    '涨停数据': '''
        SELECT * FROM limit_up_stocks 
        WHERE trade_date >= date('now', '-3 months')
        ORDER BY trade_date DESC
    '''
}

# 生成回测专用报告
report_content = '# T01选股系统近三个月回测专用完整数据\n\n'
report_content += '本报告包含所有回测所需的原始数据，无任何筛选\n\n'
report_content += '⚠️ 数据量较大，建议使用Python/Pandas进行批量分析\n\n'

# 保存所有数据到CSV文件
csv_files = []
for table_name, query in data_tables.items():
    df = pd.read_sql(query, engine)
    
    # 添加到报告
    report_content += f'## {table_name} ({len(df)}条记录)\n'
    report_content += f'字段数量: {len(df.columns)} 个\n'
    report_content += f'字段列表: {\', \'.join(df.columns)}\n\n'