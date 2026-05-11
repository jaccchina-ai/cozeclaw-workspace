#!/usr/bin/env python3
"""
记忆系统维护工具 - 根据 HEARTBEAT.md 要求每日执行
"""
import sys
from datetime import datetime, timedelta
import re

sys.path.insert(0, '/workspace/projects/workspace')
from memory_utils import calculate_importance, check_similarity, ImportanceLevel


def load_session_state():
    """从 SESSION-STATE.md 加载记忆内容"""
    try:
        with open('/workspace/projects/workspace/SESSION-STATE.md', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print("⚠️  SESSION-STATE.md 未找到")
        return ""


from datetime import timezone


def extract_memory_entries(content):
    """从 SESSION-STATE.md 中提取记忆条目"""
    entries = []
    
    # 匹配 MEM-XXXXXX-XXX 格式的记忆条目
    mem_pattern = re.compile(
        r'## \[MEM-(\d{8})-(\d{3})\] Level: (\w+) \| Score: ([\d.]+)\n'
        r'\*\*Logged\*\*: ([\d\-T:+]+) \| \*\*Type\*\*: (\w+)\n'
        r'(.*?)(?=\n## |\n\*\*Last Updated\*\*|\Z)',
        re.DOTALL
    )
    
    matches = mem_pattern.finditer(content)
    
    for match in matches:
        date_str, seq, level, score, logged_at_str, mem_type, content_part = match.groups()
        
        # 处理带时区的时间格式
        try:
            # 尝试解析带时区的时间
            logged_at = datetime.fromisoformat(logged_at_str.replace('Z', '+00:00'))
        except ValueError:
            # 处理其他格式
            from dateutil.parser import isoparse
            logged_at = isoparse(logged_at_str)
        
        # 提取内容主体
        content_lines = content_part.strip().split('\n')
        if content_lines:
            # 跳过 Keywords 和 Access 行
            content_lines = [line for line in content_lines if not line.startswith('**Keywords**:') and not line.startswith('**Access**:')]
            mem_content = '\n'.join(content_lines).strip()
        else:
            mem_content = ''
        
        entries.append({
            'id': f"MEM-{date_str}-{seq}",
            'logged_at': logged_at,
            'level': level,
            'original_score': float(score),
            'type': mem_type,
            'content': mem_content
        })
    
    return entries


def main():
    print("🧠 记忆系统维护任务开始")
    print("=" * 60)
    
    # 1. 加载SESSION-STATE.md
    session_content = load_session_state()
    if not session_content:
        print("\n❌ 无会话状态数据，维护结束")
        return
    
    # 2. 提取记忆条目
    entries = extract_memory_entries(session_content)
    print(f"\n📊 共找到 {len(entries)} 条记忆条目")
    
    if not entries:
        print("\n❌ 无有效记忆条目，维护结束")
        return
    
    # 3. 重新计算时间衰减后的分数
    print("\n🔄 重新计算记忆分数（含时间衰减）")
    print("-" * 60)
    
    updated_entries = []
    low_score_entries = []
    high_access_entries = []
    duplicate_pairs = []
    
    # 获取当前时间（带时区）
    now = datetime.now(timezone.utc)
    
    for entry in entries:
        # 确保时间时区一致
        entry_time = entry['logged_at'].astimezone(timezone.utc)
        days_old = (now - entry_time).days
        importance = calculate_importance(
            entry['content'],
            entry['type'],
            days_old=days_old,
            access_count=0  # 暂时无法获取访问次数，设为0
        )
        
        updated_entry = entry.copy()
        updated_entry['days_old'] = days_old
        updated_entry['new_score'] = importance['final_score']
        updated_entry['new_level'] = importance['level']
        updated_entries.append(updated_entry)
        
        # 记录低分记忆
        if importance['level'] in [ImportanceLevel.LOW.value, ImportanceLevel.TRANSIENT.value]:
            low_score_entries.append(updated_entry)
        
        # 打印变化
        if entry['original_score'] != importance['final_score']:
            change_direction = "↑" if importance['final_score'] > entry['original_score'] else "↓"
            print(f"[{entry['id']}] {entry['content'][:50]}...")
            print(f"   原分数: {entry['original_score']:.2f} → 新分数: {importance['final_score']:.2f} {change_direction}")
            print(f"   原等级: {entry['level']} → 新等级: {importance['level']}")
    
    # 4. 识别重复记忆
    print("\n🔍 检测重复记忆")
    print("-" * 60)
    
    for i in range(len(updated_entries)):
        for j in range(i+1, len(updated_entries)):
            similarity = check_similarity(
                updated_entries[i]['content'],
                updated_entries[j]['content']
            )
            if similarity >= 0.85:
                duplicate_pairs.append((updated_entries[i], updated_entries[j], similarity))
    
    # 5. 输出维护结果
    print("\n📋 记忆系统维护报告")
    print("=" * 60)
    
    print(f"\n📊 总体统计:")
    print(f"   总记忆数: {len(updated_entries)}")
    print(f"   超过7天的记忆数: {sum(1 for e in updated_entries if e['days_old'] > 7)}")
    print(f"   需要归档的低分记忆数: {len(low_score_entries)}")
    print(f"   重复记忆对数: {len(duplicate_pairs)}")
    
    print("\n⚠️ 需要归档的低分记忆:")
    for entry in low_score_entries[:5]:  # 最多显示5个
        retention = "永久" if entry['new_score'] >= 8 else f"{7 if entry['new_level'] == 'Low' else 1}天"
        print(f"   [{entry['id']}] {entry['content'][:60]}...")
        print(f"      等级: {entry['new_level']}, 分数: {entry['new_score']:.2f}, 已存在: {entry['days_old']}天")
        print(f"      建议: {'归档' if entry['new_level'] == 'Low' else '删除'}")
    
    if duplicate_pairs:
        print("\n🔄 检测到重复记忆:")
        for pair in duplicate_pairs[:3]:  # 最多显示3对
            entry1, entry2, similarity = pair
            print(f"   相似度: {similarity:.2f}")
            print(f"   {entry1['id']}: {entry1['content'][:50]}...")
            print(f"   {entry2['id']}: {entry2['content'][:50]}...")
            print(f"   建议: 合并为单条记忆")
    
    # 6. 保存维护结果
    print("\n💾 保存维护报告")
    report_content = generate_maintenance_report(updated_entries, low_score_entries, duplicate_pairs)
    report_path = f"/workspace/projects/workspace/memory_maintenance_{datetime.now().strftime('%Y%m%d')}.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ 维护报告已保存到: {report_path}")
    print("\n📝 维护建议:")
    print("   1. 及时处理需要归档/删除的低分记忆")
    print("   2. 合并重复记忆以优化记忆库")
    print("   3. 定期运行此维护任务（建议每日执行）")
    
    print("\n✅ 记忆系统维护任务完成")


