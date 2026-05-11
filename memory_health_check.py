#!/usr/bin/env python3
"""
记忆系统健康检查脚本
基于 HEARTBEAT.md 要求
"""
import sys
import re
from datetime import datetime, timedelta
from memory_utils import calculate_importance, should_merge

# 读取SESSION-STATE.md
with open('/workspace/projects/workspace/SESSION-STATE.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取记忆条目（假设以## [MEM-开头的条目）
mem_entries = re.findall(r'## \[MEM-(.*?)\].*?\n.*?\n### Content\n(.*?)\n---', content, re.DOTALL)

# 分析每个条目
print("📊 记忆系统健康检查报告")
print("="*60)
print(f"总记忆条目数: {len(mem_entries)}")
print()

# 按等级统计
level_counts = {"Critical":0, "High":0, "Medium":0, "Low":0, "Transient":0}
total_score = 0.0
similarity_warnings = []

# 检查重复
for i, entry1 in enumerate(mem_entries):
    content1 = entry1[1].strip()
    result = calculate_importance(content1, days_old=(datetime.now() - datetime.strptime(entry1[0].split('-')[0], '%Y%m%d')).days)
    level_counts[result['level']] +=1
    total_score += result['final_score']
    
    # 检查与其他条目的相似度
    for j, entry2 in enumerate(mem_entries[i+1:], i+1):
        content2 = entry2[1].strip()
        if should_merge(content1, content2):
            similarity_warnings.append(f"⚠️ 条目 {i+1} 和 {j+1} 相似度极高，建议合并")

# 计算平均分
avg_score = total_score / len(mem_entries) if mem_entries else 0

print("📌 重要性等级分布")
for level, count in level_counts.items():
    print(f"{level}: {count} 条 ({count/len(mem_entries)*100:.1f}%)" if mem_entries else f"{level}: 0 条")
print()

print("📈 分数统计")
print(f"平均分数: {avg_score:.2f}")
print(f"Critical 记忆数: {level_counts['Critical']} (≥1 为健康)")
print(f"High 记忆数: {level_counts['High']} (5-20 为健康)")
print(f"重复记忆率: {len(similarity_warnings)/len(mem_entries)*100:.1f}% (<10% 为健康)" if mem_entries else "无记忆条目")
print()

if similarity_warnings:
    print("🔍 重复记忆告警")
    for warn in similarity_warnings:
        print(warn)
    print()

# 检查健康阈值
healthy = True
if level_counts['Critical'] <1:
    print("❌ 健康问题: Critical 记忆数不足 (应≥1)")
    healthy = False
if not (5 <= level_counts['High'] <=20) and mem_entries:
    print(f"❌ 健康问题: High 记忆数不在5-20范围内 (当前 {level_counts['High']})")
    healthy = False
if len(mem_entries) > 0 and len(similarity_warnings)/len(mem_entries)*100 >=10:
    print(f"❌ 健康问题: 重复记忆率过高 (当前 {len(similarity_warnings)/len(mem_entries)*100:.1f}%)")
    healthy = False
if avg_score <=3.0 and mem_entries:
    print(f"❌ 健康问题: 平均分数过低 (当前 {avg_score:.2f}，应>3.0)")
    healthy = False

if healthy:
    print("✅ 记忆系统健康状态良好")
else:
    print("⚠️ 记忆系统存在健康问题，请及时处理")