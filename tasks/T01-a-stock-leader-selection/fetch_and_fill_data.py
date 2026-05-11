#!/usr/bin/env python3
"""
T01 选股系统 - 数据获取与填充脚本（优化版）

业务逻辑：
- T日选股策略：只从涨停股中选出最优质股票
- 因此只需要获取涨停股相关数据，不需要全市场行情

数据获取策略：
1. 获取涨跌停列表（确定候选股票池）
2. 获取涨停股的资金流向（计算因子）
3. 获取市场情绪数据（整体市场热度）

使用方法:
    python3 fetch_and_fill_data.py                  # 获取今天的数据
    python3 fetch_and_fill_data.py --date 20260403 # 获取指定日期数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import sqlite3
import time

# 导入配置
with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
    config = json.load(f)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入数据库模块
from database.db_config import DB_TYPE, POSTGRES_CONFIG, SQLITE_DB_PATH
from database.models import init_db, get_session
from sqlalchemy import text


class DataFetcher:
    """数据获取器 - 针对涨停股优化"""
    
    def __init__(self):
        # 从配置文件读取 token
        self.token = config.get('tushare', {}).get('token', '')
        if not self.token:
            raise ValueError("Tushare token未在config.json中配置")
        self.pro = ts.pro_api(self.token)
        logger.info(f"✅ Tushare 初始化成功")
        
        # 初始化数据库
        init_db()
        self.session = get_session()
        logger.info(f"✅ 数据库初始化成功 (类型: {DB_TYPE})")
    
    def get_limit_list_d(self, trade_date: str) -> pd.DataFrame:
        """获取涨跌停列表（涨停+跌停）"""
        try:
            dfs = []
            
            # 获取涨停
            try:
                df_u = self.pro.limit_list_d(trade_date=trade_date, limit_type='U')
                if df_u is not None and not df_u.empty:
                    df_u['limit_type'] = 'U'  # 添加标识
                    dfs.append(df_u)
            except Exception as e:
                logger.warning(f"获取涨停数据失败: {e}")
            
            # 获取跌停
            try:
                df_d = self.pro.limit_list_d(trade_date=trade_date, limit_type='D')
                if df_d is not None and not df_d.empty:
                    df_d['limit_type'] = 'D'  # 添加标识
                    dfs.append(df_d)
            except Exception as e:
                logger.warning(f"获取跌停数据失败: {e}")
            
            if not dfs:
                return pd.DataFrame()
            elif len(dfs) == 1:
                df = dfs[0].copy()
            else:
                df = pd.concat(dfs, ignore_index=True)
            
            logger.info(f"✅ 获取涨跌停列表成功: {len(df)} 只 ({trade_date})")
            return df
        except Exception as e:
            logger.error(f"❌ 获取涨跌停列表失败: {e}")
            return pd.DataFrame()
    
    def get_moneyflow_data(self, trade_date: str) -> pd.DataFrame:
        """获取资金流向数据（全市场，用于计算市场情绪）"""
        try:
            df = self.pro.moneyflow(trade_date=trade_date)
            logger.info(f"✅ 获取资金流向数据成功: {len(df)} 条 ({trade_date})")
            return df
        except Exception as e:
            logger.error(f"❌ 获取资金流向数据失败: {e}")
            return pd.DataFrame()
    
    def get_market_sentiment(self, trade_date: str) -> dict:
        """获取市场情绪指标"""
        try:
            # 获取涨跌停数量
            limit_df = self.get_limit_list_d(trade_date)
            zt_count = len(limit_df[limit_df['limit_type'] == 'U']) if not limit_df.empty else 0
            dt_count = len(limit_df[limit_df['limit_type'] == 'D']) if not limit_df.empty else 0
            
            # 获取资金流向（市场整体）
            mf_df = self.get_moneyflow_data(trade_date)
            
            # 计算情绪指标
            north_money = 0  # 北向资金（需要额外接口）
            
            sentiment = {
                'trade_date': trade_date,
                'zt_count': zt_count,
                'dt_count': dt_count,
                'zt_dt_ratio': zt_count / (dt_count + 1),  # 涨跌停比
                'total_money': mf_df['net_mf_amount'].sum() if not mf_df.empty else 0,
                'main_net': mf_df['net_mf_amount'].sum() if not mf_df.empty else 0,
                'north_money': north_money,
            }
            
            logger.info(f"✅ 市场情绪: 涨停{zt_count}只, 跌停{dt_count}只")
            return sentiment
            
        except Exception as e:
            logger.error(f"❌ 获取市场情绪失败: {e}")
            return {}
    
    def get_limit_stock_moneyflow(self, ts_code: str, trade_date: str) -> pd.DataFrame:
        """获取单只涨停股的资金流向"""
        try:
            df = self.pro.moneyflow(ts_code=ts_code, trade_date=trade_date)
            return df
        except Exception as e:
            return pd.DataFrame()


class DatabaseWriter:
    """数据库写入器 - 双写 PG + SQLite"""
    
    def __init__(self):
        init_db()
        self.session = get_session()
        self.sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        self.sqlite_cursor = self.sqlite_conn.cursor()
        logger.info(f"✅ 数据库写入器初始化完成")
    
    def save_limit_stocks(self, df: pd.DataFrame, trade_date: str) -> dict:
        """保存涨跌停数据"""
        if df.empty:
            return {'postgres': 0, 'sqlite': 0}
        
        pg_count = 0
        sqlite_count = 0
        
        for _, row in df.iterrows():
            record = {
                'ts_code': row['ts_code'],
                'trade_date': trade_date,
                'name': row.get('name', ''),
                'close': row.get('close', 0),
                'pct_chg': row.get('pct_chg', 0),
                'limit_price': row.get('limit_price', 0),
                'open_times': row.get('open_times', 0),
                'up_stat': row.get('up_stat', 0),
                'exchange': row.get('exchange', ''),
                'limit_type': row.get('limit_type', ''),
                'industry': row.get('industry', ''),  # 行业
                'market': row.get('market', ''),     # 市场
            }
            
            # PostgreSQL
            try:
                self.session.execute(text("""
                    INSERT INTO limit_up_stocks 
                    (ts_code, trade_date, name, close, pct_chg, limit_price, open_times, up_stat, exchange, limit_type, industry, market)
                    VALUES (:ts_code, :trade_date, :name, :close, :pct_chg, :limit_price, :open_times, :up_stat, :exchange, :limit_type, :industry, :market)
                    ON CONFLICT DO NOTHING
                """), record)
                pg_count += 1
            except Exception as e:
                pass
            
            # SQLite
            try:
                self.sqlite_cursor.execute("""
                    INSERT OR IGNORE INTO limit_up_stocks 
                    (ts_code, trade_date, name, close, pct_chg, limit_price, open_times, up_stat, exchange, limit_type, industry, market)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (record['ts_code'], record['trade_date'], record['name'], 
                      record['close'], record['pct_chg'], record['limit_price'],
                      record['open_times'], record['up_stat'], record['exchange'], 
                      record['limit_type'], record.get('industry', ''), record.get('market', '')))
                sqlite_count += 1
            except Exception as e:
                pass
        
        try:
            self.session.commit()
        except:
            self.session.rollback()
        
        self.sqlite_conn.commit()
        
        return {'postgres': pg_count, 'sqlite': sqlite_count}
    
    def save_moneyflow_data(self, df: pd.DataFrame, trade_date: str) -> dict:
        """保存资金流向数据"""
        if df.empty:
            return {'postgres': 0, 'sqlite': 0}
        
        pg_count = 0
        sqlite_count = 0
        
        for _, row in df.iterrows():
            record = {
                'ts_code': row['ts_code'],
                'trade_date': trade_date,
                'buy_sm_vol': row.get('buy_sm_vol', 0),
                'buy_sm_amount': row.get('buy_sm_amount', 0),
                'sell_sm_vol': row.get('sell_sm_vol', 0),
                'sell_sm_amount': row.get('sell_sm_amount', 0),
                'buy_md_vol': row.get('buy_md_vol', 0),
                'buy_md_amount': row.get('buy_md_amount', 0),
                'sell_md_vol': row.get('sell_md_vol', 0),
                'sell_md_amount': row.get('sell_md_amount', 0),
                'buy_lg_vol': row.get('buy_lg_vol', 0),
                'buy_lg_amount': row.get('buy_lg_amount', 0),
                'sell_lg_vol': row.get('sell_lg_vol', 0),
                'sell_lg_amount': row.get('sell_lg_amount', 0),
                'buy_elg_vol': row.get('buy_elg_vol', 0),
                'buy_elg_amount': row.get('buy_elg_amount', 0),
                'sell_elg_vol': row.get('sell_elg_vol', 0),
                'sell_elg_amount': row.get('sell_elg_amount', 0),
                'net_mf_vol': row.get('net_mf_vol', 0),
                'net_mf_amount': row.get('net_mf_amount', 0)
            }
            
            # PostgreSQL
            try:
                self.session.execute(text("""
                    INSERT INTO moneyflow_data 
                    (ts_code, trade_date, buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
                     buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
                     buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
                     buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
                     net_mf_vol, net_mf_amount)
                    VALUES (:ts_code, :trade_date, :buy_sm_vol, :buy_sm_amount, :sell_sm_vol, :sell_sm_amount,
                            :buy_md_vol, :buy_md_amount, :sell_md_vol, :sell_md_amount,
                            :buy_lg_vol, :buy_lg_amount, :sell_lg_vol, :sell_lg_amount,
                            :buy_elg_vol, :buy_elg_amount, :sell_elg_vol, :sell_elg_amount,
                            :net_mf_vol, :net_mf_amount)
                    ON CONFLICT DO NOTHING
                """), record)
                pg_count += 1
            except Exception as e:
                pass
            
            # SQLite
            try:
                self.sqlite_cursor.execute("""
                    INSERT OR IGNORE INTO moneyflow_data 
                    (ts_code, trade_date, buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
                     buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
                     buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
                     buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
                     net_mf_vol, net_mf_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (record['ts_code'], record['trade_date'],
                      record['buy_sm_vol'], record['buy_sm_amount'], record['sell_sm_vol'], record['sell_sm_amount'],
                      record['buy_md_vol'], record['buy_md_amount'], record['sell_md_vol'], record['sell_md_amount'],
                      record['buy_lg_vol'], record['buy_lg_amount'], record['sell_lg_vol'], record['sell_lg_amount'],
                      record['buy_elg_vol'], record['buy_elg_amount'], record['sell_elg_vol'], record['sell_elg_amount'],
                      record['net_mf_vol'], record['net_mf_amount']))
                sqlite_count += 1
            except Exception as e:
                pass
        
        try:
            self.session.commit()
        except:
            self.session.rollback()
        
        self.sqlite_conn.commit()
        
        return {'postgres': pg_count, 'sqlite': sqlite_count}
    
    def save_market_sentiment(self, sentiment: dict) -> dict:
        """保存市场情绪数据"""
        if not sentiment:
            return {'postgres': 0, 'sqlite': 0}
        
        record = {
            'trade_date': sentiment.get('trade_date'),
            'zt_count': sentiment.get('zt_count', 0),
            'dt_count': sentiment.get('dt_count', 0),
            'zt_dt_ratio': sentiment.get('zt_dt_ratio', 0),
            'total_money': sentiment.get('total_money', 0),
            'main_net': sentiment.get('main_net', 0),
            'north_money': sentiment.get('north_money', 0),
        }
        
        pg_ok = False
        sqlite_ok = False
        
        # PostgreSQL
        try:
            self.session.execute(text("""
                INSERT INTO market_sentiment 
                (trade_date, zt_count, dt_count, zt_dt_ratio, total_money, main_net, north_money)
                VALUES (:trade_date, :zt_count, :dt_count, :zt_dt_ratio, :total_money, :main_net, :north_money)
                ON CONFLICT (trade_date) DO UPDATE SET
                    zt_count = EXCLUDED.zt_count,
                    dt_count = EXCLUDED.dt_count,
                    zt_dt_ratio = EXCLUDED.zt_dt_ratio,
                    total_money = EXCLUDED.total_money,
                    main_net = EXCLUDED.main_net,
                    north_money = EXCLUDED.north_money
            """), record)
            self.session.commit()
            pg_ok = True
        except Exception as e:
            self.session.rollback()
            logger.error(f"PG保存情绪数据失败: {e}")
        
        # SQLite
        try:
            self.sqlite_cursor.execute("""
                INSERT INTO market_sentiment 
                (trade_date, zt_count, dt_count, zt_dt_ratio, total_money, main_net, north_money)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_date) DO UPDATE SET
                    zt_count = excluded.zt_count,
                    dt_count = excluded.dt_count,
                    zt_dt_ratio = excluded.zt_dt_ratio,
                    total_money = excluded.total_money,
                    main_net = excluded.main_net,
                    north_money = excluded.north_money
            """, (record['trade_date'], record['zt_count'], record['dt_count'],
                  record['zt_dt_ratio'], record['total_money'], record['main_net'], record['north_money']))
            self.sqlite_conn.commit()
            sqlite_ok = True
        except Exception as e:
            logger.error(f"SQLite保存情绪数据失败: {e}")
        
        return {'postgres': int(pg_ok), 'sqlite': int(sqlite_ok)}
    
    def close(self):
        """关闭数据库连接"""
        if self.session:
            self.session.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()


def main(trade_date: str = None):
    """主函数"""
    if not trade_date:
        trade_date = datetime.now().strftime('%Y%m%d')
    
    print("\n" + "="*60)
    print("📊 T01 数据获取与填充（优化版）")
    print(f"📅 日期: {trade_date}")
    print("💡 策略：只获取涨停股相关数据")
    print("="*60 + "\n")
    
    # 初始化
    fetcher = DataFetcher()
    writer = DatabaseWriter()
    
    try:
        # 1. 获取涨跌停数据（核心数据源）
        print("\n📥 步骤1: 获取涨跌停数据...")
        limit_df = fetcher.get_limit_list_d(trade_date)
        if not limit_df.empty:
            result = writer.save_limit_stocks(limit_df, trade_date)
            zt_count = len(limit_df[limit_df['limit_type'] == 'U'])
            dt_count = len(limit_df[limit_df['limit_type'] == 'D'])
            print(f"   ✅ 涨跌停数据已保存")
            print(f"      涨停: {zt_count} 只 | 跌停: {dt_count} 只")
            print(f"      (PG: {result['postgres']}, SQLite: {result['sqlite']})")
        else:
            print(f"   ⚠️ 今日无涨跌停数据（可能是非交易日）")
        
        # 等待避免IP限制
        time.sleep(2)
        
        # 2. 获取资金流向数据（市场整体，用于计算情绪）
        print("\n📥 步骤2: 获取资金流向数据...")
        moneyflow_df = fetcher.get_moneyflow_data(trade_date)
        if not moneyflow_df.empty:
            result = writer.save_moneyflow_data(moneyflow_df, trade_date)
            print(f"   ✅ 资金流向已保存: {result['postgres']} 条")
        else:
            print(f"   ⚠️ 获取资金流向失败")
        
        # 等待避免IP限制
        time.sleep(2)
        
        # 3. 获取并保存市场情绪
        print("\n📥 步骤3: 计算并保存市场情绪...")
        sentiment = fetcher.get_market_sentiment(trade_date)
        if sentiment:
            result = writer.save_market_sentiment(sentiment)
            print(f"   ✅ 市场情绪已保存")
            print(f"      涨停: {sentiment.get('zt_count', 0)} | 跌停: {sentiment.get('dt_count', 0)}")
            print(f"      涨停/跌停比: {sentiment.get('zt_dt_ratio', 0):.2f}")
        
        # 汇总
        print("\n" + "="*60)
        print("📈 数据获取汇总")
        print("="*60)
        print(f"   📊 涨跌停数据: {len(limit_df) if not limit_df.empty else 0} 条 (候选股票池)")
        print(f"   💰 资金流向: {len(moneyflow_df) if not moneyflow_df.empty else 0} 条")
        print(f"   🎯 市场情绪: {'已保存' if sentiment else '未保存'}")
        
        print("\n✅ 数据获取与填充完成!")
        
    finally:
        writer.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T01 数据获取与填充（优化版）')
    parser.add_argument('--date', '-d', help='交易日期 (YYYYMMDD)', default=None)
    args = parser.parse_args()
    
    main(args.date)