def generate_maintenance_report(entries, low_entries, duplicates):
    """生成维护报告"""
    report = f"# 记忆系统维护报告\n"
    report += f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"**总记忆数**: {len(entries)}\n"
    report += f"**需要归档的低分记忆**: {len(low_entries)}\n"
    report += f"**重复记忆对数**: {len(duplicates)}\n"
    
    report += "\n## 记忆分数变化\n"
    for entry in entries:
        if entry['original_score'] != entry['new_score']:
            change = entry['new_score'] - entry['original_score']
            change_dir = "↑" if change > 0 else "↓" if change < 0 else "→"
            report += f"\n### [{entry['id']}]\n"
            report += f"- **内容**: {entry['content'][:100]}\n"
            report += f"- **原分数**: {entry['original_score']:.2f} → **新分数**: {entry['new_score']:.2f} {change_dir}\n"
            report += f"- **原等级**: {entry['level']} → **新等级**: {entry['new_level']}\n"
            report += f"- **已存在天数**: {entry['days_old']}天\n"
    
    if low_entries:
        report += "\n## 需要归档的低分记忆\n"
        for entry in low_entries:
            report += f"\n### [{entry['id']}]\n"
            report += f"- **内容**: {entry['content'][:100]}\n"
            report += f"- **等级**: {entry['new_level']}, **分数**: {entry['new_score']:.2f}\n"
            report += f"- **建议**: {'归档' if entry['new_level'] == 'Low' else '删除'}\n"
    
    if duplicates:
        report += "\n## 检测到的重复记忆\n"
        for i, pair in enumerate(duplicates, 1):
            entry1, entry2, similarity = pair
            report += f"\n### 第 {i} 对 (相似度: {similarity:.2f})\n"
            report += f"- [{entry1['id']}]: {entry1['content'][:100]}\n"
            report += f"- [{entry2['id']}]: {entry2['content'][:100]}\n"
            report += f"- **建议**: 合并为单条记忆\n"
    
    return report


if __name__ == "__main__":
    main()