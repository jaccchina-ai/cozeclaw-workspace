#!/usr/bin/env python3
import os
import sys

def check_pending_messages():
    """检查待发送消息队列"""
    try:
        sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
        from heartbeat_task import check_and_send_pending_messages
        messages = check_and_send_pending_messages()
        return messages
    except Exception as e:
        print(f"❌ 检查消息队列失败: {e}")
        return []

def check_cron_status():
    """检查定时任务状态"""
    print("\n⏰ 定时任务状态检查:")
    import subprocess
    result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True)
    
    # 检查关键任务
    tasks_to_check = [
        ('T01-Track', '今日16:10执行的跟踪任务'),
        ('T01-Unifuncs-Warmup', '19:30待执行的预热任务'),
        ('T01-T-Day', '20:00待执行的选股任务'),
        ('T01-Market-Review', '21:00待执行的复盘任务'),
        ('T01-T1-Auction', '每日09:27的竞价选股任务'),
        ('T01-Deps-Check', '每日09:00的依赖检查任务')
    ]
    
    for task_name, description in tasks_to_check:
        found = False
        for line in result.stdout.split('\n'):
            if task_name in line:
                found = True
                if 'error' in line.lower():
                    print(f'  ❌ {task_name}: {description} (状态: ERROR)')
                elif 'ok' in line.lower() or 'idle' in line.lower() or 'in' in line.lower():
                    print(f'  ✅ {task_name}: {description} (状态: 正常)')
                else:
                    print(f'  ℹ️ {task_name}: {description} (状态: {line.strip()})')
                break
        if not found:
            print(f'  ⚠️ {task_name}: {description} (未找到任务)')

def check_system_status():
    """检查系统时间和基础状态"""
    print("\n🕒 系统时间检查:")
    os.system('date')
    
    print("\n🧠 记忆系统维护检查:")
    try:
        sys.path.insert(0, '/workspace/projects/workspace')
        from memory_utils import calculate_importance
        print('  ✅ 记忆评分模块正常')
    except Exception as e:
        print(f'  ❌ 记忆模块异常: {e}')

# 主程序
print("🧠 HEARTBEAT 系统健康检查")
print("="*50)

# 检查待发送消息
messages = check_pending_messages()
print(f"📭 待发送消息数: {len(messages)}")
if messages:
    print("\n🔔 发现待发送消息:")
    for msg in messages:
        print(f'  - {msg["file"]}')
else:
    print("\n✅ 没有待发送的消息")

# 检查其他状态
check_cron_status()
check_system_status()

print("\n" + "="*50)
print("✅ HEARTBEAT 检查完成")