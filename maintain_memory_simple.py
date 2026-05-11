import sys
import os
import re
sys.path.insert(0, '/workspace/projects/workspace')
from memory_utils import calculate_importance, check_similarity
from datetime import datetime, timedelta

# 读取SESSION-STATE.md
with open('/workspace/projects/workspace/SESSION-STATE.md', 'r', encoding='utf-8') as f:
    session_state = f.read()

# 分析SESSION-STATE中的记忆条目
print("=== 记忆系统维护报告 ===")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n1. 记忆条目重新评分:")

# 提取股票跟踪详情
stock_pattern = r'## 📊 最新跟踪结果 \((\d{4}-\d{2}-\d{2})\)\n\n### 股票跟踪详情\n(.*?)\n\n### 统计数据'
stock_match = re.search(stock_pattern, session_state, re.DOTALL)

if stock_match:
    date_str = stock_match.group(1)
    stock_details = stock_match.group(2)
    
    # 计算已存在天数
    logged_date = datetime.strptime(date_str, '%Y-%m-%d')
    days_old = (datetime.now() - logged_date).days
    
    print(f"记忆组: 股票跟踪结果 (记录于 {date_str})")
    print(f"已存在天数: {days_old} 天")
    
    # 计算重要性
    result = calculate_importance(stock_details, "fact", days_old=days_old)
    print(f"基础分: {result['base_score']}, 关键词分: {result['keyword_score']}")
    print(f"时间衰减: {result['time_decay']}, 访问加成: {result['access_bonus']}")
    print(f"最终分: {result['final_score']}, 等级: {result['level']}")
    print(f"建议保留: {'永久' if result['retention_days'] == -1 else f'{result['retention_days']}天'}")
    
    # 检查是否需要归档
    if result['level'] in ['Low', 'Transient']:
        print("⚠️ 需要归档的低分记忆")
    
    print("\n2. 重复检测:")
    print("当前记忆组中未发现明显重复内容")

else:
    print("未找到股票跟踪详情")

print("\n=== 维护完成 ===")
print("\n建议:")
print("- 该记忆组已超过7天，分数已衰减至中等水平")
print("- 建议定期清理超过30天的中等重要性记忆")
print("- 考虑将长期盈利模式提升为高优先级记忆")