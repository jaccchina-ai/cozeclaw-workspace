#!/usr/bin/env python3
"""Tushare Pro Level-2数据接入验证脚本"""

import tushare as ts
import json
import os

# 读取配置文件
def read_config():
    config_path = os.path.expanduser('~/.tushare_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        return None

def main():
    # 读取配置
    config = read_config()
    if not config:
        print("❌ 未找到Tushare配置文件，请先配置token")
        return
    
    # 初始化Tushare
    ts.set_token(config['token'])
    pro = ts.pro_api()
    
    try:
        # 验证Level-2数据权限
        print("🔍 验证Level-2数据权限...")
        # 查询用户权限
        auth = pro.auth()
        print(f"✅ 用户ID: {auth['id']}")
        print(f"📅 权限到期日: {auth['expire_date']}")
        
        # 测试Level-2行情数据接口
        print("\n📊 测试Level-2行情数据接口...")
        # 查询最近的Level-2盘口数据
        df = pro.l2_tick(ts_code='000001.SZ', trade_date='20260329')
        if not df.empty:
            print(f"✅ 成功获取Level-2数据，共{len(df)}条记录")
            print("📋 示例数据:")
            print(df.head(2))
        else:
            print("⚠️ 未获取到Level-2数据，可能非交易日或数据尚未更新")
        
        # 测试主力资金流向数据
        print("\n💰 测试主力资金流向数据...")
        money_flow = pro.moneyflow(ts_code='000001.SZ', trade_date='20260329')
        if not money_flow.empty:
            print(f"✅ 成功获取主力资金流向数据")
            print(f"📈 主力净流入: {money_flow['net_amount'][0]}元")
        
        print("\n🎉 Level-2数据接入验证完成!")
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        if 'permission' in str(e).lower():
            print("💡 提示: 可能需要升级Tushare权限套餐以获取Level-2数据")

if __name__ == '__main__':
    main()