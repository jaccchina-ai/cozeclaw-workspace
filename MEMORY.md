# Memory

**Purpose**: Curated long-term wisdom distilled from daily logs and working sessions.

**Only use in**: Main session (direct chats with your human)

**Security**: DO NOT load in shared contexts (Discord, group chats, sessions with other people)

---

## 🎯 Core Knowledge

### User Profile

**目标**:
- 原始目标: 构建AI驱动的商业自动化系统（客户开发、销售跟进、市场分析、投资决策）
- 当前目标: T01 A股龙头选股系统开发

**决策模式**: 审核批准制（Agent提出方案，人类最终决策）

**沟通原则**:
- 先结论后论述，内容详细但避免废话
- 优先异步沟通，紧急事项实时沟通
- 晚上工作效率最高

**Agent性格**: 专业、严谨、不杜撰

**风险承受**: 平衡（允许实验，但关键系统需稳定）

**偏好**:
- 编程: Python优先，结构清晰，注释充分
- AI模型: OpenRouter, DeepSeek, GLM, Kimi, Gemini, ChatGPT
- 通讯: 飞书, 钉钉, Email
- 日志管理: 避免重复记录、过度记录琐碎细节

**专属邮箱**: jarvis@jaccoffice.com (阿里云企业邮箱)
- 专属工作邮箱，用于业务沟通和自动化任务
- 配置: IMAP/SMTP 已就绪

### Project Context

**运行环境**: Vefaas 容器 (Coze Coding 场景)
- 环境 ID: `vefaas-u1rxyyuj-5jjgnvfm8a-d70eg182iniujq141pe0-sandbox`
- 场景类型: `coze_coding`
- init 进程: `dumb-init` (非 systemd)
- 工作目录: `/workspace/projects/`
- 状态目录: `OPENCLAW_STATE_DIR=/workspace/projects`

**OpenClaw 个人 AI 助手**
- 版本: 2026.3.12
- Node.js: 24.14.0
- 技术栈: Node.js + Python 3.x
- 已配置渠道: 飞书、钉钉
- 已安装技能: tushare-finance, unifuncs, self-improvement, proactive-agent 等

**T01 A股龙头选股策略系统**
- 位置: `/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/`
- 数据库: PostgreSQL 16 (主) + SQLite (备用) 双写模式
- 数据源: Tushare (Token: 已配置)
- 外部分析: Unifuncs API (预热任务 19:30)
- 调度: OpenClaw Cron Jobs
- **双数据库**: 所有数据同时写入 PostgreSQL 和 SQLite，确保数据安全

**Cron Jobs 配置**:
| 时间 | 任务 | 功能 |
|:---|:---|:---|
| 09:25 | T1-Auction | T+1 竞价精选 |
| 15:45 | Track | 结果跟踪 |
| 18:00 | Deps-Check | 依赖检查 (install_deps.py) |
| 19:30 | Unifuncs-Warmup | Unifuncs 预热 |
| 20:00 | T-Day | T日晚间选股 |
| 周日 20:00 | Evolution | 策略进化 |

**关键约束**:
- T01: 所有指标数值不能用模拟数据，无法获取必须告知用户
- T01: 每天 18:00 自动执行 `install_deps.py` 确认所有依赖已安装
- Unifuncs: 19:30 创建任务，最多25分钟超时，结果保存到本地文件

---

## 📚 Learned Patterns

### What Works

1. **双数据库架构**: PostgreSQL 主库 + SQLite 备用库，所有数据同时写入，机器学习时可自动回退
2. **SQLite 时间旅行**: 支持查询历史日期数据、日期对比、快照管理和时间模式分析
3. **游资席位识别优化**: 地址关键词匹配（成都北一环路、拉萨系列）解决券商改名问题
4. **通达信板块数据**: 使用行业板块而非概念板块
5. **Unifuncs 异步调用**: 预热任务 + 本地文件读取，避免同步超时
6. **混合搜索**: 向量70% + 文本30%，效果优于单一模式
7. **超时配置**: timeoutSeconds: 900 (15分钟) 解决长时间任务超时

### What Doesn't Work

1. **券商改名问题**: 国泰君安 → 国泰海通，需用地址关键词匹配
2. **API 限流**: concept_detail 接口有单独50次/分钟限流，应避免调用
3. **数据库唯一约束**: 市场情绪数据需先删除旧记录再插入

---

## 🔄 Processes

### Workflows

**T01 开发流程**:
1. 修改代码 → 手动测试验证 → 确认功能正常 → 提交修改
2. 使用 git 做版本控制，方便回滚
3. 沙箱环境 = 生产环境，修改立即生效

**记忆系统工作流**:
1. 重要信息写入 MEMORY.md（长期记忆）
2. 日常工作写入 memory/YYYY-MM-DD.md（日记）
3. Auto-Capture 自动捕获对话中的重要信息
4. Auto-Recall 自动注入相关记忆到上下文

### Decision Frameworks

**遇到问题时的排查顺序**:
1. `openclaw doctor --fix` - 检查配置健康
2. `openclaw status --all` - 完整诊断报告
3. `openclaw docs <关键词>` - 搜索官方文档
4. 查看日志: `openclaw logs --follow`

---

## 📌 Important Facts

### API Keys & Tokens

| 服务 | 用途 | 状态 |
|:---|:---|:---:|
| Tushare | 金融数据 | ✅ |
| Unifuncs | 深度市场研究 | ✅ |
| OpenRouter | LLM + Embedding | ✅ |
| 飞书 | 消息渠道 | ✅ |
| 钉钉 | 消息渠道 | ✅ |

### 游资画像数据库

已初始化 10 个知名游资画像:
- 章盟主、呼家楼、赵老哥、92科比、乔帮主
- 佛山无影脚、逍遥子、武林盟主、左右护法

### 关键文件位置

| 文件 | 路径 |
|:---|:---|
| 主配置 | `/workspace/projects/openclaw.json` |
| T01 代码 | `/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/` |
| 双数据库管理器 | `.../database/dual_db_manager.py` |
| 时间旅行模块 | `.../database/time_travel.py` |
| SQLite 数据库 | `.../database/t01_stocks.db` |
| 快照目录 | `.../database/snapshots/` |
| 记忆文件 | `/workspace/projects/workspace/memory/` |
| Cron 日志 | `~/.openclaw/cron/runs/` |
| PostgreSQL 数据 | `/var/lib/postgresql/16/main/` |
| T01 日志 | `/workspace/projects/workspace/logs/t01/` |

### 环境服务

| 服务 | 状态 | 说明 |
|:---|:---|:---|
| PostgreSQL 16 | 需手动启动 | `pg_ctlcluster 16 main start` |
| 端口 5000 | OpenClaw Web | Gateway 服务 |
| 端口 5432 | PostgreSQL | 数据库服务 |
| systemd | 不可用 | 容器使用 dumb-init |

---

## 🔗 References

- **OpenClaw 文档**: https://docs.openclaw.ai/
- **Tushare 文档**: https://tushare.pro/document/
- **通达信板块**: 使用 tdx_index, tdx_member, tdx_daily 接口

---

**Last Distilled**: 2026-03-24
