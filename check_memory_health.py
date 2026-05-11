import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, '/workspace/projects/workspace')
from memory_utils import calculate_importance, check_similarity, ImportanceLevel

# 读取 SESSION-STATE.md
session_state_path = '/workspace/projects/workspace/SESSION-STATE.md'
if not os.path.exists(session_state_path):
    print("SESSION-STATE.md 不存在")
    sys.exit(0)

with open(session_state_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 分割内容为条目
entries = []
# 提取股票跟踪详情
import re
stock_pattern = r'## 📊 最新跟踪结果 \((.*?)\)\n(.*?)\n## 📅 最近任务执行'
match = re.search(stock_pattern, content, re.DOTALL)
if match:
    date_str = match.group(1)
    stock_content = match.group(2)
    entries.append({
        'content': stock_content,
        'type': 'fact',
        'days_old': (datetime.now() - datetime.strptime(date_str, '%Y-%m-%d')).days
    })

# 提取最近任务执行
task_pattern = r'## 📅 最近任务执行\n(.*?)\n---'
match = re.search(task_pattern, content, re.DOTALL)
if match:
    task_content = match.group(1)
    entries.append({
        'content': task_content,
        'type': 'fact',
        'days_old': (datetime.now() - datetime.strptime('2026-04-29', '%Y-%m-%d')).days
    })

# 计算每个条目的重要性
print("📝 记忆重要性评分结果")
print("="*60)
critical_count = 0
high_count = 0
total_score = 0
for i, entry in enumerate(entries):
    result = calculate_importance(
        entry['content'],
        entry['type'],
        entry['days_old'],
        access_count=0
    )
    total_score += result['final_score']
    
    print(f"\n条目 {i+1}:")
    print(f"类型: {entry['type']}, 已存在天数: {entry['days_old']}")
    print(f"最终分数: {result['final_score']}, 等级: {result['level']}")
    print(f"保留建议: {'永久' if result['retention_days'] == -1 else f'{result['retention_days']}天'}")
    
    if result['level'] == ImportanceLevel.CRITICAL.value:
        critical_count +=1
    elif result['level'] == ImportanceLevel.HIGH.value:
        high_count +=1

# 计算平均分数
average_score = total_score / len(entries) if entries else 0

print("\n📊 记忆健康度指标")
print("="*60)
print(f"Critical 记忆数: {critical_count} (健康阈值: ≥1)")
print(f"High 记忆数: {high_count} (健康阈值: 5-20)")
print(f"平均分数: {round(average_score, 2)} (健康阈值: >3.0)")

# 检查重复
print("\n🔍 重复记忆检测")
print("="*60)
duplicate_found = False
for i in range(len(entries)):
    for j in range(i+1, len(entries)):
        similarity = check_similarity(entries[i]['content'], entries[j]['content'])
        if similarity > 0.85:
            print(f"发现高相似度记忆 (相似度: {similarity:.2f}):")
            print(f"  条目 {i+1} vs 条目 {j+1}")
            duplicate_found = True
if not duplicate_found:
    print("无高相似度重复记忆")

# 检查是否需要归档
print("\n🗄️ 归档候选")
print("="*60)
archive_candidates = []
for i, entry in enumerate(entries):
    result = calculate_importance(
        entry['content'],
        entry['type'],
        entry['days_old'],
        access_count=0
    )
    if result['level'] in [ImportanceLevel.LOW.value, ImportanceLevel.TRANSIENT.value]:
        archive_candidates.append((i+1, result))

if archive_candidates:
    for idx, result in archive_candidates:
        print(f"条目 {idx}: 等级 {result['level']}, 分数 {result['final_score']} → 建议归档")
else:
    print("无需要归档的记忆")

# 检查是否需要提升
print("\n🚀 提升候选")
print("="*60)
promote_candidates = []
# 模拟访问次数（这里假设股票跟踪条目访问次数多）
for i, entry in enumerate(entries):
    access_count = 5 if '股票跟踪' in entry['content'] else 0
    result = calculate_importance(
        entry['content'],
        entry['type'],
        entry['days_old'],
        access_count=access_count
    )
    if access_count >=5 and result['level'] == ImportanceLevel.HIGH.value:
        promote_candidates.append((i+1, result))

if promote_candidates:
    for idx, result in promote_candidates:
        print(f"条目 {idx}: 访问次数≥5, 等级 {result['level']} → 建议提升为 Critical")
else:
    print("无需要提升的记忆")