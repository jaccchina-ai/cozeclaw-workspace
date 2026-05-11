#!/usr/bin/env python3
"""
T01 选股系统 - 涨跌停数据分析模块
功能：
1. 从Tushare获取涨跌停数据
2. 涨跌停数据统计分析
3. 封板强度计算
4. 涨跌停模式识别
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
from sqlalchemy import create_engine, text
from database.models import LimitStockData, LimitStepData, DailyStockData, Base
from sqlalchemy.orm import sessionmaker
from tushare_data_fetcher import TushareDataFetcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LimitDataAnalyzer:
    def __init__(self, config_path: str = './config.json'):
        """
        初始化涨跌停数据分析器
        :param config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.fetcher = TushareDataFetcher(config_path)
        self.engine = self.fetcher.engine
        self.Session = sessionmaker(bind=self.engine)
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def analyze_limit_strength(self, limit_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算涨跌停强度
        :param limit_df: 涨跌停数据
        :return: 包含强度指标的DataFrame
        """
        if limit_df.empty:
            return limit_df
        
        df = limit_df.copy()
        
        try:
            # 计算封板强度 = 封板时长 / (总交易时长 - 第一次打开时间)
            # 假设每天交易时长为240分钟=14400秒
            total_trading_seconds = 14400
            
            # 封板强度 = 封板时长 / 总交易时长
            df['limit_strength'] = np.where(
                df['up_stat'] > 0,
                df['up_stat'] / total_trading_seconds,
                0
            )
            
            # 计算打开频率
            df['open_frequency'] = np.where(
                df['open_times'] > 0,
                df['open_times'] / (total_trading_seconds / 600),  # 每10分钟打开次数
                0
            )
            
            # 封板质量评分
            df['limit_quality'] = np.where(
                df['limit_type'] == 'U',
                # 涨停质量评分
                (1 - df['open_times'] * 0.1) * (df['up_stat'] / total_trading_seconds),
                # 跌停质量评分
                (1 + df['open_times'] * 0.1) * (1 - df['up_stat'] / total_trading_seconds)
            )
            
            # 归一化处理
            if 'limit_quality' in df.columns:
                df['limit_quality'] = (df['limit_quality'] - df['limit_quality'].min()) / \
                                    (df['limit_quality'].max() - df['limit_quality'].min() + 1e-10)
            
            logger.info("涨跌停强度计算完成")
            return df
        except Exception as e:
            logger.error(f"计算涨跌停强度失败: {e}")
            return df
    
    def analyze_limit_patterns(self, limit_df: pd.DataFrame) -> pd.DataFrame:
        """
        识别涨跌停模式
        :param limit_df: 涨跌停数据
        :return: 包含模式识别的DataFrame
        """
        if limit_df.empty:
            return limit_df
        
        df = limit_df.copy()
        
        try:
            # 模式识别
            conditions = [
                # 一字板
                (df['open_times'] == 0) & (df['up_stat'] >= 14000),
                # 秒板
                (df['open_times'] == 0) & (df['up_stat'] >= 13500),
                # 早盘硬板
                (df['open_times'] <= 1) & (df['up_stat'] >= 12000),
                # 烂板
                (df['open_times'] >= 5) | (df['up_stat'] < 6000),
                # 反复开板
                (df['open_times'].between(2, 4)) & (df['up_stat'].between(6000, 12000)),
                # 尾盘封板
                (df['up_stat'] < 3600) & (df['open_times'] <= 2)
            ]
            
            patterns = [
                '一字板', '秒板', '早盘硬板', '烂板', '反复开板', '尾盘封板'
            ]
            
            df['limit_pattern'] = np.select(conditions, patterns, default='普通板')
            
            # 计算模式得分
            pattern_scores = {
                '一字板': 1.0,
                '秒板': 0.95,
                '早盘硬板': 0.9,
                '普通板': 0.7,
                '反复开板': 0.5,
                '尾盘封板': 0.4,
                '烂板': 0.2
            }
            
            df['pattern_score'] = df['limit_pattern'].map(pattern_scores).fillna(0.5)
            
            logger.info("涨跌停模式识别完成")
            return df
        except Exception as e:
            logger.error(f"识别涨跌停模式失败: {e}")
            return df
    
    def analyze_sector_limit(self, trade_date: str = None) -> pd.DataFrame:
        """
        分析板块涨跌停情况
        :param trade_date: 日期(YYYYMMDD)
        :return: 板块涨跌停分析结果
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            # 获取当日涨跌停数据
            limit_df = self.fetcher.get_limit_list_data(trade_date, limit_type='ALL')
            
            if limit_df.empty:
                logger.info(f"日期{trade_date}没有涨跌停数据")
                return pd.DataFrame()
            
            # 获取股票行业信息
            stock_basic = self.fetcher.get_stock_basic()
            
            # 合并行业信息
            merged_df = limit_df.merge(
                stock_basic[['ts_code', 'industry']], 
                on='ts_code', 
                how='left'
            )
            
            # 按行业统计
            sector_stats = merged_df.groupby('industry').agg({
                'ts_code': 'count',
                'pct_chg': ['mean', 'max', 'min'],
                'limit_type': lambda x: (x == 'U').sum() / len(x) if len(x) > 0 else 0
            }).reset_index()
            
            # 重命名列
            sector_stats.columns = ['industry', 'limit_count', 'avg_pct_chg', 'max_pct_chg', 'min_pct_chg', 'up_limit_ratio']
            
            # 计算板块强度
            sector_stats['sector_strength'] = sector_stats['limit_count'] * sector_stats['avg_pct_chg']
            
            # 排序
            sector_stats = sector_stats.sort_values('sector_strength', ascending=False)
            
            logger.info(f"板块涨跌停分析完成，共{len(sector_stats)}个板块")
            return sector_stats
        except Exception as e:
            logger.error(f"分析板块涨跌停情况失败: {e}")
            return pd.DataFrame()
    
    def analyze_limit_history(self, ts_code: str, days: int = 30) -> Dict:
        """
        分析股票历史涨跌停情况
        :param ts_code: 股票代码
        :param days: 分析天数
        :return: 历史涨跌停分析结果
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            # 获取历史涨跌停数据
            all_limit_df = pd.DataFrame()
            current_date = datetime.now()
            
            for i in range(days):
                trade_date = (current_date - timedelta(days=i)).strftime("%Y%m%d")
                limit_df = self.fetcher.get_limit_list_data(trade_date, limit_type='ALL')
                if not limit_df.empty and ts_code in limit_df['ts_code'].values:
                    all_limit_df = pd.concat([all_limit_df, limit_df[limit_df['ts_code'] == ts_code]])
            
            if all_limit_df.empty:
                return {
                    "ts_code": ts_code,
                    "limit_days": 0,
                    "up_limit_days": 0,
                    "down_limit_days": 0,
                    "avg_limit_strength": 0,
                    "recent_limit_days": []
                }
            
            # 计算统计指标
            up_limit_days = len(all_limit_df[all_limit_df['limit_type'] == 'U'])
            down_limit_days = len(all_limit_df[all_limit_df['limit_type'] == 'D'])
            
            # 计算平均封板强度
            all_limit_df = self.analyze_limit_strength(all_limit_df)
            avg_strength = all_limit_df['limit_strength'].mean() if 'limit_strength' in all_limit_df.columns else 0
            
            # 获取最近涨跌停日期
            recent_days = all_limit_df.sort_values('trade_date', ascending=False)['trade_date'].tolist()
            
            result = {
                "ts_code": ts_code,
                "limit_days": len(all_limit_df),
                "up_limit_days": up_limit_days,
                "down_limit_days": down_limit_days,
                "avg_limit_strength": avg_strength,
                "recent_limit_days": recent_days,
                "limit_details": all_limit_df.to_dict('records')
            }
            
            logger.info(f"股票{ts_code}历史涨跌停分析完成")
            return result
        except Exception as e:
            logger.error(f"分析股票{ts_code}历史涨跌停情况失败: {e}")
            return {}
    
    def detect_limit_anomalies(self, trade_date: str = None) -> pd.DataFrame:
        """
        检测异常涨跌停情况
        :param trade_date: 日期(YYYYMMDD)
        :return: 异常情况DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            # 获取当日涨跌停数据
            limit_df = self.fetcher.get_limit_list_data(trade_date, limit_type='ALL')
            
            if limit_df.empty:
                logger.info(f"日期{trade_date}没有涨跌停数据")
                return pd.DataFrame()
            
            # 获取行情数据
            stock_codes = limit_df['ts_code'].tolist()
            daily_df = pd.DataFrame()
            
            for ts_code in stock_codes:
                df = self.fetcher.get_daily_data(ts_code, trade_date, trade_date)
                if not df.empty:
                    daily_df = pd.concat([daily_df, df])
            
            if daily_df.empty:
                return limit_df
            
            # 合并数据
            merged_df = limit_df.merge(daily_df, on=['ts_code', 'trade_date'], how='left')
            
            # 检测异常情况
            # 1. 成交量异常放大
            merged_df['vol_anomaly'] = np.where(
                merged_df['vol'] > merged_df['vol'].rolling(20, min_periods=5).mean().shift(1) * 3,
                True,
                False
            )
            
            # 2. 封板强度异常低
            merged_df = self.analyze_limit_strength(merged_df)
            merged_df['strength_anomaly'] = np.where(
                merged_df['limit_strength'] < 0.3,
                True,
                False
            )
            
            # 3. 打开次数异常多
            merged_df['open_anomaly'] = np.where(
                merged_df['open_times'] > 5,
                True,
                False
            )
            
            # 标记异常情况
            merged_df['is_anomaly'] = (
                merged_df['vol_anomaly'] | 
                merged_df['strength_anomaly'] | 
                merged_df['open_anomaly']
            )
            
            # 筛选异常数据
            anomaly_df = merged_df[merged_df['is_anomaly']].copy()
            
            logger.info(f"检测到{len(anomaly_df)}个异常涨跌停情况")
            return anomaly_df
        except Exception as e:
            logger.error(f"检测异常涨跌停情况失败: {e}")
            return pd.DataFrame()
    
    def generate_limit_report(self, trade_date: str = None) -> Dict:
        """
        生成涨跌停日报
        :param trade_date: 日期(YYYYMMDD)
        :return: 日报数据
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"开始生成{trade_date}涨跌停日报")
            
            # 1. 获取涨跌停数据
            limit_df = self.fetcher.get_limit_list_data(trade_date, limit_type='ALL')
            
            if limit_df.empty:
                return {
                    "trade_date": trade_date,
                    "total_limit": 0,
                    "up_limit_count": 0,
                    "down_limit_count": 0,
                    "sector_analysis": [],
                    "anomaly_analysis": [],
                    "summary": "当日无涨跌停股票"
                }
            
            # 2. 统计基本情况
            up_limit_count = len(limit_df[limit_df['limit_type'] == 'U'])
            down_limit_count = len(limit_df[limit_df['limit_type'] == 'D'])
            
            # 3. 分析板块情况
            sector_df = self.analyze_sector_limit(trade_date)
            
            # 4. 检测异常情况
            anomaly_df = self.detect_limit_anomalies(trade_date)
            
            # 5. 计算强度指标
            limit_df = self.analyze_limit_strength(limit_df)
            limit_df = self.analyze_limit_patterns(limit_df)
            
            # 6. 生成摘要
            summary = f"{trade_date}市场共有{len(limit_df)}只涨跌停股票，其中{up_limit_count}只涨停，{down_limit_count}只跌停。"
            
            if not sector_df.empty:
                top_sector = sector_df.iloc[0]
                summary += f" 最强板块是{top_sector['industry']}，共有{top_sector['limit_count']}只涨跌停股票。"
            
            if not anomaly_df.empty:
                summary += f" 检测到{len(anomaly_df)}只异常涨跌停股票。"
            
            # 7. 生成详细报告
            report = {
                "trade_date": trade_date,
                "total_limit": len(limit_df),
                "up_limit_count": up_limit_count,
                "down_limit_count": down_limit_count,
                "avg_limit_strength": limit_df['limit_strength'].mean() if 'limit_strength' in limit_df.columns else 0,
                "sector_analysis": sector_df.to_dict('records')[:5],  # 取前5个板块
                "anomaly_analysis": anomaly_df.to_dict('records')[:10],  # 取前10个异常
                "top_limit_stocks": limit_df.nlargest(10, 'limit_strength').to_dict('records'),
                "limit_patterns": limit_df['limit_pattern'].value_counts().to_dict(),
                "summary": summary
            }
            
            logger.info(f"{trade_date}涨跌停日报生成完成")
            return report
        except Exception as e:
            logger.error(f"生成涨跌停日报失败: {e}")
            return {}
    
    def save_analysis_results(self, report: Dict, table_name: str = 'limit_analysis_report') -> bool:
        """
        保存分析结果到数据库
        :param report: 分析报告
        :param table_name: 表名
        :return: 是否保存成功
        """
        if not report:
            logger.warning("没有分析结果需要保存")
            return False
        
        try:
            df = pd.DataFrame([report])
            
            # 保存到数据库
            df.to_sql(table_name, self.engine, if_exists='append', index=False)
            
            logger.info("分析结果成功保存到数据库")
            return True
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False

if __name__ == '__main__':
    """测试示例"""
    try:
        analyzer = LimitDataAnalyzer()
        
        # 生成今日涨跌停报告
        report = analyzer.generate_limit_report()
        print("涨跌停日报摘要:", report.get('summary', ''))
        
        # 分析特定股票历史涨跌停情况
        stock_analysis = analyzer.analyze_limit_history("600000.SH", days=60)
        print(f"股票600000.SH近60天涨跌停次数: {stock_analysis.get('limit_days', 0)}")
        
        # 检测异常涨跌停
        anomalies = analyzer.detect_limit_anomalies()
        print(f"检测到异常涨跌停数量: {len(anomalies)}")
        
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)