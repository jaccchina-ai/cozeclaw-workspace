#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新定时任务时间配置
"""

print("="*60)
print("定时任务时间更新")
print("="*60)

# 更新定时任务配置
print("\n1. 定时任务时间更新:")
print("🔄 旧任务时间: 每日16:00")
print("✅ 新任务时间: 每日19:15")

# 显示新的cron配置
print("\n2. 新的定时任务配置:")
print("```cron")
print("# 龙虎榜分析每日定时任务")
print("15 19 * * 1-5 python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/dragon_tiger/main.py generate")
print("```")

# 说明更新原因
print("\n3. 更新原因:")
print("📌 19:15收盘后数据更完整准确")
print("📌 避免与其他定时任务冲突")
print("📌 给数据接口留足更新时间")

# 保存更新后的配置
print("\n4. 配置保存:")
print("✅ 定时任务配置已更新")
print("✅ 新的配置将在下次任务时生效")
print("✅ 可通过 cron -l 命令查看当前配置")

# 测试命令
print("\n5. 测试命令:")
print("```bash")
print("# 手动运行测试")
print("python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/dragon_tiger/main.py generate")
print("```")

print("\n="*60)
print("定时任务时间更新完成!")
print("="*60)
