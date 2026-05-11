"""
记忆重要性评分工具
基于 MEMORY-SCORING.md 规则实现

Usage:
    from memory_utils import calculate_importance, MemoryEntry
    score = calculate_importance("用户说：记住我的邮箱是...")
    entry = MemoryEntry(content="...", memory_type="preference")
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from enum import Enum


class ImportanceLevel(Enum):
    """重要性等级"""
    CRITICAL = "Critical"      # ≥8分
    HIGH = "High"              # 5-7.9分
    MEDIUM = "Medium"          # 3-4.9分
    LOW = "Low"                # 1-2.9分
    TRANSIENT = "Transient"    # <1分


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    memory_type: str  # preference, correction, decision, fact, error
    logged_at: datetime = field(default_factory=datetime.now)
    keywords: List[str] = field(default_factory=list)
    access_count: int = 0
    last_access: Optional[datetime] = None
    base_score: float = 0.0
    final_score: float = 0.0
    level: ImportanceLevel = ImportanceLevel.TRANSIENT


# 关键词评分规则
KEYWORD_RULES = {
    # 安全敏感 (+5)
    "security_keywords": {
        "patterns": [r"密码", r"密钥", r"token", r"api.?key", r"secret", r"凭证", r"登录"],
        "score": 5,
        "description": "安全敏感信息"
    },
    # 财务相关 (+4)
    "finance_keywords": {
        "patterns": [r"资金", r"账户", r"交易", r"转账", r"支付", r"余额", r"持仓", r"股票.*买", r"股票.*卖"],
        "score": 4,
        "description": "财务相关信息"
    },
    # 用户强调 (+3)
    "emphasis_keywords": {
        "patterns": [r"重要", r"记住", r"必须", r"一定", r"千万不要", r"特别注意"],
        "score": 3,
        "description": "用户强调"
    },
    # 认知纠正 (+3)
    "correction_keywords": {
        "patterns": [r"不是", r"错了", r"不对", r"应该是", r"你理解", r"纠正"],
        "score": 3,
        "description": "认知纠正"
    },
    # 决策确认 (+2)
    "decision_keywords": {
        "patterns": [r"就用", r"确定", r"决定", r"选择", r"采用", r"执行"],
        "score": 2,
        "description": "决策确认"
    },
    # 偏好表达 (+2)
    "preference_keywords": {
        "patterns": [r"我喜欢", r"我讨厌", r"我不喜欢", r"我更", r"倾向于", r"偏好"],
        "score": 2,
        "description": "偏好表达"
    }
}

# 类型基础分
TYPE_BASE_SCORES = {
    "correction": 3,      # 纠正有高基础分
    "preference": 2,      # 偏好中等
    "decision": 2,        # 决策中等
    "fact": 1,            # 事实较低
    "error": 2,           # 错误中等
    "temporary": -1       # 临时为负
}


def calculate_keyword_score(content: str) -> tuple[float, List[str]]:
    """
    计算关键词匹配得分
    
    Returns:
        (分数, 匹配到的关键词列表)
    """
    content_lower = content.lower()
    total_score = 0
    matched_keywords = []
    
    for category, rule in KEYWORD_RULES.items():
        for pattern in rule["patterns"]:
            if re.search(pattern, content_lower):
                total_score += rule["score"]
                matched_keywords.append(f"{rule['description']}({pattern})")
                break  # 每个类别只加一次分
    
    return total_score, matched_keywords


def calculate_time_decay(days_old: int) -> float:
    """
    计算时间衰减因子
    
    艾宾浩斯遗忘曲线简化版
    """
    if days_old <= 1:
        return 1.0
    elif days_old <= 3:
        return 0.9
    elif days_old <= 7:
        return 0.7
    elif days_old <= 30:
        return 0.4
    else:
        return 0.2


def calculate_access_bonus(access_count: int) -> float:
    """
    计算访问频率加成
    """
    if access_count >= 10:
        return 2.0
    elif access_count >= 5:
        return 1.5
    elif access_count >= 2:
        return 1.2
    return 1.0


def get_importance_level(final_score: float) -> ImportanceLevel:
    """
    根据最终分数确定重要性等级
    """
    if final_score >= 8:
        return ImportanceLevel.CRITICAL
    elif final_score >= 5:
        return ImportanceLevel.HIGH
    elif final_score >= 3:
        return ImportanceLevel.MEDIUM
    elif final_score >= 1:
        return ImportanceLevel.LOW
    else:
        return ImportanceLevel.TRANSIENT


def calculate_importance(
    content: str,
    memory_type: str = "fact",
    days_old: int = 0,
    access_count: int = 0
) -> dict:
    """
    计算记忆重要性
    
    Args:
        content: 记忆内容
        memory_type: 记忆类型 (correction, preference, decision, fact, error, temporary)
        days_old: 已存在天数
        access_count: 访问次数
    
    Returns:
        {
            "base_score": 基础分,
            "keyword_score": 关键词分,
            "keyword_matches": 匹配的关键词,
            "time_decay": 时间衰减,
            "access_bonus": 访问加成,
            "final_score": 最终分数,
            "level": 重要性等级,
            "retention_days": 建议保留天数
        }
    """
    # 基础分
    type_score = TYPE_BASE_SCORES.get(memory_type, 1)
    
    # 关键词分
    keyword_score, matched_keywords = calculate_keyword_score(content)
    
    # 基础总分
    base_score = type_score + keyword_score
    
    # 时间衰减
    time_decay = calculate_time_decay(days_old)
    
    # 访问加成
    access_bonus = calculate_access_bonus(access_count)
    
    # 最终分数
    final_score = base_score * time_decay * access_bonus
    
    # 确定等级
    level = get_importance_level(final_score)
    
    # 保留策略
    retention_days = {
        ImportanceLevel.CRITICAL: -1,    # 永久
        ImportanceLevel.HIGH: 90,
        ImportanceLevel.MEDIUM: 30,
        ImportanceLevel.LOW: 7,
        ImportanceLevel.TRANSIENT: 1
    }[level]
    
    return {
        "base_score": round(base_score, 2),
        "keyword_score": keyword_score,
        "keyword_matches": matched_keywords,
        "time_decay": time_decay,
        "access_bonus": access_bonus,
        "final_score": round(final_score, 2),
        "level": level.value,
        "retention_days": retention_days
    }


def check_similarity(content1: str, content2: str) -> float:
    """
    简单相似度检查（基于关键词重叠）
    
    Returns:
        0-1 的相似度分数
    """
    # 提取关键词（简单实现：分词后取交集）
    def extract_keywords(text):
        # 简单分词：取2-4个字符的词组
        words = set()
        for i in range(len(text) - 1):
            for j in range(2, min(5, len(text) - i + 1)):
                words.add(text[i:i+j])
        return words
    
    words1 = extract_keywords(content1)
    words2 = extract_keywords(content2)
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


def should_merge(content1: str, content2: str, threshold: float = 0.85) -> bool:
    """
    检查是否应该合并两条记忆
    """
    similarity = check_similarity(content1, content2)
    return similarity >= threshold


def format_memory_entry(
    content: str,
    memory_type: str,
    seq_num: int,
    importance: dict
) -> str:
    """
    格式化记忆条目为 Markdown
    
    Args:
        content: 记忆内容
        memory_type: 类型
        seq_num: 序号
        importance: calculate_importance 返回的字典
    
    Returns:
        Markdown 格式的记忆条目
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    date_str = datetime.now().strftime("%Y%m%d")
    
    keywords_str = ", ".join(importance["keyword_matches"][:3]) if importance["keyword_matches"] else "none"
    
    return f"""## [MEM-{date_str}-{seq_num:03d}] Level: {importance['level']} | Score: {importance['final_score']}

**Logged**: {now} | **Type**: {memory_type}
**Keywords**: [{keywords_str}] | **Access**: 0 times
**Base**: {importance['base_score']} × **Decay**: {importance['time_decay']} × **Bonus**: {importance['access_bonus']} = **Final**: {importance['final_score']}

### Content
{content}

---
"""


# 测试
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        ("用户说：记住我的邮箱是 jarvis@jaccoffice.com，密码是 Abc123", "preference"),
        ("用户纠正：不是深华发B，是深华发A", "correction"),
        ("我决定采用方案A来实施", "decision"),
        ("今天天气不错", "fact"),
        ("等下再说", "temporary"),
    ]
    
    print("记忆重要性评分测试")
    print("=" * 60)
    
    for content, mem_type in test_cases:
        result = calculate_importance(content, mem_type)
        print(f"\n内容: {content[:30]}...")
        print(f"类型: {mem_type}")
        print(f"基础分: {result['base_score']}, 关键词分: {result['keyword_score']}")
        print(f"最终分: {result['final_score']}, 等级: {result['level']}")
        print(f"保留: {'永久' if result['retention_days'] == -1 else str(result['retention_days']) + '天'}")
