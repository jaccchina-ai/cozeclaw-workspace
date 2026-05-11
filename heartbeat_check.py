#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from heartbeat_task import check_and_send_pending_messages

# 检查待发送消息
messages = check_and_send_pending_messages()
print(f'📭 待发送消息数: {len(messages)}')
if messages:
    print('\n🔔 发现待发送消息:')
    for msg in messages:
        print(f'  - {msg["file"]}')
else:
    print('\n✅ 没有待发送的消息')

# 检查定时任务状态，特别是T01-Track（16:10执行）
print('\n⏰ 定时任务状态检查:')
import subprocess
result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True)
track_task_found = False
for line in result.stdout.split('\n'):
    if 'T01-Track' in line:
        track_task_found = True
        if 'ok' in line.lower() or 'idle' in line.lower():
            print(f'  ✅ {line.strip()}')
        else:
            print(f'  ❌ {line.strip()}')
    elif 'T01-T1-Auction' in line and 'error' in line.lower():
        print(f'  ⚠️ {line.strip()}')

if not track_task_found:
    print('  ❌ 未找到T01-Track定时任务')

# 检查系统时间
print('\n🕒 系统时间检查:')
subprocess.run(['date'], capture_output=False)

# 记忆系统维护检查
print('\n🧠 记忆系统维护检查:')
try:
    sys.path.insert(0, '/workspace/projects/workspace')
    from memory_utils import calculate_importance
    print('  ✅ 记忆评分模块正常')
except Exception as e:
    print(f'  ❌ 记忆模块异常: {e}')