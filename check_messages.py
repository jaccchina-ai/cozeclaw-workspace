import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages, mark_message_sent

messages = check_and_send_pending_messages()
print(f'待发送消息数量: {len(messages)}')
for msg in messages:
    print(f'消息内容: {msg["content"]}')
    # 发送消息到飞书
    # mark_message_sent(msg['file'])