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
            return cal.iloc[-2]['cal_date']
        except Exception as e:
            print(f"获取上一交易日失败: {e}")
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
    
    # ==================== 板块数据 ====================
    
    def get_sector_data(self, ts_code: str, date: str) -> Dict:
        """获取个股所属板块数据"""
        try:
            # 获取概念板块
            concept = self.pro.concept_detail(
                ts_code=ts_code,
                fields='ts_code,name'
            )
            
            # 获取行业板块
            industry = self.pro.index_classify(
                level='L1',
                src='SW'
            )
            
            return {
                'concepts': concept.to_dict('records') if not concept.empty else [],
                'industry': industry.to_dict('records') if not industry.empty else []
            }
            
        except Exception as e:
            print(f"获取板块数据失败 {ts_code}: {e}")
            return {'concepts': [], 'industry': []}
    
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
        
        注意: stk_premarket_a 接口需要付费权限
        如果没有权限，使用其他方式模拟
        """
        try:
            # 尝试使用竞价接口
            auction = self.pro.stk_premarket_a(
                ts_code=ts_code,
                trade_date=date
            )
            
            if not auction.empty:
                return auction.iloc[0].to_dict()
            
            # 如果没有竞价接口，使用开盘价作为近似
            daily = self.pro.daily(
                ts_code=ts_code,
                start_date=date,
                end_date=date
            )
            
            if not daily.empty:
                row = daily.iloc[0]
                return {
                    'trade_date': date,
                    'ts_code': ts_code,
                    'auction_price': row['open'],
                    'auction_vol': row['vol'] * 0.05,  # 估算
                    'auction_amount': row['amount'] * 0.05,
                    'auction_pct_chg': (row['open'] - row['pre_close']) / row['pre_close'] * 100
                }
            
            return {}
            
        except Exception as e:
            print(f"获取竞价数据失败 {ts_code}: {e}")
            return {}
    
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
