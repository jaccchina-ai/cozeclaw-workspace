import sys
import os
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from monitor import Monitor

monitor = Monitor()
alerts = monitor.get_active_alerts()

print(f"Found {len(alerts)} active alerts")

if alerts:
    alert = alerts[0]
    print(f"Resolving alert {alert['id']}...")
    monitor.resolve_alert(alert['id'])
    
    alerts = monitor.get_active_alerts()
    print(f"Now {len(alerts)} active alerts remaining")
else:
    print("No active alerts")