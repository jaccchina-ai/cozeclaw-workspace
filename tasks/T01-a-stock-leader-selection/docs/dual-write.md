# T01 双写架构文档

## 概述

T01 系统采用 **PostgreSQL (外部持久化) + SQLite (本地备份)** 双写架构，确保数据安全和完整性。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     应用层 (T01)                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   写入操作 ──→ DualWriteManager                        │
│                      │                                 │
│              ┌───────┴───────┐                         │
│              ↓               ↓                         │
│     ┌──────────────┐  ┌──────────────┐                │
│     │ PostgreSQL   │  │   SQLite     │                │
│     │  (主库)      │  │  (本地备份)  │                │
│     └──────────────┘  └──────────────┘                │
│           │                   │                         │
└───────────┼───────────────────┼─────────────────────────┘
            ↓                   ↓
     ┌──────────────┐    ┌──────────────┐
     │ 远程云数据库  │    │ 本地文件     │
     │ 持久化存储   │    │ 快速备份     │
     └──────────────┘    └──────────────┘
```

## 配置

### PostgreSQL (主库)

```python
# 连接信息
HOST = "cp-hip-veil-65383f4d.pg5.aidap-global.cn-beijing.volces.com"
PORT = 5432
DATABASE = "postgres"
```

### SQLite (本地备份)

```python
# 本地路径
PATH = "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01.db"
```

## 双写管理器

### 核心接口

```python
from database.dual_write_manager import get_dual_write_manager

manager = get_dual_write_manager()

# 写入数据 (自动双写)
manager.write_selection_result(data)

# 读取数据 (优先 PostgreSQL)
results = manager.read_selection_results(date)

# 一致性检查
manager.check_consistency()
```

### 双写流程

```python
def write_with_dual(self, table_name: str, data: dict):
    """双写流程"""
    errors = []
    
    # 1. 先写入 PostgreSQL
    try:
        self.pg_session.add(data)
        self.pg_session.commit()
    except Exception as e:
        errors.append(f"PostgreSQL: {e}")
        self.pg_session.rollback()
    
    # 2. 再写入 SQLite
    try:
        self.sqlite_session.add(data)
        self.sqlite_session.commit()
    except Exception as e:
        errors.append(f"SQLite: {e}")
        self.sqlite_session.rollback()
    
    # 3. 返回结果
    if errors:
        return False, errors
    return True, None
```

## 数据表

### 选股结果表 (selection_results)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| trade_date | VARCHAR | 交易日期 |
| ts_code | VARCHAR | 股票代码 |
| stock_name | VARCHAR | 股票名称 |
| selection_type | VARCHAR | 选股类型 (t_day/t1_auction) |
| total_score | FLOAT | 综合评分 |
| sector | VARCHAR | 所属板块 |
| reason | TEXT | 推荐理由 |
| created_at | TIMESTAMP | 创建时间 |

### 市场情绪表 (market_sentiment)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| trade_date | VARCHAR | 交易日期 |
| risk_score | FLOAT | 风险评分 |
| market_heat | FLOAT | 市场热度 |
| bullish_ratio | FLOAT | 多头比例 |
| created_at | TIMESTAMP | 创建时间 |

### 竞价数据表 (auction_data)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| trade_date | VARCHAR | 交易日期 |
| ts_code | VARCHAR | 股票代码 |
| auction_pct_chg | FLOAT | 竞价涨幅 |
| auction_volume_ratio | FLOAT | 竞价量比 |
| auction_amount | FLOAT | 竞价成交额 |
| created_at | TIMESTAMP | 创建时间 |

## 一致性检查

### 命令行工具

```bash
# 检查一致性
python database/consistency_checker.py --check

# 自动同步 (从数据多的同步到数据少的)
python database/consistency_checker.py --sync

# 查看详细状态
python database/consistency_checker.py --status

# 指定表检查
python database/consistency_checker.py --check --table selection_results
```

### 检查逻辑

```python
def check_table_consistency(self, table_name: str) -> dict:
    """检查单表一致性"""
    pg_count = self.pg_session.query(
        func.count()
    ).select_from(self.get_model(table_name)).scalar()
    
    sqlite_count = self.sqlite_session.query(
        func.count()
    ).select_from(self.get_model(table_name)).scalar()
    
    return {
        'table': table_name,
        'postgresql': pg_count,
        'sqlite': sqlite_count,
        'diff': abs(pg_count - sqlite_count),
        'consistent': pg_count == sqlite_count
    }
```

### 自动同步

```python
def auto_sync(self):
    """
    自动同步策略:
    1. 比较两个数据库的记录数
    2. 从数据多的库同步缺失记录到数据少的库
    3. 记录同步日志
    """
    for table in self.tables:
        pg_data = self.get_table_data(self.pg_session, table)
        sqlite_data = self.get_table_data(self.sqlite_session, table)
        
        pg_keys = set(pg_data.keys())
        sqlite_keys = set(sqlite_data.keys())
        
        # PostgreSQL 有而 SQLite 没有
        if pg_keys > sqlite_keys:
            missing = pg_keys - sqlite_keys
            self._sync_to_sqlite(table, {k: pg_data[k] for k in missing})
        
        # SQLite 有而 PostgreSQL 没有
        elif sqlite_keys > pg_keys:
            missing = sqlite_keys - pg_keys
            self._sync_to_postgres(table, {k: sqlite_data[k] for k in missing})
```

## 故障处理

### PostgreSQL 故障

```
1. 应用继续写入 SQLite
2. 记录故障日志
3. 故障恢复后自动同步
```

### SQLite 故障

```
1. 应用继续写入 PostgreSQL
2. 记录故障日志
3. 重建 SQLite 后自动同步
```

### 两者都故障

```
1. 记录错误
2. 抛出异常
3. 等待人工干预
```

## 备份策略

### PostgreSQL (云数据库)

- 云厂商自动备份
- 每日增量备份

### SQLite (本地)

- 每次写入自动更新
- 可手动备份: `cp t01.db t01.db.bak`

## 监控

```python
# 检查双写健康状态
from database.dual_write_manager import get_dual_write_manager

manager = get_dual_write_manager()
health = manager.check_health()

# health = {
#     'postgresql': {'connected': True, 'latency_ms': 50},
#     'sqlite': {'connected': True, 'latency_ms': 1},
#     'consistent': True
# }
```
