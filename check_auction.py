import os
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from datetime import datetime

today = datetime.now().strftime('%Y%m%d')
log_file = f'/workspace/projects/workspace/logs/t01/t1-auction-{today}.log'

if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()[-10:]
        print('📊 今日竞价选股日志最后10行:')
        print('\n'.join(lines))
else:
    print('❌ 今日竞价选股日志不存在')
    print('💡 可能原因:')
    print('  1. 定时任务未到执行时间 (09:25)')
    print('  2. 任务执行失败未生成日志')
    print('  3. 系统时间不准确')

# 检查定时任务配置
print('\n⏰ 定时任务配置检查:')
cmd_result = os.popen('openclaw cron list').read()
for line in cmd_result.split('\n'):
    if 'T01-T1-Auction' in line:
        print('✅ 找到任务:', line.strip())
        break
else:
    print('❌ 未找到T01-T1-Auction定时任务')

# 检查进程状态
print('\n🔍 系统时间检查:')
os.system('date')

# 检查日志目录
print('\n📁 日志目录内容:')
log_dir = '/workspace/projects/workspace/logs/t01/'
if os.path.exists(log_dir):
    os.system(f'ls -la {log_dir} | tail -5')
else:
    print('❌ 日志目录不存在')