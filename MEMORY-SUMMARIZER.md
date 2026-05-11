# 智能记忆摘要系统

> 自动压缩和分层管理记忆，防止 SESSION-STATE.md 无限增长

---

## 🎯 核心功能

1. **记忆分层**：活跃记忆 → 归档记忆 → 历史记忆
2. **自动摘要**：长内容自动压缩为一句话
3. **链接保留**：归档记忆保留链接，可追溯完整内容
4. **智能清理**：低分记忆自动识别，提示归档

---

## 📚 记忆分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      记忆分层架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: 活跃记忆 (Active)                                  │
│  ├── 位置: SESSION-STATE.md 顶部                            │
│  ├── 保留: 最近3天 或 访问次数>2                             │
│  ├── 格式: 完整详细                                          │
│  └── 用途: 当前会话工作记忆                                   │
│                                                             │
│  Layer 2: 归档记忆 (Archived)                                │
│  ├── 位置: SESSION-STATE.md 底部归档区                        │
│  ├── 保留: 3-30天 且 分数≥Medium                            │
│  ├── 格式: 一句话摘要 + 完整链接                              │
│  └── 用途: 快速回顾，需要时可追溯                             │
│                                                             │
│  Layer 3: 历史记忆 (Historical)                              │
│  ├── 位置: MEMORY.md                                        │
│  ├── 保留: >30天 且 分数≥High 或 Critical                    │
│  ├── 格式: 精炼摘要                                          │
│  └── 用途: 长期智慧积累                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 分层格式规范

### Layer 1: 活跃记忆 (完整格式)

```markdown
## [MEM-20260318-001] Level: High | Score: 6.5 ⭐ ACTIVE

**Logged**: 2026-03-18T12:30:00+08:00 | **Type**: preference
**Keywords**: [邮箱, 阿里云] | **Access**: 3 times | **Last**: 2026-03-18T15:00:00

### Content
用户的工作邮箱是 jarvis@jaccoffice.com（阿里云企业邮箱）
这是用户反复确认的重要信息，用于所有业务沟通。

### Context
- 用户主动提供
- 强调是"专属工作邮箱"
- 已配置IMAP/SMTP

---
```

### Layer 2: 归档记忆 (摘要格式)

```markdown
## [MEM-20260318-001] Level: High | Score: 4.2 📦 ARCHIVED

**Logged**: 2026-03-18T12:30:00 | **Type**: preference | **Archived**: 2026-03-21
**Access**: 5 times | **Summary**: 用户工作邮箱 jarvis@jaccoffice.com
**Full**: See [原始记录](memory/archive/20260318-001.md)

---
```

### Layer 3: 历史记忆 (精炼格式)

```markdown
## 2026-03: 用户核心偏好

- **工作邮箱**: jarvis@jaccoffice.com (阿里云) [High]
- **沟通风格**: 简洁优先，先结论后论述 [Critical]
- **工作时间**: 晚上效率最高 [Medium]

*Source: SESSION-STATE.md [MEM-20260318-001]*
```

---

## 🔄 自动摘要算法

### 文本摘要策略

```python
def generate_summary(content: str, max_length: int = 50) -> str:
    """
    生成一句话摘要
    """
    # 策略1: 提取关键信息
    # 移除修饰词，保留主干
    
    # 策略2: 模板化摘要
    templates = {
        "preference": "用户偏好: {key_info}",
        "correction": "纠正: 用户指出 {key_info}",
        "decision": "决策: 采用 {key_info}",
        "fact": "信息: {key_info}"
    }
    
    # 策略3: 关键词提取
    keywords = extract_keywords(content)
    summary = " | ".join(keywords[:3])
    
    return summary[:max_length]
```

### 摘要示例

