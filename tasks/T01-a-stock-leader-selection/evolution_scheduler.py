#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 策略进化调度器
定期执行策略进化任务
"""

import os
import time
import schedule
from datetime import datetime, timedelta
import subprocess
import traceback

def run_evolution():
    """执行策略进化任务"""
    print(f"\n{'='*60}")
    print(f"T01 策略进化任务启动")
    print(f"时间: {datetime.now()}")
    print(f"{'='*60}\n")
    
    try:
        # 运行进化任务
        result = subprocess.run(
            ['python3', '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py', 'evolution'],
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )
        
        if result.returncode == 0:
            print("✅ 策略进化任务执行成功")
            print(result.stdout)
            
            # 分析进化结果
            print(f"\n{'='*60}")
            print(f"分析进化结果")
            print(f"{'='*60}")
            
            analyze_result = subprocess.run(
                ['python3', '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/analyze_evolution_results.py'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if analyze_result.returncode == 0:
                print("✅ 进化结果分析完成")
                print(analyze_result.stdout)
            else:
                print("⚠️ 进化结果分析失败")
                print(analyze_result.stderr)
                
        else:
            print("❌ 策略进化任务执行失败")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("❌ 策略进化任务超时")
    except Exception as e:
        print(f"❌ 策略进化任务异常: {e}")
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"策略进化任务结束")
    print(f"时间: {datetime.now()}")
    print(f"{'='*60}\n")

def start_scheduler():
    """启动调度器"""
    print("🚀 T01 策略进化调度器启动")
    print("调度规则: 每周日 20:00 执行")
    
    # 每周日20:00执行
    schedule.every().sunday.at("20:00").do(run_evolution)
    
    # 立即执行一次测试
    print("\n立即执行一次测试...")
    run_evolution()
    
    # 运行调度循环
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n调度器已停止")

if __name__ == '__main__':
    # 确保在正确的工作目录
    os.chdir('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    
    # 启动调度器
    start_scheduler()