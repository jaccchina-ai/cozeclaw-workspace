import os
import json

run_logs_dir = os.path.expanduser('~/.openclaw/cron/runs')
print('📜 最近10次定时任务运行日志:')

if not os.path.exists(run_logs_dir):
    print('❌ 定时任务运行日志目录不存在')
    os.system('openclaw cron status')
    exit()

files = sorted(os.listdir(run_logs_dir), reverse=True)[:10]
task_found = False

for file in files:
    if file.endswith('.log'):
        file_path = os.path.join(run_logs_dir, file)
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                if not lines:
                    continue
                    
                # 解析第一行JSON
                try:
                    job_info = json.loads(lines[0])
                    if 'job' in job_info and 'name' in job_info['job']:
                        job_name = job_info['job']['name']
                        if 'T01-T1-Auction' in job_name:
                            task_found = True
                            print(f'✅ {file[0:19]} - {job_name}')
                            # 显示错误信息
                            for line in lines[1:]:
                                if 'error' in line.lower() or 'fail' in line.lower():
                                    print(f'   ❌ {line.strip()}')
                            # 显示最后一行输出
                            if lines:
                                print(f'   📊 {lines[-1].strip()}')
                except json.JSONDecodeError:
                    # 不是JSON格式，直接显示内容
                    if 'T01-T1-Auction' in lines[0]:
                        task_found = True
                        print(f'📝 {file[0:19]} - {lines[0][:50]}...')
                        
        except Exception as e:
            print(f'⚠️ 读取文件失败: {file} - {e}')

if not task_found:
    print('ℹ️ 未找到T01-T1-Auction任务运行记录')
    print('💡 可能原因:')
    print('  1. 任务从未执行过')
    print('  2. 任务执行记录已被清理')
    print('  3. 任务名称不匹配')

print('\n🔍 定时任务执行历史:')
os.system('openclaw doctor --fix 2>&1 | grep -A5 -B5 "cron"')

print('\n⏰ 手动测试执行:')
print('可以运行以下命令手动测试竞价选股:')
print('  cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
print('  python3 main.py t1-auction --date 20260326')