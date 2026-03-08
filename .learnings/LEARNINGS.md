# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to CLAUDE.md, AGENTS.md, or copilot-instructions.md |
| `promoted_to_skill` | Extracted as a reusable skill |

---

## 🎯 记录指南

### 何时记录到 LEARNINGS.md

| 类型 | 示例 | 优先级 |
|------|------|--------|
| **correction** | 用户纠正了我的理解 | 高 |
| **best_practice** | 发现更好的工作方法 | 中 |
| **knowledge_gap** | 发现知识盲区 | 中 |
| **insight** | 有价值的洞察 | 低 |

### 何时不记录

- ❌ 简单偏好（记录到 SESSION-STATE.md）
- ❌ 临时决策（记录到 SESSION-STATE.md）
- ❌ 操作失败（记录到 ERRORS.md）
- ❌ 日常对话

### 记录格式

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high
**Status**: pending
**Area**: 具体领域

### Summary
一句话描述学到了什么

### Details
完整上下文：发生了什么，哪里错了，正确的是什么

### Action
具体的改进建议

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-XXXXXX (相关条目)

---
```

---

## 📊 维护规则

- **条目 > 20 条**: 审查并提升/归档
- **状态 = resolved**: 移动到归档区
- **状态 = promoted**: 合并到 SOUL.md/AGENTS.md/TOOLS.md

---

## 📝 Entries

<!-- 在此下方添加新条目 -->

