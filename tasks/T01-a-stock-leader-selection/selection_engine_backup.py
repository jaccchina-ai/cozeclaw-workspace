"""
T01 选股系统 - 主选股引擎

整合所有模块，实现完整的选股流程
"""

import os
import sys
import json
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# 忽略 SIGPIPE 信号，防止 BrokenPipeError
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入安全输出工具
try:
    from safe_output import safe_print
except ImportError:
    # 如果导入失败，定义一个简单版本
    def safe_print(*args, **kwargs):
        try:
            print(*args, **kwargs)
        except (BrokenPipeError, IOError):
            pass

from data_fetcher import DataFetcher, create_fetcher
from scoring_model import ScoringModel, AuctionScoringModel, StockScore, FactorWeights
from database.models import (
    init_db, get_session,
    MarketSentiment, LimitUpStock, StockFactorScore,
    AuctionData, SelectionResult, DailyStockRecord
)
from database.dual_write_manager import get_dual_write_manager

# 添加 unifuncs skill 路径
unifuncs_path = '/workspace/projects/workspace/skills/unifuncs/scripts'
if os.path.exists(unifuncs_path):
    sys.path.insert(0, unifuncs_path)
try:
    from unifuncs_client import UnifuncsClient
    UNIFUNCS_AVAILABLE = True
except ImportError as e:
    UNIFUNCS_AVAILABLE = False
    print(f"⚠️ unifuncs skill 未安装，舆情分析功能不可用: {e}")

# 导入游资管理器
try:
    from hot_money_manager import create_hot_money_manager, HotMoneyManager
    HOT_MONEY_AVAILABLE = True
except ImportError as e:
    HOT_MONEY_AVAILABLE = False
    print(f"⚠️ 游资管理器未安装，游资画像功能不可用: {e}")


