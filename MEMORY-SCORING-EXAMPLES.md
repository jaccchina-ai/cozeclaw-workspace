# 记忆评分系统使用示例

> 展示如何在实际对话中使用新的记忆评分系统

---

## 📝 示例 1: 记录用户偏好

### 场景
用户说："记住，我喜欢简洁的回复，不要太多废话"

### 使用评分系统

```python
from memory_utils import calculate_importance, format_memory_entry

content = "用户偏好：喜欢简洁的回复，不要太多废话"
memory_type = "preference"

# 计算重要性
result = calculate_importance(content, memory_type)
print(f"重要性: {result['level']} | 分数: {result['final_score']}")
# 输出: 重要性: High | 分数: 5.0

# 格式化写入
entry = format_memory_entry(content, memory_type, seq_num=1, importance=result)
print(entry)
```

### 生成的记忆条目

```markdown
## [MEM-20260318-001] Level: High | Score: 5.0

**Logged**: 2026-03-18T12:50:00+08:00 | **Type**: preference
**Keywords**: [偏好表达(我喜欢)] | **Access**: 0 times
**Base**: 4 × **Decay**: 1.0 × **Bonus**: 1.0 = **Final**: 5.0

### Content
用户偏好：喜欢简洁的回复，不要太多废话

---
```

---

## 📝 示例 2: 记录认知纠正

### 场景
用户说："不是深华发B，是深华发A，你搞错了"

### 使用评分系统

```python
content = "用户纠正：股票名称是深华发A (000020.SZ)，不是深华发B"
memory_type = "correction"

result = calculate_importance(content, memory_type)
print(f"重要性: {result['level']} | 分数: {result['final_score']}")
# 输出: 重要性: High | 分数: 6.0
```

### 生成的记忆条目

```markdown
## [MEM-20260318-002] Level: High | Score: 6.0

**Logged**: 2026-03-18T12:52:00+08:00 | **Type**: correction
**Keywords**: [认知纠正(纠正)] | **Access**: 0 times
**Base**: 6 × **Decay**: 1.0 × **Bonus**: 1.0 = **Final**: 6.0

### Content
用户纠正：股票名称是深华发A (000020.SZ)，不是深华发B

---
```

---

## 📝 示例 3: 记录关键决策

### 场景
用户说："就用方案A吧，确定用这个方案"

### 使用评分系统

```python
content = "决策确认：采用方案A实施选股系统优化"
memory_type = "decision"

result = calculate_importance(content, memory_type)
print(f"重要性: {result['level']} | 分数: {result['final_score']}")
# 输出: 重要性: Medium | 分数: 4.0
```

---

## 📝 示例 4: 记录安全信息

### 场景
用户说："我的API密钥是 sk-abc123，记住这个"

### 使用评分系统

```python
content = "用户API密钥: sk-abc123 (注意安全保密)"
memory_type = "fact"

result = calculate_importance(content, memory_type)
print(f"重要性: {result['level']} | 分数: {result['final_score']}")
# 输出: 重要性: Critical | 分数: 10.0

# 注意：安全信息应该特殊标记，永不删除
```

---

## 📝 示例 5: 检查重复记忆

### 场景
用户再次提到："我说过了，我喜欢简洁的回复"

### 使用评分系统

```python
from memory_utils import should_merge

new_content = "用户偏好：喜欢简洁的回复"
existing_content = "用户偏好：喜欢简洁的回复，不要太多废话"

# 检查是否应该合并
if should_merge(new_content, existing_content):
    print("检测到相似记忆，建议合并而非新建")
    # 合并策略：保留更详细的版本，分数累加
else:
    print("记忆不相似，可以新建")
```

---

## 🔄 时间衰减示例

### 场景
一条7天前的 High 等级记忆，检查其当前分数

```python
from memory_utils import calculate_importance

content = "用户偏好：喜欢简洁的回复"
memory_type = "preference"

# 新记录时
result_new = calculate_importance(content, memory_type, days_old=0)
print(f"新记录: {result_new['final_score']} | {result_new['level']}")
# 输出: 5.0 | High

# 7天后
result_old = calculate_importance(content, memory_type, days_old=7)
print(f"7天后: {result_old['final_score']} | {result_old['level']}")
# 输出: 3.5 | Medium

# 30天后
result_very_old = calculate_importance(content, memory_type, days_old=30)
print(f"30天后: {result_very_old['final_score']} | {result_very_old['level']}")
# 输出: 2.0 | Low
```

---

## 📊 批量记忆分析

### 统计当前记忆分布

```python
from memory_utils import calculate_importance, ImportanceLevel

memories = [
    {"content": "邮箱是 a@b.com", "type": "preference"},
    {"content": "不是X是Y", "type": "correction"},
    {"content": "用方案A", "type": "decision"},
    # ... 更多记忆
]

level_counts = {level.value: 0 for level in ImportanceLevel}
total_score = 0

for mem in memories:
    result = calculate_importance(mem["content"], mem["type"])
    level_counts[result["level"]] += 1
    total_score += result["final_score"]

print("记忆分布:")
for level, count in level_counts.items():
    print(f"  {level}: {count}条")
print(f"平均分数: {total_score / len(memories):.2f}")
```

---

## ✅ 实施检查清单

- [ ] 安装/确认 `memory_utils.py` 可用
- [ ] 更新 `SESSION-STATE.md` 使用新格式
- [ ] 更新 `LEARNINGS.md` 使用新格式
- [ ] 在写入记忆前调用 `calculate_importance()`
- [ ] 在写入前检查 `should_merge()` 避免重复
- [ ] 每日 Heartbeat 检查记忆健康度
- [ ] 每周归档低分记忆

---

*Created: 2026-03-18*
