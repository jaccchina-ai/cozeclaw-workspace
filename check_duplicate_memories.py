#!/usr/bin/env python3
"""
检查重复记忆脚本
"""
import sys
import os
from datetime import datetime
from memory_utils import check_similarity, should_merge

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
                            'score': float(match[2]),
                            'content': match[3].strip(),
                            'file_path': file_path
                        })
    return entries

# 读取所有记忆条目
entries = read_memory_entries('/workspace/projects/workspace/memory')

print(f"读取到 {len(entries)} 个记忆条目")
print("="*60)

# 检查重复
duplicate_count = 0
similar_pairs = []

for i in range(len(entries)):
    for j in range(i+1, len(entries)):
        entry1 = entries[i]
        entry2 = entries[j]
        similarity = check_similarity(entry1['content'], entry2['content'])
        if should_merge(entry1['content'], entry2['content']):
            duplicate_count +=1
            similar_pairs.append({
                'id1': entry1['id'],
                'id2': entry2['id'],
                'similarity': similarity,
                'level1': entry1['level'],
                'level2': entry2['level']
            })

# 统计重复率
duplicate_rate = (duplicate_count / len(entries)) * 100 if len(entries) >0 else 0

print(f"发现 {duplicate_count} 对重复记忆")
print(f"重复记忆率: {duplicate_rate:.1f}% (<10% 为健康)")
print()

if similar_pairs:
    print("📋 重复记忆列表:")
    for pair in similar_pairs:
        print(f"⚠️ {pair['id1']} (Level: {pair['level1']}) 和 {pair['id2']} (Level: {pair['level2']}) 相似度: {pair['similarity']:.2f}")
else:
    print("✅ 无重复记忆")

# 健康判断
if duplicate_rate < 10:
    print("\n✅ 重复记忆率符合健康标准")
else:
    print("\n❌ 重复记忆率过高，建议合并重复条目")