class TDaySelectionEngine:
    """T日20:00选股引擎"""
    
    def __init__(self):
        self.fetcher = create_fetcher()
        self.scoring_model = ScoringModel()
        self.session = get_session()
        self.tdx_sector_zt_count = {}  # 通达信板块涨停股数量缓存
        self.hot_sectors_tdx = []  # 通达信热门板块缓存
        self.hot_money_manager = None  # 游资管理器
        
        # 初始化游资管理器
        if HOT_MONEY_AVAILABLE:
            try:
                self.hot_money_manager = create_hot_money_manager()
            except Exception as e:
                safe_print(f"   ⚠️ 游资管理器初始化失败: {e}")
        self.hot_sectors_tdx = []  # 通达信热门板块缓存
        self.industry_sector_daily = {}  # 行业板块行情缓存 {行业名: {pct_change, amount, limit_up_num}}
        
    def run(self, date: str = None, top_n: int = 10) -> Tuple[List[Dict], Dict]:
        """
        执行T日选股流程
        
        Args:
            date: 日期 YYYYMMDD，默认今天
            top_n: 返回前N只股票
            
        Returns:
            (选股结果列表, 市场情绪数据)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n{'='*60}")
        print(f"T01 龙头战法 - T日选股引擎")
        print(f"日期: {date}")
        print(f"{'='*60}\n")
        
        # 1. 检查是否为交易日
        if not self.fetcher.is_trading_day(date):
            print(f"❌ {date} 不是交易日，跳过选股")
            return [], {}
        
        print(f"✅ 确认交易日")
        
        # 2. 获取市场情绪数据
        print("\n📊 获取市场情绪数据...")
        sentiment = self._get_market_sentiment(date)
        self._save_sentiment(sentiment)
        
        # 3. 获取涨停股票列表
        print("\n📈 获取涨停股票列表...")
        limit_stocks = self.fetcher.get_limit_up_stocks(date)
        if limit_stocks.empty:
            print("❌ 今日无涨停股票")
            return [], sentiment
        
        print(f"   找到 {len(limit_stocks)} 只涨停股票")
        
        # 保存涨停股数据用于板块联动因子计算
        self.limit_up_stocks_df = limit_stocks
        
        # 3.5. 获取通达信热门板块（新增）
        print("\n🔥 分析通达信热门板块...")
        self._analyze_tdx_hot_sectors(date, limit_stocks['ts_code'].tolist())
        
        # 4. 过滤涨停股票
        print("\n🔍 过滤涨停股票...")
        filtered_stocks = self.fetcher.filter_limit_up_stocks(limit_stocks, date)
        if filtered_stocks.empty:
            print("❌ 过滤后无符合条件的股票")
            return [], sentiment
        
        print(f"   过滤后剩余 {len(filtered_stocks)} 只")
        
        # 5. 对每只股票进行评分
        print("\n⭐ 计算十一因子评分...")
        scored_stocks = self._score_all_stocks(filtered_stocks, date)
        
        # 6. 按评分排序
        scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 7. 使用 Unifuncs 舆情分析结果（优先读取本地预热结果）
        if len(scored_stocks) > 0:
            print("\n🤖 读取 Unifuncs 预热结果...")
            try:
                top_for_analysis = scored_stocks[:min(20, len(scored_stocks))]
                unifuncs_scores = self._get_unifuncs_scores(top_for_analysis, date)
                
                # 更新评分结果 - Unifuncs推荐的股票直接加10分，不赋予权重
                for stock in scored_stocks:
                    ts_code = stock['ts_code']
                    if ts_code in unifuncs_scores:
                        stock['unifuncs_recommended'] = True
                        stock['sentiment_score'] = unifuncs_scores[ts_code]  # 10分
                        # 直接加10分，不乘以权重
                        stock['total_score'] += unifuncs_scores[ts_code]  # 直接加10分
                        print(f"   🎯 Unifuncs推荐股票加分: {ts_code}")
            except Exception as e:
                print(f"   ⚠️ 读取 Unifuncs 结果失败: {e}")
        
        # 8. 重新排序（考虑舆情分析附加分后）
        scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 9. 使用StockMatcher增强Unifuncs匹配
        try:
            from stock_matcher import StockMatcher
            from unifuncs_sync import UnifuncsSync
            
            sync = UnifuncsSync()
            unifuncs_recommendations = sync.sync_results(date)
            
            if unifuncs_recommendations:
                print(f"\n🔍 使用StockMatcher增强Unifuncs匹配...")
                matcher = StockMatcher()
                scored_stocks = matcher.batch_match(scored_stocks, unifuncs_recommendations)
                
                # 重新排序
                scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
                
                # 统计匹配结果
                matched_count = sum(1 for s in scored_stocks if s.get('unifuncs_recommended', False))
                print(f"   ✅ 已匹配 {matched_count} 只Unifuncs推荐股票")
        except Exception as e:
            print(f"   ⚠️ StockMatcher增强失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 10. 取前N只
        top_stocks = scored_stocks[:top_n]
        
        # 8. 生成推荐理由
        for i, stock in enumerate(top_stocks):
            stock['rank'] = i + 1
            stock['reason'] = self.scoring_model.generate_reason(
                self._dict_to_stock_score(stock)
            )
        
        # 9. mx_search 增强 (涨停原因、风险检测)
        try:
            from mx_search_integration import MxSearchIntegration
            mx = MxSearchIntegration()
            if mx.check_quota(10):  # 检查是否有足够配额
                print("\n🔍 使用 mx_search 增强选股信息...")
                top_stocks = mx.enhance_t_day_stocks(top_stocks, top_n=10)
                print(f"   ✅ 已增强 {len(top_stocks)} 只股票信息")
            else:
                print(f"\n⚠️ mx_search API配额不足 ({mx.get_remaining_quota()} 次剩余)，跳过增强")
        except Exception as e:
            print(f"\n⚠️ mx_search 增强失败: {e}")

        # 10. 保存结果
        self._save_selection_results(top_stocks, date, 't_day')

        # 11. 保存因子评分详情 (用于机器学习)
        self._save_factor_scores(scored_stocks, date)

        # 12. 更新 SESSION-STATE
        self._update_session_state(date, top_stocks, sentiment)

        print(f"\n✅ 选股完成，共选出 {len(top_stocks)} 只股票")
        
        return top_stocks, sentiment
    
    def _get_market_sentiment(self, date: str) -> Dict:
        """获取完整市场情绪数据"""
        sentiment = self.fetcher.get_market_sentiment(date)
        
        # 获取融资融券数据
        margin = self.fetcher.get_margin_data(date)
        if margin:
            sentiment['rz_ye'] = margin.get('rzye', 0) / 1e8  # 转换为亿
            sentiment['rz_ye_change'] = margin.get('rzye_chg', 0)
            sentiment['rq_ye'] = margin.get('rqye', 0) / 1e8
            sentiment['rq_ye_change'] = margin.get('rqye_chg', 0)
        
        # 获取北向资金
        north = self.fetcher.get_north_money(date)
        sentiment['north_net_inflow'] = north.get('total_net', 0)
        
        # 计算风险评分
        sentiment['risk_score'] = self._calculate_risk_score(sentiment)
        sentiment['suggested_position'] = self._calculate_suggested_position(sentiment)
        
        return sentiment
    
    def _calculate_risk_score(self, sentiment: Dict) -> float:
        """
        计算宏观风险评分 (0-10, 越高风险越大)
        """
        risk = 0
        
        # 大盘偏离度风险
        sh_bias = float(sentiment.get('sh_bias', 0) or 0)
        if sh_bias > 3:
            risk += 2
        elif sh_bias > 2:
            risk += 1
        elif sh_bias < -3:
            risk += 3  # 超跌风险
        elif sh_bias < -2:
            risk += 1
        
        # 涨跌停比例风险
        zt_num = int(sentiment.get('zt_num', 0) or 0)
        dt_num = int(sentiment.get('dt_num', 0) or 0)
        if dt_num > zt_num:
            risk += 3
        elif dt_num > zt_num * 0.5:
            risk += 2
        
        # 融资融券风险 - 四大风险因子
        rz_ye_change = float(sentiment.get('rz_ye_change', 0) or 0)
        if rz_ye_change < -2:  # 融资余额下降>2%
            risk += 2
        
        rq_ye_change = float(sentiment.get('rq_ye_change', 0) or 0)
        if rq_ye_change > 5:  # 融券余额上升>5%
            risk += 2
        
        rz_buy_repay_ratio = float(sentiment.get('rz_buy_repay_ratio', 1) or 1)
        if rz_buy_repay_ratio < 0.8:  # 融资买入/偿还比率<0.8
            risk += 2
        
        rz_ye = float(sentiment.get('rz_ye', 0) or 0)
        if rz_ye > 8000e8:  # 融资余额>8000亿
            risk += 1
        
        # 北向资金风险
        north_net = float(sentiment.get('north_net_inflow', 0) or 0)
        if north_net < -50:
            risk += 2
        elif north_net < -20:
            risk += 1
        
        # 时间窗口风险
        date_str = sentiment.get('trade_date', '')
        if date_str:
            time_risk = self._check_time_window_risk(date_str)
            risk += time_risk
        
        return min(10, risk)
    
    def _check_time_window_risk(self, date_str: str) -> float:
        """
        检查时间窗口风险
        
        - 月末最后3天
        - 季末月份（3、6、9、12月）
        - 年末最后5天
        """
        risk = 0
        
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            month = date.month
            day = date.day
            
            # 月末最后3天
            if day >= 28:
                risk += 0.5
            
            # 季末月份（3、6、9、12月）
            if month in [3, 6, 9, 12]:
                risk += 0.5
            
            # 年末最后5天
            if month == 12 and day >= 27:
                risk += 1
            
        except:
            pass
        
        return risk
    
    def _calculate_suggested_position(self, sentiment: Dict) -> float:
        """计算建议仓位 (0-1)"""
        risk = sentiment.get('risk_score', 5)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        
        # 基础仓位
        base_position = 0.5
        
        # 根据风险调整
        position = base_position - risk * 0.05
        
        # 根据情绪阶段调整
        stage_adjust = {
            '冰点': -0.2,
            '混沌': 0,
            '主升': 0.2,
            '高潮': -0.1  # 高潮时反而要谨慎
        }
        position += stage_adjust.get(sentiment_stage, 0)
        
        return max(0.1, min(0.8, position))
    
    def _score_all_stocks(self, stocks_df: pd.DataFrame, date: str) -> List[Dict]:
        """对所有股票进行评分（优化版：批量预获取数据）"""
        import time
        
        results = []
        all_amounts = stocks_df['amount'].tolist() if 'amount' in stocks_df.columns else []
        ts_codes = stocks_df['ts_code'].tolist() if 'ts_code' in stocks_df.columns else []
        
        # ===== 批量预获取数据（减少API调用次数） =====
        print("   📦 批量获取数据中...")
        
        # 1. 批量获取日线数据（用于计算MA3乖离率等）
        daily_data_cache = {}
        try:
            batch_df = self.fetcher.get_stocks_daily_batch(ts_codes, date)
            if not batch_df.empty:
                for _, row in batch_df.iterrows():
                    daily_data_cache[row['ts_code']] = row.to_dict()
            print(f"      日线数据: {len(daily_data_cache)} 只")
        except Exception as e:
            print(f"      ⚠️ 批量获取日线数据失败: {e}")
        
        # 1.5 批量获取历史数据并计算MA3乖离率
        bias_ma3_cache = {}
        try:
            # 获取当前收盘价
            current_prices = {code: daily_data_cache.get(code, {}).get('close', 0) for code in ts_codes}
            # 从涨停股数据获取收盘价（更准确）
            for _, row in stocks_df.iterrows():
                current_prices[row['ts_code']] = row['close']
            
            # 批量获取历史数据
            history_data = self.fetcher.get_stocks_history_batch(ts_codes, date, days=5)
            print(f"      历史数据: {len(history_data)} 只")
            
            # 批量计算MA3乖离率
            bias_ma3_cache = self.fetcher.calculate_bias_ma3_batch(history_data, current_prices)
            print(f"      MA3乖离率: {sum(1 for v in bias_ma3_cache.values() if v != 0)} 只有值")
        except Exception as e:
            print(f"      ⚠️ 计算MA3乖离率失败: {e}")
            # 使用默认值
            bias_ma3_cache = {code: 0 for code in ts_codes}
        moneyflow_cache = {}
        for i, code in enumerate(ts_codes):
            try:
                moneyflow_cache[code] = self.fetcher.get_stock_moneyflow(code, date)
                time.sleep(0.05)  # 速率限制
            except Exception:
                moneyflow_cache[code] = None
            if (i + 1) % 10 == 0:
                print(f"      资金流向进度: {i+1}/{len(ts_codes)}")
        print(f"      资金流向数据: {sum(1 for v in moneyflow_cache.values() if v)} 只")
        
        # 3. 批量获取龙虎榜数据
        dragon_tiger_cache = {}
        for i, code in enumerate(ts_codes):
            try:
                dragon_tiger_cache[code] = self.fetcher.get_dragon_tiger_list(code, date)
                time.sleep(0.05)  # 速率限制
            except Exception:
                dragon_tiger_cache[code] = None
            if (i + 1) % 10 == 0:
                print(f"      龙虎榜进度: {i+1}/{len(ts_codes)}")
        print(f"      龙虎榜数据: {sum(1 for v in dragon_tiger_cache.values() if v)} 只")
        
        print("   ✅ 数据预获取完成，开始评分...")
        
        # ===== 开始评分 =====
        for _, row in stocks_df.iterrows():
            try:
                stock_data = row.to_dict()
                ts_code = stock_data.get('ts_code', '')
                
                # 处理首次涨停时间格式（HHMMSS -> HH:MM:SS）
                first_time = str(stock_data.get('first_time', ''))
                if first_time and len(first_time) >= 5:
                    # 格式如 "93012" -> "09:30:12"
                    hour = first_time[:-4].zfill(2)
                    minute = first_time[-4:-2]
                    second = first_time[-2:]
                    stock_data['first_limit_time'] = f"{hour}:{minute}:{second}"
                else:
                    stock_data['first_limit_time'] = ''
                
                # 炸板次数
                stock_data['limit_times'] = int(stock_data.get('open_times', 0) or 0)
                
                # 连板数
                up_stat = str(stock_data.get('up_stat', '1/1'))
                try:
                    stock_data['consecutive_limit'] = int(up_stat.split('/')[0])
                except:
                    stock_data['consecutive_limit'] = 1
                
                # 从缓存获取龙虎榜数据
                dragon_tiger = dragon_tiger_cache.get(ts_code)
                
                # 使用游资管理器增强龙虎榜分析
                hot_money_details = {}
                if self.hot_money_manager and dragon_tiger:
                    try:
                        hm_score, hot_money_details = self.hot_money_manager.get_hot_money_score(
                            dragon_tiger, 
                            stock_mv=float(stock_data.get('float_mv', 0) or 0) / 1e8  # 转换为亿
                        )
                        # 将游资评分合并到龙虎榜数据中
                        dragon_tiger['hot_money_score'] = hm_score
                        dragon_tiger['hot_money_details'] = hot_money_details
                    except Exception as e:
                        pass
                
                # 从缓存获取资金流向数据
                moneyflow = moneyflow_cache.get(ts_code)
                if moneyflow:
                    # 主力净流入（万元）
                    stock_data['main_net_inflow'] = moneyflow.get('net_mf_amount', 0)
                    # 主力净占比（需要计算）
                    buy_lg = float(moneyflow.get('buy_lg_amount', 0) or 0)
                    buy_elg = float(moneyflow.get('buy_elg_amount', 0) or 0)
                    sell_lg = float(moneyflow.get('sell_lg_amount', 0) or 0)
                    sell_elg = float(moneyflow.get('sell_elg_amount', 0) or 0)
                    total_main = buy_lg + buy_elg + sell_lg + sell_elg
                    if total_main > 0:
                        stock_data['main_net_ratio'] = moneyflow.get('net_mf_amount', 0) / total_main * 100
                    else:
                        stock_data['main_net_ratio'] = 0
                    # 中单净额
                    stock_data['medium_net'] = float(moneyflow.get('buy_md_amount', 0) or 0) - float(moneyflow.get('sell_md_amount', 0) or 0)
                
                # 使用 fd_amount 作为封单金额（单位：元），limit_amount 通常为空
                stock_data['seal_amount'] = float(stock_data.get('fd_amount', 0) or 0)
                
                # 使用 float_mv 作为流通市值（单位：元）
                stock_data['free_mv'] = float(stock_data.get('float_mv', 0) or 0)
                
                # 板块数据（使用行业板块行情缓存）
                industry = stock_data.get('industry', '')
                sector_info = self.industry_sector_daily.get(industry, {})
                sector_data = {
                    'name': industry,
                    'zt_count': len(self.limit_up_stocks_df[
                        self.limit_up_stocks_df['industry'] == industry
                    ]) if hasattr(self, 'limit_up_stocks_df') else 0,
                    'pct_chg': sector_info.get('pct_change', 0),
                    'main_inflow': sector_info.get('amount', 0) / 1e8  # 转换为亿
                }
                
                # MA3 乖离率（从缓存获取）
                stock_data['bias_ma3'] = bias_ma3_cache.get(ts_code, 0)
                
                # 计算板块联动强度因子 (增强版：加入行业涨跌幅)
                try:
                    industry = stock_data.get('industry', '')
                    if industry:
                        # 1. 获取该行业内的涨停股数量
                        industry_zt_count = 0
                        if hasattr(self, 'limit_up_stocks_df'):
                            industry_zt_count = len(self.limit_up_stocks_df[
                                self.limit_up_stocks_df['industry'] == industry
                            ])
                        
                        # 2. 从行业板块行情缓存获取涨跌幅等数据
                        sector_info = self.industry_sector_daily.get(industry, {})
                        sector_pct_change = sector_info.get('pct_change', 0)
                        sector_amount = sector_info.get('amount', 0)
                        sector_up_num = sector_info.get('up_num', 0)
                        sector_down_num = sector_info.get('down_num', 0)
                        
                        # 3. 计算各子指标得分
                        
                        # 3.1 行业涨停股数量得分 (0-40分)
                        # 涨停股越多，板块热度越高
                        zt_score = min(40, industry_zt_count * 5)
                        
                        # 3.2 行业涨跌幅得分 (0-30分)
                        # 涨幅越大，板块越强
                        # 映射：-5% -> 0分, 0% -> 15分, +10% -> 30分
                        pct_score = max(0, min(30, (sector_pct_change + 5) / 15 * 30))
                        
                        # 3.3 行业内涨跌家数比得分 (0-20分)
                        # 上涨家数占比越高，板块越健康
                        total_stocks = sector_up_num + sector_down_num
                        if total_stocks > 0:
                            up_ratio = sector_up_num / total_stocks
                            up_ratio_score = up_ratio * 20
                        else:
                            up_ratio_score = 10  # 默认中等分
                        
                        # 3.4 行业成交额排名得分 (0-10分)
                        # 成交额越大，关注度越高
                        if sector_amount > 0:
                            # 计算成交额排名（所有行业中）
                            all_amounts = [s.get('amount', 0) for s in self.industry_sector_daily.values()]
                            if all_amounts:
                                rank = sum(1 for a in all_amounts if a > sector_amount) + 1
                                # 排名越靠前得分越高
                                amount_score = max(0, 10 - (rank - 1) * 0.5)
                            else:
                                amount_score = 5
                        else:
                            amount_score = 5
                        
                        # 4. 计算综合得分
                        linkage_score = zt_score + pct_score + up_ratio_score + amount_score
                        
                        # 5. 角色标签初始值（后续根据板块内排名确定最终标签）
                        # 先记录板块涨停数和联动得分，用于后续判断
                        stock_data['industry_zt_count'] = industry_zt_count
                        stock_data['industry_linkage_score'] = linkage_score
                        # 初始标签，后续会根据板块内排名更新
                        stock_data['sector_role_label'] = '待定'
                        
                        stock_data['sector_linkage_score'] = linkage_score
                        stock_data['sector_linkage_raw'] = {
                            'industry': industry,
                            'industry_zt_count': industry_zt_count,
                            'sector_pct_change': round(sector_pct_change, 2),
                            'sector_up_ratio': round(up_ratio, 2) if total_stocks > 0 else 0,
                            'sector_amount_rank': rank if sector_amount > 0 else 0,
                            'zt_score': round(zt_score, 1),
                            'pct_score': round(pct_score, 1),
                            'up_ratio_score': round(up_ratio_score, 1),
                            'amount_score': round(amount_score, 1),
                        }
                    else:
                        stock_data['sector_linkage_score'] = 50
                        stock_data['sector_linkage_raw'] = {'industry': '', 'industry_zt_count': 0}
                        stock_data['sector_role_label'] = '独立强势'
                        stock_data['industry_zt_count'] = 0
                        stock_data['industry'] = ''
                        stock_data['industry_linkage_score'] = 50
                except Exception as e:
                    stock_data['sector_linkage_score'] = 50  # 默认中等分
                    stock_data['sector_linkage_raw'] = {}
                    stock_data['sector_role_label'] = '独立强势'
                    stock_data['industry_zt_count'] = 0
                    stock_data['industry'] = ''
                    stock_data['industry_linkage_score'] = 50
                
                # 执行评分
                score = self.scoring_model.score_stock(
                    stock_data,
                    all_amounts,
                    dragon_tiger,
                    {},  # north_data 在此处不重要
                    sector_data
                )
                
                if score is None:
                    continue
                
                result = {
                    'ts_code': ts_code,
                    'stock_name': stock_data.get('name', ''),
                    'total_score': score.total_score,
                    'sector': score.sector,
                    'industry': stock_data.get('industry', ''),  # 行业字段，用于板块内排名
                    'industry_zt_count': stock_data.get('industry_zt_count', 0),  # 板块涨停数
                    'industry_linkage_score': stock_data.get('industry_linkage_score', 50),  # 板块联动得分
                    'raw_values': score.raw_values,
                    'limit_quality_score': score.limit_quality_score,
                    'seal_ratio_score': score.seal_ratio_score,
                    'seal_flow_ratio_score': score.seal_flow_ratio_score,
                    'volume_ratio_score': score.volume_ratio_score,
                    'turnover_rate_score': score.turnover_rate_score,
                    'dragon_tiger_score': score.dragon_tiger_score,
                    'money_flow_score': score.money_flow_score,
                    'amount_rank_score': score.amount_rank_score,
                    'sector_heat_score': score.sector_heat_score,
                    'bias_ma3_score': score.bias_ma3_score,
                    'sentiment_score': score.sentiment_score,
                    'sector_linkage_score': score.sector_linkage_score,
                    'sector_role_label': stock_data.get('sector_role_label', '')  # 初始标签，后续更新
                }
                
                results.append(result)
                
            except Exception as e:
                safe_print(f"   ⚠️ 评分失败 {stock_data.get('ts_code', 'unknown')}: {e}")
                continue
        
        # ========== 根据板块内排名确定最终角色标签 ==========
        # 四个标签：板块龙头、前排跟随、后排跟风、独立强势
        print("   🏷️ 确定板块角色标签...")
        
        # 按行业分组
        industry_stocks = {}  # {行业名: [股票列表]}
        for r in results:
            ind = r.get('industry', '')
            if ind:
                if ind not in industry_stocks:
                    industry_stocks[ind] = []
                industry_stocks[ind].append(r)
        
        # 对每个行业内的股票按评分排序，确定角色标签
        for industry, stocks_in_industry in industry_stocks.items():
            # 按评分降序排序
            stocks_in_industry.sort(key=lambda x: x['total_score'], reverse=True)
            
            # 获取该行业的涨停股数量
            industry_zt_count = stocks_in_industry[0].get('industry_zt_count', 0)
            
            # 判断是否有板块效应（涨停股>=2）和是否够龙头标准（涨停股>=3）
            has_sector_effect = industry_zt_count >= 2
            can_be_leader = industry_zt_count >= 3  # 板块龙头需要涨停股>=3
            
            for i, stock in enumerate(stocks_in_industry):
                if has_sector_effect:
                    # 有板块效应（涨停股>=2）
                    if i == 0 and can_be_leader:
                        # 第1名且涨停股>=3：板块龙头
                        stock['sector_role_label'] = '板块龙头'
                    elif i == 0 and not can_be_leader:
                        # 第1名但涨停股只有2只：前排跟随（不够龙头标准）
                        stock['sector_role_label'] = '前排跟随'
                    elif i == 1 or i == 2:
                        # 第2-3名：前排跟随
                        stock['sector_role_label'] = '前排跟随'
                    else:
                        # 第4名及以后：后排跟风
                        stock['sector_role_label'] = '后排跟风'
                else:
                    # 无板块效应（涨停股<2），标记为独立强势
                    stock['sector_role_label'] = '独立强势'
        
        # 处理无行业的股票（独立强势）
        for r in results:
            if not r.get('industry') or r.get('sector_role_label') == '待定':
                r['sector_role_label'] = '独立强势'
        
        # 打印角色标签统计
        role_counts = {}
        for r in results:
            label = r.get('sector_role_label', '未知')
            role_counts[label] = role_counts.get(label, 0) + 1
        print(f"   角色标签分布: {role_counts}")
        
        return results
    
    def _dict_to_stock_score(self, data: Dict) -> StockScore:
        """将字典转换为 StockScore 对象"""
        return StockScore(
            ts_code=data.get('ts_code', ''),
            stock_name=data.get('stock_name', ''),
            limit_quality_score=data.get('limit_quality_score', 0),
            seal_ratio_score=data.get('seal_ratio_score', 0),
            seal_flow_ratio_score=data.get('seal_flow_ratio_score', 0),
            volume_ratio_score=data.get('volume_ratio_score', 0),
            turnover_rate_score=data.get('turnover_rate_score', 0),
            dragon_tiger_score=data.get('dragon_tiger_score', 0),
            money_flow_score=data.get('money_flow_score', 0),
            amount_rank_score=data.get('amount_rank_score', 0),
            sector_heat_score=data.get('sector_heat_score', 0),
            bias_ma3_score=data.get('bias_ma3_score', 0),
            sentiment_score=data.get('sentiment_score', 0),
            sector_linkage_score=data.get('sector_linkage_score', 0),
            total_score=data.get('total_score', 0),
            sector=data.get('sector', ''),
            unifuncs_recommended=data.get('unifuncs_recommended', False)
        )
    
    def _get_unifuncs_scores(self, stocks: List[Dict], date: str) -> Dict[str, float]:
        """
        读取 Unifuncs 预先保存的结果
        
        19:30 的预热任务已将结果保存到 unifuncs_result.json
        本方法直接从本地文件读取，不再实时调用 API

        Args:
            stocks: 股票列表
            date: 日期 YYYYMMDD
            
        Returns:
            {ts_code: 涨停概率分数(0-10)}
        """
        scores = {}

        try:
            # 从本地文件读取 Unifuncs 结果
            from unifuncs_scheduler import load_result

            result_data = load_result(date)

            if result_data is None:
                print(f"   ⚠️ 未找到 {date} 的 Unifuncs 预热结果")
                return {}

            status = result_data.get('status', '')
            print(f"   Unifuncs 预热结果状态: {status}")

            if status != 'completed':
                print(f"   ⚠️ Unifuncs 任务未完成（状态: {status}），使用空结果")
                return {}

            # 兼容两种格式：
            # 新格式（结构化摘要）：recommendations 字段
            # 旧格式（完整报告）：answer/summary 字段
            recommendations = result_data.get('recommendations', [])
            answer = result_data.get('answer', '')
            summary = result_data.get('summary', '')

            if recommendations:
                # 新格式：结构化摘要
                print(f"   ✅ 读取到 Unifuncs 结构化摘要")
                print(f"   📊 热点板块: {result_data.get('hot_sectors', [])}")
                
                # 提取推荐的股票代码
                recommended_codes = set()
                for rec in recommendations:
                    code = rec.get('code', '')
                    if code:
                        # 转换为 ts_code 格式（需要添加后缀）
                        recommended_codes.add(code)
                        print(f"   🤖 Unifuncs推荐: {code} {rec.get('name', '')} ({rec.get('consecutive_boards', 0)}板)")
                
                # 匹配股票
                for stock in stocks:
                    ts_code = stock['ts_code']
                    stock_name = stock.get('stock_name', stock.get('name', ''))
                    
                    # ts_code 格式为 002015.SZ，提取代码部分
                    code_part = ts_code.split('.')[0]
                    
                    # 检查是否在 Unifuncs 推荐中
                    if code_part in recommended_codes or ts_code in answer or stock_name in answer:
                        scores[ts_code] = 10  # 推荐的股票加10分
                        
            elif answer or summary:
                # 旧格式：完整报告
                print(f"   ✅ 读取到 Unifuncs 完整报告")
                
                for stock in stocks:
                    ts_code = stock['ts_code']
                    stock_name = stock.get('stock_name', stock.get('name', ''))
                    
                    if ts_code in answer or stock_name in answer:
                        scores[ts_code] = 10
                        print(f"   🤖 Unifuncs推荐: {ts_code} {stock_name}")
            else:
                print(f"   ⚠️ Unifuncs 结果为空")
                return {}

            return scores

        except Exception as e:
            print(f"   ❌ 读取 Unifuncs 结果失败: {e}")
            return {}
    
    def _analyze_tdx_hot_sectors(self, date: str, limit_up_codes: List[str]):
        """
        分析通达信热门板块
        
        Args:
            date: 日期 YYYYMMDD
            limit_up_codes: 涨停股票代码列表
        """
        try:
            # 1. 获取热门行业板块（只使用行业板块，不使用概念板块）
            self.hot_sectors_tdx = self.fetcher.get_hot_sectors_tdx(
                date=date, 
                top_n=10, 
                idx_type='行业板块'
            )
            
            if self.hot_sectors_tdx:
                print(f"   📈 通达信热门行业板块 TOP5:")
                for i, sector in enumerate(self.hot_sectors_tdx[:5]):
                    print(f"      {i+1}. {sector['name']}: +{sector['pct_change']:.2f}% "
                          f"(涨停{sector['limit_up_num']}只, 成分{sector['idx_count']}只)")
            
            # 2. 统计每个板块的涨停股数量
            self.tdx_sector_zt_count = self.fetcher.get_sector_zt_count_tdx(
                limit_up_codes, date
            )
            
            if self.tdx_sector_zt_count:
                # 按涨停股数量排序，显示前5
                sorted_sectors = sorted(
                    self.tdx_sector_zt_count.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
                print(f"   🔥 涨停股集中板块 TOP5:")
                for ts_code, count in sorted_sectors:
                    # 从热门板块缓存中查找名称
                    name = ts_code
                    for s in self.hot_sectors_tdx:
                        if s['ts_code'] == ts_code:
                            name = s['name']
                            break
                    print(f"      {name}: {count}只涨停")
            
            # 3. 获取并缓存所有行业板块行情数据（用于板块联动因子计算）
            try:
                sector_daily_df = self.fetcher.get_tdx_sector_daily(date=date)
                if not sector_daily_df.empty:
                    # 获取行业板块名称映射
                    industry_sectors = self.fetcher.get_tdx_industry_sectors(date)
                    name_map = dict(zip(industry_sectors['ts_code'], industry_sectors['name']))
                    
                    # 构建缓存 {行业名: {pct_change, amount, limit_up_num}}
                    for _, row in sector_daily_df.iterrows():
                        ts_code = row['ts_code']
                        sector_name = name_map.get(ts_code, '')
                        if sector_name:
                            self.industry_sector_daily[sector_name] = {
                                'pct_change': float(row.get('pct_change', 0) or 0),
                                'amount': float(row.get('amount', 0) or 0),
                                'limit_up_num': int(row.get('limit_up_num', 0) or 0),
                                'up_num': int(row.get('up_num', 0) or 0),
                                'down_num': int(row.get('down_num', 0) or 0),
                            }
                    print(f"   📊 已缓存 {len(self.industry_sector_daily)} 个行业板块行情数据")
            except Exception as e:
                print(f"   ⚠️ 获取行业板块行情失败: {e}")
                    
        except Exception as e:
            print(f"   ⚠️ 分析通达信热门板块失败: {e}")
    
    def _get_tdx_sector_data(self, ts_code: str, date: str) -> Dict:
        """
        获取股票所属通达信板块数据
        
        Args:
            ts_code: 股票代码
            date: 日期 YYYYMMDD
            
        Returns:
            板块数据字典，包含 name, zt_count, pct_chg, main_inflow
        """
        result = {
            'name': '',
            'zt_count': 0,
            'pct_chg': 0,
            'main_inflow': 0
        }
        
        try:
            # 获取热门板块代码列表（用于优化查询）
            hot_sector_codes = [s['ts_code'] for s in self.hot_sectors_tdx]
            
            # 获取股票所属的通达信板块（优先查询热门板块）
            sectors = self.fetcher.get_stock_tdx_sectors(
                ts_code, date, hot_sector_codes=hot_sector_codes
            )
            
            if not sectors:
                return result
            
            # 优先选择行业板块（不使用概念板块）
            industry_sectors = [s for s in sectors if s['idx_type'] == '行业板块']
            target_sector = industry_sectors[0] if industry_sectors else sectors[0]
            
            result['name'] = target_sector['name']
            
            # 获取该板块的涨停股数量
            sector_code = target_sector['ts_code']
            result['zt_count'] = self.tdx_sector_zt_count.get(sector_code, 0)
            
            # 从热门板块缓存中获取涨跌幅
            for hot in self.hot_sectors_tdx:
                if hot['ts_code'] == sector_code:
                    result['pct_chg'] = hot['pct_change']
                    break
            
            return result
            
        except Exception as e:
            return result
    
    def _save_sentiment(self, sentiment: Dict):
        """保存市场情绪数据（双写：PostgreSQL + SQLite）"""
        try:
            # 转换 numpy 类型为 Python 原生类型
            import numpy as np
            converted_sentiment = {}
            for key, value in sentiment.items():
                if isinstance(value, (np.integer, np.floating)):
                    converted_sentiment[key] = float(value)
                elif isinstance(value, np.ndarray):
                    converted_sentiment[key] = value.tolist()
                else:
                    converted_sentiment[key] = value
            
            # 双写
            manager = get_dual_write_manager()
            results = manager.save_sentiment(converted_sentiment)
            
            pg_ok = results.get('postgres', False)
            sqlite_ok = results.get('sqlite', False)
            
            if pg_ok and sqlite_ok:
                print(f"✅ 市场情绪数据已双写保存 (PG: ✅, SQLite: ✅)")
            elif pg_ok:
                print(f"✅ 市场情绪数据已保存到 PostgreSQL (SQLite: ⚠️)")
            elif sqlite_ok:
                print(f"⚠️ 市场情绪数据仅保存到 SQLite (PostgreSQL: ⚠️)")
            else:
                print(f"⚠️ 市场情绪数据保存失败")
                
        except Exception as e:
            print(f"保存情绪数据失败: {e}")
    
    def _save_selection_results(self, stocks: List[Dict], date: str, selection_type: str):
        """保存选股结果（双写：PostgreSQL + SQLite）"""
        try:
            manager = get_dual_write_manager()
            
            saved_count = {'postgres': 0, 'sqlite': 0}
            
            for stock in stocks:
                record_data = {
                    'trade_date': date,
                    'selection_type': selection_type,
                    'ts_code': stock['ts_code'],
                    'stock_name': stock['stock_name'],
                    'total_score': stock['total_score'],
                    'final_rank': stock.get('rank', 0),
                    'sector': stock.get('sector', ''),
                    'reason': stock.get('reason', ''),
                    'unifuncs_recommended': stock.get('unifuncs_recommended', False),
                    'sector_linkage_score': stock.get('sector_linkage_score', 0),
                    'sector_role_label': stock.get('sector_role_label', '')
                }
                
                results = manager.save_selection_result(record_data)
                if results.get('postgres'):
                    saved_count['postgres'] += 1
                if results.get('sqlite'):
                    saved_count['sqlite'] += 1
            
            print(f"   ✅ 选股结果已双写保存 (PG: {saved_count['postgres']} 条, SQLite: {saved_count['sqlite']} 条)")
            
        except Exception as e:
            print(f"保存选股结果失败: {e}")

    def _save_factor_scores(self, stocks: List[Dict], date: str):
        """保存每只股票的所有因子评分和原始值（双写：PostgreSQL + SQLite）"""
        try:
            manager = get_dual_write_manager()
            
            saved_count = {'postgres': 0, 'sqlite': 0}
            
            for stock in stocks:
                raw = stock.get('raw_values', {})
                
                # 直接构建记录数据，确保所有字段正确映射
                record_data = {
                    'ts_code': stock['ts_code'],
                    'trade_date': date,
                    'total_score': stock.get('total_score', 0),
                    
                    # 评分字段
                    'limit_quality_score': stock.get('limit_quality_score', 0),
                    'seal_ratio_score': stock.get('seal_ratio_score', 0),
                    'seal_flow_ratio_score': stock.get('seal_flow_ratio_score', 0),
                    'volume_ratio_score': stock.get('volume_ratio_score', 0),
                    'turnover_rate_score': stock.get('turnover_rate_score', 0),
                    'dragon_tiger_score': stock.get('dragon_tiger_score', 0),
                    'money_flow_score': stock.get('money_flow_score', 0),
                    'amount_rank_score': stock.get('amount_rank_score', 0),
                    'sector_heat_score': stock.get('sector_heat_score', 0),
                    'bias_ma3_score': stock.get('bias_ma3_score', 0),
                    'sentiment_score': stock.get('sentiment_score', 0),
                    'sector_linkage_score': stock.get('sector_linkage_score', 0),
                    
                    # 原始值字段 - 从 raw_values 获取
                    'first_limit_time_raw': str(raw.get('first_limit_time', '')),
                    'limit_times_raw': int(raw.get('limit_times', 0) or 0),
                    'seal_ratio_raw': float(raw.get('seal_ratio', 0) or 0),
                    'seal_flow_ratio_raw': float(raw.get('seal_flow_ratio', 0) or 0),
                    'volume_ratio_raw': float(raw.get('volume_ratio', 0) or 0),
                    'turnover_rate_raw': float(raw.get('real_turnover_rate', 0) or 0),
                    'net_buy_amount_raw': float(raw.get('net_buy', 0) or 0),
                    'main_net_inflow_raw': float(raw.get('main_net_inflow', 0) or 0),
                    'amount_rank_raw': int(raw.get('amount_rank', 0) or 0),
                    'sector_zt_count_raw': int(raw.get('sector_zt_count', 0) or 0),
                    'bias_ma3_raw': float(raw.get('bias_ma3', 0) or 0),
                }
                
                # 板块联动原始值是 JSON 格式
                if 'sector_linkage_raw' in stock.get('raw_values', {}):
                    record_data['sector_linkage_raw'] = json.dumps(
                        stock['raw_values']['sector_linkage_raw'], 
                        ensure_ascii=False
                    )

                # 双写
                results = manager.save_factor_score(record_data)
                if results.get('postgres'):
                    saved_count['postgres'] += 1
                if results.get('sqlite'):
                    saved_count['sqlite'] += 1

            print(f"   ✅ 因子评分已双写保存 (PG: {saved_count['postgres']} 条, SQLite: {saved_count['sqlite']} 条)")
            
        except Exception as e:
            print(f"   ⚠️ 保存因子评分失败: {e}")

    def _update_session_state(self, date: str, stocks: List[Dict], sentiment: Dict):
        """更新 SESSION-STATE.md"""
        try:
            session_state_path = os.path.join(
                os.path.dirname(__file__), 
                '../../SESSION-STATE.md'
            )
            
            # 读取现有内容
            with open(session_state_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新 Current Task 部分
            task_section = f"""
