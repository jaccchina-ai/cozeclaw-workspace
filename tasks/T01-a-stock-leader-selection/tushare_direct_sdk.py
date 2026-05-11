#!/usr/bin/env python3
"""
T01 选股系统 - Tushare数据获取脚本
直接使用Tushare Python SDK获取数据
支持：股票行情、资金流向、涨跌停数据
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tushare as ts
from typing import Dict, List, Tuple, Optional
import json
import logging
from sqlalchemy import create_engine, text
from database.models import DailyStockData, LimitStockData, LimitStepData, Base
from sqlalchemy.orm import sessionmaker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tushare_data_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TushareDirectFetcher:
    def __init__(self, token: str = None):
        """
        直接初始化Tushare SDK
        :param token: Tushare token
        """
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        self._init_tushare()
        self.engine = self._init_database()
        self.Session = sessionmaker(bind=self.engine)
    
    def _init_tushare(self):
        """初始化Tushare SDK"""
        try:
            if not self.token:
                raise ValueError("Tushare token未设置，请通过参数或环境变量TUSHARE_TOKEN提供")
            
            # 初始化Tushare
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            
            # 测试连接
            test_df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code')
            if not test_df.empty:
                logger.info("Tushare SDK初始化成功")
            else:
                raise ConnectionError("Tushare API调用失败")
                
        except Exception as e:
            logger.error(f"初始化Tushare SDK失败: {e}")
            raise
    
    def _init_database(self):
        """初始化数据库连接"""
        try:
            # 从配置文件获取数据库连接信息
            config = {}
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
            
            db_url = config.get('database', {}).get('url', 'postgresql://postgres:***@cp-hip-veil-65383f4d.pg5.aidap-global.cn-beijing.volces.com:5432/postgres?sslmode=require')
            
            engine = create_engine(db_url)
            # 创建表（如果不存在）
            Base.metadata.create_all(engine)
            logger.info("数据库连接初始化成功")
            return engine
        except Exception as e:
            logger.error(f"初始化数据库连接失败: {e}")
            raise
    
    def get_stock_list(self, list_status: str = 'L') -> pd.DataFrame:
        """
        获取股票列表
        :param list_status: 上市状态: L-上市 D-退市 P-暂停上市
        :return: 股票列表DataFrame
        """
        try:
            logger.info(f"开始获取股票列表，状态: {list_status}")
            df = self.pro.stock_basic(
                exchange='',
                list_status=list_status,
                fields='ts_code,symbol,name,area,industry,list_date,market,list_status'
            )
            logger.info(f"成功获取{len(df)}只股票")
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
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
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            logger.info(f"获取股票{ts_code}行情数据，日期范围: {start_date}至{end_date}")
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"成功获取{len(df)}条行情数据")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_money_flow_data(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
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
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            logger.info(f"获取股票{ts_code}资金流向数据，日期范围: {start_date}至{end_date}")
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"成功获取{len(df)}条资金流向数据")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}资金流向数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_data(self, trade_date: str = None, limit_type: str = 'U') -> pd.DataFrame:
        """
        获取涨跌停数据（limit_list_d接口）
        :param trade_date: 日期(YYYYMMDD)
        :param limit_type: 涨跌停类型: U-涨停, D-跌停, ALL-全部
        :return: 涨跌停数据DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"获取涨跌停数据，日期: {trade_date}, 类型: {limit_type}")
            df = self.pro.limit_list_d(
                trade_date=trade_date,
                limit_type=limit_type,
                fields='ts_code,name,close,pct_chg,limit_price,open_times,up_stat,trade_date,exchange,limit_type'
            )
            logger.info(f"成功获取{len(df)}条涨跌停数据")
            return df
        except Exception as e:
            logger.error(f"获取涨跌停数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_step_data(self, ts_code: str, trade_date: str = None) -> pd.DataFrame:
        """
        获取涨跌停分时数据（limit_step接口）
        :param ts_code: 股票代码
        :param trade_date: 日期(YYYYMMDD)
        :return: 涨跌停分时数据DataFrame
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(f"获取股票{ts_code}涨跌停分时数据，日期: {trade_date}")
            df = self.pro.limit_step(
                ts_code=ts_code,
                trade_date=trade_date,
                fields='ts_code,trade_date,time,price,pct_chg,vol,amount,type,status'
            )
            logger.info(f"成功获取{len(df)}条涨跌停分时数据")
            return df
        except Exception as e:
            logger.error(f"获取股票{ts_code}涨跌停分时数据失败: {e}")
            return pd.DataFrame()
    
    def get_today_limit_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        获取今日涨跌停数据
        :return: (涨停数据, 跌停数据)
        """
        today = datetime.now().strftime("%Y%m%d")
        
        # 获取涨停数据
        up_df = self.get_limit_data(today, limit_type='U')
        
        # 获取跌停数据
        down_df = self.get_limit_data(today, limit_type='D')
        
        return up_df, down_df
    
    def save_to_database(self, df: pd.DataFrame, model_class, if_exists: str = 'append') -> int:
        """
        将数据保存到数据库
        :param df: 要保存的数据
        :param model_class: 数据库模型类
        :param if_exists: 存在时的处理方式: append/replace/fail
        :return: 保存的记录数
        """
        if df.empty:
            logger.warning("没有数据需要保存")
            return 0
        
        try:
            session = self.Session()
            
            # 处理日期格式
            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)
            
            # 转换为模型对象
            records = df.to_dict('records')
            count = 0
            
            for record in records:
                # 创建模型实例
                model_instance = model_class(**record)
                session.add(model_instance)
                count += 1
            
            session.commit()
            session.close()
            
            logger.info(f"成功保存{count}条记录到数据库")
            return count
        except Exception as e:
            session.rollback()
            session.close()
            logger.error(f"保存数据到数据库失败: {e}")
            return 0
    
    def sync_single_stock(self, ts_code: str, start_date: str = None, end_date: str = None) -> Dict:
        """
        同步单只股票的所有数据
        :param ts_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 同步结果
        """
        try:
            result = {
                'ts_code': ts_code,
                'daily_count': 0,
                'money_flow_count': 0,
                'success': False
            }
            
            # 获取行情数据
            daily_df = self.get_daily_data(ts_code, start_date, end_date)
            if not daily_df.empty:
                daily_count = self.save_to_database(daily_df, DailyStockData)
                result['daily_count'] = daily_count
            
            # 获取资金流向数据
            money_flow_df = self.get_money_flow_data(ts_code, start_date, end_date)
            if not money_flow_df.empty:
                # 合并到行情数据
                if not daily_df.empty:
                    merged_df = daily_df.merge(money_flow_df, on=['ts_code', 'trade_date'], how='left')
                    self.save_to_database(merged_df, DailyStockData, if_exists='replace')
                else:
                    money_flow_count = self.save_to_database(money_flow_df, DailyStockData)
                    result['money_flow_count'] = money_flow_count
            
            result['success'] = True
            logger.info(f"股票{ts_code}数据同步完成")
            return result
            
        except Exception as e:
            logger.error(f"同步股票{ts_code}数据失败: {e}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def sync_limit_data(self, trade_date: str = None) -> Dict:
        """
        同步涨跌停数据
        :param trade_date: 日期(YYYYMMDD)
        :return: 同步结果
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            
            result = {
                'trade_date': trade_date,
                'up_limit_count': 0,
                'down_limit_count': 0,
                'step_data_count': 0,
                'success': False
            }
            
            # 获取涨跌停数据
            up_df, down_df = self.get_today_limit_data()
            
            # 保存涨停数据
            if not up_df.empty:
                up_count = self.save_to_database(up_df, LimitStockData)
                result['up_limit_count'] = up_count
            
            # 保存跌停数据
            if not down_df.empty:
                down_count = self.save_to_database(down_df, LimitStockData)
                result['down_limit_count'] = down_count
            
            # 获取并保存分时数据
            all_limit_df = pd.concat([up_df, down_df])
            step_count = 0
            
            for _, row in all_limit_df.iterrows():
                ts_code = row['ts_code']
                step_df = self.get_limit_step_data(ts_code, trade_date)
                if not step_df.empty:
                    step_count += self.save_to_database(step_df, LimitStepData)
            
            result['step_data_count'] = step_count
            result['success'] = True
            
            logger.info(f"{trade_date}涨跌停数据同步完成: {len(all_limit_df)}只股票, {step_count}条分时数据")
            return result
            
        except Exception as e:
            logger.error(f"同步涨跌停数据失败: {e}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def batch_sync_stocks(self, ts_codes: List[str], start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        批量同步股票数据
        :param ts_codes: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 批量同步结果
        """
        results = []
        
        for i, ts_code in enumerate(ts_codes, 1):
            logger.info(f"正在同步第{i}/{len(ts_codes)}只股票: {ts_code}")
            result = self.sync_single_stock(ts_code, start_date, end_date)
            results.append(result)
            
            # 每10只股票后休息1秒，避免API调用过于频繁
            if i % 10 == 0:
                import time
                time.sleep(1)
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"批量同步完成: 成功{success_count}/{len(ts_codes)}只股票")
        
        return results

