#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜深度数据解析模块
功能：
1. 获取龙虎榜数据
2. 解析席位信息，识别游资、机构等
3. 分析资金流向
4. 生成龙虎榜分析报告
5. 提供龙虎榜因子接口
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
from dragon_tiger.analyzer import DragonTigerAnalyzer
from dragon_tiger.api import DragonTigerAPI

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dragon_tiger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='龙虎榜深度数据解析模块')
    parser.add_argument('action', choices=['generate', 'get-report', 'get-factor', 'hot-stocks', 'capital-flow'],
                      help='操作类型')
    parser.add_argument('--date', help='交易日，格式YYYYMMDD')
    parser.add_argument('--ts-code', help='股票代码，如000001.SZ')
    parser.add_argument('--limit', type=int, default=10, help='返回数量限制')
    
    args = parser.parse_args()
    
    if args.action == 'generate':
        """生成龙虎榜分析报告"""
        analyzer = DragonTigerAnalyzer()
        report = analyzer.generate_analysis_report(args.date)
        
        if report['status'] == 'success':
            logger.info("龙虎榜分析报告生成成功")
            logger.info(f"交易日: {report['trade_date']}")
            logger.info(f"上榜股票数: {report['total_stocks']}")
            logger.info(f"资金净流入: {report['capital_flow']['net_buy']}亿元")
            logger.info(f"热门股票数: {len(report['hot_stocks'])}")
        else:
            logger.error(f"龙虎榜分析报告生成失败: {report.get('message', '未知错误')}")
    
    elif args.action == 'get-report':
        """获取龙虎榜分析报告"""
        api = DragonTigerAPI()
        if args.date:
            report = api.generate_analysis(args.date)
        else:
            report = api.get_latest_analysis()
        
        if report['status'] == 'success':
            print("龙虎榜分析报告:")
            print(f"交易日: {report['trade_date']}")
            print(f"资金净流入: {report['capital_flow']['net_buy']}亿元")
            print(f"上榜股票数: {report['total_stocks']}")
            print(f"热门股票数: {len(report['hot_stocks'])}")
            
            if report['hot_stocks']:
                print("\n热门股票:")
                for i, stock in enumerate(report['hot_stocks'][:5], 1):
                    print(f"{i}. {stock['ts_code']} {stock['name']}: 净流入{stock['net_buy']}亿元，涨幅{stock['pct_change']}%")
        else:
            print(f"获取报告失败: {report.get('message', '未知错误')}")
    
    elif args.action == 'get-factor':
        """获取龙虎榜因子"""
        if not args.ts_code:
            print("请提供股票代码参数 --ts-code")
            return
        
        api = DragonTigerAPI()
        result = api.get_dragon_tiger_factor(args.ts_code, args.date)
        
        if result['status'] == 'success':
            print(f"{args.ts_code} 龙虎榜因子分数: {result['dragon_tiger_score']}")
        else:
            print(f"获取因子失败: {result.get('message', '未知错误')}")
    
    elif args.action == 'hot-stocks':
        """获取热门股票"""
        api = DragonTigerAPI()
        result = api.get_hot_stocks(args.date, args.limit)
        
        if result['status'] == 'success':
            print(f"{result['trade_date']} 热门股票:")
            for i, stock in enumerate(result['hot_stocks'], 1):
                print(f"{i}. {stock['ts_code']} {stock['name']}")
                print(f"   净流入: {stock['net_buy']}亿元，涨幅: {stock['pct_change']}%")
                if stock.get('has_institutional_buy'):
                    print("   ✅ 有机构买入")
        else:
            print(f"获取热门股票失败: {result.get('message', '未知错误')}")
    
    elif args.action == 'capital-flow':
        """获取资金流向"""
        api = DragonTigerAPI()
        result = api.get_capital_flow(args.date)
        
        if result['status'] == 'success':
            flow = result['capital_flow']
            print(f"{result['trade_date']} 资金流向:")
            print(f"总买入: {flow['total_buy']}亿元")
            print(f"总卖出: {flow['total_sell']}亿元")
            print(f"净流入: {flow['net_buy']}亿元")
            
            if flow['seat_stats']:
                print("\n席位类型统计:")
                for stat in flow['seat_stats']:
                    print(f"{stat['seat_type']}: 买入{stat['buy_amount']}亿元，卖出{stat['sell_amount']}亿元，净额{stat['net_buy']}亿元")
        else:
            print(f"获取资金流向失败: {result.get('message', '未知错误')}")


if __name__ == '__main__':
    main()
