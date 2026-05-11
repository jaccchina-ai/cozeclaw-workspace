"""
T01 选股系统 - 数据获取模块

通过 Tushare API 获取各类数据
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import sys
import time

# 添加 tushare-finance skill 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../skills/tushare-finance/scripts'))

# Tushare Token
TUSHARE_TOKEN = '870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab'

# 初始化 Tushare API
pro = ts.pro_api(TUSHARE_TOKEN)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        self.pro = pro
        
    # ==================== 交易日历 ====================
    
    def is_trading_day(self, date: str = None) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期 YYYYMMDD 格式，默认今天
            
        Returns:
            是否为交易日
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            cal = self.pro.trade_cal(
                exchange='SSE',
                start_date=date,
                end_date=date
            )
            if cal.empty:
                return False
            return int(cal.iloc[0]['is_open']) == 1
        except Exception as e:
            print(f"获取交易日历失败: {e}")
            return False
    
    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取日期范围内的交易日列表"""
        try:
            cal = self.pro.trade_cal(
                exchange='SSE',
                start_date=start_date,
                end_date=end_date,
                is_open='1'
            )
            return cal['cal_date'].tolist()
        except Exception as e:
            print(f"获取交易日列表失败: {e}")
            return []
    
    def get_previous_trading_day(self, date: str = None) -> Optional[str]:
        """获取上一个交易日"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            # 往前查10天
            start = (datetime.strptime(date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
            cal = self.pro.trade_cal(
                exchange='SSE',
                start_date=start,
                end_date=date,
                is_open='1'
            )
            if len(cal) < 2:
                return None

            # trade_cal 返回的是倒序排列（最新日期在前）
            # 需要找到当前日期的位置，然后取下一条记录
            dates = cal['cal_date'].tolist()
            if date in dates:
                idx = dates.index(date)
                if idx + 1 < len(dates):
                    return dates[idx + 1]  # 倒序列表中的下一条就是上一交易日
            # 如果当前日期不在列表中（非交易日），取第一条（最近交易日）
            return dates[0]
        except Exception as e:
            print(f"获取上一交易日失败: {e}")
            return None
    
    def get_next_trading_day(self, date: str = None) -> Optional[str]:
        """获取下一个交易日"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            # 往后查10天
            end = (datetime.strptime(date, '%Y%m%d') + timedelta(days=10)).strftime('%Y%m%d')
            cal = self.pro.trade_cal(
                exchange='SSE',
                start_date=date,
                end_date=end,
                is_open='1'
            )
            if len(cal) < 2:
                return None

            # trade_cal 返回的是倒序排列（最新日期在前）
            # 需要找到当前日期的位置，然后取前一条记录
            dates = cal['cal_date'].tolist()
            if date in dates:
                idx = dates.index(date)
                if idx > 0:
                    return dates[idx - 1]  # 倒序列表中的前一条就是下一交易日
            # 如果当前日期不在列表中（非交易日），取最后一条（最近的下一个交易日）
            return dates[-1]
        except Exception as e:
            print(f"获取下一交易日失败: {e}")
            return None
    
    # ==================== 市场情绪数据 ====================
    
    def get_market_sentiment(self, date: str = None) -> Dict:
        """
        获取市场情绪数据
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            市场情绪数据字典
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        sentiment = {
            'trade_date': date,
            'zt_num': 0,
            'dt_num': 0,
            'fb_ratio': 0,
            'yzt_num': 0,
            'sentiment_stage': '混沌',
            'sh_close': 0,
            'sh_ma5': 0,
            'sh_bias': 0
        }
        
        try:
            # 获取涨停股票列表
            limit_up = self.pro.limit_list_d(
                trade_date=date,
                limit_type='U'
            )
            
            if not limit_up.empty:
                sentiment['zt_num'] = len(limit_up)
                # 一字涨停数量 (开盘即涨停，first_time 格式为 '0930xx')
                sentiment['yzt_num'] = len(limit_up[limit_up['first_time'].astype(str).str.startswith('0930')])
            
            # 获取跌停股票列表
            limit_down = self.pro.limit_list_d(
                trade_date=date,
                limit_type='D'
            )
            if not limit_down.empty:
                sentiment['dt_num'] = len(limit_down)
            
            # 计算炸板率 (炸板次数 > 0 的比例)
            if sentiment['zt_num'] > 0:
                zha_ban = len(limit_up[limit_up['open_times'] > 0])
                sentiment['fb_ratio'] = zha_ban / sentiment['zt_num'] * 100
            
            # 获取上证指数数据
            index_data = self.pro.index_daily(
                ts_code='000001.SH',
                start_date=date,
                end_date=date
            )
            if not index_data.empty:
                sentiment['sh_close'] = index_data.iloc[0]['close']
                
                # 计算5日均线
                index_5d = self.pro.index_daily(
                    ts_code='000001.SH',
                    end_date=date,
                    limit=5
                )
                if len(index_5d) >= 5:
                    sentiment['sh_ma5'] = index_5d['close'].mean()
                    sentiment['sh_bias'] = (sentiment['sh_close'] - sentiment['sh_ma5']) / sentiment['sh_ma5'] * 100
            
            # 判断市场情绪阶段
            sentiment['sentiment_stage'] = self._determine_sentiment_stage(sentiment)
            
        except Exception as e:
            print(f"获取市场情绪数据失败: {e}")
            
        return sentiment
    
    def _determine_sentiment_stage(self, sentiment: Dict) -> str:
        """判断市场情绪阶段"""
        zt_num = sentiment['zt_num']
        dt_num = sentiment['dt_num']
        sh_bias = sentiment['sh_bias']
        
        if zt_num < 20:
            return '冰点'
        elif zt_num > 100 and dt_num < 10:
            return '高潮'
        elif sh_bias > 2:
            return '主升'
        elif sh_bias < -2:
            return '冰点'
        else:
            return '混沌'
    
    # ==================== 涨停股票数据 ====================
    
    def get_limit_up_stocks(self, date: str = None) -> pd.DataFrame:
        """
        获取涨停股票列表
        
        Args:
            date: 日期 YYYYMMDD
            
        Returns:
            涨停股票 DataFrame
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            # 获取涨停股票
            limit_list = self.pro.limit_list_d(
                trade_date=date,
                limit_type='U'
            )
            
            if limit_list.empty:
                return pd.DataFrame()
            
            return limit_list
            
        except Exception as e:
            print(f"获取涨停股票失败: {e}")
            return pd.DataFrame()
    
    def filter_limit_up_stocks(self, df: pd.DataFrame, date: str = None) -> pd.DataFrame:
        """
        过滤涨停股票
        
        过滤条件：
        - 剔除新股和次新股(上市不足60天)
        - 剔除ST股票
        - 剔除科创板(688开头)和北交所(8开头/4开头)
        - 自由流通市值 < 10亿元: 剔除
        - 真实换手率 > 30%: 标记高风险
        - 连续涨停天数 >= 4: 剔除
        """
        if df.empty:
            return df
            
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        filtered = df.copy()
        
        # 获取股票基本信息
        ts_codes = filtered['ts_code'].tolist()
        
        # 剔除科创板和北交所
        filtered = filtered[~filtered['ts_code'].str.startswith('688')]
        filtered = filtered[~filtered['ts_code'].str.startswith('8')]
        filtered = filtered[~filtered['ts_code'].str.startswith('4')]
        
        # 获取股票基本信息进行进一步过滤
        try:
            stock_basic = self.pro.stock_basic(exchange='', list_status='L')
            stock_basic = stock_basic.set_index('ts_code')
            
            # 剔除ST股票
            st_stocks = stock_basic[stock_basic['name'].str.contains('ST|退', na=False)].index.tolist()
            filtered = filtered[~filtered['ts_code'].isin(st_stocks)]
            
            # 剔除次新股(上市不足60天)
            list_date_threshold = (datetime.strptime(date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')
            new_stocks = stock_basic[stock_basic['list_date'] > list_date_threshold].index.tolist()
            filtered = filtered[~filtered['ts_code'].isin(new_stocks)]
            
        except Exception as e:
            print(f"获取股票基本信息失败: {e}")
        
        # 获取市值数据
        try:
            daily_basic = self.pro.daily_basic(
                trade_date=date,
                fields='ts_code,circ_mv,total_mv,turnover_rate,volume_ratio'
            )
            if not daily_basic.empty:
                daily_basic = daily_basic.set_index('ts_code')
                
                # 合并市值数据
                filtered = filtered.merge(
                    daily_basic.reset_index(),
                    on='ts_code',
                    how='left'
                )
                
                # 剔除流通市值 < 10亿的 (circ_mv 单位是万元)
                filtered = filtered[filtered['circ_mv'] >= 100000]  # 10亿 = 100000万
                
                # 标记高风险 (真实换手率 > 30%)
                filtered['high_risk'] = filtered['turnover_rate'] > 30
                
        except Exception as e:
            print(f"获取市值数据失败: {e}")
        
        # 解析连板数
        def parse_consecutive(up_stat):
            if pd.isna(up_stat) or up_stat == '':
                return 1
            try:
                # up_stat 格式如 "2/3" 表示2连板
                return int(up_stat.split('/')[0])
            except:
                return 1
        
        filtered['consecutive_limit'] = filtered['up_stat'].apply(parse_consecutive)
        
        # 剔除连板数 >= 4 的
        filtered = filtered[filtered['consecutive_limit'] < 4]
        
        return filtered.reset_index(drop=True)
    
    # ==================== 个股详细数据 ====================
    
    def get_stock_daily_data(self, ts_code: str, date: str) -> Dict:
        """获取个股日线数据"""
        try:
            daily = self.pro.daily(
                ts_code=ts_code,
                start_date=date,
                end_date=date
            )
            if daily.empty:
                return {}
            return daily.iloc[0].to_dict()
        except Exception as e:
            print(f"获取个股日线数据失败 {ts_code}: {e}")
            return {}
    
    def get_stock_moneyflow(self, ts_code: str, date: str) -> Dict:
        """获取个股资金流向"""
        try:
            mf = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=date,
                end_date=date
            )
            if mf.empty:
                return {}
            return mf.iloc[0].to_dict()
        except Exception as e:
            print(f"获取资金流向失败 {ts_code}: {e}")
            return {}
    
    def get_dragon_tiger_list(self, ts_code: str, date: str) -> Dict:
        """获取龙虎榜数据"""
        try:
            # 获取龙虎榜明细
            top_list = self.pro.top_list(
                ts_code=ts_code,
                trade_date=date
            )
            if top_list.empty:
                return {}
            
            # 获取龙虎榜机构明细
            top_inst = self.pro.top_inst(
                ts_code=ts_code,
                trade_date=date
            )
            
            result = {
                'top_list': top_list.to_dict('records'),
                'top_inst': top_inst.to_dict('records') if not top_inst.empty else [],
                'net_buy': 0,
                'institution_net_buy': 0,
                'hot_money_seats': [],
                'institution_seats': [],
                'quant_seats': []
            }
            
            # 计算净买入 (使用 net_amount 字段)
            if not top_list.empty:
                result['net_buy'] = float(top_list.iloc[0].get('net_amount', 0) or 0)
            
            # 从机构明细中识别席位类型
            if not top_inst.empty:
                for _, row in top_inst.iterrows():
                    exalter = str(row.get('exalter', ''))
                    
                    # 识别机构席位
                    if any(inst in exalter for inst in ['机构专用', '沪股通', '深股通']):
                        result['institution_seats'].append(exalter)
                    
                    # 识别知名游资席位
                    if any(hm in exalter for hm in ['呼家楼', '章盟主', '92科比', '炒股养家', '赵老哥', '乔帮主', '佛山无影脚']):
                        result['hot_money_seats'].append(exalter)
                    
                    # 识别量化席位
                    if any(q in exalter for q in ['量化', '华鑫证券上海', '中信证券西安朱雀大街']):
                        result['quant_seats'].append(exalter)
            
            return result
            
        except Exception as e:
            print(f"获取龙虎榜数据失败 {ts_code}: {e}")
            return {}
    
    def get_north_money(self, date: str) -> Dict:
        """获取北向资金数据"""
        try:
            # 沪股通+深股通
            sh_hk = self.pro.moneyflow_hsgt(
                start_date=date,
                end_date=date,
                market='sh'
            )
            sz_hk = self.pro.moneyflow_hsgt(
                start_date=date,
                end_date=date,
                market='sz'
            )
            
            # 转换为数值类型
            sh_net = float(sh_hk.iloc[0]['ggt_ss']) if not sh_hk.empty else 0
            sz_net = float(sz_hk.iloc[0]['ggt_sz']) if not sz_hk.empty else 0
            
            result = {
                'sh_net': sh_net,
                'sz_net': sz_net,
                'total_net': sh_net + sz_net
            }
            return result
            
        except Exception as e:
            print(f"获取北向资金失败: {e}")
            return {'sh_net': 0, 'sz_net': 0, 'total_net': 0}
    
    # ==================== 融资融券数据 ====================
    
    def get_margin_data(self, date: str) -> Dict:
        """
        获取融资融券数据
        
        四大风险因子：
        1. 融资余额变化率（下降>2%: 风险↑）
        2. 融券余额变化率（上升>5%: 风险↑）
        3. 融资买入/偿还比率（<0.8: 风险↑）
        4. 融资余额绝对值水平（>8000亿: 风险↑）
        """
        try:
            # 获取当日融资融券数据
            margin = self.pro.margin(
                start_date=date,
                end_date=date
            )
            
            if margin.empty:
                return {}
            
            result = margin.iloc[0].to_dict()
            
            # 获取前一日数据计算变化率
            prev_date = self.get_previous_trading_day(date)
            if prev_date:
                prev_margin = self.pro.margin(
                    start_date=prev_date,
                    end_date=prev_date
                )
                if not prev_margin.empty:
                    prev_data = prev_margin.iloc[0].to_dict()
                    
                    # 融资余额变化率
                    rzye = float(result.get('rzye', 0) or 0)
                    prev_rzye = float(prev_data.get('rzye', 0) or 0)
                    if prev_rzye > 0:
                        result['rz_ye_change'] = (rzye - prev_rzye) / prev_rzye * 100
                    
                    # 融券余额变化率
                    rqye = float(result.get('rqye', 0) or 0)
                    prev_rqye = float(prev_data.get('rqye', 0) or 0)
                    if prev_rqye > 0:
                        result['rq_ye_change'] = (rqye - prev_rqye) / prev_rqye * 100
            
            # 融资买入/偿还比率
            rz_buy = float(result.get('rzmre', 0) or 0)  # 融资买入额
            rz_repay = float(result.get('rzye', 0) or 0)  # 融资偿还额
            if rz_repay > 0:
                result['rz_buy_repay_ratio'] = rz_buy / rz_repay
            
            return result
            
        except Exception as e:
            print(f"获取融资融券数据失败: {e}")
            return {}
    
    def get_sector_heat(self, date: str) -> pd.DataFrame:
        """获取板块热度数据"""
        try:
            # 获取板块涨跌幅
            sector_daily = self.pro.index_daily(
                ts_code='',  # 需要板块代码列表
                start_date=date,
                end_date=date
            )
            
            return sector_daily
            
        except Exception as e:
            print(f"获取板块热度失败: {e}")
            return pd.DataFrame()
    
    # ==================== 竞价数据 ====================
    
    def get_auction_data(self, ts_code: str, date: str) -> Dict:
        """
        获取竞价数据
        
        使用 stk_auction 接口获取集合竞价成交情况
        接口说明：https://tushare.pro/document/2?doc_id=369
        可获取时间：每天9点25~29分之间
        
        接口字段说明（来自官方文档）：
        - vol: 成交量（股）
        - price: 成交均价（元）
        - amount: 成交金额（元）
        - pre_close: 昨收价（元）
        - turnover_rate: 换手率（%）- 已为百分比形式，如 1.45575 表示 1.46%
        - volume_ratio: 量比 - 直接使用
        - float_share: 流通股本（万股）
        """
        try:
            # 使用 stk_auction 接口获取竞价数据
            auction = self.pro.stk_auction(
                ts_code=ts_code,
                trade_date=date
            )
            
            if auction.empty:
                return {}
            
            row = auction.iloc[0]
            
            # 计算竞价涨跌幅
            auction_pct_chg = 0
            pre_close = float(row['pre_close']) if row['pre_close'] else 0
            auction_price = float(row['price']) if row['price'] else 0
            if pre_close > 0 and auction_price > 0:
                auction_pct_chg = (auction_price - pre_close) / pre_close * 100
            
            # 竞价成交量（股）- 注意单位是股，不是手
            auction_vol = float(row['vol']) if row['vol'] else 0
            
            # 竞价成交额（元 -> 万元）
            auction_amount = float(row['amount']) if row['amount'] else 0
            auction_amount_wan = auction_amount / 10000  # 元转万元
            
            # 竞价换手率（%）- 接口已返回百分比形式，直接使用
            auction_turnover = float(row['turnover_rate']) if row['turnover_rate'] else 0
            
            # 量比 - 接口直接返回，直接使用
            volume_ratio = float(row['volume_ratio']) if row['volume_ratio'] else 1
            
            # 计算竞价爆量比：竞价量(股) / 昨日成交量(手*100股)
            auction_burst_ratio = 0
            prev_date = self.get_previous_trading_day(date)
            if prev_date:
                prev_daily = self.pro.daily(
                    ts_code=ts_code,
                    start_date=prev_date,
                    end_date=prev_date
                )
                if not prev_daily.empty:
                    prev_vol = float(prev_daily.iloc[0]['vol'])  # 昨日成交量（手）
                    # 转换为股：手 * 100 = 股
                    prev_vol_shares = prev_vol * 100
                    if prev_vol_shares > 0:
                        auction_burst_ratio = auction_vol / prev_vol_shares
            
            return {
                'trade_date': date,
                'ts_code': ts_code,
                'auction_price': auction_price,
                'auction_vol': auction_vol,                    # 股
                'auction_amount': auction_amount_wan,          # 万元
                'pre_close': pre_close,
                'auction_pct_chg': round(auction_pct_chg, 2),
                'auction_turnover': round(auction_turnover, 4),  # 百分比，如 1.45575
                'auction_volume_ratio': round(volume_ratio, 2),
                'auction_burst_ratio': round(auction_burst_ratio, 4),
                'volume_ratio': volume_ratio,
                'turnover_rate': auction_turnover,
                'float_share': float(row['float_share']) if row['float_share'] else 0  # 万股
            }
            
        except Exception as e:
            print(f"获取竞价数据失败 {ts_code}: {e}")
            return {}
    
    def get_auction_data_batch(self, ts_codes: List[str], date: str, max_retries: int = 3, retry_delay: int = 10) -> Dict[str, Dict]:
        """
        批量获取多只股票的竞价数据（带重试机制）
        
        stk_auction 接口单次最多返回8000行，适合批量获取
        同时获取昨日成交量用于计算爆量比
        
        注意：竞价数据在 09:25 后需要几分钟才能同步完成，
        建议在 09:27 之后调用，或使用重试机制
        
        Args:
            ts_codes: 股票代码列表
            date: 交易日期 YYYYMMDD
            max_retries: 最大重试次数（默认3次）
            retry_delay: 重试间隔秒数（默认10秒）
            
        Returns:
            {ts_code: 竞价数据字典}
        """
        import time
        result = {}
        
        for retry in range(max_retries):
            try:
                # 获取当日所有竞价数据
                auction_df = self.pro.stk_auction(trade_date=date)
                
                if auction_df.empty:
                    print(f"   ⚠️ 竞价数据为空 (尝试 {retry+1}/{max_retries})")
                    if retry < max_retries - 1:
                        print(f"   等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"   当日无竞价数据: {date} (已重试 {max_retries} 次)")
                        return result
                
                # 检查目标股票是否在数据中
                target_set = set(ts_codes)
                available_set = set(auction_df['ts_code'].tolist())
                matched = target_set & available_set
                
                if len(matched) < len(ts_codes):
                    missing = target_set - available_set
                    print(f"   ⚠️ 部分股票无竞价数据: {len(matched)}/{len(ts_codes)}")
                    print(f"   缺失股票: {list(missing)[:3]}...")
                    if retry < max_retries - 1:
                        print(f"   等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                
                # 数据获取成功，跳出重试循环
                break
                
            except Exception as e:
                print(f"   ❌ 获取竞价数据失败 (尝试 {retry+1}/{max_retries}): {e}")
                if retry < max_retries - 1:
                    print(f"   等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"   批量获取竞价数据失败: {e}")
                    return result
        
        try:
            # 获取昨日日期和成交量
            prev_date = self.get_previous_trading_day(date)
            prev_vol_map = {}
            if prev_date:
                # 批量获取昨日行情
                prev_daily = self.pro.daily(
                    ts_code=','.join(ts_codes),
                    start_date=prev_date,
                    end_date=prev_date
                )
                if not prev_daily.empty:
                    for _, row in prev_daily.iterrows():
                        # 昨日成交量（手）转换为股
                        prev_vol_map[row['ts_code']] = float(row['vol']) * 100
            
            # 筛选目标股票并计算派生字段
            for ts_code in ts_codes:
                stock_auction = auction_df[auction_df['ts_code'] == ts_code]
                
                if stock_auction.empty:
                    continue
                
                row = stock_auction.iloc[0]
                
                # 计算竞价涨跌幅
                auction_pct_chg = 0
                pre_close = float(row['pre_close']) if row['pre_close'] else 0
                auction_price = float(row['price']) if row['price'] else 0
                if pre_close > 0 and auction_price > 0:
                    auction_pct_chg = (auction_price - pre_close) / pre_close * 100
                
                # 竞价成交量（股）
                auction_vol = float(row['vol']) if row['vol'] else 0
                
                # 竞价成交额（元 -> 万元）
                auction_amount = float(row['amount']) if row['amount'] else 0
                auction_amount_wan = auction_amount / 10000
                
                # 竞价换手率（%）- 接口已返回百分比形式
                auction_turnover = float(row['turnover_rate']) if row['turnover_rate'] else 0
                
                # 量比 - 直接使用
                volume_ratio = float(row['volume_ratio']) if row['volume_ratio'] else 1
                
                # 竞价爆量比：竞价量(股) / 昨日成交量(股)
                auction_burst_ratio = 0
                prev_vol_shares = prev_vol_map.get(ts_code, 0)
                if prev_vol_shares > 0:
                    auction_burst_ratio = auction_vol / prev_vol_shares
                
                result[ts_code] = {
                    'trade_date': date,
                    'ts_code': ts_code,
                    'auction_price': auction_price,
                    'auction_vol': auction_vol,                    # 股
                    'auction_amount': auction_amount_wan,          # 万元
                    'pre_close': pre_close,
                    'auction_pct_chg': round(auction_pct_chg, 2),
                    'auction_turnover': round(auction_turnover, 4),  # 百分比
                    'auction_volume_ratio': round(volume_ratio, 2),
                    'auction_burst_ratio': round(auction_burst_ratio, 4),
                    'volume_ratio': volume_ratio,
                    'turnover_rate': auction_turnover,
                    'float_share': float(row['float_share']) if row['float_share'] else 0  # 万股
                }
            
            print(f"   获取到 {len(result)}/{len(ts_codes)} 只股票的竞价数据")
            
        except Exception as e:
            print(f"批量获取竞价数据失败: {e}")
        
        return result
    
    # ==================== 技术指标计算 ====================
    
    def calculate_ma(self, ts_code: str, date: str, period: int = 3) -> float:
        """计算移动平均线"""
        try:
            daily = self.pro.daily(
                ts_code=ts_code,
                end_date=date,
                limit=period
            )
            
            if len(daily) < period:
                return 0
            
            return daily['close'].mean()
            
        except Exception as e:
            print(f"计算MA失败 {ts_code}: {e}")
            return 0
    
    def calculate_bias_ma3(self, ts_code: str, date: str) -> float:
        """计算MA3乖离率"""
        try:
            daily = self.pro.daily(
                ts_code=ts_code,
                end_date=date,
                limit=5
            )
            
            if len(daily) < 3:
                return 0
            
            close = daily.iloc[0]['close']
            ma3 = daily.head(3)['close'].mean()
            
            bias = (close - ma3) / ma3 * 100
            return bias
            
        except Exception as e:
            print(f"计算MA3乖离率失败 {ts_code}: {e}")
            return 0
    
    # ==================== 批量数据获取 ====================
    
    def get_stocks_daily_batch(self, ts_codes: List[str], date: str) -> pd.DataFrame:
        """批量获取多只股票日线数据"""
        try:
            all_data = []
            for code in ts_codes:
                data = self.get_stock_daily_data(code, date)
                if data:
                    all_data.append(data)
            
            return pd.DataFrame(all_data)
            
        except Exception as e:
            print(f"批量获取日线数据失败: {e}")
            return pd.DataFrame()
    
    def get_stocks_history_batch(self, ts_codes: List[str], date: str, days: int = 5) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票的历史日线数据（用于计算MA等指标）
        
        Args:
            ts_codes: 股票代码列表
            date: 结束日期 YYYYMMDD
            days: 获取天数
            
        Returns:
            {ts_code: DataFrame} 每只股票的历史数据
        """
        import time
        
        result = {}
        for i, code in enumerate(ts_codes):
            try:
                # 获取历史数据
                daily = self.pro.daily(
                    ts_code=code,
                    end_date=date,
                    limit=days
                )
                if not daily.empty:
                    result[code] = daily
                time.sleep(0.05)  # 速率限制
            except Exception as e:
                pass
            
            if (i + 1) % 10 == 0:
                print(f"      历史数据进度: {i+1}/{len(ts_codes)}")
        
        return result
    
    def calculate_bias_ma3_batch(self, history_data: Dict[str, pd.DataFrame], 
                                  current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        批量计算MA3乖离率
        
        Args:
            history_data: {ts_code: DataFrame} 历史数据
            current_prices: {ts_code: close} 当前收盘价（可选，如果不提供则从历史数据第一行获取）
            
        Returns:
            {ts_code: bias_ma3} 乖离率字典
        """
        result = {}
        for code, df in history_data.items():
            try:
                if len(df) < 3:
                    result[code] = 0
                    continue
                
                # 当日收盘价（最新一天）
                current_close = current_prices.get(code, df.iloc[0]['close'])
                
                # 计算MA3（最近3天收盘价均值）
                ma3 = df.head(3)['close'].mean()
                
                if ma3 > 0:
                    bias = (current_close - ma3) / ma3 * 100
                    result[code] = round(bias, 2)
                else:
                    result[code] = 0
                    
            except Exception:
                result[code] = 0
        
        return result
    
    # ==================== 通达信板块数据 ====================
    
    def get_tdx_sectors(self, date: str = None, idx_type: str = None) -> pd.DataFrame:
        """
        获取通达信板块列表
        
        Args:
            date: 日期 YYYYMMDD
            idx_type: 板块类型（概念板块、行业板块、风格板块、地区板块）
            
        Returns:
            板块列表 DataFrame，包含 ts_code, name, idx_type, idx_count 等字段
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            params = {'trade_date': date}
            if idx_type:
                params['idx_type'] = idx_type
                
            df = self.pro.tdx_index(**params)
            
            if df.empty:
                print(f"未找到通达信板块数据: {date}")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            print(f"获取通达信板块列表失败: {e}")
            return pd.DataFrame()
    
    def get_tdx_concept_sectors(self, date: str = None) -> pd.DataFrame:
        """获取通达信概念板块列表"""
        return self.get_tdx_sectors(date, idx_type='概念板块')
    
    def get_tdx_industry_sectors(self, date: str = None) -> pd.DataFrame:
        """获取通达信行业板块列表"""
        return self.get_tdx_sectors(date, idx_type='行业板块')
    
    def get_tdx_sector_members(self, ts_code: str, date: str = None) -> pd.DataFrame:
        """
        获取通达信板块成分股

        Args:
            ts_code: 板块代码（如 880535.TDX）
            date: 日期 YYYYMMDD

        Returns:
            成分股 DataFrame，包含 ts_code, con_code, con_name 等字段
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            df = self.pro.tdx_member(trade_date=date, ts_code=ts_code)
            time.sleep(0.12)  # 延迟0.12秒，避免触发速率限制

            if df.empty:
                return pd.DataFrame()

            return df

        except Exception as e:
            print(f"获取通达信板块成分股失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def get_tdx_sector_daily(self, ts_code: str = None, date: str = None, 
                              start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取通达信板块行情数据
        
        Args:
            ts_code: 板块代码（可选，不传则返回所有板块）
            date: 日期 YYYYMMDD（可选）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            板块行情 DataFrame，包含涨跌幅、涨停家数、成交额等字段
        """
        try:
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if date:
                params['trade_date'] = date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
                
            df = self.pro.tdx_daily(**params)
            
            if df.empty:
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            print(f"获取通达信板块行情失败: {e}")
            return pd.DataFrame()
    
    def get_hot_sectors_tdx(self, date: str = None, top_n: int = 10, 
                             idx_type: str = '概念板块') -> List[Dict]:
        """
        获取通达信热门板块
        
        Args:
            date: 日期 YYYYMMDD
            top_n: 返回前N个板块
            idx_type: 板块类型（概念板块、行业板块）
            
        Returns:
            热门板块列表，按涨跌幅排序
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            # 获取板块行情
            daily_df = self.get_tdx_sector_daily(date=date)
            if daily_df.empty:
                return []
            
            # 获取板块信息
            index_df = self.get_tdx_sectors(date=date, idx_type=idx_type)
            if index_df.empty:
                return []
            
            # 筛选指定类型的板块
            type_codes = index_df['ts_code'].tolist()
            filtered_daily = daily_df[daily_df['ts_code'].isin(type_codes)]
            
            # 按涨跌幅排序
            sorted_df = filtered_daily.nlargest(top_n, 'pct_change')
            
            # 合并板块名称
            result_df = sorted_df.merge(
                index_df[['ts_code', 'name', 'idx_count']], 
                on='ts_code', 
                how='left'
            )
            
            # 转换为字典列表
            result = []
            for _, row in result_df.iterrows():
                result.append({
                    'ts_code': row['ts_code'],
                    'name': row['name'],
                    'pct_change': float(row['pct_change']) if pd.notna(row['pct_change']) else 0,
                    'limit_up_num': int(row['limit_up_num']) if pd.notna(row['limit_up_num']) else 0,
                    'up_num': int(row['up_num']) if pd.notna(row['up_num']) else 0,
                    'down_num': int(row['down_num']) if pd.notna(row['down_num']) else 0,
                    'amount': float(row['amount']) if pd.notna(row['amount']) else 0,  # 万元
                    'idx_count': int(row['idx_count']) if pd.notna(row['idx_count']) else 0
                })
            
            return result
            
        except Exception as e:
            print(f"获取热门板块失败: {e}")
            return []
    
    def get_stock_tdx_sectors(self, ts_code: str, date: str = None, 
                                hot_sector_codes: List[str] = None) -> List[Dict]:
        """
        获取股票所属的通达信板块
        
        Args:
            ts_code: 股票代码（如 002015.SZ）
            date: 日期 YYYYMMDD
            hot_sector_codes: 热门板块代码列表（可选，用于优化查询）
            
        Returns:
            股票所属板块列表
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            # 获取板块信息
            sector_info = self.get_tdx_sectors(date=date)
            
            if sector_info.empty:
                return []
            
            result = []
            
            # 如果提供了热门板块代码，只查询这些板块
            if hot_sector_codes:
                query_codes = hot_sector_codes[:20]  # 限制最多20个板块，避免速率限制
            else:
                # 否则查询所有行业板块（前20个）
                industry_codes = sector_info[sector_info['idx_type'] == '行业板块']['ts_code'].tolist()[:20]
                query_codes = industry_codes

            # 遍历板块查询成分股（添加延迟避免触发速率限制）
            for sector_code in query_codes:
                try:
                    members = self.pro.tdx_member(trade_date=date, ts_code=sector_code)
                    time.sleep(0.15)  # 延迟0.15秒，确保不超过500次/分钟

                    if members.empty:
                        continue
                    
                    # 检查目标股票是否在该板块中
                    if ts_code in members['con_code'].values:
                        info = sector_info[sector_info['ts_code'] == sector_code]
                        if not info.empty:
                            result.append({
                                'ts_code': sector_code,
                                'name': info.iloc[0]['name'],
                                'idx_type': info.iloc[0]['idx_type']
                            })
                            
                except Exception:
                    continue
            
            return result
            
        except Exception as e:
            print(f"获取股票所属板块失败 {ts_code}: {e}")
            return []
    
    def get_sector_zt_count_tdx(self, limit_up_codes: List[str], date: str = None,
                                  top_n: int = 30) -> Dict[str, int]:
        """
        统计热门通达信板块的涨停股数量
        
        Args:
            limit_up_codes: 涨停股票代码列表
            date: 日期 YYYYMMDD
            top_n: 统计前N个热门板块
            
        Returns:
            {板块代码: 涨停股数量}
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        try:
            # 获取热门概念板块
            hot_sectors = self.get_hot_sectors_tdx(date=date, top_n=top_n, idx_type='概念板块')
            
            if not hot_sectors:
                return {}
            
            sector_zt_count = {}

            # 遍历热门板块统计涨停股数量（添加延迟避免触发速率限制）
            for sector in hot_sectors:
                sector_code = sector['ts_code']
                try:
                    members = self.pro.tdx_member(trade_date=date, ts_code=sector_code)
                    time.sleep(0.15)  # 延迟0.15秒，确保不超过500次/分钟

                    if members.empty:
                        continue

                    # 统计该板块内的涨停股数量
                    zt_count = members['con_code'].isin(limit_up_codes).sum()
                    if zt_count > 0:
                        sector_zt_count[sector_code] = int(zt_count)

                except Exception:
                    continue
            
            return sector_zt_count
            
        except Exception as e:
            print(f"统计板块涨停股数量失败: {e}")
            return {}


# 便捷函数
def create_fetcher() -> DataFetcher:
    """创建数据获取器实例"""
    return DataFetcher()


if __name__ == '__main__':
    fetcher = DataFetcher()
    
    # 测试
    today = datetime.now().strftime('%Y%m%d')
    print(f"今天是否交易日: {fetcher.is_trading_day(today)}")
    
    sentiment = fetcher.get_market_sentiment(today)
    print(f"市场情绪: {sentiment}")