## Current Task

**T01: A股龙头选股策略系统**

状态: T日选股完成
- [x] T日({date})选股完成
- [ ] T+1竞价阶段选股

**最新选股结果 ({date})**:
"""
            for i, stock in enumerate(stocks):
                sector = stock.get('sector', '-')
                task_section += f"\n{i+1}. {stock['ts_code']} {stock['stock_name']} - 得分: {stock['total_score']:.1f} - {sector}"
            
            # 简单替换 Current Task 部分
            if '## Current Task' in content:
                start = content.find('## Current Task')
                end = content.find('## ', start + 10)
                if end > start:
                    content = content[:start] + task_section + '\n\n' + content[end:]
            
            # 写回文件
            with open(session_state_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"更新 SESSION-STATE 失败: {e}")


class T1AuctionEngine:
    """T+1日9:25竞价选股引擎"""
    
    def __init__(self):
        self.fetcher = create_fetcher()
        self.scoring_model = AuctionScoringModel()
        self.session = get_session()
    
    def run(self, date: str = None, t_day_stocks: List[Dict] = None, top_n: int = 3) -> List[Dict]:
        """
        执行T+1竞价选股流程
        
        Args:
            date: T+1日期 YYYYMMDD
            t_day_stocks: T日选股结果列表
            top_n: 返回前N只股票
            
        Returns:
            选股结果列表
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        print(f"\n{'='*60}")
        print(f"T01 龙头战法 - T+1竞价选股引擎")
        print(f"日期: {date}")
        print(f"{'='*60}\n")
        
        # 1. 检查是否为交易日
        if not self.fetcher.is_trading_day(date):
            print(f"❌ {date} 不是交易日，跳过选股")
            return []
        
        # 2. 获取T日选股结果
        if t_day_stocks is None:
            t_day = self.fetcher.get_previous_trading_day(date)
            print(f"   获取T日({t_day})选股结果...")
            t_day_stocks = self._get_t_day_results(t_day)
        
        if not t_day_stocks:
            print(f"❌ 无T日({t_day if t_day_stocks is None else 'N/A'})选股结果，跳过竞价选股")
            return []
        
        print(f"   T日初选股票数: {len(t_day_stocks)}")
        
        # 3. 获取市场风险
        market_risk = self._get_market_risk(date)
        
        # 4. 批量获取竞价数据（使用 stk_auction 接口）
        print("\n📊 批量获取竞价数据...")
        ts_codes = [s['ts_code'] for s in t_day_stocks]
        auction_data_map = self.fetcher.get_auction_data_batch(ts_codes, date)
        
        # 5. 对每只股票进行评分（同时保存所有数据供ML使用）
        print("\n⭐ 竞价评分...")
        all_stocks_data = []  # 保存所有股票的完整数据（用于ML）
        scored_stocks = []    # 通过评分的股票（用于选股）
        
        for t_stock in t_day_stocks:
            ts_code = t_stock['ts_code']
            
            # 获取竞价数据
            auction_data = auction_data_map.get(ts_code)
            if not auction_data:
                print(f"   ⚠️ {ts_code} 无竞价数据")
                continue
            
            # 基础数据（所有股票都保存）
            base_data = {
                'ts_code': ts_code,
                'stock_name': t_stock.get('stock_name', ''),
                'sector': t_stock.get('sector', ''),
                't_day_score': t_stock.get('total_score', 0),
                'raw_values': auction_data.copy(),  # 竞价原始数据
                'scores': {},  # 各因子评分
                'market_risk': market_risk,
                'is_filtered': False,
                'filter_reason': None,
                'auction_score': 0,
                'final_score': 0,
                'is_weak_to_strong': False
            }
            
            # 检查是否竞价爆量弱转强
            is_weak_to_strong = self.scoring_model.check_weak_to_strong(
                t_stock, auction_data
            )
            
            if is_weak_to_strong:
                # 弱转强直接给予95分
                base_data['auction_score'] = 95
                base_data['final_score'] = 95
                base_data['is_weak_to_strong'] = True
                # 弱转强时给予满分评分
                base_data['scores'] = {
                    'auction_turnover': 10,
                    'auction_amount': 10,
                    'auction_pct_chg': 10,
                    'auction_volume_ratio': 10,
                    'auction_burst_ratio': 10,
                    'sector_auction_pct': 10,
                    'sector_resonance': 10,
                    't_day_score': 10,
                    'market_risk': 10
                }
                scored_stocks.append(base_data)
                all_stocks_data.append(base_data)
                print(f"   🔥 {ts_code} 竞价爆量弱转强! 自动95分")
                continue
            
            # 正常评分
            result = self.scoring_model.score_auction_stock(
                auction_data,
                t_stock.get('total_score', 50),
                market_risk
            )
            
            if result is None:
                # 被过滤排除，记录原因
                base_data['is_filtered'] = True
                # 根据竞价涨幅判断过滤原因
                pct_chg = auction_data.get('auction_pct_chg', 0)
                if pct_chg < 1:
                    base_data['filter_reason'] = '竞价涨幅<1%'
                else:
                    base_data['filter_reason'] = '评分未通过'
                all_stocks_data.append(base_data)
                continue
            
            # 通过评分的股票
            base_data['auction_score'] = result.get('auction_score', 0)
            base_data['final_score'] = result.get('final_score', 0)
            # 更新 raw_values 为评分模型返回的完整值（包含计算的 sector_resonance 等）
            base_data['raw_values'].update(result.get('raw_values', {}))
            # 保存各因子评分
            base_data['scores'] = result.get('scores', {})
            scored_stocks.append(base_data)
            all_stocks_data.append(base_data)
        
        # 6. 按评分排序
        scored_stocks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 7. 取前N只
        top_stocks = scored_stocks[:top_n]
        
        # 标记选中的股票
        selected_ts_codes = {s['ts_code'] for s in top_stocks}
        for stock in all_stocks_data:
            stock['is_selected'] = stock['ts_code'] in selected_ts_codes
        
        # 8. 生成推荐理由和仓位建议
        for i, stock in enumerate(top_stocks):
            stock['rank'] = i + 1
            stock['reason'] = self._generate_auction_reason(stock)
            stock['suggested_position'] = self._calculate_stock_position(stock, market_risk)
        
        # 9. 保存结果
        self._save_selection_results(top_stocks, date, 't1_auction')

        # 10. 保存所有竞价数据详情 (用于机器学习)
        self._save_auction_data(all_stocks_data, date)

        if len(top_stocks) == 0:
            print(f"\n⚠️ 竞价选股完成，无符合条件的股票（共评估 {len(scored_stocks)} 只）")
        else:
            print(f"\n✅ 竞价选股完成，共选出 {len(top_stocks)} 只股票（评估 {len(scored_stocks)} 只，T日初选 {len(t_day_stocks)} 只，保存 {len(all_stocks_data)} 只完整数据）")
        
        return top_stocks
    
    def _get_t_day_results(self, date: str) -> List[Dict]:
        """从数据库获取T日选股结果"""
        try:
            results = self.session.query(SelectionResult).filter(
                SelectionResult.trade_date == date,
                SelectionResult.selection_type == 't_day'
            ).all()
            
            return [
                {
                    'ts_code': r.ts_code,
                    'stock_name': r.stock_name,
                    'total_score': r.total_score,
                    'sector': r.sector
                }
                for r in results
            ]
        except Exception as e:
            print(f"获取T日结果失败: {e}")
            return []
    
    def _get_market_risk(self, date: str) -> float:
        """获取市场风险评分"""
        try:
            sentiment = self.session.query(MarketSentiment).filter(
                MarketSentiment.trade_date == date
            ).first()
            
            if sentiment:
                return sentiment.risk_score
        except:
            pass
        
        # 获取大盘竞价数据
        try:
            index_data = self.fetcher.get_auction_data('000001.SH', date)
            if index_data:
                # 简单估算风险
                pct_chg = index_data.get('auction_pct_chg', 0)
                if pct_chg > 1:
                    return 3
                elif pct_chg > 0:
                    return 5
                else:
                    return 7
        except:
            pass
        
        return 5  # 默认中等风险
    
    def _generate_auction_reason(self, stock: Dict) -> str:
        """生成竞价推荐理由"""
        reasons = []
        
        if stock.get('is_weak_to_strong'):
            return "竞价爆量弱转强，无视技术指标"
        
        raw = stock.get('raw_values', {})
        
        auction_pct = raw.get('auction_pct_chg', 0)
        if 2 <= auction_pct <= 5:
            reasons.append("竞价涨幅适中")
        
        burst_ratio = raw.get('auction_burst_ratio', 0)
        if burst_ratio > 0.1:
            reasons.append("竞价爆量")
        
        resonance = raw.get('sector_resonance', 0)
        if resonance > 2:
            reasons.append("主动领涨")
        
        t_score = stock.get('t_day_score', 0)
        if t_score > 80:
            reasons.append("T日评分优秀")
        
        if not reasons:
            reasons.append("综合竞价表现良好")
        
        return " + ".join(reasons)
    
    def _calculate_stock_position(self, stock: Dict, market_risk: float) -> float:
        """计算单只股票建议仓位"""
        base = 0.3  # 基础30%
        
        # 根据评分调整
        score = stock.get('final_score', 50)
        if score >= 90:
            base += 0.1
        elif score >= 80:
            base += 0.05
        elif score < 60:
            base -= 0.1
        
        # 根据市场风险调整
        if market_risk > 7:
            base -= 0.15
        elif market_risk > 5:
            base -= 0.05
        
        return max(0.1, min(0.5, base))
    
    def _save_selection_results(self, stocks: List[Dict], date: str, selection_type: str):
        """保存选股结果（自动去重）"""
        try:
            # 先删除该日期和类型的旧记录，避免重复
            self.session.query(SelectionResult).filter(
                SelectionResult.trade_date == date,
                SelectionResult.selection_type == selection_type
            ).delete()
            
            for stock in stocks:
                record = SelectionResult(
                    trade_date=date,
                    selection_type=selection_type,
                    ts_code=stock['ts_code'],
                    stock_name=stock['stock_name'],
                    total_score=stock.get('final_score', 0),
                    final_rank=stock.get('rank', 0),
                    sector=stock.get('sector', ''),
                    reason=stock.get('reason', ''),
                    suggested_position=stock.get('suggested_position', 0.3),
                    auction_price=stock.get('raw_values', {}).get('auction_price'),
                    auction_pct_chg=stock.get('raw_values', {}).get('auction_pct_chg'),
                    sector_linkage_score=stock.get('sector_linkage_score', 0),
                    sector_role_label=stock.get('sector_role_label', '')
                )
                self.session.add(record)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"保存选股结果失败: {e}")

    def _save_auction_data(self, stocks: List[Dict], date: str):
        """保存竞价数据详情（双写：PostgreSQL + SQLite，包含所有股票，用于机器学习）"""
        
        try:
            manager = get_dual_write_manager()
            saved_count = {'postgres': 0, 'sqlite': 0}
            
            for stock in stocks:
                raw = stock.get('raw_values', {})
                scores = stock.get('scores', {})  # 各因子评分

                # 创建记录数据（包含ML所需的所有字段）
                record_data = {
                    'ts_code': stock['ts_code'],
                    'trade_date': date,
                    # 竞价基础数据
                    'auction_price': raw.get('auction_price', 0),
                    'auction_vol': raw.get('auction_vol', 0),
                    'auction_amount': raw.get('auction_amount', 0),
                    'auction_pct_chg': raw.get('auction_pct_chg', 0),
                    'auction_turnover': raw.get('auction_turnover', 0),
                    'auction_volume_ratio': raw.get('auction_volume_ratio', 0),
                    'auction_burst_ratio': raw.get('auction_burst_ratio', 0),
                    # 板块相关
                    'sector_auction_pct': raw.get('sector_auction_pct', 0),
                    'sector_resonance': raw.get('sector_resonance', 0),
                    # 评分数据
                    'auction_score': stock.get('auction_score', 0),
                    'final_score': stock.get('final_score', 0),
                    't_day_score': stock.get('t_day_score', 0),
                    # 特殊情况
                    'is_weak_to_strong': stock.get('is_weak_to_strong', False),
                    # ML训练用字段
                    'is_selected': stock.get('is_selected', False),
                    'is_filtered': stock.get('is_filtered', False),
                    'filter_reason': stock.get('filter_reason'),
                    'market_risk': stock.get('market_risk', 0),
                    # 各因子评分
                    'auction_turnover_score': scores.get('auction_turnover', 0),
                    'auction_turnover_raw': raw.get('auction_turnover', 0),
                    'auction_amount_score': scores.get('auction_amount', 0),
                    'auction_amount_raw': raw.get('auction_amount', 0),
                    'auction_pct_chg_score': scores.get('auction_pct_chg', 0),
                    'auction_pct_chg_raw': raw.get('auction_pct_chg', 0),
                    'auction_volume_ratio_score': scores.get('auction_volume_ratio', 0),
                    'auction_volume_ratio_raw': raw.get('auction_volume_ratio', 0),
                    'auction_burst_ratio_score': scores.get('auction_burst_ratio', 0),
                    'auction_burst_ratio_raw': raw.get('auction_burst_ratio', 0),
                    'sector_auction_pct_score': scores.get('sector_auction_pct', 0),
                    'sector_auction_pct_raw': raw.get('sector_auction_pct', 0),
                    'sector_resonance_score': scores.get('sector_resonance', 0),
                    'sector_resonance_raw': raw.get('sector_resonance', 0),
                    't_day_score_score': scores.get('t_day_score', 0),
                    't_day_score_raw': raw.get('t_day_score', 0)
                }
                
                # 双写
                results = manager.save_auction_data(record_data)
                if results.get('postgres'):
                    saved_count['postgres'] += 1
                if results.get('sqlite'):
                    saved_count['sqlite'] += 1

            selected_count = sum(1 for s in stocks if s.get('is_selected'))
            filtered_count = sum(1 for s in stocks if s.get('is_filtered'))
            print(f"   ✅ 竞价数据已双写保存 (PG: {saved_count['postgres']} 条, SQLite: {saved_count['sqlite']} 条)")
            print(f"      选中 {selected_count} 只，过滤 {filtered_count} 只")
            
        except Exception as e:
            print(f"   ⚠️ 保存竞价数据失败: {e}")


# 便捷函数
def run_t_day_selection(date: str = None) -> Tuple[List[Dict], Dict]:
    """执行T日选股"""
    engine = TDaySelectionEngine()
    return engine.run(date)


def run_t1_auction_selection(date: str = None, t_day_stocks: List[Dict] = None) -> List[Dict]:
    """执行T+1竞价选股"""
    engine = T1AuctionEngine()
    return engine.run(date, t_day_stocks)


if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 测试T日选股
    print("测试 T日选股引擎...")
    stocks, sentiment = run_t_day_selection()
    
    if stocks:
        print("\n选股结果:")
        for s in stocks[:5]:
            print(f"  {s['rank']}. {s['ts_code']} {s['stock_name']} - {s['total_score']}分")
