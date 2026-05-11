import tushare as ts
import sys

# 设置token
pro = ts.pro_api('870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab')

# 尝试调用limit_up接口
print("尝试调用limit_up接口：")
try:
    # 先不传递参数，看看错误信息
    result = pro.limit_up()
    print(result)
except Exception as e:
    print(f"错误：{e}")
    print("\n尝试传递trade_date参数：")
    try:
        # 传递今天的日期
        result = pro.limit_up(trade_date='20260420')
        print(result)
    except Exception as e2:
        print(f"错误：{e2}")
        print("\n尝试调用其他相关接口：")
        # 查看是否有其他涨停相关接口
        try:
            # 调用daily接口查看是否有涨停字段
            result = pro.daily(ts_code='000001.SZ', trade_date='20260419')
            print("daily接口字段：", result.columns)
        except Exception as e3:
            print(f"daily接口错误：{e3}")
            
print("\n查看Tushare版本：", ts.__version__)
print("建议查看最新接口文档：https://tushare.pro/document/2")