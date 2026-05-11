# T01 选股系统 - OpenClaw Cron 定时任务配置

## 任务列表

| 任务名称 | 执行时间 | 周期 | 时区 | 状态 |
|---------|---------|------|------|------|
| T01-T1-Auction | **09:26** | 工作日 (1-5) | Asia/Shanghai | ✅ 已启用 |
| T01-Track | **16:10** | 工作日 (1-5) | Asia/Shanghai | ✅ 已启用 |
| T01-T-Day | 20:00 | 工作日 (1-5) | Asia/Shanghai | ✅ 已启用 |
| T01-Unifuncs-Warmup | 19:30 | 工作日 (1-5) | Asia/Shanghai | ✅ 已启用 |
| T01-Evolution | 20:00 | 周日 (0) | Asia/Shanghai | ✅ 已启用 |

## 任务详情

### 1. T01-T1-Auction (T+1竞价选股)
- **Job ID**: `742242b0-b92b-4169-bf38-d070827a0230`
- **执行命令**: `python3 cron_runner.py t1-auction`
- **执行时间**: 交易日 **09:26**
- **说明**: 在交易日 09:26 执行竞价选股，基于T日初选股票的竞价数据精选前3名
- **重试机制**: 代码内置重试机制（最多3次，每次间隔10秒，应对数据同步延迟）

### 2. T01-Track (结果跟踪)
- **Job ID**: `fb9bcc78-1866-479c-88b3-41725ea3797f`
- **执行命令**: `python3 cron_runner.py track`
- **执行时间**: 交易日 **16:10**
- **说明**: 在交易日 16:10 收盘后跟踪T+1竞价选股结果的T+2收益情况
- **数据填充**: 此任务会自动填充 `ml_training_records` 表

### 3. T01-T-Day (T日选股)
- **Job ID**: `451c9008-2aac-4b8c-8a7d-c2ed2eaf11c5`
- **执行命令**: `python3 cron_runner.py t-day`
- **执行时间**: 交易日 **20:00**
- **说明**: 在交易日 20:00 执行T日选股，基于涨停数据筛选明日观察标的

### 4. T01-Unifuncs-Warmup (Unifuncs预热)
- **Job ID**: `b37a187f-b0cf-4332-b4d2-0b71f9950a85`
- **执行命令**: `python3 cron_runner.py unifuncs`
- **执行时间**: 交易日 **19:30**
- **说明**: 预热 Unifuncs 服务

### 5. T01-Evolution (策略进化)
- **Job ID**: `2a45f4f2-78eb-438a-b729-ea5e9b53bae1`
- **执行命令**: `python3 cron_runner.py evolution`
- **执行时间**: 每周日 **20:00**
- **说明**: 每周日 20:00 执行策略进化，回测并优化选股参数

## 管理命令

### 查看任务列表
```bash
openclaw cron list
```

### 查看任务详情
```bash
openclaw cron runs --id <job-id>
```

### 手动执行任务
```bash
openclaw cron run <job-id> --force
```

### 禁用任务
```bash
openclaw cron edit <job-id> --enabled false
```

### 启用任务
```bash
openclaw cron edit <job-id> --enabled true
```

### 删除任务
```bash
openclaw cron remove <job-id>
```

## 消息发送

所有任务执行完成后，选股结果通过以下方式发送：
1. **执行脚本**: `cron_runner.py` 运行选股
2. **保存消息**: 结果保存到 `/logs/messages/`
3. **Heartbeat 检测**: 检测到待发送消息后
4. **飞书发送**: 通过 OpenClaw message 工具直接发送

## 依赖

- **OpenClaw Gateway**: 必须持续运行
- **Tushare Token**: 已配置环境变量
- **Python 环境**: 已安装依赖 (tushare, pandas, numpy, sqlalchemy, schedule)

## 配置文件

- **定时任务配置**: `~/.openclaw/cron/jobs.json`
- **执行脚本**: `cron_runner.py`
- **任务运行日志**: `~/.openclaw/cron/runs/<job-id>.jsonl`

## 注意事项

1. **工作日判断**: Cron 表达式使用 1-5 表示周一到周五，但实际的交易日需要程序内部再次确认
2. **竞价数据时间**: stk_auction 接口的数据在 09:25 后可用
3. **消息投递**: 任务以 isolated 会话运行，输出通过 announce 投递到 last 渠道
