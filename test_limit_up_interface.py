#!/usr/bin/env python3
"""测试Tushare涨停股票接口"""
import tushare as ts
from datetime import datetime

# 设置Tushare token（假设已经配置，或者从环境变量获取）
ts.set_token("your_token_here")
pro = ts.pro_api()

# 获取今天日期
today = datetime.now().strftime("%Y%m%d")
print(f"测试日期: {today}")

# 尝试调用limit_list接口
print("\n=== 测试limit_list接口 ===")
try:
    df = pro.limit_list(trade_date=today)
    if df is not None and not df.empty:
        print(f"✅ 获取到{len(df)}条涨停数据")
        print(df.head())
    else:
        print("❌ 没有获取到数据，可能是接口问题或当前无涨停股票")
except Exception as e:
    print(f"❌ limit_list接口调用失败: {e}")

# 尝试其他可能的接口
print("\n=== 测试其他可能的涨停接口 ===")
# 尝试调用limit_up接口（之前test里的错误提示）
try:
    df = pro.limit_up(trade_date=today)
    if df is not None and not df.empty:
        print(f"✅ limit_up接口获取到{len(df)}条数据")
        print(df.head())
    else:
        print("❌ limit_up接口无数据")
except Exception as e:
    print(f"❌ limit_up接口调用失败: {e}")

# 尝试获取每日涨跌停统计
print("\n=== 测试每日涨跌停统计 ===")
try:
    df = pro.daily_limit(trade_date=today)
    if df is not None and not df.empty:
        print(f"✅ daily_limit接口获取到数据")
        print(df)
    else:
        print("❌ daily_limit接口无数据")
except Exception as e:
    print(f"❌ daily_limit接口调用失败: {e}")

# 查看Tushare版本和可用接口
print(f"\n=== Tushare版本: {ts.__version__} ===")
# 查看所有可用接口
print("可用接口列表（部分）:", [attr for attr in dir(pro) if not attr.startswith('_')][:20])