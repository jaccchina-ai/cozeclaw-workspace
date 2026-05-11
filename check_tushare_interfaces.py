import tushare as ts

# 设置token
pro = ts.pro_api('870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab')

# 查看所有可用接口
print("可用接口列表：")
interfaces = pro.__dict__.keys()
for interface in sorted(interfaces):
    if not interface.startswith('_') and callable(getattr(pro, interface)):
        print(f"  - {interface}")

# 查找与涨停、竞价相关的接口
print("\n与涨停、竞价相关的接口：")
keywords = ['limit', 'auction', 'up', 'zt']
for interface in sorted(interfaces):
    if not interface.startswith('_') and callable(getattr(pro, interface)):
        for keyword in keywords:
            if keyword in interface.lower():
                print(f"  - {interface}")
                break

# 查看具体接口的帮助
print("\n查看limit_up接口帮助：")
try:
    help(pro.limit_up)
except AttributeError:
    print("limit_up接口不存在")

print("\n查看auction接口帮助：")
try:
    help(pro.auction)
except AttributeError:
    print("auction接口不存在")

# 查看最新的接口文档
print("\n建议访问Tushare官网查看最新接口文档：https://tushare.pro/document/2")