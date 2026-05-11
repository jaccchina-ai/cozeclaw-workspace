#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
妙想资讯搜索 Skill 测试脚本
"""

import sys
import os

# 添加脚本路径
sys.path.insert(0, os.path.dirname(__file__))

from mx_search_client import MxSearchClient, MxSearchError


def test_mx_search():
    """测试妙想资讯搜索功能"""
    print("="*60)
    print("妙想资讯搜索 Skill 测试")
    print("="*60)
    
    # 检查 API Key
    api_key = os.environ.get('MX_APIKEY', '')
    if not api_key:
        print("\n⚠️ 未配置 MX_APIKEY 环境变量")
        print("请先设置环境变量: export MX_APIKEY='your_api_key'")
        print("\n测试跳过（API Key 未配置）")
        return
    
    print(f"\n✅ API Key 已配置")
    
    # 初始化客户端
    client = MxSearchClient()
    
    # 测试搜索
    test_queries = [
        "格力电器最新研报",
        "贵州茅台机构观点",
        "今日大盘异动原因"
    ]
    
    print("\n开始测试搜索...")
    for query in test_queries:
        print(f"\n测试查询: {query}")
        try:
            result = client.search(query)
            
            # 解析结果
            items = result.get('results', [])
            print(f"  ✅ 找到 {len(items)} 条结果")
            
            if items:
                # 显示第一条结果
                first = items[0]
                print(f"  ✅ 第一条: {first.get('title')}")
                print(f"     日期: {first.get('date')}")
                print(f"     机构: {first.get('insName')}")
                if first.get('rating'):
                    print(f"     评级: {first.get('rating')}")
                
        except MxSearchError as e:
            print(f"  ❌ 搜索失败: {e.message}")
        except Exception as e:
            print(f"  ❌ 未知错误: {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == '__main__':
    test_mx_search()
