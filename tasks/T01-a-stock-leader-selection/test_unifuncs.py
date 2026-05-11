#!/usr/bin/env python3
"""
快速测试 Unifuncs 调用
"""

import sys
sys.path.insert(0, '/workspace/projects/workspace/skills/unifuncs/scripts')
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from unifuncs_client import UnifuncsClient
import re
import time

# 测试股票列表
test_stocks = [
    {'ts_code': '300246.SZ', 'stock_name': '宝莱特'},
    {'ts_code': '000545.SZ', 'stock_name': '金浦钛业'},
    {'ts_code': '601016.SH', 'stock_name': '节能风电'},
]

stock_list = "\n".join([f"{s['ts_code']} {s['stock_name']}" for s in test_stocks])

output_prompt = f"""请对以下今日涨停股票进行深度研究分析，预测下一个交易日（T+1）继续涨停概率最大的3只股票：

股票列表：
{stock_list}

分析要求：
1. 结合市场情绪、资金流向、技术面等因素
2. 重点分析连板潜力最大的股票
3. 返回格式必须包含股票代码（如300246.SZ）

请按涨停概率从高到低排序返回："""

print("="*60)
print("Unifuncs 快速测试")
print("="*60)
print(f"\n提示词:\n{output_prompt}\n")

client = UnifuncsClient()

# 创建任务
print("创建任务...")
task_id = client.create_task(output_prompt=output_prompt)
print(f"任务ID: {task_id}\n")

# 快速轮询结果（最多30秒）
max_wait = 30
start = time.time()

while time.time() - start < max_wait:
    result = client.query_task(task_id)
    elapsed = time.time() - start
    
    if result.status == "completed":
        print(f"✅ 完成! (用时{elapsed:.1f}秒)\n")
        answer = result.answer or result.summary or ""
        print(f"回答:\n{answer}\n")
        
        # 解析股票代码
        pattern = r'(\d{6}\.(?:SZ|SH|BJ))'
        matches = re.findall(pattern, answer)
        print(f"匹配到的股票代码: {matches}")
        
        if matches:
            print("\n🤖 Unifuncs 推荐股票:")
            for code in matches[:3]:
                if any(s['ts_code'] == code for s in test_stocks):
                    print(f"  ✅ {code}")
                else:
                    print(f"  ⚠️ {code} (不在测试列表中)")
        break
        
    elif result.status == "failed":
        print(f"❌ 失败: {result.error}")
        break
    
    print(f"  状态: {result.status} ({elapsed:.1f}s)")
    time.sleep(1)

else:
    print(f"⏱️ 超时 (>{max_wait}秒)")

print("\n" + "="*60)
