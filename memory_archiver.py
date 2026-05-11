"""
智能记忆摘要与归档系统
基于 MEMORY-SUMMARIZER.md 实现

功能：
1. 生成记忆摘要
2. 管理记忆分层 (活跃/归档/历史)
3. 自动归档检查
4. 记忆健康度监控
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from enum import Enum
import os


class MemoryLayer(Enum):
    """记忆分层"""
    ACTIVE = "active"       # 活跃记忆
    ARCHIVED = "archived"   # 归档记忆
    HISTORICAL = "historical"  # 历史记忆


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    summary: str = ""
    memory_type: str = "fact"
    level: str = "Low"
    score: float = 0.0
    logged_at: datetime = field(default_factory=datetime.now)
    last_access: Optional[datetime] = None
    access_count: int = 0
    keywords: List[str] = field(default_factory=list)
    layer: MemoryLayer = MemoryLayer.ACTIVE
    archived_at: Optional[datetime] = None


class MemorySummarizer:
    """记忆摘要生成器"""
    
    # 模板化摘要
    SUMMARY_TEMPLATES = {
        "preference": "用户偏好: {key_info}",
        "correction": "纠正: {key_info}",
        "decision": "决策: 采用 {key_info}",
        "fact": "信息: {key_info}",
        "error": "错误: {key_info}",
        "temporary": "临时: {key_info}"
    }
    
    # 关键信息提取模式
    KEY_PATTERNS = [
        r"邮箱[:：]\s*([\w.@]+)",
        r"密码[:：]\s*(\S+)",
        r"密钥[:：]\s*(\S+)",
        r"([\w.]+@[\w.]+\.\w+)",
        r"(方案[A-Z])",
        r"(股票[\dA-Z]+)",
        r"(\d{4}-\d{2}-\d{2})",
        r"https?://\S+",
    ]
    
    def generate_summary(self, content: str, memory_type: str = "fact", max_length: int = 60) -> str:
        """
        生成一句话摘要
        
        Args:
            content: 原始内容
            memory_type: 记忆类型
            max_length: 最大长度
        
        Returns:
            摘要字符串
        """
        # 清理内容
        clean_content = self._clean_content(content)
        
        # 提取关键信息
        key_info = self._extract_key_info(clean_content)
        
        # 使用模板
        template = self.SUMMARY_TEMPLATES.get(memory_type, "信息: {key_info}")
        summary = template.format(key_info=key_info)
        
        # 截断
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def _clean_content(self, content: str) -> str:
        """清理内容，移除噪音"""
        # 移除 Markdown 标记
        content = re.sub(r'[#*`\[\]]', '', content)
        # 移除多余空格
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    def _extract_key_info(self, content: str) -> str:
        """提取关键信息"""
        key_infos = []
        
        for pattern in self.KEY_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            key_infos.extend(matches)
        
        if key_infos:
            # 取前3个关键信息
            return " | ".join(key_infos[:3])
        
        #  fallback: 提取前20个字符
        return content[:40] + "..." if len(content) > 40 else content
    
    def compress_context(self, context: List[Dict], max_items: int = 5) -> str:
        """
        压缩上下文历史
        
        Args:
            context: 对话历史列表
            max_items: 保留的最大条目数
        
        Returns:
            压缩后的上下文摘要
        """
        if len(context) <= max_items:
            return self._format_full_context(context)
        
        # 保留最近3条，压缩前面的
        recent = context[-3:]
        older = context[:-3]
        
        # 生成早期对话摘要
        older_summary = self._summarize_older_dialogue(older)
        
        result = f"【历史对话摘要】{older_summary}\n\n"
        result += "【最近对话】\n"
        result += self._format_full_context(recent)
        
        return result
    
    def _format_full_context(self, items: List[Dict]) -> str:
        """格式化完整上下文"""
        lines = []
        for item in items:
            role = item.get("role", "unknown")
            content = item.get("content", "")[:100]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
    
    def _summarize_older_dialogue(self, items: List[Dict]) -> str:
        """摘要化早期对话"""
        # 统计对话主题
        topics = set()
        decisions = []
        
        for item in items:
            content = item.get("content", "")
            # 提取主题词
            if "选股" in content:
                topics.add("选股系统")
            if "策略" in content:
                topics.add("策略优化")
            if "方案" in content:
                decisions.append("方案选择")
        
        summary_parts = []
        if topics:
            summary_parts.append(f"讨论了: {', '.join(topics)}")
        if decisions:
            summary_parts.append(f"做了: {', '.join(set(decisions))}")
        
        return "；".join(summary_parts) if summary_parts else "早期对话"


class MemoryArchiver:
    """记忆归档管理器"""
    
    # 归档规则
    ARCHIVE_RULES = {
        "to_layer2": {
            "days_old": 3,
            "max_access": 2,
            "min_level": "Medium"
        },
        "to_layer3": {
            "days_old": 30,
            "min_level": "High"
        },
        "cleanup": {
            "days_old": 7,
            "max_level": "Low"
        }
    }
    
    def __init__(self, workspace_path: str = "/workspace/projects/workspace"):
        self.workspace = workspace_path
        self.session_state_path = os.path.join(workspace_path, "SESSION-STATE.md")
        self.memory_path = os.path.join(workspace_path, "MEMORY.md")
        self.archive_dir = os.path.join(workspace_path, "memory", "archive")
        
        # 确保目录存在
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def check_archive_candidates(self, memories: List[MemoryEntry]) -> Dict:
        """
        检查需要归档的记忆
        
        Returns:
            {
                "to_layer2": [...],  # 归档到 Layer 2
                "to_layer3": [...],  # 提升到 Layer 3
                "cleanup": [...]     # 建议清理
            }
        """
        candidates = {
            "to_layer2": [],
            "to_layer3": [],
            "cleanup": []
        }
        
        now = datetime.now()
        
        for memory in memories:
            if memory.layer != MemoryLayer.ACTIVE:
                continue
            
            days_old = (now - memory.logged_at).days
            
            # 规则1: 超过30天且高分 → Layer 3
            if (days_old >= self.ARCHIVE_RULES["to_layer3"]["days_old"] and 
                memory.level in ["High", "Critical"]):
                candidates["to_layer3"].append(memory)
                continue
            
            # 规则2: 超过3天且低访问 → Layer 2
            if (days_old >= self.ARCHIVE_RULES["to_layer2"]["days_old"] and
                memory.access_count <= self.ARCHIVE_RULES["to_layer2"]["max_access"] and
                memory.level in ["Medium", "High", "Critical"]):
                candidates["to_layer2"].append(memory)
                continue
            
            # 规则3: 超过7天且低分 → 清理
            if (days_old >= self.ARCHIVE_RULES["cleanup"]["days_old"] and
                memory.level in ["Low", "Transient"]):
                candidates["cleanup"].append(memory)
        
        return candidates
    
    def archive_to_layer2(self, memory: MemoryEntry) -> str:
        """
        归档到 Layer 2
        
        Returns:
            归档后的 Markdown 格式
        """
        summarizer = MemorySummarizer()
        summary = summarizer.generate_summary(memory.content, memory.memory_type)
        
        now = datetime.now().strftime("%Y-%m-%d")
        archive_file = f"{memory.id}.md"
        
        # 保存完整内容到归档文件
        full_content = self._format_full_memory(memory)
        archive_path = os.path.join(self.archive_dir, archive_file)
        with open(archive_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 生成 Layer 2 格式
        layer2_entry = f"""## [{memory.id}] Level: {memory.level} | Score: {memory.score:.1f} 📦 ARCHIVED

