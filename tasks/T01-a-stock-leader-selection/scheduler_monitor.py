#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 调度器监控工具
实时监控调度器状态，显示任务执行情况
"""

import os
import sys
import time
import psutil
from datetime import datetime

def get_scheduler_pid():
    """获取调度器进程ID"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python3' in cmdline[0] and 'main.py' in cmdline[-1] and 'schedule' in cmdline:
                return proc.info['pid']
        except Exception as e:
            continue
    return None

def get_task_logs():
    """获取最近的任务日志"""
    log_dir = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/logs'
    
    tasks = {
        't-day': {'name': 'T日选股', 'status': 'unknown'},
        't1-auction': {'name': 'T+1竞价选股', 'status': 'unknown'},
        'track': {'name': '结果跟踪', 'status': 'unknown'},
        'evolution': {'name': '策略进化', 'status': 'unknown'},
        'market-review': {'name': '市场复盘', 'status': 'unknown'},
        'unifuncs': {'name': 'Unifuncs预热', 'status': 'unknown'},
        'deps-check': {'name': '依赖检查', 'status': 'unknown'}
    }
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        return tasks
    
    for task_name in tasks:
        log_files = []
        # 查找所有日志文件
        for filename in os.listdir(log_dir):
            if filename.startswith(f'task_{task_name}_') and filename.endswith('.log'):
                log_files.append(os.path.join(log_dir, filename))
        
        if log_files:
            # 按修改时间排序，获取最新的
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_log = log_files[0]
            
            if latest_log and os.path.exists(latest_log):
                # 检查日志最后更新时间
                mtime = os.path.getmtime(latest_log)
                age = time.time() - mtime
                
                # 判断任务状态
                if age < 3600:  # 1小时内执行过
                    # 读取最后几行日志
                    with open(latest_log, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-5:]
                        
                    success = any('✅' in line or '完成' in line for line in lines)
                    error = any('❌' in line or '失败' in line for line in lines)
                    
                    if success:
                        tasks[task_name]['status'] = '✅ 成功'
                    elif error:
                        tasks[task_name]['status'] = '❌ 失败'
                    else:
                        tasks[task_name]['status'] = '⏳ 运行中'
                        
                    # 获取执行时间
                    date_str = os.path.basename(latest_log).split('_')[-1].split('.')[0]
                    tasks[task_name]['date'] = date_str
                    
                    # 获取最后更新时间
                    tasks[task_name]['update_time'] = datetime.fromtimestamp(mtime).strftime('%H:%M')
                else:
                    tasks[task_name]['status'] = '⏰ 未执行'
    
    return tasks

def show_scheduler_status():
    """显示调度器状态"""
    print(f"{'='*60}")
    print(f"T01 选股系统调度器监控")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 检查调度器进程
    pid = get_scheduler_pid()
    if pid:
        print(f"✅ 调度器运行中 (PID: {pid})")
    else:
        # 尝试查找所有Python进程
        running_schedule = False
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python3' in cmdline[0] and 'main.py' in cmdline[-1] and 'schedule' in cmdline:
                    print(f"✅ 调度器运行中 (PID: {proc.info['pid']})")
                    running_schedule = True
                    break
            except:
                continue
        if not running_schedule:
            print("❌ 调度器未运行")
    
    print()
    print("任务执行状态:")
    print("-" * 40)
    
    tasks = get_task_logs()
    for task_name, info in tasks.items():
        status_line = f"{info['name']}: {info['status']}"
        if 'date' in info:
            status_line += f" ({info['date']} {info['update_time']})"
        print(status_line)
    
    print()
    print("下一次执行计划:")
    print("-" * 40)
    print("T日选股: 交易日 20:00")
    print("T+1竞价选股: 交易日 09:27")
    print("结果跟踪: 交易日 16:10")
    print("策略进化: 每周日 20:00")
    print("市场复盘: 交易日 21:00")
    print("Unifuncs预热: 交易日 19:30")
    print("依赖检查: 交易日 09:00")
    
    print(f"\n{'='*60}")

def show_task_detail(task_name):
    """显示任务详细日志"""
    log_dir = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/logs'
    
    # 查找所有日志文件
    log_files = []
    for filename in os.listdir(log_dir):
        if filename.startswith(f'task_{task_name}_') and filename.endswith('.log'):
            log_files.append(os.path.join(log_dir, filename))
    
    if not log_files:
        print(f"未找到 {task_name} 的日志文件")
        return
    
    # 按修改时间排序，获取最新的
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    latest_log = log_files[0]
    
    print(f"{'='*60}")
    print(f"任务详细日志: {task_name}")
    print(f"日志文件: {latest_log}")
    print(f"{'='*60}")
    
    # 显示最后20行日志
    with open(latest_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-20:]
        print(''.join(lines))
    
    print(f"{'='*60}")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'show-logs' and len(sys.argv) > 2:
            task_name = sys.argv[2]
            show_task_detail(task_name)
        else:
            print("未知命令")
            print("使用方法:")
            print("  python3 scheduler_monitor.py          # 显示状态")
            print("  python3 scheduler_monitor.py show-logs <task_name>  # 显示任务日志")
    else:
        show_scheduler_status()

if __name__ == '__main__':
    main()