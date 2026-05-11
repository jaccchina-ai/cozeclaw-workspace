import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages, mark_message_sent

messages = check_and_send_pending_messages()
print(f'Found {len(messages)} pending messages.')
for msg in messages:
    print(f'Message: {msg["content"]}')
    # Uncomment to send and mark as sent
    # message(content=msg['content'])
    # mark_message_sent(msg['file'])