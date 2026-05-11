#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 快速启动脚本
一键启动所有服务
"""

import os
import sys
import subprocess
import time
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='T01 选股系统快速启动')
    parser.add_argument('--only-scheduler', action='store_true', help='只启动调度器')
    parser.add_argument('--test-mode', action='store_true', help='测试模式')
    parser.add_argument('--no-check', action='store_true', help='不检查依赖')
    return parser.parse_args()

def start_scheduler():
    """启动调度器"""
    print("\n🚀 启动选股系统调度器...")
    
    # 检查是否已有调度器运行
    try:
        result = subprocess.run(['pgrep', '-f', 'main.py.*schedule'], capture_output=True, text=True)
        pid = result.stdout.strip()
        if pid:
            print(f"⚠️ 已有调度器运行 (PID: {pid})")
            print("⏳ 先停止现有调度器...")
            subprocess.run(['pkill', '-f', 'main.py.*schedule'], capture_output=True)
            time.sleep(3)
    except:
        pass
    
    # 启动新的调度器
    cmd = 'nohup python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py schedule > /dev/null 2>&1 &'
    subprocess.run(cmd, shell=True)
    
    print("✅ 调度器已启动")

def check_scheduler_status():
    """检查调度器状态"""
    print("\n📋 检查调度器状态...")
    
    # 等待调度器启动
    time.sleep(2)
    
    try:
        result = subprocess.run(['pgrep', '-f', 'main.py.*schedule'], capture_output=True, text=True)
        if result.stdout.strip():
            print("✅ 调度器运行正常")
            return True
        else:
            print("❌ 调度器启动失败")
            return False
    except:
        print("❌ 无法检查调度器状态")
        return False

def run_deps_check():
    """运行依赖检查"""
    print("\n🔍 运行依赖检查...")
    
    # 跳过复杂的依赖检查，只检查基础依赖
    try:
        import pandas
        import numpy
        import sqlalchemy
        import schedule
        import tushare
        import deap
        print("✅ 基础依赖检查通过")
        print("""  ├── pandas
  ├── numpy
  ├── sqlalchemy
  ├── schedule
  ├── tushare
  ├── deap""")
        return True
    except ImportError as e:
        print(f"❌ 基础依赖检查失败: {e}")
        return False

def show_scheduler_status():
    """显示调度器状态"""
    print("\n📊 显示调度器详情...")
    
    subprocess.run(['python3', '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/scheduler_monitor.py'])

def test_mode():
    """测试模式"""
    print("\n🧪 测试模式运行...")
    
    # 运行模拟测试
    result = subprocess.run(
        ['python3', '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py', 'test'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print("❌ 测试失败:")
        print(result.stderr)

def main():
    """主函数"""
    args = parse_args()
    
    print(f"{'='*60}")
    print("🎯 T01 选股系统一键启动")
    print(f"{'='*60}")
    
    # 确保在正确的工作目录
    os.chdir('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    
    try:
        # 1. 启动调度器
        start_scheduler()
        
        # 2. 检查调度器状态
        if not check_scheduler_status():
            print("\n❌ 启动失败")
            sys.exit(1)
        
        # 3. 运行依赖检查
        if not args.no_check and not args.only_scheduler:
            run_deps_check()
        
        # 4. 测试模式
        if args.test_mode:
            test_mode()
        
        print(f"\n{'='*60}")
        print("✅ T01 选股系统启动完成")
        print(f"{'='*60}")
        print("📅 定时任务计划:")
        print("  - 09:00    🛠️  依赖检查")
        print("  - 09:27    📈  T+1竞价选股")
        print("  - 16:10    📊  结果跟踪")
        print("  - 19:30    🤖  Unifuncs预热")
        print("  - 20:00    🎯  T日选股")
        print("  - 21:00    📝  市场复盘")
        print("  - 周日20:00  🔄  策略进化")
        print(f"\n💡 快速命令:")
        print("  $ t01                  # 启动交互式命令行")
        print("  $ t01 help             # 显示帮助信息")
        print("  $ t01 status           # 查看系统状态")
        print("  $ t01 start            # 启动系统")
        print("  $ t01 stop             # 停止系统")
        print("  $ t01 restart          # 重启系统")
        print("  $ t01 evolution        # 执行策略进化")
        print(f"\n📁 核心工具:")
        print("  ├── main.py               # 主程序入口")
        print("  ├── quick_start.py         # 一键启动脚本")
        print("  ├── t01_cli.py             # 交互式命令行工具")
        print("  ├── scheduler_monitor.py   # 调度器监控工具")
        print(f"\n⚠️ 注意:")
        print("  - 调度器已在后台启动")
        print("  - 使用 't01 status' 查看运行状态")
        print("  - 使用 't01 stop' 停止调度器")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ 启动过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()