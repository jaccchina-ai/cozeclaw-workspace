#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 进化任务一键执行脚本
"""

import os
import sys
import subprocess
import traceback
from datetime import datetime

def run_evolution_task():
    """运行进化任务"""
    print(f"{'='*60}")
    print(f"T01 策略进化任务一键执行")
    print(f"时间: {datetime.now()}")
    print(f"{'='*60}")
    
    # 确保在正确的工作目录
    os.chdir('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    
    try:
        # 1. 运行进化任务
        print("\n1. 运行策略进化...")
        result = subprocess.run(
            ['python3', 'evolution.py'],
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.returncode != 0:
            print("❌ 策略进化任务失败")
            print(result.stderr)
            return False
        
        print("✅ 策略进化任务完成")
        
        # 2. 分析进化结果
        print("\n2. 分析进化结果...")
        result = subprocess.run(
            ['python3', 'analyze_evolution_results.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print("❌ 进化结果分析失败")
            print(result.stderr)
            return False
        
        print("✅ 进化结果分析完成")
        
        # 3. 自动部署最佳策略
        print("\n3. 自动部署最佳策略...")
        result = subprocess.run(
            ['python3', 'evolution_deployment.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print("❌ 自动部署失败")
            print(result.stderr)
            return False
        
        print("✅ 最佳策略已部署")
        
        print(f"\n{'='*60}")
        print(f"✅ 策略进化任务全部完成")
        print(f"{'='*60}")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ 任务超时")
        return False
    except Exception as e:
        print(f"❌ 任务异常: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_evolution_task()
    sys.exit(0 if success else 1)