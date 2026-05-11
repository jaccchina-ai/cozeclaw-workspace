#!/usr/bin/env python3
"""
T01 选股系统 - Tushare数据获取模块
功能：
1. 获取股票基础数据
2. 获取资金流向数据
3. 数据清洗和转换
4. 数据入库
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tushare as ts
from sqlalchemy import create_engine, text
from typing import Dict, List, Tuple, Optional
import json
import logging
from database.models import DailyStockData, Base
from sqlalchemy.orm import sessionmaker

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TushareDataFetcher:
    def __init__(self, config_path: str = '../config.json'):
        """
        初始化Tushare数据获取器
        :param config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.pro = self._init_tushare()
        self.engine = self._init_database()
        self.Session = sessionmaker(bind=self.engine)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 使用默认配置
            return {
                "tushare": {
                    "token": "你的Tushare token"
                },
                "database": {
                    "url": "postgresql://postgres:***@cp-hip-veil-65383f4d.pg5.aidap-global.cn-beijing.volces.com:5432/postgres?sslmode=require"
                }
            }
    
    def _init_tushare(self):
        """初始化Tushare接口"""
        try:
            token = self.config.get('tushare', {}).get('token', '')
            if not token:
                raise ValueError("Tushare token未配置")
            pro = ts.pro_api(token)
            logger.info("Tushare接口初始化成功")
            return pro
        except Exception as e:
            logger.error(f"Tushare接口初始化失败: {e}")
            raise
    
    def _init_database(self):
        """初始化数据库连接"""
        try:
            db_url = self.config.get('database', {}).get('url', '')
            if not db_url:
                raise ValueError("数据库URL未配置")
            engine = create_engine(db_url)
            logger.info("数据库连接初始化成功")
            return engine
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise
    
    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基础数据
        :return: 股票基础数据DataFrame
        """
        try:
            logger.info("开始获取股票基础数据")
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date'
            )
            logger.info(f"获取股票基础数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取股票基础数据失败: {e}")
            return pd.DataFrame()
    
    def get_daily_data(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票行情数据
        :param ts_code: 股票代码
        :param start_date: 开始日期(YYYYMMDD)
        :param end_date: 结束日期(YYYYMMDD)
        :return: 行情数据DataFrame
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                # 默认获取最近一年的数据
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            logger.info(f"开始获取股票{ts_code}行情数据，日期范围: {start_date}至{end_date}")
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"获取股票{ts_code}行情数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_moneyflow_data(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取资金流向数据
        :param ts_code: 股票代码
        :param start_date: 开始日期(YYYYMMDD)
        :param end_date: 结束日期(YYYYMMDD)
        :return: 资金流向数据DataFrame
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                # 默认获取最近30天的数据
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            logger.info(f"开始获取股票{ts_code}资金流向数据，日期范围: {start_date}至{end_date}")
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"获取股票{ts_code}资金流向数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}资金流向数据失败: {e}")
            return pd.DataFrame()
    
    def get_daily_basic_data(self, ts_code: str, trade_date: str = None) -> pd.DataFrame:
        """
        获取每日指标数据
        :param ts_code: 股票代码
        :param trade_date: 日期(YYYYMMDD)
        :return: 每日指标数据DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"开始获取股票{ts_code}每日指标数据，日期: {trade_date}")
            df = self.pro.daily_basic(
                ts_code=ts_code,
                trade_date=trade_date,
                fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            )
            logger.info(f"获取股票{ts_code}每日指标数据成功")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}每日指标数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_list_data(self, trade_date: str = None, limit_type: str = 'U') -> pd.DataFrame:
        """
        获取涨跌停列表数据
        :param trade_date: 日期(YYYYMMDD)
        :param limit_type: 涨跌停类型: U-涨停, D-跌停, ALL-全部
        :return: 涨跌停列表数据DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"开始获取涨跌停列表数据，日期: {trade_date}, 类型: {limit_type}")
            df = self.pro.limit_list_d(
                trade_date=trade_date,
                limit_type=limit_type,
                fields='ts_code,name,close,pct_chg,limit_price,open_times,up_stat,trade_date,exchange,limit_type'
            )
            logger.info(f"获取涨跌停列表数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取涨跌停列表数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_step_data(self, ts_code: str, trade_date: str = None) -> pd.DataFrame:
        """
        获取涨跌停分时数据
        :param ts_code: 股票代码
        :param trade_date: 日期(YYYYMMDD)
        :return: 涨跌停分时数据DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"开始获取股票{ts_code}涨跌停分时数据，日期: {trade_date}")
            df = self.pro.limit_step(
                ts_code=ts_code,
                trade_date=trade_date,
                fields='ts_code,trade_date,time,price,pct_chg,vol,amount,type,status'
            )
            logger.info(f"获取股票{ts_code}涨跌停分时数据成功，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}涨跌停分时数据失败: {e}")
            return pd.DataFrame()
    
    def merge_stock_data(self, daily_df: pd.DataFrame, moneyflow_df: pd.DataFrame, daily_basic_df: pd.DataFrame = None, limit_list_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        合并股票数据
        :param daily_df: 行情数据
        :param moneyflow_df: 资金流向数据
        :param daily_basic_df: 每日指标数据
        :param limit_list_df: 涨跌停列表数据
        :return: 合并后的数据
        """
        try:
            if daily_df.empty:
                raise ValueError("行情数据为空")
            
            merged_df = daily_df.copy()
            
            # 合并资金流向数据
            if not moneyflow_df.empty:
                merged_df = merged_df.merge(
                    moneyflow_df, 
                    on=['ts_code', 'trade_date'], 
                    how='left',
                    suffixes=('', '_mf')
                )
            
            # 合并每日指标数据
            if not daily_basic_df.empty:
                merged_df = merged_df.merge(
                    daily_basic_df, 
                    on=['ts_code', 'trade_date'], 
                    how='left',
                    suffixes=('', '_db')
                )
            
            # 合并涨跌停数据
            if not limit_list_df.empty:
                merged_df = merged_df.merge(
                    limit_list_df, 
                    on=['ts_code', 'trade_date'], 
                    how='left',
                    suffixes=('', '_limit')
                )
            
            logger.info(f"数据合并成功，合并后字段数: {len(merged_df.columns)}")
            return merged_df
        except Exception as e:
            logger.error(f"数据合并失败: {e}")
            return pd.DataFrame()
    
    def get_limit_status(self, ts_code: str, trade_date: str = None) -> Dict:
        """
        获取股票涨跌停状态
        :param ts_code: 股票代码
        :param trade_date: 日期(YYYYMMDD)
        :return: 涨跌停状态字典
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            # 获取涨跌停列表数据
            limit_df = self.get_limit_list_data(trade_date, limit_type='ALL')
            
            if not limit_df.empty and ts_code in limit_df['ts_code'].values:
                stock_data = limit_df[limit_df['ts_code'] == ts_code].iloc[0]
                return {
                    "is_limit": True,
                    "limit_type": stock_data['limit_type'],
                    "limit_price": stock_data['limit_price'],
                    "close_price": stock_data['close'],
                    "pct_chg": stock_data['pct_chg'],
                    "open_times": stock_data['open_times'],
                    "up_stat": stock_data['up_stat']
                }
            else:
                # 获取行情数据判断是否接近涨跌停
                daily_df = self.get_daily_data(ts_code, trade_date, trade_date)
                if not daily_df.empty:
                    pct_chg = daily_df.iloc[0]['pct_chg']
                    return {
                        "is_limit": False,
                        "limit_type": None,
                        "pct_chg": pct_chg,
                        "is_near_limit": abs(pct_chg) >= 9.5
                    }
                else:
                    return {
                        "is_limit": False,
                        "limit_type": None,
                        "pct_chg": None,
                        "is_near_limit": False
                    }
        except Exception as e:
            logger.error(f"获取股票{ts_code}涨跌停状态失败: {e}")
            return {
                "is_limit": False,
                "limit_type": None,
                "pct_chg": None,
                "is_near_limit": False
            }
    
    def clean_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗股票数据
        :param df: 原始数据
        :return: 清洗后的数据
        """
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        try:
            # 处理缺失值
            numeric_columns = ['open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount',
                             'turnover_rate', 'volume_ratio', 'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
                             'total_share', 'float_share', 'free_share', 'total_mv', 'circ_mv',
                             'buy_sm_vol', 'buy_sm_amount', 'sell_sm_vol', 'sell_sm_amount',
                             'buy_md_vol', 'buy_md_amount', 'sell_md_vol', 'sell_md_amount',
                             'buy_lg_vol', 'buy_lg_amount', 'sell_lg_vol', 'sell_lg_amount',
                             'buy_elg_vol', 'buy_elg_amount', 'sell_elg_vol', 'sell_elg_amount',
                             'net_mf_vol', 'net_mf_amount', 'limit_price', 'open_times', 'up_stat']
            
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
                    # 使用前一日数据填充缺失值
                    cleaned_df[col] = cleaned_df[col].ffill()
            
            # 处理日期格式
            if 'trade_date' in cleaned_df.columns:
                cleaned_df['trade_date'] = pd.to_datetime(cleaned_df['trade_date'], format='%Y%m%d')
            
            # 计算真实换手率
            if 'turnover_rate' in cleaned_df.columns and 'free_share' in cleaned_df.columns and 'total_share' in cleaned_df.columns:
                cleaned_df['real_turnover_rate'] = np.where(
                    cleaned_df['total_share'] > 0,
                    cleaned_df['vol'] / cleaned_df['free_share'] * 100,
                    cleaned_df['turnover_rate']
                )
            
            # 标记涨跌停状态
            if 'limit_type' in cleaned_df.columns:
                cleaned_df['is_limit_up'] = cleaned_df['limit_type'] == 'U'
                cleaned_df['is_limit_down'] = cleaned_df['limit_type'] == 'D'
                cleaned_df['limit_strength'] = np.where(
                    cleaned_df['up_stat'] > 0,
                    cleaned_df['up_stat'] / (cleaned_df['open_times'] + 1),
                    0
                )
            
            logger.info("数据清洗完成")
            return cleaned_df
        except Exception as e:
            logger.error(f"数据清洗失败: {e}")
            return df
    
    def save_to_database(self, df: pd.DataFrame, table_name: str = 'daily_stock_data') -> int:
        """
        将数据保存到数据库
        :param df: 要保存的数据
        :param table_name: 表名
        :return: 保存的记录数
        """
        if df.empty:
            logger.warning("没有数据需要保存")
            return 0
        
        try:
            # 创建表（如果不存在）
            Base.metadata.create_all(self.engine)
            
            # 将数据转换为适合数据库的格式
            save_df = df.copy()
            
            # 处理日期格式
            if 'trade_date' in save_df.columns:
                save_df['trade_date'] = save_df['trade_date'].dt.strftime('%Y%m%d')
            
            # 保存到数据库
            count = len(save_df)
            save_df.to_sql(table_name, self.engine, if_exists='append', index=False)
            
            logger.info(f"成功保存{count}条记录到数据库表{table_name}")
            return count
        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}")
            return 0
    
    def fetch_and_save_stock_data(self, ts_code: str, start_date: str = None, end_date: str = None) -> int:
        """
        获取并保存单只股票的数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 保存的记录数
        """
        try:
            # 获取各类数据
            daily_df = self.get_daily_data(ts_code, start_date, end_date)
            moneyflow_df = self.get_moneyflow_data(ts_code, start_date, end_date)
            
            # 获取最新的每日指标数据
            if end_date:
                daily_basic_df = self.get_daily_basic_data(ts_code, end_date)
            else:
                daily_basic_df = self.get_daily_basic_data(ts_code)
            
            # 获取涨跌停数据（只获取最新日期）
            limit_list_df = None
            if end_date:
                limit_list_df = self.get_limit_list_data(end_date, limit_type='ALL')
                if not limit_list_df.empty:
                    limit_list_df = limit_list_df[limit_list_df['ts_code'] == ts_code]
            
            # 合并数据
            merged_df = self.merge_stock_data(daily_df, moneyflow_df, daily_basic_df, limit_list_df)
            
            # 清洗数据
            cleaned_df = self.clean_stock_data(merged_df)
            
            # 保存到数据库
            count = self.save_to_database(cleaned_df)
            
            return count
        except Exception as e:
            logger.error(f"获取并保存股票{ts_code}数据失败: {e}")
            return 0
    
    def fetch_and_save_limit_data(self, trade_date: str = None) -> int:
        """
        获取并保存当日涨跌停数据
        :param trade_date: 日期(YYYYMMDD)
        :return: 保存的记录数
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            # 获取所有涨跌停数据
            limit_df = self.get_limit_list_data(trade_date, limit_type='ALL')
            
            if limit_df.empty:
                logger.info(f"日期{trade_date}没有涨跌停数据")
                return 0
            
            # 保存到数据库
            count = self.save_to_database(limit_df, table_name='limit_stock_data')
            
            # 同时获取涨跌停分时数据
            for _, row in limit_df.iterrows():
                ts_code = row['ts_code']
                step_df = self.get_limit_step_data(ts_code, trade_date)
                if not step_df.empty:
                    self.save_to_database(step_df, table_name='limit_step_data')
                    logger.info(f"成功保存股票{ts_code}涨跌停分时数据")
            
            logger.info(f"成功保存{count}条涨跌停数据及对应分时数据")
            return count
        except Exception as e:
            logger.error(f"获取并保存涨跌停数据失败: {e}")
            return 0
    
    def fetch_and_save_batch_stocks(self, ts_codes: List[str], start_date: str = None, end_date: str = None) -> Dict[str, int]:
        """
        批量获取并保存股票数据
        :param ts_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 每个股票的保存记录数
        """
        result = {}
        
        for ts_code in ts_codes:
            try:
                count = self.fetch_and_save_stock_data(ts_code, start_date, end_date)
                result[ts_code] = count
            except Exception as e:
                logger.error(f"处理股票{ts_code}失败: {e}")
                result[ts_code] = 0
        
        return result

if __name__ == '__main__':
    """测试示例"""
    try:
        # 初始化数据获取器
        fetcher = TushareDataFetcher()
        
        # 获取单只股票数据
        ts_code = "600000.SH"
        count = fetcher.fetch_and_save_stock_data(ts_code, start_date="20260101")
        print(f"成功保存{count}条记录")
        
        # 批量获取股票数据
        # ts_codes = ["600000.SH", "000001.SZ", "600036.SH"]
        # results = fetcher.fetch_and_save_batch_stocks(ts_codes, start_date="20260101")
        # print("批量保存结果:", results)
        
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)