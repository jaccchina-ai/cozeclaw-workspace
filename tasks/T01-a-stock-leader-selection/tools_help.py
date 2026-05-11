#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 工具包汇总
"""

import os
import sys
import pkgutil

def show_help():
    """显示帮助信息"""
    print(f"{'='*60}")
    print("T01 选股系统 - 工具包使用指南")
    print(f"{'='*60}")
    
    print("\n📁 核心工具:")
    print("""  ├── main.py               # 主程序入口
  ├── quick_start.py         # 一键启动脚本
  ├── t01_cli.py             # 交互式命令行工具
  ├── scheduler_monitor.py   # 调度器监控工具""")
    
    print("\n🔧 策略进化工具:")
    print("""  ├── evolution.py          # 进化核心算法
  ├── evolution_scheduler.py # 进化调度器
  ├── analyze_evolution_results.py  # 进化结果分析
  ├── evolution_deployment.py      # 进化策略部署
  ├── run_evolution.py       # 进化任务一键执行""")
    
    print("\n📊 数据分析工具:")
    print("""  ├── attribution_analyzer.py    # 归因分析工具
  ├── limit_data_analyzer.py       # 涨停数据分析工具
  ├── money_flow_analyzer.py       # 资金流向分析工具""")
    
    print("\n⚙️ 配置文件:")
    print("""  ├── evolution_config.json      # 进化配置文件
  ├── strategy/config/factor_weights.json  # 因子权重配置""")
    
    print("\n📁 目录结构:")
    print("""  ├── logs/                 # 日志文件目录
  ├── evolution_results/     # 进化结果目录
  ├── weight_backups/        # 权重备份目录
  ├── database/              # 数据库模块""")
    
    print("\n💡 使用示例:")
    print("""  # 一键启动系统
  python3 quick_start.py
  
  # 启动交互式命令行
  python3 t01_cli.py
  
  # 查看系统状态
  python3 scheduler_monitor.py
  
  # 执行策略进化
  python3 run_evolution.py
  
  # 手动执行T日选股
  python3 main.py t-day --date 20260423
  
  # 查看任务日志
  python3 scheduler_monitor.py show-logs --task t-day""")
    
    print("\n⌚ 定时任务:")
    print("""  ├── 09:00    依赖检查 (deps-check)
  ├── 09:27    T+1竞价选股 (t1-auction)
  ├── 16:10    结果跟踪 (track)
  ├── 19:30    Unifuncs预热 (unifuncs)
  ├── 20:00    T日选股 (t-day)
  ├── 21:00    市场复盘 (market-review)
  ├── 周日20:00  策略进化 (evolution)""")
    
    print(f"\n{'='*60}")
    print("💡 快捷命令:")
    print("""  $ t01                  # 启动交互式命令行
  $ t01 help             # 显示帮助信息
  $ t01 status           # 查看系统状态
  $ t01 start            # 启动系统
  $ t01 stop             # 停止系统
  $ t01 restart          # 重启系统
  $ t01 evolution        # 执行策略进化
  $ t01 t-day [date]     # 手动执行T日选股
  $ t01 t1-auction [date]# 手动执行T+1竞价选股
  $ t01 track            # 手动执行结果跟踪""")
    
    print(f"{'='*60}")

if __name__ == '__main__':
    show_help()