**Logged**: {memory.logged_at.strftime("%Y-%m-%d")} | **Type**: {memory.memory_type} | **Archived**: {now}
**Access**: {memory.access_count} times | **Summary**: {summary}
**Full**: See [原始记录](memory/archive/{archive_file})

---
"""
        return layer2_entry
    
    def promote_to_layer3(self, memory: MemoryEntry) -> str:
        """
        提升到 Layer 3 (历史记忆)
        
        Returns:
            Layer 3 格式
        """
        summarizer = MemorySummarizer()
        summary = summarizer.generate_summary(memory.content, memory.memory_type)
        
        # Layer 3 更精炼
        month = memory.logged_at.strftime("%Y-%m")
        
        layer3_entry = f"- **{summary}** [{memory.level}]\n"
        
        return layer3_entry
    
    def _format_full_memory(self, memory: MemoryEntry) -> str:
        """格式化完整记忆内容"""
        return f"""# 归档记忆 - {memory.id}

## 元信息
- **ID**: {memory.id}
- **等级**: {memory.level}
- **分数**: {memory.score}
- **类型**: {memory.memory_type}
- **创建时间**: {memory.logged_at}
- **访问次数**: {memory.access_count}

## 内容
{memory.content}

## 关键词
{', '.join(memory.keywords) if memory.keywords else '无'}
"""


class MemoryHealthMonitor:
    """记忆健康度监控"""
    
    # 健康阈值
    THRESHOLDS = {
        "max_active_count": 50,
        "max_active_size_kb": 100,
        "max_duplicate_ratio": 0.2,
        "min_avg_score": 2.0
    }
    
    def __init__(self, workspace_path: str = "/workspace/projects/workspace"):
        self.workspace = workspace_path
    
    def check_health(self, memories: List[MemoryEntry]) -> Dict:
        """
        检查记忆系统健康度
        
        Returns:
            健康报告
        """
        metrics = self._calculate_metrics(memories)
        
        status = "healthy"
        alerts = []
        recommendations = []
        
        # 检查活跃记忆数
        if metrics["active_count"] > self.THRESHOLDS["max_active_count"]:
            alerts.append(f"活跃记忆过多: {metrics['active_count']} > {self.THRESHOLDS['max_active_count']}")
            recommendations.append("建议归档超过3天的低访问记忆")
            status = "warning"
        
        # 检查重复率
        if metrics["duplicate_ratio"] > self.THRESHOLDS["max_duplicate_ratio"]:
            alerts.append(f"重复率过高: {metrics['duplicate_ratio']:.1%}")
            recommendations.append("建议合并相似记忆")
            status = "warning"
        
        # 检查平均分数
        if metrics["avg_score"] < self.THRESHOLDS["min_avg_score"]:
            alerts.append(f"平均分数过低: {metrics['avg_score']:.2f}")
            recommendations.append("建议提升记忆质量，减少低价值记录")
        
        # 检查待归档数量
        archiver = MemoryArchiver(self.workspace)
        candidates = archiver.check_archive_candidates(memories)
        total_candidates = sum(len(v) for v in candidates.values())
        
        if total_candidates > 0:
            recommendations.append(f"有 {total_candidates} 条记忆建议处理 ({len(candidates['to_layer2'])}条归档, {len(candidates['cleanup'])}条清理)")
        
        return {
            "status": status,
            "metrics": metrics,
            "alerts": alerts,
            "recommendations": recommendations,
            "candidates": candidates
        }
    
    def _calculate_metrics(self, memories: List[MemoryEntry]) -> Dict:
        """计算指标"""
        active_memories = [m for m in memories if m.layer == MemoryLayer.ACTIVE]
        
        total_size = sum(len(m.content) for m in active_memories)
        avg_score = sum(m.score for m in memories) / len(memories) if memories else 0
        
        # 计算重复率 (简化版：基于内容相似度)
        duplicates = self._count_duplicates(memories)
        duplicate_ratio = duplicates / len(memories) if memories else 0
        
        return {
            "active_count": len(active_memories),
            "active_size_kb": round(total_size / 1024, 2),
            "total_count": len(memories),
            "avg_score": round(avg_score, 2),
            "duplicate_ratio": round(duplicate_ratio, 2),
            "cleanup_candidates": duplicates
        }
    
    def _count_duplicates(self, memories: List[MemoryEntry]) -> int:
        """计算重复记忆数 (简化版)"""
        content_hashes = {}
        duplicates = 0
        
        for memory in memories:
            # 使用内容的前50个字符作为简单哈希
            key = memory.content[:50]
            if key in content_hashes:
                duplicates += 1
            else:
                content_hashes[key] = memory.id
        
        return duplicates
    
    def generate_report(self, memories: List[MemoryEntry]) -> str:
        """生成健康报告"""
        report = self.check_health(memories)
        
        status_emoji = "✅" if report["status"] == "healthy" else "⚠️"
        
        lines = [
            f"## 记忆系统健康报告 - {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"### 整体状态: {status_emoji} {report['status'].upper()}",
            "",
            "### 指标概览",
            "| 指标 | 当前值 | 阈值 | 状态 |",
            "|------|--------|------|------|"
        ]
        
        metrics = report["metrics"]
        
        # 活跃记忆数
        active_status = "✅" if metrics["active_count"] <= self.THRESHOLDS["max_active_count"] else "⚠️"
        lines.append(f"| 活跃记忆数 | {metrics['active_count']} | <{self.THRESHOLDS['max_active_count']} | {active_status} |")
        
        # 平均分数
        score_status = "✅" if metrics["avg_score"] >= self.THRESHOLDS["min_avg_score"] else "⚠️"
        lines.append(f"| 平均分数 | {metrics['avg_score']} | >{self.THRESHOLDS['min_avg_score']} | {score_status} |")
        
        # 重复率
        dup_status = "✅" if metrics["duplicate_ratio"] <= self.THRESHOLDS["max_duplicate_ratio"] else "⚠️"
        lines.append(f"| 重复率 | {metrics['duplicate_ratio']:.0%} | <{self.THRESHOLDS['max_duplicate_ratio']:.0%} | {dup_status} |")
        
        lines.extend([
            "",
            "### 警报",
        ])
        
        if report["alerts"]:
            for alert in report["alerts"]:
                lines.append(f"- ⚠️ {alert}")
        else:
            lines.append("- 无警报")
        
        lines.extend([
            "",
            "### 建议操作",
        ])
        
        if report["recommendations"]:
            for rec in report["recommendations"]:
                lines.append(f"- [ ] {rec}")
        else:
            lines.append("- 系统健康，无需操作")
        
        return "\n".join(lines)


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("记忆摘要与归档系统测试")
    print("=" * 60)
    
    # 测试摘要生成
    summarizer = MemorySummarizer()
    
    test_contents = [
        ("用户的工作邮箱是 jarvis@jaccoffice.com（阿里云企业邮箱），这是我的专属工作邮箱，用于业务沟通和自动化任务", "preference"),
        ("用户纠正：不是深华发B，是深华发A，你搞错了", "correction"),
        ("我决定采用方案A来实施选股系统优化", "decision"),
    ]
    
    print("\n【摘要生成测试】")
    for content, mtype in test_contents:
        summary = summarizer.generate_summary(content, mtype)
        print(f"\n原始: {content[:40]}...")
        print(f"摘要: {summary}")
    
    # 测试健康度检查
    print("\n\n【健康度检查测试】")
    
    # 创建测试记忆
    test_memories = [
        MemoryEntry(id="MEM-001", content="邮箱是 a@b.com", score=5.0, level="High"),
        MemoryEntry(id="MEM-002", content="密码是 123456", score=8.0, level="Critical"),
        MemoryEntry(id="MEM-003", content="喜欢用蓝色", score=4.0, level="Medium"),
        MemoryEntry(id="MEM-004", content="临时信息", score=0.5, level="Transient"),
    ]
    
    monitor = MemoryHealthMonitor()
    report = monitor.generate_report(test_memories)
    print(report)
    
    print("\n" + "=" * 60)
    print("测试完成!")
