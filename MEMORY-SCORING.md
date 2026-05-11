# MEMORY-SCORING.md - 记忆重要性评分系统

> 定义记忆重要性评分规则，用于优化检索质量和记忆管理

---

## 🎯 评分目标

- **高价值记忆优先检索**：关键决策、用户纠正、重要偏好
- **自动去重**：相似记忆合并而非重复记录
- **智能归档**：低分记忆定期清理，高分记忆长期保留

---

## 📊 重要性评分算法

### 基础评分规则

| 维度 | 触发条件 | 分值 | 说明 |
|------|---------|------|------|
| **安全敏感** | 涉及密码、密钥、Token、API Key | +5 | 最高优先级，永不删除 |
| **财务相关** | 涉及资金、账户、交易指令 | +4 | 高优先级，长期保留 |
| **用户强调** | 包含"重要"、"记住"、"必须"等词 | +3 | 用户明确标记重要 |
| **认知纠正** | 用户纠正理解错误 | +3 | 避免重复犯错 |
| **决策确认** | "就用X"、"确定是Y" | +2 | 关键决策点 |
| **专有名词** | 人名、公司名、产品名首次出现 | +2 | 建立知识图谱 |
| **偏好表达** | "我喜欢"、"我讨厌" | +2 | 个性化服务 |
| **关键数值** | ID、URL、日期、配置参数 | +1 | 参考信息 |
| **临时信息** | "等下再说"、"暂时" | -1 | 可能过时 |

### 时间衰减因子

```python
def time_decay(days_old):
    """
    艾宾浩斯遗忘曲线简化版
    - 第1天: 100%
    - 第3天: 90%
    - 第7天: 70%
    - 第30天: 40%
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
```

### 访问频率加成

```python
def access_bonus(access_count):
    """
    被多次访问的记忆更重要
    """
    if access_count >= 10:
        return 2.0
    elif access_count >= 5:
        return 1.5
    elif access_count >= 2:
        return 1.2
    return 1.0
```

### 最终计算公式

```python
final_score = (base_score + keyword_bonus) * time_decay(days_old) * access_bonus(access_count)
```

---

## 🏷️ 重要性等级

| 等级 | 分数范围 | 处理方式 | 保留策略 |
|------|---------|---------|---------|
| **Critical** | ≥8 | 永久保留，多副本备份 | 永不过期 |
| **High** | 5-7.9 | 长期保留，优先检索 | 保留90天 |
| **Medium** | 3-4.9 | 标准保留 | 保留30天 |
| **Low** | 1-2.9 | 短期保留 | 保留7天 |
| **Transient** | <1 | 临时记忆 | 会话结束删除 |

---

## 🔍 检索排序规则

### 默认排序
```
检索结果 = 按 (重要性分数 × 语义相似度) 排序
```

### 紧急模式
当用户表达紧急/困惑时，优先显示 **Critical** 和 **High** 等级记忆

### 探索模式
当用户询问"之前有没有说过"时，显示所有等级，但标注重要性

---

## 📝 记录格式更新

### SESSION-STATE.md 新格式

```markdown
## [MEM-YYYYMMDD-NNN] Level: Critical | Score: 8.5

**Logged**: 2026-03-18T12:30:00+08:00
**Type**: correction | preference | decision | fact
**Keywords**: [keyword1, keyword2]
**Access**: 3 times, last: 2026-03-18T15:00:00

### Content
[记忆内容]

### Context
[上下文信息]

---
```

### LEARNINGS.md 新格式

```markdown
## [LRN-YYYYMMDD-NNN] category | Score: 6.2

**Logged**: ISO-8601 timestamp
**Priority**: high | medium | low
**Status**: pending | in_progress | resolved | promoted
**Area**: frontend | backend | infra | tests | docs | config

### Summary
[一句话总结]

### Details
[详细内容]

### Action
[改进行动]

### Metadata
- Source: conversation | error | user_feedback
- Related: [MEM-XXX, LRN-YYY]
- Score History: 6.2 → 5.8 (30天后)

---
```

---

## 🤖 实施检查清单

### 写入时
- [ ] 计算基础分值
- [ ] 检查重复/相似记忆
- [ ] 如有重复，合并而非新建
- [ ] 添加重要性标记

### 读取时
- [ ] 更新访问次数
- [ ] 按重要性排序结果
- [ ] 高重要性记忆优先显示

### 维护时 (Heartbeat)
- [ ] 重新计算时间衰减
- [ ] 识别可归档的低分记忆
- [ ] 提示用户清理建议

---

## 🔄 与现有系统协作

### 与 proactive-agent 协作
- 写入 SESSION-STATE.md 前计算重要性
- 高重要性记忆同步到 MEMORY.md

### 与 self-improvement 协作
- 认知纠正自动标记 High 等级
- best_practice 类型自动标记 Medium 以上

### 与 memory_search 协作
- 返回结果包含重要性分数
- 支持按重要性过滤

---

*Created: 2026-03-18*
*Status: Implementation in progress*
