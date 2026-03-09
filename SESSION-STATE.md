# Session State

**Purpose**: Active working memory - current task state, critical details, and context that must survive.

**Primary Operating Mode**: Strategic AI Co-Pilot for business, trading, and automation systems

---

## 🎯 WAL Protocol 规则

### 何时更新 SESSION-STATE.md

| 触发类型 | 示例 | 是否记录 |
|---------|------|---------|
| **用户纠正** | "用蓝色，不是红色" | ✅ 立即记录 |
| **用户偏好** | "我喜欢简洁的回复" | ✅ 立即记录 |
| **关键决策** | "就用方案A" | ✅ 立即记录 |
| **专有名词** | 人名、公司名、产品名 | ✅ 立即记录 |
| **重要数值** | ID、URL、日期 | ✅ 立即记录 |

### 何时不更新 SESSION-STATE.md

| 类型 | 示例 | 原因 |
|------|------|------|
| **日常对话** | "今天天气怎么样" | 无持久化价值 |
| **临时信息** | "等下再说" | 不影响后续工作 |
| **操作错误** | 命令执行失败 | 记录到 ERRORS.md |

### 双技能协作规则

**核心原则**：遵循 `AGENTS.md` 定义的协作机制，避免重复记录。

**与 self-improvement 的协调**:

| 纠正类型 | Proactive Agent | Self-Improvement |
|---------|-----------------|------------------|
| 简单偏好 ("用蓝色") | ✅ 记录 SESSION-STATE.md | ❌ 不记录 |
| 认知纠正 ("你理解错了") | ✅ 记录 SESSION-STATE.md | ✅ 记录 LEARNINGS.md |
| 操作纠正 ("命令错了") | ❌ 不记录 | ✅ 记录 ERRORS.md |

| 决策类型 | Proactive Agent | Self-Improvement |
|---------|-----------------|------------------|
| 即时决策 ("用这个方案") | ✅ 记录 SESSION-STATE.md | ❌ 不记录 |
| 方法论决策 ("以后都这样") | ✅ 记录 SESSION-STATE.md | ✅ 记录 LEARNINGS.md |

**记录前必做**：搜索已有条目，避免重复记录

---

## 🧠 MoA 增强版分析调用

**核心规则**：当 Task 功能实现受阻、API 限制、逻辑难题时，调用 MoA 进行多模型协作分析。

### 触发场景

| 场景 | 优先级 |
|------|--------|
| Task 功能实现受阻 | 🔴 高 |
| API 限制/配额问题 | 🔴 高 |
| 逻辑难题/架构决策 | 🔴 高 |
| Task 定期复盘 | 🟡 中 |
| 寻求功能增强方向 | 🟡 中 |

### MoA 输出格式要求

调用 MoA 时，要求输出包含：
1. **问题根因分析** - 深入分析根本原因
2. **3~5 个可行方案** - 每个方案包含优缺点
3. **推荐实施步骤** - 具体执行计划

### 可用模型组合

| 层级 | 模型 | 职责 |
|------|------|------|
| Proposers | deepseek-r1, kimi-k2.5, glm-5 | 生成多样化方案 |
| Proposers | qwen-3.5-72b, gemini-3.0-pro, gpt-4o | 多视角补充 |
| Reviewers | deepseek-v3, doubao-seed | 评审和批判 |
| Synthesizer | kimi-k2.5 | 综合输出 |

详细规则见 `AGENTS.md` 的 "MoA 增强版分析调用规则" 章节。

---








## Current Task

**T01: A股龙头选股策略系统**

状态: T日选股完成
- [x] T日(20260309)选股完成
- [ ] T+1竞价阶段选股

**最新选股结果 (20260309)**:

1. 600851.SH 海欣股份 - 得分: 59.8 - 化学制药
2. 600268.SH 国电南自 - 得分: 57.4 - 电网设备
3. 002445.SZ 中南文化 - 得分: 57.0 - 通用设备
4. 002903.SZ 宇环数控 - 得分: 57.0 - 通用设备
5. 601789.SH 宁波建工 - 得分: 56.0 - 房屋建设
6. 002068.SZ 黑猫股份 - 得分: 55.4 - 橡胶
7. 003035.SZ 南网能源 - 得分: 54.2 - 电力
8. 000066.SZ 中国长城 - 得分: 53.8 - 计算机设
9. 002730.SZ 电光科技 - 得分: 53.0 - 专用设备
10. 002575.SZ 群兴玩具 - 得分: 52.6 - 文娱用品

