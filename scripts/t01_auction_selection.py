import os
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

# 初始化Tushare API
token = os.getenv('TUSHARE_TOKEN')
if not token:
    raise EnvironmentError("TUSHARE_TOKEN 环境变量未设置，请先配置")
pro = ts.pro_api(token)

# 获取当前日期（中国市场交易日）
today = datetime.now().strftime('%Y%m%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

print(f"开始执行T01 T+1竞价选股任务，日期：{today}")

# 1. 获取涨停数据
print("\n1. 获取涨停数据...")
limit_up = pro.limit_up(
    trade_date=today,
    limit_type='U'  # U表示涨停
)
if limit_up.empty:
    print("今日无涨停股票，任务结束")
    exit()

# 2. 获取竞价数据
print("\n2. 获取竞价数据...")
auction = pro.auction(
    trade_date=today
)

# 3. 获取龙虎榜数据
print("\n3. 获取龙虎榜数据...")
top_list = pro.top_list(
    trade_date=today
)

# 合并数据
print("\n4. 合并数据并应用选股逻辑...")
# 首先合并涨停和竞价数据
merged = pd.merge(
    limit_up,
    auction,
    on=['ts_code', 'trade_date'],
    how='inner'
)

# 应用风控过滤条件
# 条件1：竞价涨幅 < 1%
merged = merged[merged['auction_pct'] < 1.0]

# 条件2：MA3偏差 < 6%
# 这里需要获取MA3数据，暂时简化处理，后续可以补充
# merged = merged[abs(merged['close'] - merged['ma3']) / merged['ma3'] < 0.06]

# 条件3：加入龙虎榜数据过滤
if not top_list.empty:
    merged = pd.merge(
        merged,
        top_list,
        on=['ts_code', 'trade_date'],
        how='inner'
    )

# 应用11因子权重筛选（示例，根据实际权重调整）
# 暂时选择市值、换手率、量比等核心因子
if not merged.empty:
    # 按市值排序（从小到大）
    merged = merged.sort_values('float_mv', ascending=True)
    # 取前20只股票
    selected = merged.head(20)
else:
    selected = pd.DataFrame()

# 输出结果
print("\n5. 选股结果：")
if selected.empty:
    print("没有符合条件的股票")
else:
    print(selected[['ts_code', 'name', 'close', 'auction_pct', 'float_mv']])
    # 保存结果到文件
    result_file = f"/workspace/projects/workspace/t01_selection_result_{today}.csv"
    selected.to_csv(result_file, index=False, encoding='utf-8-sig')
    print(f"\n选股结果已保存到：{result_file}")

# 记录到SESSION-STATE.md
with open("/workspace/projects/workspace/SESSION-STATE.md", "a", encoding='utf-8') as f:
    f.write(f"\n## T01 T+1竞价选股任务执行记录")
    f.write(f"\n- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    f.write(f"\n- 选股日期：{today}")
    f.write(f"\n- 入选股票数量：{len(selected)}")
    if not selected.empty:
        f.write(f"\n- 入选股票代码：{', '.join(selected['ts_code'].tolist())}")

print("\nT01 T+1竞价选股任务执行完成")