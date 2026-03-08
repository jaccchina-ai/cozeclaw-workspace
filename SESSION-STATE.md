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

**与 self-improvement 的协调**:
- 简单偏好 → 只写 SESSION-STATE.md
- 认知纠正 → SESSION-STATE.md + LEARNINGS.md
- 方法论决策 → SESSION-STATE.md + LEARNINGS.md

---

## Current Task

**T01: A股龙头选股策略系统**

状态: 等待用户提供详细配置
- [ ] API数据接口文档
- [ ] 选股逻辑说明
- [ ] 风控建议
- [ ] 回测进化建议

---

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
**Timestamp**: 2026-03-07T00:00:00.000Z
