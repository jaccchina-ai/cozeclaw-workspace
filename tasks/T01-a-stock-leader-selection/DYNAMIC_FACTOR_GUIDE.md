# 动态因子配置系统使用指南

## 概述

动态因子配置系统允许您通过简单的配置添加新因子，自动完成：
- 数据库字段创建
- 评分计算
- 数据保存
- 消息展示

## 文件结构

```
tasks/T01-a-stock-leader-selection/
├── factor_config.py          # 因子配置定义
├── dynamic_db_migrate.py     # 数据库迁移工具
└── database/models.py        # 数据库模型（自动更新）
```

## 添加新因子的步骤

### 步骤1：在 factor_config.py 中添加因子定义

```python
# 在 DEFAULT_FACTORS 中添加
't_day_factors': {
    # ... 现有因子 ...
    
    # 新增因子
    'new_factor_code': FactorDefinition(
        code='new_factor_code',           # 因子代码（英文，用于数据库字段）
        name='新因子显示名称',             # 显示名称（中文）
        type=FactorType.BOTH,              # 类型：score/raw/both
        weight=8.0,                        # 权重（0表示不计入总分）
        description='因子描述',            # 描述
        score_rules=[                      # 评分规则 [(阈值, 得分), ...]
            (10, 10),                      # 值>=10，得10分
            (5, 8),                        # 值>=5，得8分
            (0, 6),                        # 值>=0，得6分
        ],
        higher_is_better=True              # 越高越好（True/False）
    ),
}
```

### 步骤2：运行数据库迁移

```bash
cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection
python3 dynamic_db_migrate.py
```

系统会自动：
- 检查现有表结构
- 添加缺失的字段
- 验证数据库完整性

### 步骤3：在评分模型中使用新因子

**文件**: `scoring_model.py`

```python
def score_stock(self, stock_data, ...):
    # ... 现有评分 ...
    
    # 新因子评分
    new_factor_value = stock_data.get('new_factor_field', 0)
    new_factor_score = factor_manager.calculate_score(
        'new_factor_code', 
        new_factor_value,
        't_day_factors'
    )
    
    score.new_factor_score = new_factor_score
    score.raw_values['new_factor_field'] = new_factor_value
    
    return score
```

### 步骤4：测试

运行选股任务，检查：
- 数据库是否正确保存新因子
- 消息是否正确显示新因子

## FactorDefinition 参数说明

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `code` | str | 因子代码（英文，数据库字段名） | `'seal_ratio'` |
| `name` | str | 显示名称（中文） | `'封成比'` |
| `type` | FactorType | 保存类型 | `FactorType.BOTH` |
| `weight` | float | 权重（总和100） | `10.0` |
| `description` | str | 描述 | `'封单金额/成交金额'` |
| `score_rules` | List[Tuple] | 评分规则 | `[(0.5, 10), (0.3, 8)]` |
| `higher_is_better` | bool | 方向 | `True` |

### FactorType 类型

| 类型 | 说明 | 数据库字段 |
|------|------|-----------|
| `FactorType.SCORE_ONLY` | 只保存得分 | `{code}_score` |
| `FactorType.RAW_ONLY` | 只保存原始值 | `{code}_raw` |
| `FactorType.BOTH` | 同时保存 | `{code}_score`, `{code}_raw` |

### 评分规则格式

```python
score_rules=[
    (阈值1, 得分1),   # 值 >= 阈值1，得得分1
    (阈值2, 得分2),   # 值 >= 阈值2，得得分2
    (阈值3, 得分3),   # 值 >= 阈值3，得得分3
]
```

系统会自动按阈值排序，找到匹配的得分。

## 完整示例：添加"流通市值"因子

### 1. 修改 factor_config.py

```python
't_day_factors': {
    # ... 现有因子 ...
    
    'float_mv': FactorDefinition(
        code='float_mv',
        name='流通市值',
        type=FactorType.BOTH,
        weight=5.0,
        description='自由流通市值（亿元）',
        score_rules=[
            (100, 10),    # 100亿以上，大盘股，10分
            (50, 8),      # 50-100亿，8分
            (20, 6),      # 20-50亿，6分
            (0, 4),       # 20亿以下，小盘股，4分
        ],
        higher_is_better=False  # 流通市值越小越好（龙头股通常市值适中）
    ),
}
```

### 2. 运行迁移

```bash
python3 dynamic_db_migrate.py
```

输出：
```
【同步 stock_factor_scores 表】
配置要求字段数: 23
现有字段数: 21
需要添加字段数: 2
  ✅ 添加字段: float_mv_score
  ✅ 添加字段: float_mv_raw
```

### 3. 修改评分模型

**文件**: `scoring_model.py`

```python
def score_stock(self, stock_data, ...):
    # ... 现有代码 ...
    
    # 流通市值因子
    float_mv = stock_data.get('float_mv', 0) / 1e8  # 转换为亿
    from factor_config import factor_manager
    score.float_mv_score = factor_manager.calculate_score(
        'float_mv', float_mv, 't_day_factors'
    )
    score.raw_values['float_mv'] = float_mv
    
    return score
```

### 4. 测试

```bash
python3 main.py t-day --date 20260314
```

检查数据库：
```sql
SELECT ts_code, float_mv_score, float_mv_raw 
FROM stock_factor_scores 
WHERE trade_date = '20260314';
```

## 便捷函数

```python
from factor_config import (
    factor_manager,           # 全局因子管理器
    get_t_day_factors,        # 获取T日因子
    get_auction_factors,      # 获取竞价因子
    get_factor_score,         # 计算因子得分
    add_custom_factor,        # 动态添加因子
)

# 获取所有因子
t_day = get_t_day_factors()
print(f"T日因子数: {len(t_day)}")

# 获取归一化权重
weights = factor_manager.normalize_weights('t_day_factors')
print(weights)

# 计算得分
score = factor_manager.calculate_score('seal_ratio', 0.4, 't_day_factors')
print(f"封成比0.4的得分: {score}")

# 动态添加因子（运行时）
add_custom_factor(
    category='t_day_factors',
    code='custom_factor',
    name='自定义因子',
    weight=5.0,
    score_rules=[(10, 10), (5, 8), (0, 6)],
    factor_type='both'
)
```

## 数据库字段命名规范

| 类型 | 字段名格式 | 示例 |
|------|-----------|------|
| 得分 | `{code}_score` | `seal_ratio_score` |
| 原始值 | `{code}_raw` | `seal_ratio_raw` |

## 注意事项

1. **权重总和**：建议T日因子总权重为100，竞价因子总权重为100
2. **code命名**：使用英文小写+下划线，避免与现有字段冲突
3. **score_rules**：阈值从高到低排列（higher_is_better=True时）
4. **数据库迁移**：修改配置后必须运行迁移脚本
5. **备份**：重要修改前建议备份数据库

## 故障排查

### 问题1：迁移后字段未创建
```bash
# 检查表结构
python3 -c "from dynamic_db_migrate import get_existing_columns; print(get_existing_columns('stock_factor_scores'))"
```

### 问题2：评分计算错误
```bash
# 测试评分
python3 -c "from factor_config import factor_manager; print(factor_manager.calculate_score('seal_ratio', 0.4, 't_day_factors'))"
```

### 问题3：数据未保存
检查 `_save_factor_scores` 方法是否正确映射了字段名。
