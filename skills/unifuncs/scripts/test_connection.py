#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unifuncs API 连接测试脚本
"""

import sys
sys.path.insert(0, '/workspace/projects/workspace/skills/unifuncs/scripts')

from unifuncs_client import UnifuncsClient

print("=" * 60)
print("Unifuncs Deep Research API 连接测试")
print("=" * 60)

try:
    # 创建客户端
    client = UnifuncsClient()
    print(f"\n[1] 客户端初始化成功")
    print(f"    Base URL: {client.base_url}")
    print(f"    API Key: {client.api_key[:20]}...")
    
    # 创建任务
    print(f"\n[2] 创建测试任务...")
    task_id = client.create_task(
        "今天A股热门板块哪几个？所有涨停股中，哪3个涨停股在下一个交易日继续涨停的概率最大？"
    )
    print(f"    任务ID: {task_id}")
    
    # 查询任务状态
    print(f"\n[3] 查询任务状态...")
    result = client.query_task(task_id)
    print(f"    状态: {result.status}")
    
    print(f"\n[测试结果] API 连接正常 ✓")
    print(f"任务已创建，状态为: {result.status}")
    print(f"可以使用 task_id: {task_id} 继续轮询结果")
    
except Exception as e:
    print(f"\n[测试结果] API 连接失败 ✗")
    print(f"错误信息: {e}")

print("\n" + "=" * 60)
