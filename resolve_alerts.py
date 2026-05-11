#!/usr/bin/env python3
"""
清理历史依赖检查失败告警
"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from monitor import Monitor

monitor = Monitor()
alerts = monitor.get_active_alerts()

print(f'当前未解决告警数: {len(alerts)}')
resolved_count = 0

for alert in alerts:
    alert_id = alert['id']
    title = alert['title']
    severity = alert['severity']
    
    print(f"{alert_id} - [{severity}] {title}")
    
    if title == 'T01 依赖检查失败':
        monitor.resolve_alert(alert_id)
        print(f"✅ 已解决告警: {alert_id}")
        resolved_count += 1

print(f"\n已解决 {resolved_count} 个依赖检查失败告警")