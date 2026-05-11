#!/usr/bin/env python3
"""重启T01-T1-Auction任务"""
import subprocess
import json

def main():
    # 获取任务列表
    result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True)
    
    # 查找T01-T1-Auction任务
    for line in result.stdout.split('\n'):
        if 'T01-T1-Auction' in line:
            parts = line.split()
            task_id = parts[0]
            print(f"找到T01-T1-Auction任务: {task_id}")
            
            # 重启任务
            print("正在重启任务...")
            result = subprocess.run(['openclaw', 'cron', 'restart', task_id], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 任务重启成功")
            else:
                print(f"❌ 任务重启失败: {result.stderr}")
            
            return
    
    print("❌ 未找到T01-T1-Auction任务")

if __name__ == "__main__":
    main()