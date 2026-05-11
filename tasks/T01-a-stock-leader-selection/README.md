# T01 A股龙头选股系统

## 概述

T01 是一个基于 AI 的 A股龙头战法选股系统，通过多维度因子分析、竞价数据挖掘和遗传算法优化，实现智能化选股决策。

### 核心特性

- **T日选股**: 每日20:00初选10只优质股票
- **T+1竞价**: 每日09:27从T日初选中精选不超过2只股票
- **市场复盘**: AI 分析热点板块持续性
- **结果跟踪**: 自动跟踪选股胜率，持续优化策略
- **策略进化**: 遗传算法动态优化因子权重

---

## 文档目录

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目总览 |
| [docs/scheduler.md](docs/scheduler.md) | Cron 任务调度详解 |
| [docs/dual-write.md](docs/dual-write.md) | 双写架构文档 |

---

## 系统架构

```
T01 选股系统
├── main.py                 # 主入口 & Cron 调度器
├── selection_engine.py     # 选股引擎 (T日 + T+1竞价)
├── data_fetcher.py         # Tushare 数据获取
├── scoring_model.py        # 评分模型
├── factor_config.py        # 因子配置
├── unifuncs_scheduler.py   # Unifuncs 舆情预热
├── market_review.py        # 市场复盘
├── evolution.py            # 策略进化 (遗传算法)
├── messenger.py            # 消息通知 (飞书/钉钉)
├── monitor.py              # 任务监控
├── mx_search_integration.py # 搜索集成
├── money_flow_analyzer.py  # 资金流向分析
└── database/
    ├── models.py           # 数据模型
    ├── dual_write_manager.py # 双写管理
    └── consistency_checker.py # 一致性检查
```

---

## Cron 任务调度

| 时间 | 任务 | 说明 |
|------|------|------|
| 19:30 | Unifuncs预热 | 获取舆情分析结果 |
| 20:00 | T日选股 | 执行T日初选 |
| 21:00 | T01-Market-Review | 市场复盘分析 |
| 09:00 | T01-Deps-Check | 依赖检查 |
| 09:27 | T01-T1-Auction | T+1竞价选股 |
| 16:10 | T01-Track | 跟踪结果 & 计算胜率 |
| 周日 20:00 | 策略进化 | 遗传算法优化 |

### 启动调度器

```bash
cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection
python main.py schedule
```

---

## 手动命令

```bash
# 依赖检查
python main.py deps-check

# T日选股
python main.py t-day

# T+1竞价选股
python main.py t1-auction

# 市场复盘
python main.py market-review

# 结果跟踪
python main.py track

# Unifuncs预热
python main.py unifuncs

# 策略进化
python main.py evolution

# 查看状态
python main.py status

# 指定日期执行
python main.py t-day --date 20250401
```

---

## 数据架构

### 双写架构

采用 PostgreSQL (外部持久化) + SQLite (本地备份) 双写架构：

```
写入操作
    │
    ├─→ PostgreSQL (主库)
    │      URL: cp-hip-veil-65383f4d.pg5.aidap-global.cn-beijing.volces.com:5432
    │
    └─→ SQLite (本地备份)
           路径: /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01.db
```

### 一致性检查

```bash
# 检查数据一致性
python database/consistency_checker.py --check

# 自动同步 (从数据多的库同步到数据少的)
python database/consistency_checker.py --sync

# 查看详细状态
python database/consistency_checker.py --status
```

---

## 核心因子

### T日选股因子

| 因子 | 说明 | 权重 |
|------|------|------|
| limit_up_strength | 涨停强度 | 15% |
| sector_linkage_score | 板块联动 | 15% |
| main_money_flow | 主力资金流向 | 20% |
| market_sentiment | 市场情绪 | 10% |
| burst_signal | 爆量信号 | 15% |
| continuity | 连板效应 | 25% |

### 竞价评分因子

| 因子 | 说明 |
|------|------|
| auction_turnover | 竞价换手率 |
| auction_amount | 竞价成交额 |
| auction_pct_chg | 竞价涨幅 |
| auction_volume_ratio | 竞价量比 |
| auction_burst_ratio | 竞价爆量比 |
| sector_resonance | 板块共振 |

---

## 数据获取策略

### T日数据获取 (20:00)

只获取必要数据，初选 **10 只** 优质股票：

1. **涨停股数据** (~60条)
   - `pro_bar` 或 `stk_moneyflow` 接口

2. **资金流向数据**
   - `moneyflow_data` 接口

3. **市场情绪**
   - `market_sentiment` 接口

### T+1竞价数据获取 (09:27)

从 T 日初选的 10 只中精选 **不超过 2 只**：

1. **竞价数据**
   - `stk_auction` 接口

2. **注意事项**: 竞价阶段**不使用**主力资金流向模块

---

## 依赖检查 (T01-Deps-Check)

09:00 执行，检查项：

1. Tushare API 连接
2. 数据库连接
3. T日选股数据存在性
4. 市场情绪数据完整性

---

## 飞书消息通知

系统通过飞书卡片消息推送选股结果和复盘报告。

### 消息类型

- T日选股结果
- T+1竞价结果
- 市场复盘报告
- 异常告警

---

## 测试与调试

### 模块测试

```bash
# 运行因子 IC 分析
python factor_ic_check.py

# 运行选股引擎测试
python run_module_tests.py

# 测试资金流向分析
python test_money_flow_analyzer.py

# 检查数据库结构
python check_schema.py
```

### 数据回填

```bash
# 回填因子数据
python backfill_factor_data.py --start 20240101 --end 20240331

# 查看日志
tail -f /workspace/projects/workspace/logs/t01/t01_*.log
```

---

## 技术栈

| 组件 | 版本/说明 |
|------|----------|
| Python | 3.x |
| Tushare | 最新版 |
| SQLAlchemy | ORM |
| PostgreSQL | 外部持久化 |
| SQLite | 本地备份 |
| scikit-learn | 机器学习 |
| DEAP | 遗传算法 |
| LangChain | LLM 集成 |
| Coze SDK | 模型调用 |

---

## 文件路径

| 类型 | 路径 |
|------|------|
| 项目根目录 | `/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/` |
| 日志目录 | `/workspace/projects/workspace/logs/t01/` |
| 消息队列 | `/workspace/projects/delivery-queue/` |
| SQLite 数据库 | `./database/t01.db` |

---

## 注意事项

1. **数据真实性**: 所有指标数值必须使用真实数据，不允许模拟
2. **决策模式**: 采用审核批准制，Agent 提出方案，人类最终决策
3. **IP 限制**: 避免频繁调用 Tushare API，遵守接口限制
4. **版本兼容性**: OpenClaw 2026.3.22+ 与 openclaw-wechat 存在不兼容问题

---

## 更新日志

### 2026.04.06
- 新增 21:00 T01-Market-Review 市场复盘任务
- 新增 09:00 T01-Deps-Check 依赖检查任务
- 调整 T01-Track 执行时间为 16:10
- 优化数据获取策略，只获取涨停股数据
- 完成双写架构改造

### 2026.03.22
- 修复 openclaw-wechat 插件兼容性问题
- 优化因子 IC 分析
- 添加一致性检查工具
