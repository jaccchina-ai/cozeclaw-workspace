import tushare as ts
import sys

# 测试Tushare连接
token = "870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab"

try:
    pro = ts.pro_api(token)
    print("✅ Tushare API连接成功")
    
    # 获取API调用情况
    user = pro.user(token=token)
    print(f"用户信息:")
    print(user.to_dict('records')[0])
    
    # 测试获取今日大盘数据
    import datetime
    today = datetime.datetime.now().strftime('%Y%m%d')
    df = pro.index_daily(ts_code='000001.SH', trade_date=today)
    if not df.empty:
        print(f"✅ 成功获取今日上证指数数据")
        print(f"收盘点数: {df['close'][0]}")
        print(f"涨跌幅: {df['pct_chg'][0]}%")
    else:
        print("⚠️ 今日无上证指数数据（可能非交易日）")
        
except Exception as e:
    print(f"❌ Tushare API调用失败: {e}")
    sys.exit(1)