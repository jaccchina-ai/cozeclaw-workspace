#!/usr/bin/env python3
"""
重新计算记忆重要性分数脚本
基于 HEARTBEAT.md 要求
"""
import sys
import os
from datetime import datetime, timedelta
from memory_utils import calculate_importance, should_merge

def read_memory_entries(memory_dir):
    """读取所有记忆条目"""
    entries = []
    for root, dirs, files in os.walk(memory_dir):
        for file in files:
            if file.endswith('.md') and not file.startswith('.'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取每个MEM条目
                    import re
                    mem_matches = re.findall(r'## \[MEM-(.*?)\] Level: (.*?) \| Score: (.*?)\n.*?\n### Content\n(.*?)\n---', content, re.DOTALL)
                    for match in mem_matches:
                        entries.append({
                            'id': f"{file}_{match[0]}",
                            'level': match[1],
                            'old_score': float(match[2]),
                            'content': match[3].strip(),
                            'file_path': file_path,
                            'date': datetime.strptime(match[0].split('-')[0], '%Y%m%d')
                        })
    return entries

# 读取所有记忆条目
entries = read_memory_entries('/workspace/projects/workspace/memory')

print(f"读取到 {len(entries)} 个记忆条目")
print("="*60)

# 重新计算超过7天的记忆分数
updated_count = 0
for entry in entries:
    days_old = (datetime.now() - entry['date']).days
    if days_old > 7:
        # 重新计算分数
        result = calculate_importance(
            entry['content'],
            days_old=days_old,
            access_count=0  # 假设访问次数为0
        )
        entry['new_score'] = result['final_score']
        entry['new_level'] = result['level']
        updated_count +=1
        print(f"\n📝 条目 {entry['id']}")
        print(f"   已存在天数: {days_old} 天")
        print(f"   旧分数: {entry['old_score']:.2f} ({entry['level']})")
        print(f"   新分数: {result['final_score']:.2f} ({result['level']})")
        print(f"   时间衰减: {result['time_decay']}")
        print(f"   建议保留: {'永久' if result['retention_days'] == -1 else f'{result['retention_days']}天'}")
        
        # 如果分数降至Low/Transient，标记为归档候选
        if result['level'] in ['Low', 'Transient']:
            print(f"   📦 归档候选: 分数降至{result['level']}")
        
        # 如果分数较高且访问次数多，标记为提升候选
        if result['final_score'] >=8:
            print(f"   🚀 提升候选: 分数达到High以上")

print(f"\n✅ 已完成 {updated_count}/{len(entries)} 个超过7天的记忆重新评分")

# 检查重复记忆
duplicate_count = 0
similar_pairs = []

for i in range(len(entries)):
    for j in range(i+1, len(entries)):
        entry1 = entries[i]
        entry2 = entries[j]
        if should_merge(entry1['content'], entry2['content']):
            duplicate_count +=1
            similar_pairs.append({
                'id1': entry1['id'],
                'id2': entry2['id'],
                'content1': entry1['content'][:50] + "...",
                'content2': entry2['content'][:50] + "..."
            })

print(f"\n🔍 重复记忆检查")
print(f"发现 {duplicate_count} 对重复记忆")
for pair in similar_pairs:
    print(f"   ⚠️ {pair['id1']} 和 {pair['id2']} 相似度极高")
    print(f"      内容1: {pair['content1']}")
    print(f"      内容2: {pair['content2']}")