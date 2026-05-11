# T01 数据库迁移记录

## 迁移概述

**迁移时间**: 2026-03-21
**源数据库**: SQLite (`database/t01_stocks.db`)
**目标数据库**: PostgreSQL 16 (`localhost:5432/t01_stocks`)
**运行环境**: Coze Coding / IDE 场景 (KVM 虚拟机)

## 迁移结果

| 表名 | 迁移记录数 | 状态 |
|------|-----------|------|
| trading_calendar | 0 | ✅ 空表 |
| daily_stock_data | 0 | ✅ 空表 |
| limit_up_stocks | 0 | ✅ 空表 |
| stock_factor_scores | 151 | ✅ 成功 |
| auction_data | 19 | ✅ 成功 |
| market_sentiment | 10 | ✅ 成功 |
| selection_results | 144 | ✅ 成功 |
| strategy_evolution | 5 | ✅ 成功 |
| daily_stock_records | 0 | ✅ 空表 |
| tracked_results | 6 | ✅ 成功 |
| ml_training_records | 0 | ✅ 空表 |
| hot_money_profile | 10 | ✅ 成功 |
| hot_money_seat | 25 | ✅ 成功 |
| hot_money_trade | 0 | ✅ 空表 |
| hot_money_stats | 0 | ✅ 空表 |

**总计**: 370 条记录迁移成功

## PostgreSQL 配置

### 数据库信息
- 主机: localhost
- 端口: 5432
- 数据库: t01_stocks
- 用户: t01_user
- 密码: t01_pass_2026

### 连接字符串
```
postgresql://t01_user:t01_pass_2026@localhost:5432/t01_stocks
```

### 环境变量配置
可通过以下环境变量覆盖默认配置:
- `DB_TYPE`: 数据库类型 (`postgres` 或 `sqlite`)
- `PG_HOST`: PostgreSQL 主机
- `PG_PORT`: PostgreSQL 端口
- `PG_DATABASE`: 数据库名称
- `PG_USER`: 用户名
- `PG_PASSWORD`: 密码

## 配置文件更新

### 新增文件
- `database/db_config.py`: 数据库配置管理
- `database/create_pg_tables.py`: PostgreSQL 表结构创建脚本
- `database/migrate_to_postgres.py`: 数据迁移脚本

### 修改文件
- `database/models.py`: 更新为支持 PostgreSQL

## 测试验证

所有核心模块已通过 PostgreSQL 连接测试:
- ✅ DataFetcher
- ✅ T1AuctionEngine
- ✅ StrategyEvolutionEngine
- ✅ HotMoneyManager
- ✅ market_review
- ✅ cron_runner
- ✅ ml_data_exporter

## 回滚方案

如需回滚到 SQLite:
1. 设置环境变量: `export DB_TYPE=sqlite`
2. 或修改 `database/db_config.py` 中的 `DB_TYPE = 'sqlite'`

## 注意事项

1. PostgreSQL 服务需要手动启动: `service postgresql start`
2. 数据库连接使用连接池，默认 5 个连接
3. 所有布尔类型字段已从 SQLite 的 0/1 转换为 PostgreSQL 的 true/false
4. 原有 SQLite 文件保留在 `database/t01_stocks.db`

## 后续任务

- [ ] 配置 PostgreSQL 服务开机自启动
- [ ] 配置 TimescaleDB 扩展（用于时间序列数据）
- [ ] 设置数据库备份策略
