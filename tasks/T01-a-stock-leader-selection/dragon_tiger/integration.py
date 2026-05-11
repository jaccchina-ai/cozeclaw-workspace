#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜模块与选股系统的集成接口
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragon_tiger.api import DragonTigerAPI

import logging

logger = logging.getLogger(__name__)

class DragonTigerIntegration:
    """龙虎榜模块集成接口"""
    
    def __init__(self):
        self.api = DragonTigerAPI()
    
    def get_dragon_tiger_score(self, stock_data: dict) -> float:
        """
        获取龙虎榜因子分数，用于选股系统
        :param stock_data: 股票数据字典，需包含'ts_code'字段
        :return: 龙虎榜因子分数（0-100）
        """
        try:
            ts_code = stock_data.get('ts_code')
            if not ts_code:
                return 0.0
            
            result = self.api.get_dragon_tiger_factor(ts_code)
            if result['status'] == 'success':
                return result.get('dragon_tiger_score', 0.0)
            
            return 0.0
        except Exception as e:
            logger.error(f"获取龙虎榜因子失败: {e}")
            return 0.0
    
    def filter_by_dragon_tiger(self, stock_list: list, threshold: float = 50) -> list:
        """
        根据龙虎榜因子筛选股票
        :param stock_list: 股票列表，每个元素是包含'ts_code'的字典
        :param threshold: 因子分数阈值
        :return: 筛选后的股票列表，添加'dragon_tiger_score'字段
        """
        try:
            filtered = []
            for stock in stock_list:
                score = self.get_dragon_tiger_score(stock)
                stock['dragon_tiger_score'] = score
                
                if score >= threshold:
                    filtered.append(stock)
            
            logger.info(f"龙虎榜因子筛选完成，筛选前{len(stock_list)}只，筛选后{len(filtered)}只，阈值{threshold}")
            return filtered
        except Exception as e:
            logger.error(f"龙虎榜因子筛选失败: {e}")
            return stock_list
    
    def get_hot_stocks_for_selection(self) -> list:
        """
        获取适合选股的热门股票列表
        :return: 热门股票列表，包含选股所需字段
        """
        try:
            result = self.api.get_hot_stocks(limit=20)
            
            if result['status'] != 'success':
                return []
            
            hot_stocks = []
            for stock in result['hot_stocks']:
                hot_stocks.append({
                    'ts_code': stock['ts_code'],
                    'name': stock['name'],
                    'dragon_tiger_score': 90 if stock.get('has_institutional_buy') else 80,
                    'net_buy': stock['net_buy'],
                    'pct_change': stock['pct_change'],
                    'reason': stock.get('reason', '')
                })
            
            return hot_stocks
        except Exception as e:
            logger.error(f"获取选股用热门股票失败: {e}")
            return []
    
    def update_stock_selection_factors(self, stock_list: list) -> list:
        """
        更新股票列表中的龙虎榜因子
        :param stock_list: 股票列表
        :return: 更新后的股票列表
        """
        try:
            for stock in stock_list:
                score = self.get_dragon_tiger_score(stock)
                stock['dragon_tiger_score'] = score
            
            return stock_list
        except Exception as e:
            logger.error(f"更新龙虎榜因子失败: {e}")
            return stock_list


# 测试集成接口
if __name__ == '__main__':
    integration = DragonTigerIntegration()
    
    # 测试获取单只股票的龙虎榜因子
    stock_data = {'ts_code': '000001.SZ'}
    score = integration.get_dragon_tiger_score(stock_data)
    print(f"{stock_data['ts_code']} 龙虎榜因子分数: {score}")
    
    # 测试批量筛选
    test_stocks = [
        {'ts_code': '000001.SZ', 'name': '平安银行'},
        {'ts_code': '000002.SZ', 'name': '万科A'},
        {'ts_code': '600000.SH', 'name': '浦发银行'}
    ]
    
    filtered = integration.filter_by_dragon_tiger(test_stocks, threshold=0)
    print("\n筛选后的股票:")
    for stock in filtered:
        print(f"{stock['ts_code']} {stock['name']}: {stock['dragon_tiger_score']}")
    
    # 测试获取热门股票
    hot_stocks = integration.get_hot_stocks_for_selection()
    print("\n热门股票:")
    for stock in hot_stocks[:5]:
        print(f"{stock['ts_code']} {stock['name']}: {stock['dragon_tiger_score']}")
