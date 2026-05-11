#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜深度数据解析模块测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from dragon_tiger.analyzer import DragonTigerAnalyzer
from dragon_tiger.api import DragonTigerAPI

class TestDragonTigerAnalyzer(unittest.TestCase):
    """龙虎榜分析器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.analyzer = DragonTigerAnalyzer()
    
    def test_analyze_seat_type(self):
        """测试席位类型分析"""
        # 测试机构席位
        seat_type = self.analyzer.analyze_seat_type('机构专用')
        self.assertEqual(seat_type, '机构')
        
        # 测试游资席位
        seat_type = self.analyzer.analyze_seat_type('西藏东方财富证券股份有限公司拉萨团结路第二证券营业部')
        self.assertEqual(seat_type, '游资')
        
        # 测试北向资金
        seat_type = self.analyzer.analyze_seat_type('沪股通专用')
        self.assertEqual(seat_type, '北向')
        
        # 测试普通席位
        seat_type = self.analyzer.analyze_seat_type('中信证券股份有限公司北京望京证券营业部')
        self.assertEqual(seat_type, '普通')
    
    def test_seat_name_matching(self):
        """测试席位名称匹配"""
        # 测试部分匹配
        seat_type = self.analyzer.analyze_seat_type('东方财富证券拉萨团结路第二')
        self.assertEqual(seat_type, '游资')
        
        # 测试大小写不敏感
        seat_type = self.analyzer.analyze_seat_type('西藏东方财富证券股份有限公司拉萨团结路第二证券营业部')
        self.assertEqual(seat_type, '游资')

class TestDragonTigerAPI(unittest.TestCase):
    """龙虎榜API测试"""
    
    def setUp(self):
        """测试前准备"""
        self.api = DragonTigerAPI()
    
    def test_get_dragon_tiger_factor(self):
        """测试获取龙虎榜因子"""
        result = self.api.get_dragon_tiger_factor('000001.SZ')
        self.assertEqual(result['status'], 'success')
        self.assertIn('dragon_tiger_score', result)
        self.assertGreaterEqual(result['dragon_tiger_score'], 0)
        self.assertLessEqual(result['dragon_tiger_score'], 100)
    
    def test_get_latest_analysis(self):
        """测试获取最新分析"""
        result = self.api.get_latest_analysis()
        # 如果没有数据，应该返回错误状态
        if result['status'] == 'error':
            self.assertIn('message', result)
        else:
            self.assertEqual(result['status'], 'success')
            self.assertIn('trade_date', result)
            self.assertIn('capital_flow', result)

class TestDragonTigerIntegration(unittest.TestCase):
    """龙虎榜集成测试"""
    
    def test_stock_list_filtering(self):
        """测试股票列表筛选"""
        from dragon_tiger.integration import DragonTigerIntegration
        
        integration = DragonTigerIntegration()
        test_stocks = [
            {'ts_code': '000001.SZ', 'name': '平安银行'},
            {'ts_code': '000002.SZ', 'name': '万科A'},
            {'ts_code': '600000.SH', 'name': '浦发银行'}
        ]
        
        filtered = integration.filter_by_dragon_tiger(test_stocks, threshold=0)
        self.assertEqual(len(filtered), len(test_stocks))
        for stock in filtered:
            self.assertIn('dragon_tiger_score', stock)
            self.assertGreaterEqual(stock['dragon_tiger_score'], 0)

def run_performance_test():
    """运行性能测试"""
    import time
    
    analyzer = DragonTigerAnalyzer()
    
    # 测试席位类型分析性能
    test_seats = [
        '机构专用',
        '西藏东方财富证券股份有限公司拉萨团结路第二证券营业部',
        '沪股通专用',
        '中信证券股份有限公司北京望京证券营业部',
        '华泰证券股份有限公司深圳益田路荣超商务中心证券营业部'
    ]
    
    start_time = time.time()
    for _ in range(1000):
        for seat in test_seats:
            analyzer.analyze_seat_type(seat)
    
    elapsed = time.time() - start_time
    print(f"席位类型分析性能测试: 5000次请求耗时{elapsed:.3f}秒，平均每次{elapsed/5000*1000:.3f}毫秒")

if __name__ == '__main__':
    # 运行单元测试
    print("运行单元测试...")
    unittest.main(exit=False)
    
    # 运行性能测试
    print("\n运行性能测试...")
    run_performance_test()
    
    print("\n测试完成!")
