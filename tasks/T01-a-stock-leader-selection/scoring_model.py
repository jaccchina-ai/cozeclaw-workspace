"""
T01 选股系统 - 十一因子评分模型

T日20:00选股模块的核心评分逻辑
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json


@dataclass
class FactorWeights:
    """因子权重配置"""
    # 十一个因子权重 (总和100)
    limit_quality: float = 12.0       # 涨停质量
    seal_ratio: float = 10.0          # 封成比
    seal_flow_ratio: float = 12.0     # 封流比
    volume_ratio: float = 8.0         # 量比
    turnover_rate: float = 8.0        # 真实换手率
    dragon_tiger: float = 12.0        # 龙虎榜+北向资金
    money_flow: float = 10.0          # 个股资金结构
    amount_rank: float = 8.0          # 成交金额排名
    sector_heat: float = 8.0          # 热点板块
    bias_ma3: float = 6.0             # MA3乖离率(风控)
    sentiment: float = 6.0            # 舆情分析(附加)


@dataclass
class StockScore:
    """股票评分结果"""
    ts_code: str
    stock_name: str = ''
    
    # 各因子得分
    limit_quality_score: float = 0
    seal_ratio_score: float = 0
    seal_flow_ratio_score: float = 0
    volume_ratio_score: float = 0
    turnover_rate_score: float = 0
    dragon_tiger_score: float = 0
    money_flow_score: float = 0
    amount_rank_score: float = 0
    sector_heat_score: float = 0
    bias_ma3_score: float = 0
    sentiment_score: float = 0
    
    # 总分
    total_score: float = 0
    
    # 因子原始值
    raw_values: Dict = field(default_factory=dict)
    
    # 推荐信息
    sector: str = ''
    reason: str = ''
    unifuncs_recommended: bool = False


class ScoringModel:
    """十一因子评分模型"""
    
    def __init__(self, weights: FactorWeights = None):
        self.weights = weights or FactorWeights()
        
    # ==================== 评分函数 ====================
    
    def score_limit_quality(self, first_limit_time: str, limit_times: int, 
                            consecutive_limit: int) -> Tuple[float, Dict]:
        """
        涨停质量评分
        
        Args:
            first_limit_time: 首次涨停时间 HH:MM:SS
            limit_times: 炸板次数
            consecutive_limit: 连板数
            
        Returns:
            (得分, 原始值字典)
        """
        score = 0
        raw = {
            'first_limit_time': first_limit_time,
            'limit_times': limit_times,
            'consecutive_limit': consecutive_limit
        }
        
        # 首次涨停时间评分 (越早越好)
        # 9:30-10:00: 10分
        # 10:00-11:00: 8分
        # 11:00-13:30: 5分
        # 13:30-14:30: 3分
        # 14:30后: 1分
        if first_limit_time:
            try:
                hour_min = int(first_limit_time[:2] + first_limit_time[3:5])
                if hour_min <= 1000:  # 10:00前
                    time_score = 10
                elif hour_min <= 1100:  # 10:00-11:00
                    time_score = 8
                elif hour_min <= 1330:  # 11:00-13:30
                    time_score = 5
                elif hour_min <= 1430:  # 13:30-14:30
                    time_score = 3
                else:
                    time_score = 1
            except:
                time_score = 5
        else:
            time_score = 5
        
        # 炸板次数评分 (越少越好)
        # 0次: 10分, 1次: 7分, 2次: 4分, >=3次: 排除
        if limit_times >= 3:
            return -1, raw  # 排除
        times_score = 10 - limit_times * 3
        
        # 连板数评分 (2-3板最优)
        # 1板: 6分, 2板: 10分, 3板: 8分, >=5板: 排除
        if consecutive_limit >= 5:
            return -1, raw  # 排除
        elif consecutive_limit == 2:
            board_score = 10
        elif consecutive_limit == 3:
            board_score = 8
        elif consecutive_limit == 1:
            board_score = 6
        else:  # 4板
            board_score = 5
        
        # 综合得分 (加权平均)
        score = (time_score + times_score + board_score) / 3
        
        return score, raw
    
    def score_seal_ratio(self, seal_amount: float, deal_amount: float) -> Tuple[float, Dict]:
        """
        封成比评分
        
        封成比 = 封单金额 / 成交金额
        比值越大，说明主力控盘越强
        
        Args:
            seal_amount: 封单金额(万元)
            deal_amount: 成交金额(万元)
            
        Returns:
            (得分, 原始值字典)
        """
        if deal_amount <= 0:
            return 0, {'seal_ratio': 0}
        
        seal_ratio = seal_amount / deal_amount
        raw = {'seal_ratio': round(seal_ratio, 4)}
        
        # 封成比评分标准
        # >= 1.0: 10分 (极强)
        # 0.5-1.0: 8分
        # 0.3-0.5: 6分
        # 0.1-0.3: 4分
        # < 0.1: 2分
        if seal_ratio >= 1.0:
            score = 10
        elif seal_ratio >= 0.5:
            score = 8
        elif seal_ratio >= 0.3:
            score = 6
        elif seal_ratio >= 0.1:
            score = 4
        else:
            score = 2
        
        return score, raw
    
    def score_seal_flow_ratio(self, seal_amount: float, free_mv: float) -> Tuple[float, Dict]:
        """
        封流比评分 (高级指标)
        
        封流比 = 封单金额 / 自由流通市值
        更能反映主力控盘程度
        
        Args:
            seal_amount: 封单金额(万元)
            free_mv: 自由流通市值(万元)
            
        Returns:
            (得分, 原始值字典)
        """
        if free_mv <= 0:
            return 0, {'seal_flow_ratio': 0}
        
        seal_flow_ratio = seal_amount / free_mv
        raw = {'seal_flow_ratio': round(seal_flow_ratio, 4)}
        
        # 封流比评分标准
        # >= 0.1 (10%): 10分 (极强控盘)
        # 0.05-0.1: 8分
        # 0.03-0.05: 6分
        # 0.01-0.03: 4分
        # < 0.01: 2分
        if seal_flow_ratio >= 0.1:
            score = 10
        elif seal_flow_ratio >= 0.05:
            score = 8
        elif seal_flow_ratio >= 0.03:
            score = 6
        elif seal_flow_ratio >= 0.01:
            score = 4
        else:
            score = 2
        
        return score, raw
    
    def score_volume_ratio(self, volume_ratio: float) -> Tuple[float, Dict]:
        """
        量比评分
        
        量比 = 当前成交量 / 5日均量
        反映放量程度
        
        Args:
            volume_ratio: 量比
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {'volume_ratio': round(volume_ratio, 2)}
        
        # 量比评分标准
        # 1-2: 正常放量 6分
        # 2-3: 明显放量 8分
        # 3-5: 大幅放量 10分
        # 5-10: 异常放量 6分 (警惕)
        # > 10: 天量 3分 (危险)
        # < 1: 缩量 4分
        if volume_ratio < 1:
            score = 4
        elif volume_ratio < 2:
            score = 6
        elif volume_ratio < 3:
            score = 8
        elif volume_ratio < 5:
            score = 10
        elif volume_ratio < 10:
            score = 6
        else:
            score = 3
        
        return score, raw
    
    def score_turnover_rate(self, real_turnover_rate: float) -> Tuple[float, Dict]:
        """
        真实换手率评分
        
        真实换手率 = 成交金额 / 自由流通市值
        反映真实交易活跃度
        
        Args:
            real_turnover_rate: 真实换手率(%)
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {'real_turnover_rate': round(real_turnover_rate, 2)}
        
        # 真实换手率评分标准 (涨停股换手率通常较高)
        # 5-15%: 10分 (健康)
        # 15-20%: 8分
        # 20-25%: 6分
        # 25-30%: 4分
        # > 30%: 2分 (高风险)
        # < 5%: 6分 (缩量涨停)
        if real_turnover_rate < 5:
            score = 6
        elif real_turnover_rate < 15:
            score = 10
        elif real_turnover_rate < 20:
            score = 8
        elif real_turnover_rate < 25:
            score = 6
        elif real_turnover_rate < 30:
            score = 4
        else:
            score = 2
        
        return score, raw
    
    def score_dragon_tiger(self, dragon_tiger_data: Dict, north_data: Dict) -> Tuple[float, Dict]:
        """
        龙虎榜和北向资金评分
        
        Args:
            dragon_tiger_data: 龙虎榜数据
            north_data: 北向资金数据
            
        Returns:
            (得分, 原始值字典)
        """
        score = 5  # 默认基础分
        raw = {
            'net_buy': dragon_tiger_data.get('net_buy', 0),
            'institution_net_buy': dragon_tiger_data.get('institution_net_buy', 0),
            'hot_money_seats': dragon_tiger_data.get('hot_money_seats', []),
            'institution_seats': dragon_tiger_data.get('institution_seats', []),
            'quant_seats': dragon_tiger_data.get('quant_seats', []),
            'north_net': north_data.get('total_net', 0)
        }
        
        # 机构净买入 > 3000万: +3分
        if raw['net_buy'] > 3000:
            score += 3
        
        # 有知名游资席位: +2分
        if raw['hot_money_seats']:
            score += 2
        
        # 有机构席位: +1分
        if raw['institution_seats']:
            score += 1
        
        # 有量化席位: -2分
        if raw['quant_seats']:
            score -= 2
        
        # 买一席位买入量 > 总成交20% (一家独大): -2分
        # (需要更详细数据来判断)
        
        # 北向资金增仓: +1分
        if raw['north_net'] > 0:
            score += 1
        
        # 限制分数范围
        score = max(0, min(10, score))
        
        return score, raw
    
    def score_money_flow(self, main_net_inflow: float, main_net_ratio: float,
                        medium_net: float) -> Tuple[float, Dict]:
        """
        个股资金结构评分
        
        Args:
            main_net_inflow: 主力净流入(万元)
            main_net_ratio: 主力净占比(%)
            medium_net: 中单净额(万元)
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {
            'main_net_inflow': main_net_inflow,
            'main_net_ratio': round(main_net_ratio, 2),
            'medium_net': medium_net
        }
        
        score = 5  # 基础分
        
        # 主力净流入为正: +2分
        if main_net_inflow > 0:
            score += 2
        
        # 主力净占比 > 10%: +2分
        if main_net_ratio > 10:
            score += 2
        elif main_net_ratio > 5:
            score += 1
        
        # 中单净额为正: +1分
        if medium_net > 0:
            score += 1
        
        # 限制分数范围
        score = max(0, min(10, score))
        
        return score, raw
    
    def score_amount_rank(self, amount: float, all_amounts: List[float]) -> Tuple[float, Dict]:
        """
        成交金额排名评分
        
        Args:
            amount: 成交金额(万元)
            all_amounts: 所有股票成交金额列表
            
        Returns:
            (得分, 原始值字典)
        """
        if not all_amounts or amount <= 0:
            return 5, {'amount_rank': 0, 'amount': amount}
        
        # 计算排名百分位
        sorted_amounts = sorted(all_amounts, reverse=True)
        rank = sorted_amounts.index(amount) + 1 if amount in sorted_amounts else len(sorted_amounts)
        percentile = (len(sorted_amounts) - rank) / len(sorted_amounts) * 100
        
        raw = {
            'amount': amount,
            'amount_rank': rank,
            'amount_percentile': round(percentile, 1)
        }
        
        # 排名评分标准
        # 前5%: 10分
        # 5-10%: 8分
        # 10-20%: 6分
        # 20-50%: 4分
        # 50%后: 2分
        if percentile >= 95:
            score = 10
        elif percentile >= 90:
            score = 8
        elif percentile >= 80:
            score = 6
        elif percentile >= 50:
            score = 4
        else:
            score = 2
        
        return score, raw
    
    def score_sector_heat(self, sector_zt_count: int, sector_pct_chg: float,
                         sector_main_inflow: float) -> Tuple[float, Dict]:
        """
        热点板块评分
        
        Args:
            sector_zt_count: 板块涨停家数
            sector_pct_chg: 板块涨幅(%)
            sector_main_inflow: 板块主力净流入(万元)
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {
            'sector_zt_count': sector_zt_count,
            'sector_pct_chg': round(sector_pct_chg, 2),
            'sector_main_inflow': sector_main_inflow
        }
        
        score = 0
        
        # 板块涨停家数评分
        if sector_zt_count >= 5:
            score += 4
        elif sector_zt_count >= 3:
            score += 3
        elif sector_zt_count >= 2:
            score += 2
        else:
            score += 1
        
        # 板块涨幅评分
        if sector_pct_chg >= 3:
            score += 3
        elif sector_pct_chg >= 2:
            score += 2
        elif sector_pct_chg >= 1:
            score += 1
        
        # 板块主力净流入评分
        if sector_main_inflow > 0:
            score += 3
        elif sector_main_inflow > -1000:
            score += 1
        
        # 限制分数范围
        score = max(0, min(10, score))
        
        return score, raw
    
    def score_bias_ma3(self, bias_ma3: float) -> Tuple[float, Dict]:
        """
        MA3乖离率评分 (风控因子)
        
        对 MA3 乖离率 > 12% 的股票给予低分
        
        Args:
            bias_ma3: MA3乖离率(%)
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {'bias_ma3': round(bias_ma3, 2)}
        
        # MA3乖离率评分标准 (越低越好，防止追高)
        # < 3%: 10分
        # 3-6%: 8分
        # 6-9%: 6分
        # 9-12%: 3分
        # > 12%: 1分 (高风险)
        if bias_ma3 < 3:
            score = 10
        elif bias_ma3 < 6:
            score = 8
        elif bias_ma3 < 9:
            score = 6
        elif bias_ma3 < 12:
            score = 3
        else:
            score = 1
        
        return score, raw
    
    def score_sentiment(self, sentiment_score: float) -> Tuple[float, Dict]:
        """
        舆情分析评分 (通过 unifuncs API 获取)
        
        Args:
            sentiment_score: unifuncs 返回的涨停概率分数 (0-100)
            
        Returns:
            (得分, 原始值字典)
        """
        raw = {'sentiment_score': sentiment_score}
        
        # 将 0-100 映射到 0-10
        score = sentiment_score / 10
        
        return score, raw
    
    # ==================== 综合评分 ====================
    
    def calculate_total_score(self, stock: StockScore) -> float:
        """计算加权总分"""
        total = (
            stock.limit_quality_score * self.weights.limit_quality / 10 +
            stock.seal_ratio_score * self.weights.seal_ratio / 10 +
            stock.seal_flow_ratio_score * self.weights.seal_flow_ratio / 10 +
            stock.volume_ratio_score * self.weights.volume_ratio / 10 +
            stock.turnover_rate_score * self.weights.turnover_rate / 10 +
            stock.dragon_tiger_score * self.weights.dragon_tiger / 10 +
            stock.money_flow_score * self.weights.money_flow / 10 +
            stock.amount_rank_score * self.weights.amount_rank / 10 +
            stock.sector_heat_score * self.weights.sector_heat / 10 +
            stock.bias_ma3_score * self.weights.bias_ma3 / 10 +
            stock.sentiment_score * self.weights.sentiment / 10
        )
        
        return round(total, 2)
    
    def score_stock(self, stock_data: Dict, all_amounts: List[float] = None,
                   dragon_tiger_data: Dict = None, north_data: Dict = None,
                   sector_data: Dict = None, sentiment_data: float = 0) -> StockScore:
        """
        对单只股票进行完整评分
        
        Args:
            stock_data: 股票基础数据
            all_amounts: 所有股票成交金额(用于排名)
            dragon_tiger_data: 龙虎榜数据
            north_data: 北向资金数据
            sector_data: 板块数据
            sentiment_data: 舆情分析分数
            
        Returns:
            StockScore 对象
        """
        score = StockScore(
            ts_code=stock_data.get('ts_code', ''),
            stock_name=stock_data.get('name', '')
        )
        
        all_amounts = all_amounts or []
        dragon_tiger_data = dragon_tiger_data or {}
        north_data = north_data or {}
        sector_data = sector_data or {}
        
        # 1. 涨停质量评分
        limit_score, raw = self.score_limit_quality(
            stock_data.get('first_limit_time', ''),
            stock_data.get('limit_times', 0),
            stock_data.get('consecutive_limit', 1)
        )
        if limit_score < 0:
            return None  # 排除
        score.limit_quality_score = limit_score
        score.raw_values.update(raw)
        
        # 2. 封成比评分 (使用 seal_amount 即 fd_amount)
        seal_amount = float(stock_data.get('seal_amount', 0) or stock_data.get('fd_amount', 0) or 0)
        deal_amount = float(stock_data.get('amount', 0) or 0)
        seal_ratio_score, raw = self.score_seal_ratio(seal_amount, deal_amount)
        score.seal_ratio_score = seal_ratio_score
        score.raw_values.update(raw)
        
        # 3. 封流比评分 (使用 float_mv 流通市值，单位：元)
        free_mv = float(stock_data.get('free_mv', 0) or stock_data.get('float_mv', 0) or 0)
        seal_flow_score, raw = self.score_seal_flow_ratio(seal_amount, free_mv)
        score.seal_flow_ratio_score = seal_flow_score
        score.raw_values.update(raw)
        
        # 4. 量比评分 (从 daily_basic 获取)
        volume_ratio = float(stock_data.get('volume_ratio', 1) or 1)
        vr_score, raw = self.score_volume_ratio(volume_ratio)
        score.volume_ratio_score = vr_score
        score.raw_values.update(raw)
        
        # 5. 真实换手率评分
        # 真实换手率 = 成交金额(元) / 流通市值(元) * 100
        # deal_amount 单位是元，free_mv 单位也是元
        if free_mv > 0 and deal_amount > 0:
            real_turnover = deal_amount / free_mv * 100
        else:
            real_turnover = 0
        tr_score, raw = self.score_turnover_rate(real_turnover)
        score.turnover_rate_score = tr_score
        score.raw_values.update(raw)
        
        # 6. 龙虎榜和北向资金评分
        dt_score, raw = self.score_dragon_tiger(dragon_tiger_data, north_data)
        score.dragon_tiger_score = dt_score
        score.raw_values.update(raw)
        
        # 7. 个股资金结构评分
        mf_score, raw = self.score_money_flow(
            float(stock_data.get('main_net_inflow', 0) or 0),
            float(stock_data.get('main_net_ratio', 0) or 0),
            float(stock_data.get('medium_net', 0) or 0)
        )
        score.money_flow_score = mf_score
        score.raw_values.update(raw)
        
        # 8. 成交金额排名评分
        ar_score, raw = self.score_amount_rank(deal_amount, all_amounts)
        score.amount_rank_score = ar_score
        score.raw_values.update(raw)
        
        # 9. 热点板块评分
        sh_score, raw = self.score_sector_heat(
            float(sector_data.get('zt_count', 0) or 0),
            float(sector_data.get('pct_chg', 0) or 0),
            float(sector_data.get('main_inflow', 0) or 0)
        )
        score.sector_heat_score = sh_score
        score.raw_values.update(raw)
        score.sector = sector_data.get('name', '')
        
        # 10. MA3乖离率评分
        bias_ma3 = float(stock_data.get('bias_ma3', 0) or 0)
        bias_score, raw = self.score_bias_ma3(bias_ma3)
        score.bias_ma3_score = bias_score
        score.raw_values.update(raw)
        
        # 11. 舆情分析评分 (附加)
        if sentiment_data > 0:
            sent_score, raw = self.score_sentiment(sentiment_data)
            score.sentiment_score = sent_score
            score.unifuncs_recommended = True
            score.raw_values.update(raw)
        
        # 计算总分
        score.total_score = self.calculate_total_score(score)
        
        return score
    
    def generate_reason(self, score: StockScore) -> str:
        """生成推荐理由"""
        reasons = []
        
        if score.limit_quality_score >= 8:
            reasons.append("涨停质量优秀")
        if score.seal_flow_ratio_score >= 8:
            reasons.append("封流比高,主力控盘强")
        if score.dragon_tiger_score >= 7:
            reasons.append("龙虎榜资金认可")
        if score.money_flow_score >= 7:
            reasons.append("主力资金大幅流入")
        if score.sector_heat_score >= 7:
            reasons.append("所属板块热度高")
        if score.unifuncs_recommended:
            reasons.append("【AI推荐】")
        
        if not reasons:
            reasons.append("综合评分较高")
        
        return " + ".join(reasons)


