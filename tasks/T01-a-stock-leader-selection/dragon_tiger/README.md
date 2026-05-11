# 龙虎榜深度数据解析模块

## 模块简介
龙虎榜深度数据解析模块是A股龙头选股系统的重要组成部分，主要功能包括龙虎榜数据获取、席位解析、资金流向分析、报告生成等，为选股系统提供关键的龙虎榜因子。

## 功能特性

### 1. 数据获取层
- 从Tushare API获取龙虎榜基础数据和席位详情
- 支持指定交易日数据获取
- 自动处理API异常和数据空值

### 2. 席位解析层
- 智能识别游资席位、机构席位、北向资金等
- 内置15个知名游资席位数组
- 支持自定义席位配置

### 3. 资金分析层
- 分析龙虎榜资金流向、买卖净额、席位协同
- 生成资金流向统计报表
- 识别热门股票和潜在龙头

### 4. 报告生成层
- 生成结构化的龙虎榜分析报告
- 支持数据库存储和查询
- 提供可视化的分析结果

### 5. 系统集成层
- 与现有选股系统无缝集成
- 提供龙虎榜因子接口
- 支持股票筛选和排序

## 架构设计

```
dragon_tiger/
├── analyzer.py      # 核心分析器
├── api.py          # API接口封装
├── main.py         # 命令行主程序
├── models.py       # 数据库模型
├── init.py         # 初始化脚本
├── integration.py  # 系统集成接口
├── test.py         # 测试脚本
└── __init__.py     # 模块初始化
```

## 核心类说明

### DragonTigerAnalyzer
核心分析器类，提供龙虎榜数据分析的核心功能：
- `get_dragon_tiger_data()`: 获取龙虎榜数据
- `analyze_seat_type()`: 分析席位类型
- `analyze_capital_flow()`: 分析资金流向
- `identify_hot_stocks()`: 识别热门股票
- `generate_analysis_report()`: 生成分析报告
- `get_dragon_tiger_factor()`: 获取龙虎榜因子

### DragonTigerAPI
API接口类，提供对外的接口服务：
- `get_latest_analysis()`: 获取最新分析结果
- `generate_analysis()`: 生成指定日期的分析报告
- `get_dragon_tiger_factor()`: 获取龙虎榜因子
- `get_hot_stocks()`: 获取热门股票列表
- `get_capital_flow()`: 获取资金流向数据

### DragonTigerIntegration
系统集成类，提供与选股系统的集成接口：
- `get_dragon_tiger_score()`: 获取单只股票的龙虎榜因子
- `filter_by_dragon_tiger()`: 根据龙虎榜因子筛选股票
- `get_hot_stocks_for_selection()`: 获取适合选股的热门股票
- `update_stock_selection_factors()`: 更新股票列表的龙虎榜因子

## 数据库设计

### dragon_tiger_records表
龙虎榜分析主记录，存储每日龙虎榜分析结果：
- trade_date: 交易日
- total_buy: 总买入金额(亿元)
- total_sell: 总卖出金额(亿元)
- net_buy: 净流入金额(亿元)
- hot_stocks: 热门股票JSON
- seat_stats: 席位统计JSON
- stock_stats: 股票统计JSON

### dragon_tiger_details表
龙虎榜详情记录，存储每日龙虎榜明细数据：
- trade_date: 交易日
- ts_code: 股票代码
- name: 股票名称
- close: 收盘价
- pct_change: 涨跌幅(%)
- amount: 总成交额(万元)
- reason: 上榜原因
- buy_amount: 买入金额(万元)
- sell_amount: 卖出金额(万元)
- net_buy: 净额(万元)
- broker: 营业部名称
- seat_type: 席位类型

## 使用指南

### 命令行使用

```bash
# 生成最新龙虎榜分析报告
python3 dragon_tiger/main.py generate

# 获取最新分析报告
python3 dragon_tiger/main.py get-report

# 获取指定股票的龙虎榜因子
python3 dragon_tiger/main.py get-factor --ts-code 000001.SZ

# 获取热门股票列表
python3 dragon_tiger/main.py hot-stocks --limit 10

# 获取资金流向数据
python3 dragon_tiger/main.py capital-flow
```

### Python API使用

```python
from dragon_tiger.api import DragonTigerAPI

# 初始化API
api = DragonTigerAPI()

# 获取最新分析报告
report = api.get_latest_analysis()
print(f"资金净流入: {report['capital_flow']['net_buy']}亿元")

# 获取龙虎榜因子
factor = api.get_dragon_tiger_factor('000001.SZ')
print(f"龙虎榜因子: {factor['dragon_tiger_score']}")

# 获取热门股票
hot_stocks = api.get_hot_stocks(limit=10)
for stock in hot_stocks['hot_stocks']:
    print(f"{stock['ts_code']} {stock['name']}: 净流入{stock['net_buy']}亿元")
```

### 系统集成使用

```python
from dragon_tiger.integration import DragonTigerIntegration

# 初始化集成接口
integration = DragonTigerIntegration()

# 筛选股票
test_stocks = [
    {'ts_code': '000001.SZ', 'name': '平安银行'},
    {'ts_code': '000002.SZ', 'name': '万科A'}
]
filtered_stocks = integration.filter_by_dragon_tiger(test_stocks, threshold=50)

# 获取选股用热门股票
hot_stocks = integration.get_hot_stocks_for_selection()
```

## 部署说明

### 依赖安装
```bash
pip install pandas numpy tushare sqlalchemy
```

### 数据库初始化
```bash
python3 dragon_tiger/init.py
```

### 定时任务配置
在cron中添加定时任务，每天收盘后运行：
```bash
0 16 * * 1-5 python3 /path/to/dragon_tiger/main.py generate
```

## 性能指标

- 单交易日龙虎榜分析: < 10秒
- 席位类型识别: < 1ms/次
- 资金流向分析: < 5秒/次
- 数据库写入性能: < 2秒/次

## 扩展开发

### 添加新的游资席位
在DragonTigerAnalyzer类的hot_money_seats数组中添加新的席位名称：

```python
hot_money_seats = [
    # 现有席位
    '新的游资席位名称'
]
```

### 自定义分析逻辑
继承DragonTigerAnalyzer类，重写相应方法：

```python
class CustomDragonTigerAnalyzer(DragonTigerAnalyzer):
    def analyze_seat_type(self, seat_name: str) -> str:
        # 自定义席位类型分析逻辑
        pass
```

## 故障排除

### 常见问题

1. **API调用失败**
   - 检查Tushare Token是否正确配置
   - 检查网络连接和API权限
   - 检查API调用频率限制

2. **数据库写入失败**
   - 检查数据库连接配置
   - 检查表结构是否正确创建
   - 检查数据库权限和磁盘空间

3. **分析结果异常**
   - 检查数据来源和完整性
   - 检查分析算法参数配置
   - 检查日志文件中的错误信息

## 版本历史

### v1.0.0 (2026-04-13)
- 初始版本
- 实现核心龙虎榜分析功能
- 提供基本API接口
- 支持数据库存储和查询
- 与选股系统集成

## 贡献指南

欢迎提交Issue和Pull Request来改进模块功能：

1. Fork本仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request
5. 代码审查和合并

## 许可证

本模块采用MIT许可证，详见LICENSE文件。
