# Unifuncs Deep Research API 使用示例

本文档提供 Unifuncs API 的各种使用场景示例。

## 快速开始

### 基础调用

```python
from unifuncs_client import UnifuncsClient

# 初始化客户端
client = UnifuncsClient()

# 一键获取报告
result = client.get_report(
    "今天A股热门板块哪几个？所有涨停股中，哪3个涨停股在下一个交易日继续涨停的概率最大？"
)

if result.status == "completed":
    print(f"摘要: {result.summary}")
    print(f"详情: {result.answer}")
```

### 分步调用（更灵活）

```python
from unifuncs_client import UnifuncsClient

client = UnifuncsClient()

# 1. 创建任务
task_id = client.create_task(
    output_prompt="分析今日市场情绪",
    output_type="summary",  # 或 "full"
    reference_style="hidden"  # 或 "visible"
)
print(f"任务ID: {task_id}")

# 2. 轮询结果
import time
while True:
    result = client.query_task(task_id)
    
    if result.status == "completed":
        print(f"结果: {result.answer}")
        break
    elif result.status == "failed":
        print(f"失败: {result.error}")
        break
    else:
        print(f"等待中... 状态: {result.status}")
        time.sleep(3)
```

## 应用场景示例

### 场景1：热门板块分析

```python
from unifuncs_client import UnifuncsClient, get_hot_sectors

# 方式1：使用便捷函数
result = get_hot_sectors()

# 方式2：自定义查询
client = UnifuncsClient()
result = client.get_report("""
请分析今日A股热门板块：
1. 列出涨幅前5的概念板块
2. 分析各板块的领涨股
3. 统计各板块的资金净流入情况
4. 预测明日可能延续强势的板块
""")
```

### 场景2：涨停股连板预测

```python
from unifuncs_client import UnifuncsClient, predict_limit_up_stocks

# 方式1：使用便捷函数
result = predict_limit_up_stocks()

# 方式2：自定义分析
client = UnifuncsClient()
result = client.get_report("""
请分析今日所有涨停股：
1. 统计涨停股数量和板块分布
2. 筛选出连板概率最高的3只股票
3. 分析每只股票的连板理由
4. 给出风险提示
""")
```

### 场景3：市场情绪分析

```python
from unifuncs_client import analyze_market_sentiment

# 使用便捷函数
result = analyze_market_sentiment()
print(f"市场情绪分析: {result.answer}")
```

### 场景4：个股深度分析

```python
from unifuncs_client import UnifuncsClient

client = UnifuncsClient()

# 分析特定股票
result = client.get_report("""
请深度分析 000001.SZ 平安银行：
1. 今日走势分析
2. 技术面分析（均线、MACD、成交量）
3. 资金流向分析
4. 行业对比分析
5. 短期走势预测
""")
```

### 场景5：与 Tushare 配合使用

```python
import sys
sys.path.append('/workspace/projects/workspace/skills/tushare-finance/scripts')
from tushare_client import TushareClient
from unifuncs_client import UnifuncsClient

# 1. 使用 Tushare 获取数据
ts = TushareClient()
limit_up = ts.get_limit_up_list(trade_date='20241220')

# 2. 使用 Unifuncs 分析
uf = UnifuncsClient()
result = uf.get_report(f"""
以下是我通过 Tushare 获取的今日涨停股列表：
{limit_up.to_string()}

请分析：
1. 哪些股票明日连板概率最高？
2. 各股票的涨停原因是什么？
3. 资金流入情况如何？
""")
```

## 高级用法

### 自定义超时和轮询间隔

```python
client = UnifuncsClient(
    default_timeout=180,      # 默认超时180秒
    default_poll_interval=2.0  # 默认每2秒轮询一次
)

# 或在调用时指定
result = client.get_report(
    "分析市场",
    timeout=300,      # 本次超时300秒
    poll_interval=1.5  # 本次每1.5秒轮询
)
```

### 错误处理

```python
from unifuncs_client import UnifuncsClient, UnifuncsError

client = UnifuncsClient()

try:
    result = client.get_report("分析市场", timeout=60)
    print(result.answer)
except UnifuncsError as e:
    print(f"API 错误: {e.message}")
    if e.response:
        print(f"响应详情: {e.response}")
except TimeoutError as e:
    print(f"任务超时: {e}")
    # 可以尝试重新创建任务
```

### 批量分析

```python
from unifuncs_client import UnifuncsClient

client = UnifuncsClient()

prompts = [
    "分析今日热门板块",
    "预测涨停股连板概率",
    "分析北向资金流向",
]

results = []
for prompt in prompts:
    try:
        result = client.get_report(prompt, timeout=120)
        results.append({
            "prompt": prompt,
            "answer": result.answer,
            "status": "success"
        })
    except Exception as e:
        results.append({
            "prompt": prompt,
            "error": str(e),
            "status": "failed"
        })

# 输出结果
for r in results:
    print(f"\n问题: {r['prompt']}")
    if r['status'] == 'success':
        print(f"回答: {r['answer'][:200]}...")
    else:
        print(f"错误: {r['error']}")
```

## 与 T01 Task 集成

```python
"""
T01 Task: A股龙头选股策略系统
集成 Unifuncs 进行深度市场分析
"""

from unifuncs_client import UnifuncsClient

class T01Analyzer:
    def __init__(self):
        self.uf_client = UnifuncsClient()
    
    def analyze_hot_sectors(self) -> dict:
        """分析热门板块"""
        result = self.uf_client.get_report(
            "分析今日A股热门板块，给出板块名称、涨幅、领涨股、资金流向"
        )
        return {
            "status": result.status,
            "analysis": result.answer
        }
    
    def predict_limit_up(self, stock_list: str) -> dict:
        """预测涨停股连板概率"""
        result = self.uf_client.get_report(
            f"以下涨停股中，哪3只明日连板概率最高？请给出理由。\n{stock_list}"
        )
        return {
            "status": result.status,
            "prediction": result.answer
        }
    
    def generate_trading_signal(self) -> dict:
        """生成交易信号"""
        # 1. 获取热门板块
        sectors = self.analyze_hot_sectors()
        
        # 2. 获取涨停股预测
        limit_up = self.predict_limit_up("今日涨停股列表")
        
        return {
            "hot_sectors": sectors,
            "limit_up_prediction": limit_up,
            "signal_time": datetime.now().isoformat()
        }


# 使用示例
if __name__ == "__main__":
    analyzer = T01Analyzer()
    signal = analyzer.generate_trading_signal()
    print(signal)
```

## 注意事项

1. **调用频率**: 建议控制调用频率，避免过于频繁请求
2. **超时设置**: 复杂分析任务可能需要更长时间，建议设置 120-180 秒超时
3. **提示词优化**: 提供清晰、具体的问题描述可以获得更好的分析结果
4. **错误重试**: 网络波动时建议实现重试机制
