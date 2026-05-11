import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages, mark_message_sent

messages = check_and_send_pending_messages()
print(f'待发送消息数: {len(messages)}')
for msg in messages:
    print(f'处理消息: {msg["file"]}')
    mark_message_sent(msg["file"])