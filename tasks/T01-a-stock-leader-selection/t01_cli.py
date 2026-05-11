#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 命令行交互工具
提供交互式命令行界面
"""

import os
import sys
import readline

def print_menu():
    """打印主菜单"""
    print(f"{'='*60}")
    print("T01 选股系统 - 交互工具")
    print(f"{'='*60}")
    print("1. 系统状态管理")
    print("2. 任务执行管理")
    print("3. 策略进化管理")
    print("4. 数据查询与分析")
    print("5. 系统设置")
    print("0. 退出")
    print(f"{'='*60}")

def manage_system_status():
    """系统状态管理"""
    while True:
        print("\n系统状态管理")
        print("-" * 30)
        print("1. 查看系统状态")
        print("2. 启动调度器")
        print("3. 停止调度器")
        print("4. 重启调度器")
        print("5. 检查依赖状态")
        print("0. 返回主菜单")
        print("-" * 30)
        
        choice = input("请输入选择: ")
        
        if choice == "1":
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/scheduler_monitor.py")
        elif choice == "2":
            print("\n启动调度器...")
            result = os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/quick_start.py --only-scheduler")
            if result == 0:
                print("✅ 调度器启动成功")
            else:
                print("❌ 调度器启动失败")
        elif choice == "3":
            print("\n停止调度器...")
            os.system("pkill -f 'main.py.*schedule'")
            print("✅ 调度器已停止")
        elif choice == "4":
            print("\n重启调度器...")
            os.system("pkill -f 'main.py.*schedule'")
            time.sleep(2)
            result = os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/quick_start.py --only-scheduler")
            if result == 0:
                print("✅ 调度器重启成功")
            else:
                print("❌ 调度器重启失败")
        elif choice == "5":
            print("\n检查依赖状态...")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py deps-check")
        elif choice == "0":
            break
        else:
            print("无效选择，请重新输入")

def manage_task_execution():
    """任务执行管理"""
    while True:
        print("\n任务执行管理")
        print("-" * 30)
        print("1. 手动执行T日选股")
        print("2. 手动执行T+1竞价选股")
        print("3. 手动执行结果跟踪")
        print("4. 手动执行市场复盘")
        print("5. 手动执行Unifuncs预热")
        print("6. 查看任务日志")
        print("0. 返回主菜单")
        print("-" * 30)
        
        choice = input("请输入选择: ")
        
        if choice == "1":
            date = input("请输入日期(YYYYMMDD，默认今天): ") or None
            cmd = "python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py t-day"
            if date:
                cmd += f" --date {date}"
            os.system(cmd)
        elif choice == "2":
            date = input("请输入日期(YYYYMMDD，默认今天): ") or None
            cmd = "python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py t1-auction"
            if date:
                cmd += f" --date {date}"
            os.system(cmd)
        elif choice == "3":
            print("\n执行结果跟踪...")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py track")
        elif choice == "4":
            date = input("请输入日期(YYYYMMDD，默认今天): ") or None
            cmd = "python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py market-review"
            if date:
                cmd += f" --date {date}"
            os.system(cmd)
        elif choice == "5":
            date = input("请输入日期(YYYYMMDD，默认今天): ") or None
            cmd = "python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py unifuncs"
            if date:
                cmd += f" --date {date}"
            os.system(cmd)
        elif choice == "6":
            print("\n查看任务日志")
            print("可用任务: t-day, t1-auction, track, evolution, market-review, unifuncs, deps-check")
            task_name = input("请输入任务名称: ")
            if task_name:
                os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/scheduler_monitor.py show-logs --task " + task_name)
        elif choice == "0":
            break
        else:
            print("无效选择，请重新输入")

def manage_strategy_evolution():
    """策略进化管理"""
    while True:
        print("\n策略进化管理")
        print("-" * 30)
        print("1. 手动执行策略进化")
        print("2. 分析进化结果")
        print("3. 部署最佳策略")
        print("4. 查看策略进化历史")
        print("5. 配置进化参数")
        print("0. 返回主菜单")
        print("-" * 30)
        
        choice = input("请输入选择: ")
        
        if choice == "1":
            print("\n执行策略进化...")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/run_evolution.py")
        elif choice == "2":
            print("\n分析进化结果...")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/analyze_evolution_results.py")
        elif choice == "3":
            print("\n部署最佳策略...")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/evolution_deployment.py")
        elif choice == "4":
            print("\n策略进化历史:")
            os.system("ls -lt /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/evolution_results | head -20")
        elif choice == "5":
            print("\n编辑进化配置文件:")
            os.system("nano /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/evolution_config.json")
        elif choice == "0":
            break
        else:
            print("无效选择，请重新输入")

def query_and_analyze_data():
    """数据查询与分析"""
    while True:
        print("\n数据查询与分析")
        print("-" * 30)
        print("1. 查询最新选股结果")
        print("2. 查询历史选股结果")
        print("3. 查询策略回测结果")
        print("4. 查询资金流向数据")
        print("5. 运行高级分析")
        print("0. 返回主菜单")
        print("-" * 30)
        
        choice = input("请输入选择: ")
        
        if choice == "1":
            print("\n最新选股结果:")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py status")
        elif choice == "2":
            date = input("请输入查询日期(YYYYMMDD): ")
            if date:
                print(f"\n{date} 选股结果:")
                # 需要实现历史数据查询功能
                print("功能待实现")
        elif choice == "3":
            print("\n策略回测结果:")
            # 需要实现回测结果查询功能
            print("功能待实现")
        elif choice == "4":
            print("\n资金流向数据:")
            os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/money_flow_analyzer.py --latest")
        elif choice == "5":
            print("\n高级分析选项:")
            print("1. 归因分析")
            print("2. 涨停数据分析")
            print("3. 策略绩效分析")
            sub_choice = input("请输入选择: ")
            if sub_choice == "1":
                os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/attribution_analyzer.py")
            elif sub_choice == "2":
                os.system("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/limit_data_analyzer.py")
            elif sub_choice == "3":
                # 需要实现策略绩效分析功能
                print("功能待实现")
        elif choice == "0":
            break
        else:
            print("无效选择，请重新输入")

def main():
    """主函数"""
    # 确保在正确的工作目录
    os.chdir('/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    
    while True:
        print("\n")
        print_menu()
        
        choice = input("请输入选择: ")
        
        if choice == "1":
            manage_system_status()
        elif choice == "2":
            manage_task_execution()
        elif choice == "3":
            manage_strategy_evolution()
        elif choice == "4":
            query_and_analyze_data()
        elif choice == "5":
            print("\n系统设置:")
            print("功能待实现")
        elif choice == "0":
            print("\n退出系统...")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    import time
    main()