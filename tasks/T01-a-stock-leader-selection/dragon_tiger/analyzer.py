#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜深度数据解析模块
功能：获取龙虎榜数据，解析席位信息，分析资金流向，生成分析报告
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import tushare as ts
from database.models import get_session
from dragon_tiger.models import DragonTigerRecord, DragonTigerDetail
from fetcher import DataFetcher
import logging

logger = logging.getLogger(__name__)

class DragonTigerAnalyzer:
    """龙虎榜深度分析器"""
    
    def __init__(self, fetcher: Optional[DataFetcher] = None):
        self.fetcher = fetcher or DataFetcher()
        self.ts_api = ts.pro_api()
        self.session = get_session()
        
        # 游资席位数组
        self.hot_money_seats = [
            '西藏东方财富证券股份有限公司拉萨团结路第二证券营业部',
            '西藏东方财富证券股份有限公司拉萨东环路第一证券营业部',
            '西藏东方财富证券股份有限公司拉萨团结路第一证券营业部',
            '西藏东方财富证券股份有限公司拉萨东环路第二证券营业部',
            '国泰君安证券股份有限公司上海江苏路证券营业部',
            '中国国际金融股份有限公司上海分公司',
            '中信证券股份有限公司上海溧阳路证券营业部',
            '华泰证券股份有限公司深圳益田路荣超商务中心证券营业部',
            '招商证券股份有限公司深圳招商证券大厦证券营业部',
            '兴业证券股份有限公司陕西分公司',
            '华鑫证券有限责任公司上海分公司',
            '华泰证券股份有限公司无锡金融一街证券营业部',
            '光大证券股份有限公司宁波解放南路证券营业部',
            '财通证券股份有限公司杭州上塘路证券营业部',
            '东吴证券股份有限公司苏州西北街证券营业部'
        ]
    
    def get_dragon_tiger_data(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜数据
        :param trade_date: 交易日，格式YYYYMMDD，默认前一交易日
        :return: 龙虎榜数据DataFrame
        """
        if not trade_date:
            trade_date = self.fetcher.get_previous_trade_date()
        
        try:
            # 获取龙虎榜列表
            df = self.ts_api.top_list(trade_date=trade_date)
            if df.empty:
                logger.warning(f"{trade_date} 龙虎榜数据为空")
                return pd.DataFrame()
            
            # 获取龙虎榜详情
            detail_df = self.ts_api.top_detail(trade_date=trade_date)
            
            # 合并数据
            result = df.merge(detail_df, on=['trade_date', 'ts_code'], how='left')
            return result
        except Exception as e:
            logger.error(f"获取龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    def analyze_seat_type(self, seat_name: str) -> str:
        """
        分析席位类型
        :param seat_name: 席位名称
        :return: 席位类型: 游资/机构/北向/普通
        """
        seat_name = seat_name.lower()
        
        # 识别游资席位
        for hot_seat in self.hot_money_seats:
            if hot_seat.lower() in seat_name:
                return '游资'
        
        # 识别机构席位
        if '机构专用' in seat_name or '机构席位' in seat_name:
            return '机构'
        
        # 识别北向资金
        if '沪股通' in seat_name or '深股通' in seat_name or '北向资金' in seat_name:
            return '北向'
        
        return '普通'
    
    def analyze_capital_flow(self, df: pd.DataFrame) -> Dict:
        """
        分析龙虎榜资金流向
        :param df: 龙虎榜数据
        :return: 资金流向分析结果
        """
        if df.empty:
            return {}
        
        # 总体资金流向
        total_buy = df['buy_amount'].sum() / 100000000  # 转换为亿元
        total_sell = df['sell_amount'].sum() / 100000000
        net_buy = total_buy - total_sell
        
        # 按席位类型统计
        df['seat_type'] = df['broker'].apply(self.analyze_seat_type)
        seat_stats = df.groupby('seat_type').agg({
            'buy_amount': 'sum',
            'sell_amount': 'sum',
            'ts_code': 'count'
        }).reset_index()
        
        seat_stats['buy_amount'] = seat_stats['buy_amount'] / 100000000
        seat_stats['sell_amount'] = seat_stats['sell_amount'] / 100000000
        seat_stats['net_buy'] = seat_stats['buy_amount'] - seat_stats['sell_amount']
        seat_stats.columns = ['seat_type', 'buy_amount', 'sell_amount', 'stock_count', 'net_buy']
        
        # 按股票统计
        stock_stats = df.groupby(['ts_code', 'name']).agg({
            'buy_amount': 'sum',
            'sell_amount': 'sum',
            'pct_change': 'first'
        }).reset_index()
        
        stock_stats['net_buy'] = stock_stats['buy_amount'] - stock_stats['sell_amount']
        stock_stats['buy_amount'] = stock_stats['buy_amount'] / 100000000
        stock_stats['sell_amount'] = stock_stats['sell_amount'] / 100000000
        stock_stats['net_buy'] = stock_stats['net_buy'] / 100000000
        stock_stats = stock_stats.sort_values('net_buy', ascending=False)
        
        return {
            'total_buy': round(total_buy, 2),
            'total_sell': round(total_sell, 2),
            'net_buy': round(net_buy, 2),
            'seat_stats': seat_stats.to_dict('records'),
            'stock_stats': stock_stats.to_dict('records')[:10]  # 取前10
        }
    
    def identify_hot_stocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        识别热门股票
        :param df: 龙虎榜数据
        :return: 热门股票列表
        """
        if df.empty:
            return []
        
        # 筛选条件：资金净额>1亿，涨幅>5%，机构买入
        df['net_buy'] = df['buy_amount'] - df['sell_amount']
        df['net_buy_100m'] = df['net_buy'] / 100000000
        
        # 识别机构买入的股票
        df['is_buy'] = df['buy_amount'] > df['sell_amount']
        df['is_institutional'] = df['broker'].apply(lambda x: '机构专用' in x)
        
        # 筛选热门股票
        hot_stocks = df[(
            (df['net_buy_100m'] > 1) & 
            (df['pct_change'] > 5) & 
            df['is_buy']
        )].sort_values('net_buy_100m', ascending=False)
        
        # 去重
        hot_stocks = hot_stocks.drop_duplicates(['ts_code', 'name'])
        
        result = []
        for _, row in hot_stocks.iterrows():
            result.append({
                'ts_code': row['ts_code'],
                'name': row['name'],
                'net_buy': round(row['net_buy_100m'], 2),
                'pct_change': round(row['pct_change'], 2),
                'reason': row['reason'],
                'has_institutional_buy': any(df[(df['ts_code'] == row['ts_code']) & df['is_institutional']]['is_buy'])
            })
        
        return result
    
    def save_to_database(self, trade_date: str, analysis_result: Dict):
        """
        保存分析结果到数据库
        :param trade_date: 交易日
        :param analysis_result: 分析结果
        """
        try:
            # 检查是否已存在记录
            existing = self.session.query(DragonTigerRecord).filter_by(
                trade_date=trade_date
            ).first()
            
            if existing:
                self.session.delete(existing)
                self.session.commit()
            
            # 保存主记录
            record = DragonTigerRecord(
                trade_date=trade_date,
                total_buy=analysis_result.get('total_buy', 0),
                total_sell=analysis_result.get('total_sell', 0),
                net_buy=analysis_result.get('net_buy', 0),
                hot_stocks=json.dumps(analysis_result.get('hot_stocks', [])),
                seat_stats=json.dumps(analysis_result.get('seat_stats', [])),
                stock_stats=json.dumps(analysis_result.get('stock_stats', []))
            )
            
            self.session.add(record)
            self.session.commit()
            logger.info(f"龙虎榜分析结果已保存到数据库: {trade_date}")
        except Exception as e:
            logger.error(f"保存龙虎榜分析结果失败: {e}")
            self.session.rollback()
    
    def generate_analysis_report(self, trade_date: str = None) -> Dict:
        """
        生成龙虎榜分析报告
        :param trade_date: 交易日
        :return: 分析报告
        """
        if not trade_date:
            trade_date = self.fetcher.get_previous_trade_date()
        
        logger.info(f"开始生成 {trade_date} 龙虎榜分析报告")
        
        # 获取数据
        df = self.get_dragon_tiger_data(trade_date)
        if df.empty:
            return {'status': 'error', 'message': '龙虎榜数据为空'}
        
        # 分析资金流向
        capital_flow = self.analyze_capital_flow(df)
        
        # 识别热门股票
        hot_stocks = self.identify_hot_stocks(df)
        
        # 生成报告
        report = {
            'trade_date': trade_date,
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'capital_flow': capital_flow,
            'hot_stocks': hot_stocks,
            'total_stocks': len(df['ts_code'].unique()),
            'status': 'success'
        }
        
        # 保存到数据库
        self.save_to_database(trade_date, report)
        
        return report
    
    def get_dragon_tiger_factor(self, ts_code: str, trade_date: str = None) -> float:
        """
        获取龙虎榜因子分数，用于选股系统
        :param ts_code: 股票代码
        :param trade_date: 交易日
        :return: 因子分数（0-100）
        """
        if not trade_date:
            trade_date = self.fetcher.get_previous_trade_date()
        
        try:
            # 获取该股票的龙虎榜数据
            df = self.ts_api.top_detail(
                trade_date=trade_date,
                ts_code=ts_code
            )
            
            if df.empty:
                return 0.0
            
            # 计算因子分数
            net_buy = df['buy_amount'].sum() - df['sell_amount'].sum()
            buy_ratio = df['buy_amount'].sum() / (df['buy_amount'].sum() + df['sell_amount'].sum())
            
            # 机构席位加分
            institutional_buy = df[df['broker'].str.contains('机构专用')]['buy_amount'].sum()
            
            # 计算最终分数
            score = 0
            if net_buy > 0:
                score = min(buy_ratio * 100, 80)
                if institutional_buy > 0:
                    score += 20
            
            return round(min(score, 100), 2)
        except Exception as e:
            logger.error(f"计算龙虎榜因子失败: {e}")
            return 0.0


def main():
    """主函数"""
    analyzer = DragonTigerAnalyzer()
    
    # 生成最新龙虎榜分析报告
    report = analyzer.generate_analysis_report()
    
    if report['status'] == 'success':
        print("龙虎榜分析报告生成成功:")
        print(f"交易日: {report['trade_date']}")
        print(f"上榜股票数: {report['total_stocks']}")
        print(f"资金净流入: {report['capital_flow']['net_buy']}亿元")
        print(f"热门股票数: {len(report['hot_stocks'])}")
        
        # 打印热门股票
        if report['hot_stocks']:
            print("\n热门股票:")
            for stock in report['hot_stocks'][:5]:
                print(f"{stock['ts_code']} {stock['name']}: 净流入{stock['net_buy']}亿元，涨幅{stock['pct_change']}%")
    else:
        print(f"分析报告生成失败: {report.get('message', '未知错误')}")


if __name__ == '__main__':
    main()