#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜模块API封装
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragon_tiger.analyzer import DragonTigerAnalyzer
from database.models import get_session
from dragon_tiger.models import DragonTigerRecord
import json
from datetime import datetime

class DragonTigerAPI:
    """龙虎榜模块API接口"""
    
    def __init__(self):
        self.analyzer = DragonTigerAnalyzer()
    
    def get_latest_analysis(self) -> dict:
        """
        获取最新龙虎榜分析结果
        :return: 分析结果
        """
        try:
            session = get_session()
            
            # 获取最新的龙虎榜记录
            record = session.query(DragonTigerRecord).order_by(
                DragonTigerRecord.trade_date.desc()
            ).first()
            
            if not record:
                return {'status': 'error', 'message': '无龙虎榜分析记录'}
            
            result = {
                'trade_date': record.trade_date,
                'total_buy': record.total_buy,
                'total_sell': record.total_sell,
                'net_buy': record.net_buy,
                'hot_stocks': json.loads(record.hot_stocks) if record.hot_stocks else [],
                'seat_stats': json.loads(record.seat_stats) if record.seat_stats else [],
                'stock_stats': json.loads(record.stock_stats) if record.stock_stats else [],
                'status': 'success'
            }
            
            session.close()
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def generate_analysis(self, trade_date: str = None) -> dict:
        """
        生成指定交易日的龙虎榜分析报告
        :param trade_date: 交易日，格式YYYYMMDD
        :return: 分析结果
        """
        try:
            report = self.analyzer.generate_analysis_report(trade_date)
            return report
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_dragon_tiger_factor(self, ts_code: str, trade_date: str = None) -> dict:
        """
        获取股票的龙虎榜因子分数
        :param ts_code: 股票代码
        :param trade_date: 交易日
        :return: 因子分数
        """
        try:
            score = self.analyzer.get_dragon_tiger_factor(ts_code, trade_date)
            return {
                'ts_code': ts_code,
                'dragon_tiger_score': score,
                'status': 'success'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_hot_stocks(self, trade_date: str = None, limit: int = 10) -> dict:
        """
        获取热门股票列表
        :param trade_date: 交易日
        :param limit: 返回数量限制
        :return: 热门股票列表
        """
        try:
            if trade_date:
                report = self.analyzer.generate_analysis_report(trade_date)
            else:
                report = self.get_latest_analysis()
            
            if report['status'] != 'success':
                return report
            
            hot_stocks = report.get('hot_stocks', [])[:limit]
            
            return {
                'trade_date': report.get('trade_date'),
                'hot_stocks': hot_stocks,
                'total_count': len(hot_stocks),
                'status': 'success'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_capital_flow(self, trade_date: str = None) -> dict:
        """
        获取资金流向数据
        :param trade_date: 交易日
        :return: 资金流向数据
        """
        try:
            if trade_date:
                report = self.analyzer.generate_analysis_report(trade_date)
            else:
                report = self.get_latest_analysis()
            
            if report['status'] != 'success':
                return report
            
            capital_flow = report.get('capital_flow', {})
            
            return {
                'trade_date': report.get('trade_date'),
                'capital_flow': capital_flow,
                'status': 'success'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# 测试API
if __name__ == '__main__':
    api = DragonTigerAPI()
    
    # 测试生成最新分析
    print("1. 生成最新龙虎榜分析...")
    result = api.generate_analysis()
    print(f"状态: {result['status']}")
    if result['status'] == 'success':
        print(f"交易日: {result['trade_date']}")
        print(f"资金净流入: {result['capital_flow']['net_buy']}亿元")
    
    # 测试获取热门股票
    print("\n2. 获取热门股票...")
    hot_stocks = api.get_hot_stocks(limit=5)
    if hot_stocks['status'] == 'success':
        for stock in hot_stocks['hot_stocks']:
            print(f"{stock['ts_code']} {stock['name']}: 净流入{stock['net_buy']}亿元")
    
    # 测试获取龙虎榜因子
    print("\n3. 获取龙虎榜因子...")
    factor = api.get_dragon_tiger_factor('000001.SZ')
    print(f"中国平安龙虎榜因子: {factor.get('dragon_tiger_score', 0)}")
