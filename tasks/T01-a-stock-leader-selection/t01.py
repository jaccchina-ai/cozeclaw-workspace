#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 快捷命令包装器
"""

import os
import sys
import subprocess

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/scheduler_monitor.py"])
        elif command == "start":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/quick_start.py"])
        elif command == "stop":
            subprocess.run(["pkill", "-f", "main.py.*schedule"])
            print("✅ 调度器已停止")
        elif command == "restart":
            subprocess.run(["pkill", "-f", "main.py.*schedule"])
            time.sleep(2)
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/quick_start.py", "--only-scheduler"])
        elif command == "help" or command == "--help" or command == "-h":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/tools_help.py"])
        elif command == "cli":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/t01_cli.py"])
        elif command == "evolution":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/run_evolution.py"])
        elif command == "t-day":
            date = sys.argv[2] if len(sys.argv) > 2 else None
            cmd = ["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py", "t-day"]
            if date:
                cmd.extend(["--date", date])
            subprocess.run(cmd)
        elif command == "t1-auction":
            date = sys.argv[2] if len(sys.argv) > 2 else None
            cmd = ["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py", "t1-auction"]
            if date:
                cmd.extend(["--date", date])
            subprocess.run(cmd)
        elif command == "track":
            subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py", "track"])
        else:
            print(f"未知命令: {command}")
            print("可用命令: status, start, stop, restart, help, cli, evolution, t-day, t1-auction, track")
            sys.exit(1)
    else:
        # 没有参数，启动交互式命令行
        subprocess.run(["python3", "/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/t01_cli.py"])

if __name__ == '__main__':
    import time
    main()