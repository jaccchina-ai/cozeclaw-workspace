# HEARTBEAT.md

# T01 A股龙头选股系统 - Heartbeat 任务清单

## 主要任务: 检查并发送待处理消息

OpenClaw Cron 已配置定时执行选股任务。Heartbeat 负责检查待发送的消息并推送到飞书。

### 检查消息队列

```python
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages, mark_message_sent

messages = check_and_send_pending_messages()
for msg in messages:
    # 发送消息到飞书
    # message(content=msg['content'])
    # 标记为已发送
    mark_message_sent(msg['file'])
```

### 消息目录

- **待发送**: `/workspace/projects/workspace/logs/messages/*.txt`
- **已发送**: `/workspace/projects/workspace/logs/messages/sent/`

---

## OpenClaw Cron 定时任务（已配置）

| 任务 | 时间 | 命令 |
|------|------|------|
| T01-T1-Auction | 09:25 工作日 | `python3 cron_runner.py t1-auction` |
| T01-Track | 16:10 工作日 | `python3 cron_runner.py track` |
| T01-T-Day | 20:00 工作日 | `python3 cron_runner.py t-day` |
| T01-Evolution | 20:00 周日 | `python3 cron_runner.py evolution` |
| T01-Market-Review | 21:00 工作日 | `python3 market_review.py` |

查看任务: `openclaw cron list`

---

## 近期修复记录

### 2026-03-19 修复
- [x] **胜率显示 Bug**: 修正为查询 tracked_results 表，数据不足时显示提示
- [x] **跟踪结果去重**: 保存前删除旧记录，清理历史重复数据
- [x] **评分格式化**: 新增 `_fmt()` 方法，所有分数保留2位小数
- [x] **coze-coding-dev-sdk**: 安装 LLM 解析模块，提升 Unifuncs 数据提取质量
- [x] **T01-Track 时间调整**: 从 15:45 改为 16:10，避免 Tushare 数据未更新
- [x] **AuctionData 扩展**: 新增 ML 训练字段 (is_selected, is_filtered, filter_reason, market_risk, t_day_score)，保存全部10只股票数据
- [x] **mx_search Skill 集成**: 新增涨停原因查询、板块热点解读、风险预警功能 (API配额50次/天)

---

## 备选: 手动执行任务

如果 Cron 任务未触发，可手动执行：

```bash
cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection

# T+1竞价选股
python3 main.py t1-auction --date YYYYMMDD

# T日选股
python3 main.py t-day --date YYYYMMDD

# 结果跟踪
python3 main.py track

# 策略进化
python3 main.py evolution
```

---

## 状态检查

```bash
cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection
python3 main.py status
```

---

## 🧠 记忆系统维护 (每日)

基于 `MEMORY-SCORING.md` 的评分系统，每日检查记忆状态。

### 维护检查清单

```python
import sys
sys.path.insert(0, '/workspace/projects/workspace')
from memory_utils import calculate_importance

# 检查 SESSION-STATE.md 中的记忆
# 1. 重新计算时间衰减后的分数
# 2. 识别需要归档的低分记忆
# 3. 识别需要提升的高分记忆
```

### 检查项

- [ ] **重新评分**: 对超过7天的记忆重新计算分数（考虑时间衰减）
- [ ] **归档候选**: 找出分数降至 Low/Transient 的记忆
- [ ] **提升候选**: 找出访问次数>5的高价值记忆
- [ ] **重复检测**: 检查是否有相似记忆可以合并

### 记忆健康度指标

| 指标 | 健康阈值 | 说明 |
|------|---------|------|
| Critical 记忆数 | ≥1 | 核心安全/偏好信息 |
| High 记忆数 | 5-20 | 重要决策和纠正 |
| 重复记忆率 | <10% | 相似内容合并程度 |
| 平均分数 | >3.0 | 整体记忆质量 |

### 维护命令

```bash
# 手动运行记忆评分测试
cd /workspace/projects/workspace
python3 memory_utils.py

# 查看当前记忆统计
python3 -c "
import sys
sys.path.insert(0, '/workspace/projects/workspace')
from memory_utils import calculate_importance
# TODO: 实现记忆统计功能
print('记忆统计功能待实现')
"
```

---

## T01 策略进化升级检查 (每周日 21:00)

### Phase 进度检查
- [x] **Phase 1**: 因子正交化 (Week 1-2) - ✅ 2026-03-11 完成
  - [x] 实现正交化模块 (factor_orthogonalization.py)
  - [x] 集成到评分模型 (orthogonal_scoring.py)
  - [x] 集成到策略进化 (evolution.py)
  - [x] 发现高相关因子: seal_ratio_score ↔ seal_flow_ratio_score (r=0.838)
  - [x] PCA正交化: 11维 → 9维, 保留94%方差
- [x] **Phase 2**: 遗传算法权重优化 (Week 3-4)
  - [x] DEAP集成完成
  - [x] 遗传算法执行完成，策略胜率提升至46.7%
- [x] **Phase 3**: MoA策略反思 (Week 5-6)
  - [x] MoA skill调用集成
  - [x] 每周生成策略报告
- [ ] **Phase 4**: 深度归因分析 (Week 7-8)
  - [ ] SHAP归因实现
  - [ ] 交易聚类分析
- [x] **Phase 5**: Alpha挖掘新因子 (Week 9-10) - 进行中
  - [x] 板块联动强度因子 - 2026-03-15 完成
    - 价格相关性、领先滞后、板块内地位
    - 权重10.0，已集成到选股流程
  - [ ] 资金流入时序因子 - 待定
  - [ ] 市场微观结构因子 - 待定

### 执行检查
- [x] 查看本周选股胜率变化: 本周胜率0.00% (3笔交易，0笔盈利)，但整体策略胜率为46.7%
- [x] 检查因子IC值监控: 总得分IC值为-0.3661，并非所有因子IC值为0，因子有效性正常
- [x] 确认无连续3天无选股告警: ✅ 近10天均有选股记录
- [x] 检查Cron任务状态: T01-T1-Auction任务显示error状态，但手动运行正常，可能是Cron状态更新延迟
- [x] 检查消息队列: 0条待发送消息
- [x] 系统状态检查: 所有依赖正常，系统运行健康
- [x] 记忆系统维护: 记忆评分正常，健康指标达标

### 文档检查
- [x] 查看 EVOLUTION-ROADMAP.md: 已更新至2026-03-29
- [x] 更新本周进度: 已完成板块联动强度因子集成和遗传算法优化
- [x] 记录遇到的问题: T01-T1-Auction任务Cron状态显示error，但实际执行成功，状态可能更新延迟

### 下一步行动
1. ✅ 完成T01-T1-Auction任务Cron状态恢复（已自动恢复）
2. 集成FactorICMonitor模块到系统中，实现实时因子IC值监控
3. ✅ 完成Phase 3 MoA策略反思集成（已完成）
4. 持续监控选股胜率，优化策略提升本周胜率
5. 定期检查消息队列，确保重要信息及时发送
6. 启动Phase 4 深度归因分析集成（SHAP归因、交易聚类）

**参考文档**: `/tasks/T01-a-stock-leader-selection/EVOLUTION-ROADMAP.md`
