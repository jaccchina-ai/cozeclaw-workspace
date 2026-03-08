# Errors

Command failures, exceptions, and operational issues.

**Priorities**: low | medium | high | critical
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | wont_reproduce

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `wont_reproduce` | Could not reproduce after investigation |

---

## 🎯 记录指南

### 何时记录到 ERRORS.md

| 类型 | 示例 | 优先级 |
|------|------|--------|
| **配置错误** | API配置错误导致调用失败 | 高 |
| **代码错误** | 脚本执行失败 | 高 |
| **依赖错误** | 缺少必要依赖 | 中 |
| **集成错误** | 第三方服务连接失败 | 中 |

### 何时不记录

- ❌ 临时性网络错误（除非反复出现）
- ❌ 用户输入错误
- ❌ 预期的验证错误
- ❌ 一次性失败（无复现价值）

### 记录格式

```markdown
## [ERR-YYYYMMDD-XXX] error_type

**Logged**: ISO-8601 timestamp
**Priority**: high | medium | low
**Status**: pending
**Area**: 具体领域

### Summary
一句话描述什么失败了

### Error
```
关键错误信息（不要粘贴完整堆栈）
```

### Context
- 尝试的操作
- 使用的参数
- 环境信息

### Fix
建议的修复方案

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
- See Also: ERR-XXXXXX (相关错误)

---
```

---

## 📊 维护规则

- **错误已修复**: 标记为 resolved
- **条目 > 30 条**: 归档旧条目
- **重复错误**: 合并为单条，增加计数

---

## 📝 Entries

<!-- 在此下方添加新条目 -->

