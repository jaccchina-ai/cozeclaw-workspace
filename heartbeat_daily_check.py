#!/usr/bin/env python3
import os
import sys

# 1. 检查待发送消息
print("🧠 HEARTBEAT 系统健康检查")
print("="*50)

try:
    sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    from heartbeat_task import check_and_send_pending_messages, mark_message_sent
    
    messages = check_and_send_pending_messages()
    print(f"📭 待发送消息数: {len(messages)}")
    
    if messages:
        print("\n🔔 发现待发送消息:")
        for msg in messages:
            print(f'  - {msg["file"]}')
        
        # 发送并标记为已发送
        print("\n📤 正在发送消息...")
        for msg in messages:
            try:
                # 使用message工具发送
                from message import message
                result = message(content=msg["content"], channel="feishu", to="user:ou_cf1fa11596236b5fb32fa3f4efec8d2a")
                if result.get("success"):
                    mark_message_sent(msg["file"])
                    print(f'  ✅ {msg["file"]} 发送成功并标记为已发送')
                else:
                    print(f'  ❌ {msg["file"]} 发送失败: {result.get("error")}')
            except Exception as e:
                print(f'  ❌ {msg["file"]} 发送失败: {e}')
    else:
        print("\n✅ 没有待发送的消息")
        
except Exception as e:
    print(f"\n❌ 消息队列检查失败: {e}")

# 2. 检查定时任务状态
print("\n⏰ 定时任务状态检查:")
import subprocess
result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True)

# 检查所有T01任务
all_tasks = [
    'T01-T1-Auction',
    'T01-Track', 
    'T01-T-Day',
    'T01-Evolution',
    'T01-Market-Review',
    'T01-Deps-Check',
    'T01-Unifuncs-Warmup'
]

for task_name in all_tasks:
    found = False
    for line in result.stdout.split('\n'):
        if task_name in line:
            found = True
            if 'error' in line.lower():
                print(f'  ❌ {task_name}: {line.strip()}')
            elif 'ok' in line.lower() or 'idle' in line.lower():
                print(f'  ✅ {task_name}: {line.strip()}')
            else:
                print(f'  ℹ️ {task_name}: {line.strip()}')
            break
    if not found:
        print(f'  ⚠️ {task_name}: 未找到任务')

# 3. 记忆系统维护检查
print("\n🧠 记忆系统维护检查:")
try:
    sys.path.insert(0, '/workspace/projects/workspace')
    from memory_utils import calculate_importance
    
    print("  ✅ 记忆评分模块加载成功")
    print("  ℹ️ 正在运行记忆评分测试...")
    
    # 运行记忆评分测试
    test_result = subprocess.run(['python3', 'memory_utils.py'], capture_output=True, text=True, cwd='/workspace/projects/workspace')
    if test_result.returncode == 0:
        print("  ✅ 记忆评分测试成功完成")
        # 显示部分结果
        lines = test_result.stdout.split('\n')[:10]
        for line in lines:
            if '最终分' in line or '等级' in line:
                print(f'     {line.strip()}')
    else:
        print(f'  ❌ 记忆评分测试失败: {test_result.stderr}')
        
except Exception as e:
    print(f'  ❌ 记忆系统检查失败: {e}')

# 4. 系统时间检查
print("\n🕒 系统时间检查:")
os.system('date')

print("\n" + "="*50)
print("✅ HEARTBEAT 检查完成")