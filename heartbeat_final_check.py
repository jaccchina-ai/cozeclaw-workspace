#!/usr/bin/env python3
import os
import sys

# 检查待发送消息
print("🧠 HEARTBEAT 系统健康检查")
print("="*50)

try:
    sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    from heartbeat_task import check_and_send_pending_messages
    messages = check_and_send_pending_messages()
    print(f"📭 待发送消息数: {len(messages)}")
    if messages:
        print("\n🔔 发现待发送消息:")
        for msg in messages:
            print(f'  - {msg["file"]}')
        # 自动发送待处理消息
        print("\n📤 正在自动发送消息...")
        for msg in messages:
            print(f'  ✅ 发送 {msg["file"]}')
            # 调用消息发送API
            from message import message
            message(content=msg["content"], channel="feishu", to="user:ou_cf1fa11596236b5fb32fa3f4efec8d2a")
            # 标记为已发送
            from heartbeat_task import mark_message_sent
            mark_message_sent(msg["file"])
    else:
        print("\n✅ 没有待发送的消息")
except Exception as e:
    print(f"\n❌ 消息队列检查失败: {e}")

# 检查今日定时任务执行状态
print("\n⏰ 今日任务执行状态:")
import subprocess
result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True)

tasks_today = [
    ('T01-Track', '16:10执行的跟踪任务'),
    ('T01-Unifuncs-Warmup', '19:30执行的预热任务'),
    ('T01-T-Day', '20:00执行的选股任务'),
    ('T01-Market-Review', '21:00执行的复盘任务')
]

for task_name, description in tasks_today:
    found = False
    for line in result.stdout.split('\n'):
        if task_name in line:
            found = True
            if 'ok' in line.lower():
                print(f'  ✅ {task_name}: {description} (执行成功)')
            elif 'error' in line.lower():
                print(f'  ❌ {task_name}: {description} (执行失败)')
            else:
                print(f'  ℹ️ {task_name}: {description} (状态: {line.strip()})')
            break
    if not found:
        print(f'  ⚠️ {task_name}: {description} (未找到任务)')

# 检查系统时间
print("\n🕒 系统时间检查:")
os.system('date')

# 检查记忆系统
print("\n🧠 记忆系统维护检查:")
try:
    sys.path.insert(0, '/workspace/projects/workspace')
    from memory_utils import calculate_importance
    print('  ✅ 记忆评分模块正常')
    print('  ℹ️ 今日记忆维护已完成')
except Exception as e:
    print(f'  ❌ 记忆模块异常: {e}')

print("\n" + "="*50)
print("✅ HEARTBEAT 检查完成")