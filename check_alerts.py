#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from monitor import Monitor

def main():
    monitor = Monitor()
    alerts = monitor.get_active_alerts()
    
    print("\n=== 活跃告警详情 ===")
    for alert in alerts:
        print(f"\nID: {alert['id']}")
        print(f"类型: {alert['alert_type']}")
        print(f"级别: {alert['severity']}")
        print(f"标题: {alert['title']}")
        print(f"消息: {alert['message']}")
        print(f"日期: {alert['trade_date']}")
        print(f"创建时间: {alert['created_at']}")

if __name__ == '__main__':
    main()