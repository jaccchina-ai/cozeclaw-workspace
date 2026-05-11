#!/usr/bin/env python3
"""检查因子IC值"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

try:
    from factor_analysis import FactorICMonitor
    monitor = FactorICMonitor()
    ic_values = monitor.get_latest_ic_values()
    print('因子IC值:')
    for factor, ic in ic_values.items():
        print('  {}: {:.4f}'.format(factor, ic))
except ImportError as e:
    print('ImportError:', e)
    print('FactorICMonitor模块不存在，检查factor_analysis.py文件')
except Exception as e:
    print('Error:', e)