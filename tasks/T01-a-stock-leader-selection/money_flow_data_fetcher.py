#!/usr/bin/env python3
"""
T01 选股系统 - 资金流向数据获取模块
从Tushare获取股票基础数据和资金流向数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tushare as ts
import json
import sqlite3
from sqlalchemy import text

class MoneyFlowDataFetcher:
    """资金流向数据获取器"""
    
    def __init__(self):
        from database.models import get_session, DB_TYPE, POSTGRES_CONFIG
        self.session = get_session()
        self.db_type = DB_TYPE
        self.postgres_config = POSTGRES_CONFIG
        
        # 初始化Tushare
        try:
            # 从配置文件读取Tushare token
            import os
            token_found = False
            
            # 尝试从环境变量获取
            self.ts_token = os.environ.get('TUSHARE_TOKEN', '')
            if self.ts_token:
                token_found = True
            
            # 尝试从config.json获取
            if not token_found:
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self.ts_token = config.get('tushare_token', '')
                        if self.ts_token:
                            token_found = True
                except:
                    pass
            
            # 尝试从数据库配置获取
            if not token_found:
                try:
                    from database.db_config import TUSHARE_TOKEN
                    self.ts_token = TUSHARE_TOKEN
                    token_found = True
                except:
                    try:
                        with open('database/db_config.py', 'r', encoding='utf-8') as f:
                            content = f.read()
                            import re
                            match = re.search(r"TUSHARE_TOKEN[\s]*=[\s]*['\"]([^'\"]+)['\"]", content, re.IGNORECASE)
                            if match:
                                self.ts_token = match.group(1)
                                token_found = True
                    except:
                        pass
            
            # 尝试从上级目录配置获取
            if not token_found:
                try:
                    with open('../../config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self.ts_token = config.get('tushare_token', '')
                        if self.ts_token:
                            token_found = True
                except:
                    pass
            
            if token_found:
                ts.set_token(self.ts_token)
                self.pro = ts.pro_api()
                print("Tushare 初始化成功")
            else:
                print("未找到Tushare token，请设置环境变量TUSHARE_TOKEN或添加到config.json")
                self.pro = None
                
        except Exception as e:
            print(f"Tushare 初始化失败: {e}")
            self.pro = None
    
    def get_daily_stock_data(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票日K线数据和资金流向数据
        """
        if not self.pro:
            print("Tushare 未初始化，无法获取数据")
            return pd.DataFrame()
        
        try:
            # 1. 获取日K线数据
            df_daily = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df_daily.empty:
                print(f"未获取到 {ts_code} 的日K数据")
                return pd.DataFrame()
            
            # 2. 获取资金流向数据
            df_moneyflow = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            # 3. 合并数据
            if not df_moneyflow.empty:
                df_merged = pd.merge(df_daily, df_moneyflow, on=['ts_code', 'trade_date'], how='left')
            else:
                df_merged = df_daily
                print(f"未获取到 {ts_code} 的资金流向数据")
            
            # 4. 添加股票基本信息
            df_basic = self.pro.stock_basic(ts_code=ts_code)
            if not df_basic.empty:
                df_merged['name'] = df_basic['name'].iloc[0]
                df_merged['industry'] = df_basic['industry'].iloc[0]
            
            # 5. 计算扩展字段
            df_merged = self._calculate_extra_fields(df_merged)
            
            return df_merged
            
        except Exception as e:
            print(f"获取 {ts_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def _calculate_extra_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算扩展字段"""
        if df.empty:
            return df
        
        # 计算换手率
        if 'vol' in df.columns and 'free_share' in df.columns:
            df['turnover_rate'] = df['vol'] / df['free_share'] * 100
            
        # 计算量比（简单计算）
        if 'vol' in df.columns:
            df['volume_ratio'] = df['vol'] / df['vol'].rolling(5).mean()
            
        # 计算主力资金占比
        if 'net_mf_vol' in df.columns and 'vol' in df.columns:
            df['main_net_ratio'] = df['net_mf_vol'] / df['vol'] * 100
            
        # 重命名字段匹配数据库
        column_mapping = {
            'ts_code': 'ts_code',
            'trade_date': 'trade_date',
            'name': 'name',
            'industry': 'industry',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'pre_close': 'pre_close',
            'change': 'change',
            'pct_chg': 'pct_chg',
            'vol': 'vol',
            'amount': 'amount',
            'net_mf_vol': 'main_net_inflow',  # 主力净流入(万元)
            'main_net_ratio': 'main_net_ratio',  # 主力净占比(%)
            'mid_mf_vol': 'medium_net',  # 中单净额(万元)
            'mid_mf_ratio': 'medium_net_ratio',  # 中单净占比(%)
            'sm_mf_vol': 'small_net',  # 散户净额(万元)
            'sm_mf_ratio': 'small_net_ratio',  # 散户净占比(%)
            'turnover_rate': 'turnover_rate',
            'volume_ratio': 'volume_ratio'
        }
        
        # 只保留需要的字段
        df = df.rename(columns=column_mapping)
        df = df[list(column_mapping.values())]
        
        return df
    
    def save_to_database(self, df: pd.DataFrame) -> int:
        """
        将数据保存到数据库
        """
        if df.empty:
            print("没有数据可保存")
            return 0
        
        try:
            # 获取数据库连接
            if self.db_type == 'postgres':
                import psycopg2
                conn = psycopg2.connect(
                    host=self.postgres_config['host'],
                    port=self.postgres_config['port'],
                    database=self.postgres_config['database'],
                    user=self.postgres_config['user'],
                    password=self.postgres_config['password']
                )
            else:
                conn = sqlite3.connect('database/t01_stocks.db')
            
            # 数据写入
            cursor = conn.cursor()
            
            # 先删除已有数据避免重复
            for _, row in df.iterrows():
                delete_query = """
                DELETE FROM daily_stock_data
                WHERE ts_code = %s AND trade_date = %s
                """ if self.db_type == 'postgres' else """
                DELETE FROM daily_stock_data
                WHERE ts_code = ? AND trade_date = ?
                """
                cursor.execute(delete_query, (row['ts_code'], row['trade_date']))
            
            # 插入新数据
            insert_query = """
            INSERT INTO daily_stock_data (
                ts_code, trade_date, name, industry, open, high, low, close,
                pre_close, change, pct_chg, vol, amount, main_net_inflow,
                main_net_ratio, medium_net, small_net, turnover_rate, volume_ratio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """ if self.db_type == 'postgres' else """
            INSERT INTO daily_stock_data (
                ts_code, trade_date, name, industry, open, high, low, close,
                pre_close, change, pct_chg, vol, amount, main_net_inflow,
                main_net_ratio, medium_net, small_net, turnover_rate, volume_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            count = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute(insert_query, (
                        row['ts_code'], row['trade_date'], row['name'], row['industry'],
                        row['open'], row['high'], row['low'], row['close'],
                        row['pre_close'], row['change'], row['pct_chg'], row['vol'],
                        row['amount'], row.get('main_net_inflow'), row.get('main_net_ratio'),
                        row.get('medium_net'), row.get('small_net'), row.get('turnover_rate'),
                        row.get('volume_ratio')
                    ))
                    count += 1
                except Exception as e:
                    print(f"插入数据失败 {row['ts_code']} {row['trade_date']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            return count
            
        except Exception as e:
            print(f"保存数据失败: {e}")
            return 0
    
    def fetch_and_save_stocks(self, ts_codes: list, start_date: str = None, end_date: str = None):
        """
        获取多只股票的数据并保存
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
            
        print(f"开始获取 {start_date} 至 {end_date} 的数据...")
        
        total_success = 0
        total_count = 0
        
        for i, ts_code in enumerate(ts_codes):
            print(f"\n({i+1}/{len(ts_codes)}) 获取 {ts_code}...")
            
            # 获取数据
            df = self.get_daily_stock_data(ts_code, start_date, end_date)
            
            if not df.empty:
                # 保存数据
                save_count = self.save_to_database(df)
                total_success += save_count
                total_count += len(df)
                print(f"成功保存 {save_count} 条记录")
            else:
                print(f"未获取到 {ts_code} 有效数据")
                
        print(f"\n=== 数据获取完成 ===")
        print(f"总尝试天数: {total_count}")
        print(f"成功保存: {total_success} 条记录")
        print(f"成功率: {total_success/total_count*100:.1f}%" if total_count > 0 else "无数据")
    
    def get_hot_stocks(self, limit: int = 50) -> list:
        """
        获取热门股票列表
        """
        if not self.pro:
            print("Tushare 未初始化，无法获取数据")
            return []
        
        try:
            # 获取涨停股票
            df_limitup = self.pro.limit_up(
                trade_date=datetime.now().strftime('%Y%m%d'),
                limit_type='U'
            )
            
            # 获取热点板块股票
            df_sector = self.pro.ths_index()
            
            # 合并去重
            hot_stocks = []
            if not df_limitup.empty:
                hot_stocks.extend(df_limitup['ts_code'].tolist())
            if not df_sector.empty:
                hot_stocks.extend(df_sector['component'].dropna().tolist())
            
            # 去重
            hot_stocks = list(set(hot_stocks))
            
            # 获取股票基本信息过滤ST和退市股
            df_basic = self.pro.stock_basic(
                ts_code=','.join(hot_stocks),
                list_status='L'
            )
            
            return df_basic['ts_code'].tolist()[:limit]
            
        except Exception as e:
            print(f"获取热门股票失败: {e}")
            # 返回默认股票列表
            return ['000001.SZ', '000002.SZ', '000063.SZ', '600000.SH', '600036.SH']

def main():
    """主函数"""
    fetcher = MoneyFlowDataFetcher()
    
    # 获取热门股票列表
    print("获取热门股票列表...")
    hot_stocks = fetcher.get_hot_stocks(20)
    print(f"获取到 {len(hot_stocks)} 只热门股票")
    
    # 获取最近30天数据
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    
    # 获取并保存数据
    fetcher.fetch_and_save_stocks(hot_stocks, start_date, end_date)
    
    # 测试单只股票
    # df = fetcher.get_daily_stock_data('000001.SZ', start_date, end_date)
    # print(df.head())
    # save_count = fetcher.save_to_database(df)
    # print(f"保存了 {save_count} 条记录")

if __name__ == '__main__':
    main()