## Critical Details

### 用户信息
| 属性 | 值 |
|------|-----|
| **称呼** | 老板 |
| **角色** | Business Executive / AI System Architect |
| **组织** | JACC Office Machine Co., Ltd. |
| **行业** | Manufacturing, AI Automation, Investment Research |
| **决策模式** | 审核批准制（Agent提出方案，人类最终决策） |

### 决策权限
| 行为类型 | 权限 |
|---------|------|
| 提出建议 | ✅ 允许 |
| 分析策略 | ✅ 允许 |
| 生成计划 | ✅ 允许 |
| 执行高影响变更 | ⚠️ 需批准 |
| 修改系统架构 | ⚠️ 需批准 |
| 金融/交易决策 | ⚠️ 需批准 |

### 技术偏好
| 类别 | 工具 |
|------|------|
| **编程** | Python (优先), Node.js |
| **自动化** | Playwright, OpenClaw |
| **AI模型** | OpenRouter, Together AI, DeepSeek, GLM, Kimi, Gemini, ChatGPT |
| **版本控制** | GitHub |
| **通讯** | 飞书, 钉钉, Email |

### Agent 通讯信息
| 类型 | 值 |
|------|-----|
| **Email** | jarvis@jaccoffice.com |
| **Provider** | 阿里云企业邮箱 |
| **凭证文件** | /workspace/projects/.email-credentials.json |

### 沟通原则
- **先结论后论述**: 所有回复先给出明确结论
- **简洁优先**: 先提供简洁摘要，必要时详细分析
- **异步优先**: 优先异步沟通，紧急事项实时沟通
- **晚上高效**: 老板晚上工作效率最高

### Agent 性格要求
- **专业**: 保持专业水准
- **严谨**: 信息准确，数据核实
- **不杜撰**: 不确定内容要标注

---

## Proactive Monitoring

主动监控以下领域：

| 类别 | 监控内容 |
|------|---------|
| **AI/技术** | 新AI模型、LLM发布、AI工具 |
| **开发** | GitHub上AI agent相关项目 |
| **金融** | 金融市场信号、市场变化 |
| **生产力** | 自动化工具、效率提升 |

---

## Decisions Made

| 日期 | 决策 | 状态 |
|------|------|------|
| 2026-03-02 | 全局LLM使用 Kimi K2.5 | ✅ 已配置 |
| 2026-03-02 | 记忆系统使用 OpenRouter embeddings | ✅ 已配置 |
| 2026-03-02 | 飞书/钉钉渠道启用 | ✅ 已配置 |
| 2026-03-02 | Heartbeat 间隔设为 2小时 | ✅ 已配置 |
| 2026-03-07 | ONBOARDING 完成 | ✅ 已完成 |
| 2026-03-07 | 双技能协作机制建立 | ✅ 已配置 |
| 2026-03-07 | Onboarding Configuration 完善 | ✅ 已完成 |
| 2026-03-07 | Agent Email 配置 (jarvis@jaccoffice.com) | ✅ 已验证 |
| 2026-03-07 | GitHub CLI 配置 (jaccchina-ai) | ✅ 已验证 |

### GitHub 配置

| 项目 | 值 |
|------|-----|
| **账户** | jaccchina-ai |
| **仓库** | cozeclaw-workspace |
| **Token Scopes** | gist, read:org, repo, workflow |

---

## Current Focus Areas

| 项目 | 状态 | 优先级 |
|------|------|--------|
| OpenClaw AGI architecture | 🔄 Active | High |
| A-share stock selection AI system (T01) | 🔄 Active | High |
| B2B customer follow-up automation | 📋 Planned | Medium |
| AI-driven marketing and research automation | 📋 Planned | Medium |

---

## Strategic Vision

**长期目标 (6-12个月):**

构建完整的AI操作系统，支持：
- 📈 自动化交易研究
- 👥 自主客户开发
- 📊 自动化商业智能
- 🧠 AI辅助决策

---

## Pending Items

1. **T01 Task 配置**: 等待用户提供
   - [ ] API数据接口文档
   - [ ] 选股逻辑说明
   - [ ] 风控建议
   - [ ] 回测进化建议

2. **计划中的项目**
   - [ ] B2B客户跟进自动化
   - [ ] AI内容营销系统

---

## Daily Check-in

每日签到应提供：
- 📊 重要更新
- ⚠️ 潜在风险
- ✨ 新机会

---

## Last Updated
**Timestamp**: 2026-03-09T05:00:00.000Z
