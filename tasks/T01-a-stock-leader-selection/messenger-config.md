# T01 消息发送配置

## 首选方式：飞书直接发送

当任务执行后，消息将按以下流程发送：

```
1. 选股任务执行完成
   ↓
2. 消息保存到 /logs/messages/（临时存储）
   ↓  
3. Heartbeat 检测到待发送消息
   ↓
4. 通过 OpenClaw message 工具直接发送到飞书
   ↓
5. 发送成功后删除/归档消息文件
```

## Heartbeat 任务脚本

当 Heartbeat 触发时，执行以下检查：

```python
# 在 Heartbeat 响应中检查并发送消息
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages, mark_message_sent

messages = check_and_send_pending_messages()
for msg in messages:
    # 这里通过 message 工具发送
    # 内容在 msg['content']
    # 发送成功后：
    mark_message_sent(msg['file'])
```

## 定时任务时间表

| 任务 | 执行时间 | 说明 |
|------|---------|------|
| T日选股 | 工作日 20:00 | 基于T日涨停数据选股 |
| T+1竞价选股 | 工作日 09:25 | 基于竞价数据精选 |
| 结果跟踪 | 工作日 15:05 | 跟踪T+2收益情况 |
| 策略进化 | 周日 20:00 | 每周策略优化 |

## 消息格式

- **T日选股结果**：前10名股票 + 市场情绪 + 建议仓位
- **T+1竞价结果**：前3名精选 + 竞价数据 + 操作建议

## 配置状态

- ✅ FEISHU_WEBHOOK_URL: 未配置（使用直接发送）
- ✅ 消息存储目录: /workspace/projects/workspace/logs/messages/
- ✅ Heartbeat 检查: 已启用