def main():
    """主函数"""
    try:
        # 解析命令行参数
        import argparse
        parser = argparse.ArgumentParser(description='Tushare数据获取脚本')
        parser.add_argument('--token', help='Tushare token')
        parser.add_argument('--sync-stock', help='同步单只股票数据，格式: 600000.SH')
        parser.add_argument('--sync-limit', action='store_true', help='同步当日涨跌停数据')
        parser.add_argument('--batch-sync', nargs='+', help='批量同步股票数据，格式: 600000.SH 000001.SZ')
        parser.add_argument('--start-date', help='开始日期(YYYYMMDD)')
        parser.add_argument('--end-date', help='结束日期(YYYYMMDD)')
        
        args = parser.parse_args()
        
        # 初始化fetcher
        fetcher = TushareDirectFetcher(args.token)
        
        if args.sync_stock:
            # 同步单只股票
            result = fetcher.sync_single_stock(args.sync_stock, args.start_date, args.end_date)
            print(f"同步结果: {result}")
            
        elif args.sync_limit:
            # 同步涨跌停数据
            result = fetcher.sync_limit_data()
            print(f"涨跌停数据同步结果: {result}")
            
        elif args.batch_sync:
            # 批量同步
            results = fetcher.batch_sync_stocks(args.batch_sync, args.start_date, args.end_date)
            print(f"批量同步完成，共处理{len(results)}只股票")
            
        else:
            # 显示帮助
            parser.print_help()
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()