| 原始内容 | 摘要 |
|---------|------|
| 用户的工作邮箱是 jarvis@jaccoffice.com（阿里云企业邮箱），这是我的专属工作邮箱，用于业务沟通和自动化任务，配置IMAP/SMTP已就绪 | 用户工作邮箱: jarvis@jaccoffice.com (阿里云) |
| 用户纠正：不是深华发B，是深华发A，你搞错了，以后记住是这个 | 纠正: 股票名称是深华发A (非B) |
| 我决定采用方案A来实施选股系统优化，不用方案B了 | 决策: 采用方案A实施选股优化 |

---

## 🧹 自动归档流程

### 归档检查 (Heartbeat)

```python
def archive_check():
    """
    每日检查需要归档的记忆
    """
    for memory in active_memories:
        days_old = (now() - memory.logged_at).days
        
        # 规则1: 超过3天且访问次数<=2
        if days_old > 3 and memory.access_count <= 2:
            archive_to_layer2(memory)
        
        # 规则2: 超过7天且分数<Medium
        elif days_old > 7 and memory.level in ["Low", "Transient"]:
            suggest_cleanup(memory)
        
        # 规则3: 超过30天且分数>=High
        elif days_old > 30 and memory.level in ["High", "Critical"]:
            promote_to_layer3(memory)
```

### 归档流程图

```
活跃记忆检查
    │
    ├─ 3天内 或 高频访问?
    │   ├─ 是 → 保持活跃
    │   └─ 否 ↓
    │
    ├─ 分数 >= Medium?
    │   ├─ 是 → 归档到 Layer 2
    │   └─ 否 ↓
    │
    ├─ 是否需要保留?
    │   ├─ 是 → 归档到 Layer 2 (低优先级)
    │   └─ 否 → 建议删除
    │
    └─ 30天后且高分?
        ├─ 是 → 提升到 Layer 3
        └─ 否 → 保持 Layer 2
```

---

## 📊 记忆健康度监控

### 每日检查指标

```python
class MemoryHealth:
    def __init__(self):
        self.metrics = {
            "active_count": 0,        # 活跃记忆数
            "active_size_kb": 0,      # 活跃记忆大小
            "archive_count": 0,       # 归档记忆数
            "avg_score": 0,           # 平均分数
            "duplicate_ratio": 0,     # 重复率
            "cleanup_candidates": 0   # 待清理候选
        }
    
    def check_health(self) -> dict:
        """
        检查记忆系统健康度
        """
        status = "healthy"
        alerts = []
        
        if self.metrics["active_count"] > 100:
            alerts.append("活跃记忆过多，建议归档")
            status = "warning"
        
        if self.metrics["duplicate_ratio"] > 0.2:
            alerts.append("重复率过高，建议合并")
            status = "warning"
        
        if self.metrics["avg_score"] < 2.0:
            alerts.append("平均分数过低，记忆质量需提升")
        
        return {
            "status": status,
            "metrics": self.metrics,
            "alerts": alerts,
            "recommendations": self.generate_recommendations()
        }
```

### 健康度报告示例

```markdown
## 记忆系统健康报告 - 2026-03-18

### 整体状态: ✅ Healthy

### 指标概览
| 指标 | 当前值 | 阈值 | 状态 |
|------|--------|------|------|
| 活跃记忆数 | 23 | <50 | ✅ |
| 活跃记忆大小 | 15 KB | <100 KB | ✅ |
| 平均分数 | 4.2 | >2.0 | ✅ |
| 重复率 | 5% | <20% | ✅ |

### 归档建议
- 3条记忆超过3天未访问，建议归档
- 1条低分记忆可考虑删除

### 今日操作
- [ ] 归档 3条记忆到 Layer 2
- [ ] 检查 1条删除候选
```

---

## 🛠️ 实施文件

### 新增文件
- `memory_summarizer.py` - 摘要生成工具
- `memory_archiver.py` - 归档管理工具
- `memory_health.py` - 健康度监控

### 修改文件
- `SESSION-STATE.md` - 添加归档区
- `HEARTBEAT.md` - 添加记忆维护任务
- `MEMORY.md` - 添加历史记忆区

---

*Created: 2026-03-18*
*Status: Implementation in progress*
