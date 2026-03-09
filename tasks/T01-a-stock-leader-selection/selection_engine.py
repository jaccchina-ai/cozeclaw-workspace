"""
T01 选股系统 - 主选股引擎

整合所有模块，实现完整的选股流程
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher import DataFetcher, create_fetcher
from scoring_model import ScoringModel, AuctionScoringModel, StockScore, FactorWeights
from database.models import (
    init_db, get_session,
    MarketSentiment, LimitUpStock, StockFactorScore,
    AuctionData, SelectionResult, DailyStockRecord
)

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


class TDaySelectionEngine:
    """T日20:00选股引擎"""
    
    def __init__(self):
        self.fetcher = create_fetcher()
        self.scoring_model = ScoringModel()
        self.session = get_session()
        
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
        
        # 7. 使用 unifuncs 进行舆情分析（选前20只进行分析）
        if UNIFUNCS_AVAILABLE and len(scored_stocks) > 0:
            print("\n🤖 调用 Unifuncs 进行舆情分析...")
            top_for_analysis = scored_stocks[:min(20, len(scored_stocks))]
            unifuncs_scores = self._get_unifuncs_scores(top_for_analysis, date)
            
            # 更新评分结果
            for stock in scored_stocks:
                ts_code = stock['ts_code']
                if ts_code in unifuncs_scores:
                    stock['unifuncs_recommended'] = True
                    stock['sentiment_score'] = unifuncs_scores[ts_code]
                    # 更新总分（舆情分析附加分）
                    stock['total_score'] += unifuncs_scores[ts_code] * 0.6  # 6%权重
        
        # 8. 重新排序（考虑舆情分析附加分后）
        scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 9. 取前N只
        top_stocks = scored_stocks[:top_n]
        
        # 8. 生成推荐理由
        for i, stock in enumerate(top_stocks):
            stock['rank'] = i + 1
            stock['reason'] = self.scoring_model.generate_reason(
                self._dict_to_stock_score(stock)
            )
        
        # 9. 保存结果
        self._save_selection_results(top_stocks, date, 't_day')
        
        # 10. 更新 SESSION-STATE
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
        """对所有股票进行评分"""
        results = []
        all_amounts = stocks_df['amount'].tolist() if 'amount' in stocks_df.columns else []
        
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
                
                # 获取龙虎榜数据
                dragon_tiger = self.fetcher.get_dragon_tiger_list(ts_code, date)
                
                # 获取资金流向数据
                moneyflow = self.fetcher.get_stock_moneyflow(ts_code, date)
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
                
                # 获取板块数据
                sector = self.fetcher.get_sector_data(ts_code, date)
                sector_data = {
                    'name': stock_data.get('industry', ''),
                    'zt_count': 0,  # 需要额外计算
                    'pct_chg': 0,
                    'main_inflow': 0
                }
                
                # 计算MA3乖离率
                bias_ma3 = self.fetcher.calculate_bias_ma3(ts_code, date)
                stock_data['bias_ma3'] = bias_ma3
                
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
                    'sentiment_score': score.sentiment_score
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"   ⚠️ 评分失败 {stock_data.get('ts_code', 'unknown')}: {e}")
                continue
        
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
            total_score=data.get('total_score', 0),
            sector=data.get('sector', ''),
            unifuncs_recommended=data.get('unifuncs_recommended', False)
        )
    
    def _get_unifuncs_scores(self, stocks: List[Dict], date: str) -> Dict[str, float]:
        """
        调用 Unifuncs 进行涨停股舆情分析
        
        Args:
            stocks: 股票列表
            date: 日期
            
        Returns:
            {ts_code: 涨停概率分数(0-10)}
        """
        scores = {}
        
        try:
            client = UnifuncsClient()
            
            # 构建提示词
            stock_list = "\n".join([
                f"- {s['ts_code']} {s['stock_name']} (得分: {s['total_score']:.1f})"
                for s in stocks[:10]  # 只分析前10只
            ])
            
            prompt = f"""今天是{date}，以下是今日涨停股票中评分最高的10只：

{stock_list}

请分析这些股票，预测哪3只股票在下一个交易日继续涨停的概率最大。
对于每只股票，请给出一个0-100的涨停概率分数，分数越高表示概率越大。

请以JSON格式返回结果，格式如下：
{{"股票代码": 概率分数, ...}}