class AuctionScoringModel:
    """T+1竞价评分模型"""
    
    def __init__(self):
        # 竞价因子权重
        self.weights = {
            'auction_turnover': 12.0,
            'auction_amount': 10.0,
            'auction_pct_chg': 15.0,
            'auction_volume_ratio': 10.0,
            'auction_burst_ratio': 12.0,
            'sector_auction_pct': 10.0,
            'sector_resonance': 12.0,
            't_day_score': 15.0,
            'market_risk': 4.0  # 风控因子
        }
    
    def score_auction_stock(self, auction_data: Dict, t_day_score: float,
                           market_risk: float = 0) -> Dict:
        """
        竞价阶段股票评分
        
        Args:
            auction_data: 竞价数据
            t_day_score: T日评分
            market_risk: 市场风险因子
            
        Returns:
            评分结果字典
        """
        result = {
            'ts_code': auction_data.get('ts_code'),
            'auction_score': 0,
            'final_score': 0,
            'raw_values': {}
        }
        
        scores = {}
        
        # 1. 竞价换手率评分
        auction_turnover = auction_data.get('auction_turnover', 0)
        if auction_turnover > 5:
            scores['auction_turnover'] = 10
        elif auction_turnover > 3:
            scores['auction_turnover'] = 8
        elif auction_turnover > 1:
            scores['auction_turnover'] = 6
        else:
            scores['auction_turnover'] = 4
        result['raw_values']['auction_turnover'] = round(auction_turnover, 2)
        
        # 2. 竞价金额评分
        auction_amount = auction_data.get('auction_amount', 0)
        if auction_amount > 5000:  # 万
            scores['auction_amount'] = 10
        elif auction_amount > 2000:
            scores['auction_amount'] = 8
        elif auction_amount > 500:
            scores['auction_amount'] = 6
        else:
            scores['auction_amount'] = 4
        result['raw_values']['auction_amount'] = auction_amount
        
        # 3. 竞价涨幅评分
        auction_pct_chg = auction_data.get('auction_pct_chg', 0)
        if auction_pct_chg < 1:
            return None  # 排除: 竞价涨幅 < 1%
        elif auction_pct_chg > 7:
            scores['auction_pct_chg'] = 4  # 高开太多风险大
        elif auction_pct_chg > 5:
            scores['auction_pct_chg'] = 6
        elif auction_pct_chg >= 2:
            scores['auction_pct_chg'] = 10  # 理想区间
        else:
            scores['auction_pct_chg'] = 8
        result['raw_values']['auction_pct_chg'] = round(auction_pct_chg, 2)
        
        # 4. 竞价量比评分
        auction_volume_ratio = auction_data.get('auction_volume_ratio', 1)
        if auction_volume_ratio > 3:
            scores['auction_volume_ratio'] = 10
        elif auction_volume_ratio > 2:
            scores['auction_volume_ratio'] = 8
        elif auction_volume_ratio > 1:
            scores['auction_volume_ratio'] = 6
        else:
            scores['auction_volume_ratio'] = 4
        result['raw_values']['auction_volume_ratio'] = round(auction_volume_ratio, 2)
        
        # 5. 竞价爆量比评分
        auction_burst_ratio = auction_data.get('auction_burst_ratio', 0)
        if auction_burst_ratio > 0.15:
            scores['auction_burst_ratio'] = 10
        elif auction_burst_ratio > 0.10:
            scores['auction_burst_ratio'] = 8
        elif auction_burst_ratio > 0.05:
            scores['auction_burst_ratio'] = 6
        else:
            scores['auction_burst_ratio'] = 4
        result['raw_values']['auction_burst_ratio'] = round(auction_burst_ratio, 4)
        
        # 竞价量 < 昨日成交量2%: 剔除（文档要求2%，不是5%）
        if auction_burst_ratio < 0.02:
            return None
        
        # 6. 板块竞价涨幅评分
        sector_auction_pct = auction_data.get('sector_auction_pct', 0)
        scores['sector_auction_pct'] = 10 if sector_auction_pct > 0 else 4
        result['raw_values']['sector_auction_pct'] = round(sector_auction_pct, 2)
        
        # 7. 板块共振度评分
        sector_resonance = auction_pct_chg - sector_auction_pct
        if sector_resonance > 2:
            scores['sector_resonance'] = 10  # 主动领涨
        elif sector_resonance > 0:
            scores['sector_resonance'] = 8
        elif sector_resonance > -2:
            scores['sector_resonance'] = 6
        else:
            scores['sector_resonance'] = 4  # 被动跟风
        result['raw_values']['sector_resonance'] = round(sector_resonance, 2)
        
        # 8. T日评分
        scores['t_day_score'] = min(10, t_day_score / 10)
        result['raw_values']['t_day_score'] = t_day_score
        
        # 9. 市场风险因子
        scores['market_risk'] = max(0, 10 - market_risk)
        result['raw_values']['market_risk'] = market_risk
        
        # 计算加权总分
        total = sum(scores[k] * self.weights[k] / 10 for k in scores)
        result['auction_score'] = round(total, 2)
        
        # 最终评分 = 竞价评分 * 0.6 + T日评分 * 0.4
        result['final_score'] = round(result['auction_score'] * 0.6 + t_day_score * 0.4, 2)
        
        return result
    
    def check_weak_to_strong(self, t_day_data: Dict, auction_data: Dict) -> bool:
        """
        检查是否符合"竞价爆量弱转强"条件
        
        条件A: T日炸板次数 > 0
        条件B: T+1日竞价金额 > T日全天成交额的 10%
        条件C: T+1日竞价涨幅高开，大于2%
        
        满足 A+B+C，给予95分超高评级
        """
        limit_times = t_day_data.get('limit_times', 0)
        auction_amount = auction_data.get('auction_amount', 0)
        t_day_amount = t_day_data.get('amount', 0)
        auction_pct_chg = auction_data.get('auction_pct_chg', 0)
        
        condition_a = limit_times > 0
        condition_b = t_day_amount > 0 and auction_amount > t_day_amount * 0.1
        condition_c = auction_pct_chg > 2
        
        return condition_a and condition_b and condition_c


if __name__ == '__main__':
    # 测试评分模型
    model = ScoringModel()
    
    test_stock = {
        'ts_code': '000001.SZ',
        'name': '平安银行',
        'first_limit_time': '09:45:00',
        'limit_times': 0,
        'consecutive_limit': 2,
        'limit_amount': 50000,  # 万
        'amount': 200000,  # 万
        'free_mv': 500000,  # 万
        'volume_ratio': 2.5,
        'bias_ma3': 5.2
    }
    
    score = model.score_stock(test_stock, [200000, 150000, 100000])
    if score:
        print(f"总分: {score.total_score}")
        print(f"各因子得分: {score.raw_values}")
