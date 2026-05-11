#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价盘口异动识别模块
功能：识别竞价阶段的盘口异动，如爆量、大幅涨跌、异常委托等
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from database.models import get_session
from auction_anomaly.models import AuctionAnomalyRecord
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class AuctionAnomalyDetector:
    """竞价盘口异动检测器"""
    
    def __init__(self, fetcher: Optional[DataFetcher] = None):
        self.fetcher = fetcher or DataFetcher()
        self.session = get_session()
        
        # 异动检测阈值
        self.thresholds = {
            'volume_burst_ratio': 5.0,  # 爆量比阈值（竞价量/昨日均量）
            'price_change_pct': 7.0,    # 价格异动阈值（涨跌幅%）
            'turnover_rate': 3.0,       # 换手率阈值（%）
            'order_imbalance_ratio': 3.0 # 委托失衡比阈值（买盘/卖盘）
        }
    
    def get_auction_data(self, trade_date: str = None) -> pd.DataFrame:
        """
        获取竞价数据
        :param trade_date: 交易日，格式YYYYMMDD
        :return: 竞价数据DataFrame
        """
        if not trade_date:
            trade_date = self.fetcher.get_previous_trading_day()
        
        try:
            # 先获取所有A股股票列表
            stock_basic = self.fetcher.pro.stock_basic(exchange='', list_status='L')
            ts_codes = stock_basic['ts_code'].tolist()
            
            # 分批处理，每批1000个股票（Tushare接口限制）
            batch_size = 1000
            auction_data = {}
            
            for i in range(0, len(ts_codes), batch_size):
                batch_codes = ts_codes[i:i+batch_size]
                logger.info(f"正在获取第 {i//batch_size + 1} 批竞价数据，共 {len(batch_codes)} 只股票")
                
                # 批量获取竞价数据
                batch_data = self.fetcher.get_auction_data_batch(batch_codes, trade_date)
                auction_data.update(batch_data)
                
                # 添加延迟避免触发速率限制
                time.sleep(1)
            
            # 转换为DataFrame
            df = pd.DataFrame.from_dict(auction_data, orient='index').reset_index(drop=True)
            logger.info(f"共获取到 {len(df)} 只股票的竞价数据")
            
            # 获取5日均量数据（同样分批处理）
            if not df.empty:
                df['avg_vol_5d'] = 0
                prev_day = self.fetcher.get_previous_trading_day(trade_date)
                
                if prev_day:
                    # 获取前5个交易日
                    prev_dates = self.fetcher.get_trading_days(
                        (datetime.strptime(prev_day, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d'),
                        prev_day
                    )[-5:]
                    
                    if prev_dates:
                        # 分批获取日均量
                        avg_vol_5d = {}
                        
                        for i in range(0, len(ts_codes), batch_size):
                            batch_codes = ts_codes[i:i+batch_size]
                            batch_codes_str = ','.join(batch_codes)
                            
                            daily_data = self.fetcher.pro.daily(
                                ts_code=batch_codes_str,
                                start_date=prev_dates[0],
                                end_date=prev_dates[-1]
                            )
                            
                            if not daily_data.empty:
                                # 计算5日均量（股）
                                batch_avg = daily_data.groupby('ts_code')['vol'].mean() * 100
                                avg_vol_5d.update(batch_avg.to_dict())
                            
                            time.sleep(0.5)
                        
                        # 更新DataFrame中的5日均量
                        df['avg_vol_5d'] = df['ts_code'].map(avg_vol_5d)
            
            return df
        except Exception as e:
            logger.error(f"获取竞价数据失败: {e}")
            return pd.DataFrame()
    
    def detect_volume_burst(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测爆量异动
        :param df: 竞价数据
        :return: 爆量异动股票
        """
        if df.empty:
            return pd.DataFrame()
        
        # 计算爆量比（竞价量/昨日成交量均值）
        df['volume_burst_ratio'] = df['auction_vol'] / df['avg_vol_5d']
        
        # 筛选爆量股票
        burst_stocks = df[df['volume_burst_ratio'] >= self.thresholds['volume_burst_ratio']]
        
        # 添加异动类型
        burst_stocks['anomaly_type'] = 'volume_burst'
        burst_stocks['anomaly_reason'] = burst_stocks.apply(
            lambda x: f"竞价爆量{round(x['volume_burst_ratio'], 2)}倍", axis=1
        )
        
        return burst_stocks
    
    def detect_price_spike(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测价格大幅异动
        :param df: 竞价数据
        :return: 价格异动股票
        """
        if df.empty:
            return pd.DataFrame()
        
        # 筛选涨跌幅超过阈值的股票
        price_spike = df[abs(df['auction_pct_chg']) >= self.thresholds['price_change_pct']]
        
        # 添加异动类型和原因
        price_spike['anomaly_type'] = 'price_spike'
        price_spike['anomaly_reason'] = price_spike.apply(
            lambda x: f"竞价涨幅{round(x['auction_pct_chg'], 2)}%" if x['auction_pct_chg'] > 0 else f"竞价跌幅{round(x['auction_pct_chg'], 2)}%",
            axis=1
        )
        
        return price_spike
    
    def detect_high_turnover(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测高换手率异动
        :param df: 竞价数据
        :return: 高换手率股票
        """
        if df.empty:
            return pd.DataFrame()
        
        # 筛选换手率超过阈值的股票
        high_turnover = df[df['auction_turnover'] >= self.thresholds['turnover_rate']]
        
        # 添加异动类型和原因
        high_turnover['anomaly_type'] = 'high_turnover'
        high_turnover['anomaly_reason'] = high_turnover.apply(
            lambda x: f"竞价换手率{round(x['auction_turnover'], 2)}%", axis=1
        )
        
        return high_turnover
    
    def detect_order_imbalance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测委托失衡异动
        :param df: 竞价数据
        :return: 委托失衡股票
        """
        if df.empty:
            return pd.DataFrame()
        
        # 计算委托失衡比
        df['order_imbalance_ratio'] = df['buy_order_vol'] / df['sell_order_vol'].replace(0, 1)
        
        # 筛选委托失衡的股票
        imbalance = df[(
            (df['order_imbalance_ratio'] >= self.thresholds['order_imbalance_ratio']) | 
            (df['order_imbalance_ratio'] <= 1/self.thresholds['order_imbalance_ratio'])
        )]
        
        # 添加异动类型和原因
        imbalance['anomaly_type'] = 'order_imbalance'
        imbalance['anomaly_reason'] = imbalance.apply(
            lambda x: f"委托买盘是卖盘的{round(x['order_imbalance_ratio'], 2)}倍" if x['order_imbalance_ratio'] >= self.thresholds['order_imbalance_ratio'] 
            else f"委托卖盘是买盘的{round(1/x['order_imbalance_ratio'], 2)}倍",
            axis=1
        )
        
        return imbalance
    
    def detect_all_anomalies(self, trade_date: str = None) -> List[Dict]:
        """
        检测所有类型的竞价异动
        :param trade_date: 交易日
        :return: 异动股票列表
        """
        if not trade_date:
            trade_date = self.fetcher.get_previous_trading_day()
        
        logger.info(f"开始检测 {trade_date} 竞价盘口异动")
        
        # 获取竞价数据
        df = self.get_auction_data(trade_date)
        if df.empty:
            logger.warning("竞价数据为空，无法检测异动")
            return []
        
        # 检测各类异动
        burst_stocks = self.detect_volume_burst(df)
        price_spike = self.detect_price_spike(df)
        high_turnover = self.detect_high_turnover(df)
        order_imbalance = self.detect_order_imbalance(df)
        
        # 合并结果
        all_anomalies = pd.concat([burst_stocks, price_spike, high_turnover, order_imbalance])
        
        # 去重
        all_anomalies = all_anomalies.drop_duplicates(['ts_code'])
        
        # 转换为字典列表
        result = []
        for _, row in all_anomalies.iterrows():
            result.append({
                'ts_code': row['ts_code'],
                'name': row['name'],
                'trade_date': trade_date,
                'anomaly_type': row['anomaly_type'],
                'anomaly_reason': row['anomaly_reason'],
                'auction_price': row['auction_price'],
                'auction_pct_chg': row['auction_pct_chg'],
                'auction_vol': row['auction_vol'],
                'anomaly_score': self.calculate_anomaly_score(row),
                'status': 'detected'
            })
        
        # 保存到数据库
        self.save_anomalies(result, trade_date)
        
        logger.info(f"竞价异动检测完成，共检测到{len(result)}只异动股票")
        return result
    
    def calculate_anomaly_score(self, row: pd.Series) -> float:
        """
        计算异动分数
        :param row: 股票数据行
        :return: 异动分数（0-100）
        """
        score = 0
        
        # 根据异动类型加分
        if row['anomaly_type'] == 'volume_burst':
            score = min(row['volume_burst_ratio'] * 10, 40)
        elif row['anomaly_type'] == 'price_spike':
            score = min(abs(row['auction_pct_chg']) * 5, 40)
        elif row['anomaly_type'] == 'high_turnover':
            score = min(row['auction_turnover'] * 10, 30)
        elif row['anomaly_type'] == 'order_imbalance':
            score = min(row['order_imbalance_ratio'] * 10, 30)
        
        # 综合加分
        if row['auction_pct_chg'] > 0:  # 上涨异动加分
            score += 20
        
        return round(min(score, 100), 2)
    
    def save_anomalies(self, anomalies: List[Dict], trade_date: str):
        """
        保存异动检测结果到数据库
        :param anomalies: 异动列表
        :param trade_date: 交易日
        """
        try:
            # 先删除已存在的记录
            existing = self.session.query(AuctionAnomalyRecord).filter_by(
                trade_date=trade_date
            ).all()
            for record in existing:
                self.session.delete(record)
            self.session.commit()
            
            # 保存新记录
            for anomaly in anomalies:
                record = AuctionAnomalyRecord(
                    ts_code=anomaly['ts_code'],
                    name=anomaly['name'],
                    trade_date=trade_date,
                    anomaly_type=anomaly['anomaly_type'],
                    anomaly_reason=anomaly['anomaly_reason'],
                    auction_price=anomaly['auction_price'],
                    auction_pct_chg=anomaly['auction_pct_chg'],
                    auction_vol=anomaly['auction_vol'],
                    anomaly_score=anomaly['anomaly_score']
                )
                self.session.add(record)
            
            self.session.commit()
            logger.info(f"竞价异动结果已保存到数据库: {len(anomalies)}条记录")
        except Exception as e:
            logger.error(f"保存竞价异动结果失败: {e}")
            self.session.rollback()
    
    def get_anomaly_stocks_for_selection(self) -> List[Dict]:
        """
        获取适合选股的异动股票
        :return: 异动股票列表
        """
        try:
            # 获取最新异动数据
            anomalies = self.detect_all_anomalies()
            
            # 筛选适合选股的异动股票（上涨异动为主）
            selection_stocks = []
            for anomaly in anomalies:
                if anomaly['auction_pct_chg'] > 0 and anomaly['anomaly_score'] >= 60:
                    selection_stocks.append({
                        'ts_code': anomaly['ts_code'],
                        'name': anomaly['name'],
                        'anomaly_type': anomaly['anomaly_type'],
                        'anomaly_score': anomaly['anomaly_score'],
                        'auction_pct_chg': anomaly['auction_pct_chg'],
                        'reason': anomaly['anomaly_reason'],
                        'selection_priority': 'high' if anomaly['anomaly_score'] >= 80 else 'medium'
                    })
            
            return selection_stocks
        except Exception as e:
            logger.error(f"获取选股用异动股票失败: {e}")
            return []


def main():
    """主函数"""
    detector = AuctionAnomalyDetector()
    
    # 检测最新竞价异动
    anomalies = detector.detect_all_anomalies()
    
    if anomalies:
        print(f"竞价盘口异动检测结果 ({len(anomalies)}只):")
        for anomaly in anomalies[:10]:
            print(f"{anomaly['ts_code']} {anomaly['name']}: {anomaly['anomaly_reason']} (分数: {anomaly['anomaly_score']})")
    else:
        print("未检测到竞价盘口异动")


if __name__ == '__main__':
    main()