例如：{{"000001.SZ": 85, "000002.SZ": 72, ...}}
"""
            
            # 创建任务 - 使用 messages 传递提示词
            messages = [{"role": "user", "content": prompt}]
            task_id = client.create_task(output_prompt="请分析这些涨停股票，预测明日继续涨停的概率", messages=messages)
            print(f"   任务ID: {task_id}")
            
            # 等待结果
            import time
            max_wait = 180  # 最多等待180秒（Deep Research需要较长时间）
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                result = client.query_task(task_id)
                print(f"   状态: {result.status} (已等待 {time.time() - start_time:.0f}秒)")
                
                if result.status == "completed":
                    # 解析结果
                    answer = result.answer or result.summary or ""
                    print(f"   Unifuncs 分析完成，答案长度: {len(answer)}")
                    
                    # 尝试从回答中提取JSON
                    import re
                    json_match = re.search(r'\{[^}]+\}', answer)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            for code, score in data.items():
                                # 将0-100映射到0-10
                                scores[code] = min(10, max(0, float(score) / 10))
                        except:
                            pass
                    
                    # 如果没有解析到JSON，手动查找提及的股票
                    if not scores:
                        for s in stocks[:10]:
                            ts_code = s['ts_code']
                            stock_name = s['stock_name']
                            if ts_code in answer or stock_name in answer:
                                scores[ts_code] = 8  # 被提及的股票给予8分
                    
                    break
                    
                elif result.status == "failed":
                    print(f"   Unifuncs 任务失败: {result.error}")
                    break
                    
                time.sleep(3)  # 等待3秒后重试
                
        except Exception as e:
            print(f"   Unifuncs 调用失败: {e}")
        
        return scores
    
    def _save_sentiment(self, sentiment: Dict):
        """保存市场情绪数据"""
        try:
            record = MarketSentiment(**sentiment)
            self.session.add(record)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"保存情绪数据失败: {e}")
    
    def _save_selection_results(self, stocks: List[Dict], date: str, selection_type: str):
        """保存选股结果"""
        try:
            for stock in stocks:
                record = SelectionResult(
                    trade_date=date,
                    selection_type=selection_type,
                    ts_code=stock['ts_code'],
                    stock_name=stock['stock_name'],
                    total_score=stock['total_score'],
                    final_rank=stock.get('rank', 0),
                    sector=stock.get('sector', ''),
                    reason=stock.get('reason', ''),
                    unifuncs_recommended=stock.get('unifuncs_recommended', False)
                )
                self.session.add(record)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"保存选股结果失败: {e}")
    
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
            t_day_stocks = self._get_t_day_results(t_day)
        
        if not t_day_stocks:
            print("❌ 无T日选股结果")
            return []
        
        print(f"   T日初选股票数: {len(t_day_stocks)}")
        
        # 3. 获取市场风险
        market_risk = self._get_market_risk(date)
        
        # 4. 对每只股票获取竞价数据并评分
        print("\n📊 获取竞价数据并评分...")
        scored_stocks = []
        
        for t_stock in t_day_stocks:
            ts_code = t_stock['ts_code']
            
            # 获取竞价数据
            auction_data = self.fetcher.get_auction_data(ts_code, date)
            if not auction_data:
                continue
            
            # 检查是否竞价爆量弱转强
            is_weak_to_strong = self.scoring_model.check_weak_to_strong(
                t_stock, auction_data
            )
            
            if is_weak_to_strong:
                # 弱转强直接给予95分
                result = {
                    'ts_code': ts_code,
                    'stock_name': t_stock.get('stock_name', ''),
                    'auction_score': 95,
                    'final_score': 95,
                    'is_weak_to_strong': True,
                    'rank': 0,
                    'raw_values': auction_data
                }
                scored_stocks.append(result)
                print(f"   🔥 {ts_code} 竞价爆量弱转强! 自动95分")
                continue
            
            # 正常评分
            result = self.scoring_model.score_auction_stock(
                auction_data,
                t_stock.get('total_score', 50),
                market_risk
            )
            
            if result is None:
                continue
            
            result['ts_code'] = ts_code
            result['stock_name'] = t_stock.get('stock_name', '')
            result['sector'] = t_stock.get('sector', '')
            result['t_day_score'] = t_stock.get('total_score', 0)
            
            scored_stocks.append(result)
        
        # 5. 按评分排序
        scored_stocks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 6. 取前N只
        top_stocks = scored_stocks[:top_n]
        
        # 7. 生成推荐理由和仓位建议
        for i, stock in enumerate(top_stocks):
            stock['rank'] = i + 1
            stock['reason'] = self._generate_auction_reason(stock)
            stock['suggested_position'] = self._calculate_stock_position(stock, market_risk)
        
        # 8. 保存结果
        self._save_selection_results(top_stocks, date, 't1_auction')
        
        print(f"\n✅ 竞价选股完成，共选出 {len(top_stocks)} 只股票")
        
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
        """保存选股结果"""
        try:
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
                    auction_pct_chg=stock.get('raw_values', {}).get('auction_pct_chg')
                )
                self.session.add(record)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"保存选股结果失败: {e}")


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
