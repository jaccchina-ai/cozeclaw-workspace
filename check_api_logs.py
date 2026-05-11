#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from monitor import Monitor

def main():
    monitor = Monitor()
    
    # 查看 Monitor 类的所有方法
    print("Monitor 类可用方法:")
    print([method for method in dir(monitor) if not method.startswith('_')])
    
    # 尝试获取API统计
    stats = monitor.get_api_stats(days=1)
    print("\nAPI统计:")
    print(stats)

if __name__ == '__main__':
    main()