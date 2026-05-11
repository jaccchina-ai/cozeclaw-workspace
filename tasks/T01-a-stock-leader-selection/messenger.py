"""
T01 选股系统 - 消息推送模块

飞书消息推送和格式化
"""

import os
import json
import requests
import subprocess
from datetime import datetime
from typing import List, Dict, Optional


class FeishuMessenger:
    """飞书消息推送"""
    
    def __init__(self, webhook_url: str = None):
        """
        初始化飞书消息推送
        
        Args:
            webhook_url: 飞书机器人 Webhook URL
        """
        self.webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL', '')
    
    @staticmethod
    def _fmt(value, decimals: int = 2) -> str:
        """
        格式化数值，保留指定小数位
        
        Args:
            value: 要格式化的值
            decimals: 小数位数，默认2位
            
        Returns:
            格式化后的字符串
        """
        if value is None or value == '-':
            return '-'
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
        
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, date: str = None, win_rate: float = None, hot_sectors: List[str] = None) -> bool:
        """
        发送T日选股结果
        
        Args:
            stocks: 选股结果列表
            sentiment: 市场情绪数据
            date: 日期
            win_rate: 策略胜率（动态计算）
            hot_sectors: Unifuncs 推荐的热点板块
            
        Returns:
            是否发送成功
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        message = self._format_t_day_message(stocks, sentiment, date, win_rate, hot_sectors)
        return self._send_message(message)
    
    def send_t1_auction_result(self, stocks: List[Dict], sentiment: Dict, 
                               date: str = None, market_risk: float = 0) -> bool:
        """
        发送T+1竞价选股结果
        
        Args:
            stocks: 选股结果列表
            sentiment: 市场情绪数据
            date: 日期
            market_risk: 市场风险评分
            
        Returns:
            是否发送成功
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

        message = self._format_t1_auction_message(stocks, sentiment, date, market_risk)
        return self._send_message(message)

    def send_track_result(self, tracked_stocks: List[Dict], win_rate: float,
                          avg_return: float, t1_day: str, t2_day: str) -> bool:
        """
        发送T+1竞价选股跟踪结果

        Args:
            tracked_stocks: 跟踪股票列表
            win_rate: 胜率
            avg_return: 平均收益率
            t1_day: T+1日日期
            t2_day: T+2日日期

        Returns:
            是否发送成功
        """
        date = f"{t2_day[:4]}-{t2_day[4:6]}-{t2_day[6:]}"
        message = self._format_track_message(tracked_stocks, win_rate, avg_return, t1_day, t2_day, date)
        return self._send_message(message)

    def _format_track_message(self, tracked_stocks: List[Dict], win_rate: float,
                              avg_return: float, t1_day: str, t2_day: str, date: str) -> Dict:
        """格式化跟踪结果消息"""

        # 构建股票卡片
        stock_cards = []
        for stock in tracked_stocks:
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣'][stock['rank']-1] if stock['rank'] <= 3 else f"{stock['rank']}."
            win_color = "green" if stock['is_win'] else "red"
            win_mark = "✅ 盈利" if stock['is_win'] else "❌ 亏损"

            # 构建卖出历史描述
            sell_history = stock.get('sell_history', [])
            sell_desc = []
            if sell_history:
                for i, sell in enumerate(sell_history, 1):
                    sell_date = sell['date']
                    sell_price = sell['price']
                    sell_ratio = sell['ratio'] * 100
                    sell_profit = sell['profit']
                    limit_mark = "✅ 涨停" if sell['is_limit_up'] else "❌ 未涨停"
                    sell_desc.append(f"📅 {sell_date}: 卖出{sell_ratio:.0f}% @ {sell_price:.2f}, 盈利{sell_profit:.2f}元/股 {limit_mark}")
            else:
                sell_desc.append("📅 未卖出，继续持有")

            sell_text = "\n" + "\n".join(sell_desc) if sell_desc else ""

            card = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{rank_emoji} {stock['ts_code']} {stock['stock_name']}**\n{win_mark}\n剩余仓位: {stock['shares_held']*100:.0f}%"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"买入价: {stock['t1_open']:.2f}\n总收益: **{stock['return_pct']:+.2f}%**\n总盈利: {stock['final_profit']:.2f}元/股"
                        }
                    }
                ]
            }
            stock_cards.append(card)
            
            # 添加卖出历史卡片
            if sell_history:
                history_card = {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**🔍 交易历史**:\n{sell_text}"
                    }
                }
                stock_cards.append(history_card)
                stock_cards.append({"tag": "hr"})

        # 胜率颜色
        win_rate_color = "green" if win_rate >= 60 else "orange" if win_rate >= 40 else "red"

        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"T01龙头战法 - {date} T+1竞价选股跟踪报告"
                    },
                    "template": win_rate_color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**统计周期**: {t1_day} (买入) → {t2_day} (卖出)"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【胜率】**\n大于3%: **{win_rate:.1f}%**"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【平均收益】**\n{avg_return:+.2f}%"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【个股明细】**"
                        }
                    },
                    *stock_cards,
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "⚠️ 统计说明: 基于T+1开盘价买入，T+2收盘价卖出。仅供参考，不构成投资建议。"
                            }
                        ]
                    }
                ]
            }
        }

        return message

    def _format_t_day_message(self, stocks: List[Dict], sentiment: Dict, date: str, win_rate: float = None, hot_sectors: List[str] = None) -> Dict:
        """格式化T日选股消息"""
        
        # 市场情绪部分
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        fb_ratio = sentiment.get('fb_ratio', 0)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        suggested_position = sentiment.get('suggested_position', 0.5)
        risk_score = sentiment.get('risk_score', 5)
        
        # 热点板块
        hot_sectors_text = "、".join(hot_sectors) if hot_sectors else "暂无"
        
        # 动态胜率显示逻辑
        # win_rate < 0: 数据不足
        # win_rate is None: 使用默认值60%
        # win_rate >= 0: 显示实际胜率
        if win_rate is None:
            win_rate_text = "60.0% (默认)"
        elif win_rate < 0:
            win_rate_text = "数据不足 (需至少10次回测)"
        else:
            win_rate_text = f"{win_rate*100:.1f}%"
        
        # 风险描述
        risk_desc = self._get_risk_description(risk_score)
        
        # 股票列表部分 - 强制显示角色标签
        stock_cards = []
        role_emoji = {
            '板块龙头': '👑',
            '前排跟随': '🥈',
            '后排跟风': '🥉',
            '独立强势': '🌟'
        }
        for i, stock in enumerate(stocks):
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][i]
            
            # 强制显示角色标签
            role_label = stock.get('sector_role_label', '独立强势')
            role_icon = role_emoji.get(role_label, '🔹')
            role_mark = f" **【{role_icon}{role_label}】**"
            
            raw = stock.get('raw_values', {})
            
            # Unifuncs推荐醒目标记
            if stock.get('unifuncs_recommended'):
                unifuncs_mark = ' 🔴【Unifuncs顶级推荐】'
                # 在股票名称前添加醒目标记
                stock_display = f"{rank_emoji} 🔴**{stock['ts_code']} {stock['stock_name']}**"
            else:
                unifuncs_mark = ''
                stock_display = f"{rank_emoji} **{stock['ts_code']} {stock['stock_name']}**"
            
            card = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"{stock_display}{role_mark}{unifuncs_mark}\n得分: {stock['total_score']} | {stock.get('sector', '-')}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"推荐理由: {stock.get('reason', '-')}"
                        }
                    }
                ]
            }
            stock_cards.append(card)
        
        # 因子详情部分 - 展示所有指标数值供审核
        factor_cards = []
        rank_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        for i, stock in enumerate(stocks):
            rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
            raw = stock.get('raw_values', {})
            
            # 强制显示角色标签
            role_label = stock.get('sector_role_label', '独立强势')
            role_icon = role_emoji.get(role_label, '🔹')
            role_mark = f"【{role_icon}{role_label}】"
            
            # mx_search 增强信息
            limit_reason = stock.get('limit_reason', '')
            risk_alert = stock.get('risk_alert', False)
            risk_type = stock.get('risk_type', '')
            risk_details = stock.get('risk_details', '')
            
            # 构建风险提示
            risk_mark = ''
            if risk_alert:
                risk_mark = f"\n⚠️ **风险提醒**: {risk_type}\n   {risk_details[:100]}..."
            
            # 构建涨停原因
            limit_reason_text = ''
            if limit_reason:
                limit_reason_text = f"\n📰 **涨停原因**: {limit_reason[:150]}..."
            
            # 构建Unifuncs推荐详情
            unifuncs_detail_text = ''
            if stock.get('unifuncs_recommended'):
                match_score = stock.get('unifuncs_match_score', 0)
                unifuncs_reason = stock.get('unifuncs_reason', '')
                unifuncs_detail_text = f"\n🔴 **【Unifuncs顶级推荐】** 匹配度: {match_score*100:.0f}%"
                if unifuncs_reason:
                    unifuncs_detail_text += f"\n   推荐理由: {unifuncs_reason[:80]}..."
            
            # 详细展示每个因子的原始数值和得分（使用_fmt格式化，保留2位小数）
            factor_text = f"""**{rank_emoji} {stock['ts_code']} {stock['stock_name']}** {role_mark}
**总分**: {self._fmt(stock['total_score'])} | **行业**: {stock.get('sector', '-')}{limit_reason_text}{risk_mark}{unifuncs_detail_text}

**【原始指标数值】**
1️⃣ 涨停质量: 首次涨停={raw.get('first_limit_time', '-')}, 炸板次数={raw.get('limit_times', '-')}, 连板数={raw.get('consecutive_limit', '-')}
2️⃣ 封成比: {self._fmt(raw.get('seal_ratio'))} → 得分={self._fmt(stock.get('seal_ratio_score'))}
3️⃣ 封流比: {self._fmt(raw.get('seal_flow_ratio'))} → 得分={self._fmt(stock.get('seal_flow_ratio_score'))}
4️⃣ 量比: {self._fmt(raw.get('volume_ratio'))} → 得分={self._fmt(stock.get('volume_ratio_score'))}
5️⃣ 真实换手率: {self._fmt(raw.get('real_turnover_rate'))}% → 得分={self._fmt(stock.get('turnover_rate_score'))}
6️⃣ 龙虎榜净买入: {raw.get('net_buy', 0):.0f}万 → 得分={self._fmt(stock.get('dragon_tiger_score'))}
7️⃣ 主力净占比: {self._fmt(raw.get('main_net_ratio'))}% → 得分={self._fmt(stock.get('money_flow_score'))}
8️⃣ 成交额排名: 第{raw.get('amount_rank', '-')}名 → 得分={self._fmt(stock.get('amount_rank_score'))}
9️⃣ 板块热度: 板块涨停{raw.get('sector_zt_count', '-')}只 → 得分={self._fmt(stock.get('sector_heat_score'))}
🔟 Bias MA3: {self._fmt(raw.get('bias_ma3'))}% → 得分={self._fmt(stock.get('bias_ma3_score'))}
1️⃣1️⃣ 舆情分析: {self._fmt(stock.get('sentiment_score'))}分

**【评分明细】**
涨停质量:{self._fmt(stock.get('limit_quality_score'))} | 封成比:{self._fmt(stock.get('seal_ratio_score'))} | 封流比:{self._fmt(stock.get('seal_flow_ratio_score'))} | 量比:{self._fmt(stock.get('volume_ratio_score'))} | 换手:{self._fmt(stock.get('turnover_rate_score'))} | 龙虎榜:{self._fmt(stock.get('dragon_tiger_score'))} | 资金流:{self._fmt(stock.get('money_flow_score'))} | 成交额:{self._fmt(stock.get('amount_rank_score'))} | 板块:{self._fmt(stock.get('sector_heat_score'))} | Bias:{self._fmt(stock.get('bias_ma3_score'))} | 舆情:{self._fmt(stock.get('sentiment_score'))}"""
            
            factor_cards.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": factor_text
                }
            })
        
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"T01龙头战法 - {date} 晚间初选结果"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【市场情绪】**\n{sentiment_stage}，涨停{zt_num}家，跌停{dt_num}家"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【建议仓位】**\n{suggested_position*100:.0f}%"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**【宏观风险】**\n评分: {risk_score}/10 - {risk_desc}"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**【热点板块】** {hot_sectors_text}（AI推荐）"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**【策略胜率】** {win_rate_text}"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【明日观察标的】**（按优先级排序）"
                        }
                    },
                    *stock_cards,
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【个股评分因子详情】**"
                        }
                    },
                    *factor_cards,
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "⚠️ 以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
                            }
                        ]
                    }
                ]
            }
        }
        
        return message
    
    def _format_t1_auction_message(self, stocks: List[Dict], sentiment: Dict, 
                                   date: str, market_risk: float) -> Dict:
        """格式化T+1竞价选股消息"""
        
        # 风险描述
        risk_desc = self._get_risk_description(market_risk)
        
        # 是否建议交易
        should_trade = market_risk < 7
        
        # 股票列表部分
        stock_cards = []
        for i, stock in enumerate(stocks):
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣'][i] if i < 3 else f'{i+1}.'
            
            raw = stock.get('raw_values', {})
            is_wts = stock.get('is_weak_to_strong', False)
            wts_mark = ' 🔥【弱转强】' if is_wts else ''
            
            # Unifuncs推荐醒目标记
            if stock.get('unifuncs_recommended'):
                unifuncs_mark = ' 🔴【Unifuncs顶级推荐】'
                # 在股票名称前添加醒目标记
                stock_display = f"{rank_emoji} 🔴**{stock['ts_code']} {stock['stock_name']}**"
            else:
                unifuncs_mark = ''
                stock_display = f"{rank_emoji} **{stock['ts_code']} {stock['stock_name']}**"
            
            card = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"{stock_display}{unifuncs_mark}{wts_mark}\n得分: {stock.get('final_score', 0)} | {stock.get('sector', '-')}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"竞价涨幅: {raw.get('auction_pct_chg', 0):.2f}%\n建议仓位: {stock.get('suggested_position', 0.3)*100:.0f}%"
                        }
                    }
                ]
            }
            stock_cards.append(card)
        
        # 因子详情部分 - 展示所有竞价指标数值供审核
        factor_cards = []
        for i, stock in enumerate(stocks):
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣'][i] if i < 3 else f'{i+1}.'
            raw = stock.get('raw_values', {})
            
            # 详细展示每个竞价因子的原始数值和得分
            factor_text = f"""**{rank_emoji} {stock['ts_code']} {stock['stock_name']}**
**综合得分**: {stock.get('final_score', 0)} | **T日得分**: {stock.get('t_day_score', 0)} | **行业**: {stock.get('sector', '-')}

**【竞价原始指标数值】**
1️⃣ 竞价价格: {raw.get('auction_price', '-')}元
2️⃣ 竞价涨幅: {raw.get('auction_pct_chg', 0):.2f}% → 得分:{stock.get('auction_score', '-')}
3️⃣ 竞价成交量: {raw.get('auction_vol', 0)/10000:.0f}万手
4️⃣ 竞价金额: {raw.get('auction_amount', 0):.0f}万元
5️⃣ 竞价换手率: {raw.get('auction_turnover', 0):.4f}%
6️⃣ 竞价量比: {raw.get('auction_volume_ratio', '-'):.2f}
7️⃣ 竞价爆量比: {raw.get('auction_burst_ratio', '-'):.4f}
8️⃣ 昨日收盘价: {raw.get('pre_close', '-')}元
9️⃣ 流通股本: {raw.get('float_share', 0):.0f}万股
🔟 板块竞价涨幅: {raw.get('sector_auction_pct', '-'):.2f}%
1️⃣1️⃣ 板块共振度: {raw.get('sector_resonance', '-'):.2f}
1️⃣2️⃣ 是否弱转强: {'✅是' if stock.get('is_weak_to_strong') else '❌否'}

**【竞价评分明细】**
竞价涨幅:{stock.get('auction_score', '-')} | T日基础:{stock.get('t_day_score', '-')} | 板块:{stock.get('sector_score', '-')} | 风险调整:{stock.get('risk_adjustment', '-')} | 最终:{stock.get('final_score', '-')}

**【操作建议】**
建议仓位: {stock.get('suggested_position', 0.3)*100:.0f}% | 推荐理由: {stock.get('reason', '-')}***"""
            
            factor_cards.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": factor_text
                }
            })
        
        # 风险提示
        risk_warning = ""
        if not should_trade:
            risk_warning = "\n\n⚠️ **风险提示：当前市场风险较高，建议谨慎操作或观望！**"
        
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"T01龙头战法 - {date} 竞价精选股票"
                    },
                    "template": "red" if market_risk > 6 else "green"
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【市场风险】**\n评分: {market_risk}/10 - {risk_desc}{risk_warning}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**【建议仓位】**\n{sentiment.get('suggested_position', 0.5)*100:.0f}%"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【策略胜率】** 60%"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【精选标的】**（按优先级排序）"
                        }
                    },
                    *stock_cards,
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**【竞价因子详情】**"
                        }
                    },
                    *factor_cards,
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "⚠️ 以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
                            }
                        ]
                    }
                ]
            }
        }
        
        return message
    
    def _get_risk_description(self, risk_score: float) -> str:
        """获取风险描述"""
        if risk_score >= 8:
            return "高风险，建议观望"
        elif risk_score >= 6:
            return "风险偏高，谨慎操作"
        elif risk_score >= 4:
            return "风险适中"
        else:
            return "风险较低"
    
    def _send_message(self, message: Dict) -> bool:
        """发送飞书消息"""
        if not self.webhook_url:
            print("⚠️ 未配置飞书 Webhook URL，跳过消息发送")
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print("✅ 飞书消息发送成功")
                    return True
                else:
                    print(f"❌ 飞书消息发送失败: {result}")
                    return False
            else:
                print(f"❌ 飞书消息发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 飞书消息发送异常: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """发送简单文本消息"""
        message = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        return self._send_message(message)


class FeishuApiMessenger:
    """通过飞书开放平台API发送消息（支持富文本和交互式卡片）"""
    
    def __init__(self, app_id: str = None, app_secret: str = None, target: str = None):
        """
        初始化飞书API消息推送
        
        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
            target: 目标用户 open_id
        """
        self.app_id = app_id or os.environ.get('FEISHU_APP_ID', 'cli_a92ff54e1db89cd3')
        self.app_secret = app_secret or os.environ.get('FEISHU_APP_SECRET', 'EhmusafOBTT8EnDs1g4cXf1zpwZs0P5Z')
        self.target = target or os.environ.get('FEISHU_TARGET', 'ou_cf1fa11596236b5fb32fa3f4efec8d2a')
        self._token = None
        self._token_expire = 0
    
    def _get_token(self) -> str:
        """获取 tenant_access_token"""
        import time
        
        # 检查缓存
        if self._token and time.time() < self._token_expire:
            return self._token
        
        try:
            response = requests.post(
                'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                json={'app_id': self.app_id, 'app_secret': self.app_secret},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            result = response.json()
            if result.get('code') == 0:
                self._token = result['tenant_access_token']
                self._token_expire = time.time() + result.get('expire', 3600) - 300  # 提前5分钟过期
                return self._token
            else:
                print(f"❌ 获取飞书Token失败: {result}")
                return None
        except Exception as e:
            print(f"❌ 获取飞书Token异常: {e}")
            return None
    
    def _send_api_message(self, msg_type: str, content: dict, target: str = None) -> bool:
        """
        通过飞书API发送消息
        
        Args:
            msg_type: 消息类型 (text/post/interactive)
            content: 消息内容
            target: 目标用户ID
            
        Returns:
            是否发送成功
        """
        token = self._get_token()
        if not token:
            return False
        
        target = target or self.target
        
        try:
            response = requests.post(
                'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                json={
                    'receive_id': target,
                    'msg_type': msg_type,
                    'content': json.dumps(content, ensure_ascii=False)
                },
                timeout=15
            )
            
            result = response.json()
            if result.get('code') == 0:
                print(f"✅ 飞书API消息发送成功 ({msg_type})")
                return True
            else:
                print(f"❌ 飞书API消息发送失败: {result.get('msg', result)}")
                return False
        except Exception as e:
            print(f"❌ 飞书API消息发送异常: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """发送纯文本消息"""
        return self._send_api_message('text', {'text': text})
    
    def send_post(self, title: str, content: list) -> bool:
        """
        发送富文本消息
        
        Args:
            title: 标题
            content: 内容列表，格式见飞书文档
        """
        return self._send_api_message('post', {
            'zh_cn': {'title': title, 'content': content}
        })
    
    def send_card(self, title: str, elements: list, template: str = 'blue') -> bool:
        """
        发送交互式卡片消息
        
        Args:
            title: 卡片标题
            elements: 卡片元素列表
            template: 标题颜色 (blue/green/red/orange等)
        """
        card = {
            'config': {'wide_screen_mode': True},
            'header': {
                'template': template,
                'title': {'tag': 'plain_text', 'content': title}
            },
            'elements': elements
        }
        return self._send_api_message('interactive', card)
    
    def _build_stock_table(self, stocks: List[Dict], max_rows: int = 10) -> str:
        """构建股票表格的Markdown文本"""
        headers = "| 排名 | 股票 | 评分 | 标签 | 行业 | 连板 | 换手率 |"
        separator = "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
        rows = []
        
        for i, stock in enumerate(stocks[:max_rows], 1):
            name = stock.get('stock_name', stock.get('name', ''))[:4]
            score = stock.get('total_score', 0)
            tag = stock.get('sector_role', '跟随')
            tag_icon = {'板块龙头': '👑', '前排跟随': '🥈', '独立强势': '🌟'}.get(tag, '📈')
            sector = stock.get('sector', '')[:4]
            limit_days = stock.get('raw_values', {}).get('limit_days', 1)
            turnover = stock.get('raw_values', {}).get('real_turnover_rate', 0)
            
            rows.append(f"| {i} | {name} | {score:.1f} | {tag_icon}{tag[:2]} | {sector} | {limit_days}板 | {turnover:.1f}% |")
        
        return f"{headers}\n{separator}\n" + "\n".join(rows)
    
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, 
                          date: str = None, win_rate: float = None, 
                          hot_sectors: List[str] = None) -> bool:
        """发送T日选股结果（交互式卡片）"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 市场情绪
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        suggested_position = sentiment.get('suggested_position', 0.5) * 100
        risk_score = sentiment.get('risk_score', 5)
        
        # 构建卡片元素
        elements = [
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**市场情绪**: {sentiment_stage}，涨停{zt_num}家，跌停{dt_num}家\n**建议仓位**: {suggested_position:.0f}% | **宏观风险**: {risk_score}/10"
                }
            },
            {'tag': 'hr'}
        ]
        
        # 添加表格
        if stocks:
            table_md = self._build_stock_table(stocks)
            elements.append({
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': table_md}
            })
        
        # 底部备注
        elements.extend([
            {'tag': 'hr'},
            {
                'tag': 'note',
                'elements': [
                    {'tag': 'plain_text', 'content': f'⚠️ 仅供参考，不构成投资建议 | {date}'}
                ]
            }
        ])
        
        return self.send_card(f"📊 T01晚间选股结果 - {date}", elements, 'blue')
    
    def send_t1_auction_result(self, stocks: List[Dict], sentiment: Dict,
                               date: str = None, market_risk: float = 0) -> bool:
        """发送T+1竞价选股结果（交互式卡片）"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 市场情绪
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        
        elements = [
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**竞价时间**: {date} 09:25\n**市场情绪**: 涨停{zt_num}家，跌停{dt_num}家\n**风险评分**: {market_risk}/10"
                }
            },
            {'tag': 'hr'}
        ]
        
        if stocks:
            table_md = self._build_stock_table(stocks, max_rows=5)
            elements.append({
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': table_md}
            })
        else:
            elements.append({
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': '今日竞价阶段无符合条件股票'}
            })
        
        elements.extend([
            {'tag': 'hr'},
            {
                'tag': 'note',
                'elements': [
                    {'tag': 'plain_text', 'content': f'⚠️ 竞价结果仅供参考 | {date} 09:26'}
                ]
            }
        ])
        
        return self.send_card(f"📊 T+1竞价选股结果 - {date}", elements, 'green')
    
    def send_track_result(self, tracked_stocks: List[Dict], win_rate: float,
                          avg_return: float, t1_day: str, t2_day: str) -> bool:
        """发送T+1竞价选股跟踪结果"""
        # 构建详细的跟踪报告内容
        elements = [
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**统计周期**: {t1_day} (买入) → 多日跟踪\n**胜率**: {win_rate:.1f}% (总收益为正)\n**平均收益**: {avg_return:+.2f}%"
                }
            },
            {'tag': 'hr'}
        ]
        
        for stock in tracked_stocks:
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣'][stock['rank']-1] if stock['rank'] <= 3 else f"{stock['rank']}."
            win_mark = "✅" if stock['is_win'] else "❌"
            
            # 股票基本信息
            stock_info = {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"{rank_emoji} **{stock['ts_code']} {stock['stock_name']}**\n**买入价**: {stock['t1_open']:.2f} | **总收益**: {stock['return_pct']:+.2f}% | **总盈利**: {stock['final_profit']:.2f}元/股\n**剩余仓位**: {stock['shares_held']*100:.0f}% | **跟踪天数**: {stock['days_tracked']}天"
                }
            }
            elements.append(stock_info)
            
            # 卖出历史
            sell_history = stock.get('sell_history', [])
            if sell_history:
                sell_desc = []
                for i, sell in enumerate(sell_history, 1):
                    sell_date = sell['date']
                    sell_price = sell['price']
                    sell_ratio = sell['ratio'] * 100
                    sell_profit = sell['profit']
                    limit_mark = "✅ 涨停" if sell['is_limit_up'] else "❌ 未涨停"
                    sell_desc.append(f"{i}. 📅 {sell_date}: 卖出{sell_ratio:.0f}% @ {sell_price:.2f}, 盈利{sell_profit:.2f}元/股 {limit_mark}")
                
                sell_text = "\n" + "\n".join(sell_desc)
                sell_card = {
                    'tag': 'div',
                    'text': {
                        'tag': 'lark_md',
                        'content': f"**🔍 交易历史**:{sell_text}"
                    }
                }
                elements.append(sell_card)
            else:
                hold_card = {
                    'tag': 'div',
                    'text': {
                        'tag': 'lark_md',
                        'content': "**🔍 交易历史**: 未卖出，继续持有"
                    }
                }
                elements.append(hold_card)
            
            elements.append({'tag': 'hr'})
        
        # 底部备注
        elements.append({
            'tag': 'note',
            'elements': [
                {'tag': 'plain_text', 'content': f'⚠️ 策略规则: T+2日涨停卖一半，否则全卖；后续交易日涨停继续持有，否则卖出剩余仓位 | {t2_day}'}
            ]
        })
        
        return self.send_card(f"📊 T+1竞价跟踪报告 - {t2_day}", elements, 'orange')


class OpenClawChannelMessenger:
    """通过 OpenClaw Channel 发送消息（使用 openclaw message send 命令）"""
    
    def __init__(self, channel: str = 'feishu', target: str = None):
        """
        初始化 OpenClaw Channel 消息推送
        
        Args:
            channel: 渠道名称，默认 feishu
            target: 目标用户/群 ID
        """
        self.channel = channel
        self.target = target or os.environ.get('OPENCLAW_FEISHU_TARGET', 'ou_cf1fa11596236b5fb32fa3f4efec8d2a')
    
    def _send_via_openclaw(self, message: str) -> bool:
        """
        通过 openclaw message send 命令发送消息
        
        Args:
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        try:
            # 限制单条消息长度（飞书限制约 30KB）
            if len(message) > 28000:
                # 分段发送
                chunks = self._split_message(message, 28000)
                success = True
                for i, chunk in enumerate(chunks):
                    if not self._send_single(chunk):
                        success = False
                    if i < len(chunks) - 1:
                        import time
                        time.sleep(0.5)  # 避免发送过快
                return success
            else:
                return self._send_single(message)
        except Exception as e:
            print(f"❌ OpenClaw Channel 发送失败: {e}")
            return False
    
    def _send_single(self, message: str) -> bool:
        """发送单条消息"""
        try:
            result = subprocess.run(
                [
                    'openclaw', '--log-level', 'error', 
                    'message', 'send',
                    '--channel', self.channel,
                    '--target', self.target,
                    '--message', message
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"✅ 已通过 OpenClaw {self.channel} 渠道发送消息")
                return True
            else:
                print(f"❌ 发送失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ 发送超时")
            return False
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False
    
    def _split_message(self, message: str, max_length: int) -> List[str]:
        """按自然段落分割长消息"""
        paragraphs = message.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_length:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, 
                          date: str = None, win_rate: float = None, 
                          hot_sectors: List[str] = None) -> bool:
        """发送T日选股结果"""
        # 复用 FeishuMessenger 的格式化逻辑，但通过 OpenClaw 发送
        formatter = FeishuMessenger()
        message = formatter._format_t_day_message(stocks, sentiment, date, win_rate, hot_sectors)
        return self._send_via_openclaw(message)
    
    def send_t1_auction_result(self, stocks: List[Dict], sentiment: Dict,
                               date: str = None, market_risk: float = 0) -> bool:
        """发送T+1竞价选股结果"""
        formatter = FeishuMessenger()
        message = formatter._format_t1_auction_message(stocks, sentiment, date, market_risk)
        return self._send_via_openclaw(message)
    
    def send_track_result(self, tracked_stocks: List[Dict], win_rate: float,
                          avg_return: float, t1_day: str, t2_day: str) -> bool:
        """发送T+1竞价选股跟踪结果"""
        formatter = FeishuMessenger()
        message = formatter._format_track_message(tracked_stocks, win_rate, avg_return, t1_day, t2_day)
        return self._send_via_openclaw(message)
    
    def send_text(self, text: str) -> bool:
        """发送简单文本消息"""
        return self._send_via_openclaw(text)


class FileMessenger:
    """文件消息推送（将消息保存到文件，供OpenClaw读取发送）"""
    
    def __init__(self, message_dir: str = None):
        """
        初始化文件消息推送
        
        Args:
            message_dir: 消息文件保存目录
        """
        self.message_dir = message_dir or '/workspace/projects/workspace/logs/messages'
        os.makedirs(self.message_dir, exist_ok=True)
    
    @staticmethod
    def _fmt(value, decimals: int = 2) -> str:
        """
        格式化数值，保留指定小数位
        
        Args:
            value: 要格式化的值
            decimals: 小数位数，默认2位
            
        Returns:
            格式化后的字符串
        """
        if value is None or value == '-':
            return '-'
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
    
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, date: str = None, win_rate: float = None, hot_sectors: List[str] = None) -> bool:
        """保存T日选股结果到文件"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        message = self._format_t_day_message(stocks, sentiment, date, win_rate, hot_sectors)
        return self._save_message(message, 't_day', date)
    
    def send_t1_auction_result(self, stocks: List[Dict], sentiment: Dict,
                               date: str = None, market_risk: float = 0) -> bool:
        """保存T+1竞价选股结果到文件"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

        message = self._format_t1_auction_message(stocks, sentiment, date, market_risk)
        return self._save_message(message, 't1_auction', date)

    def send_track_result(self, tracked_stocks: List[Dict], win_rate: float,
                          avg_return: float, t1_day: str, t2_day: str) -> bool:
        """保存T+1竞价选股跟踪结果到文件"""
        lines = [
            f"📊 **T01龙头战法 - T+1竞价选股多日跟踪报告**",
            "",
            f"**统计周期**: {t1_day} (T+1买入) -> 多日跟踪",
            "",
            "**【收益统计】**",
            f"   跟踪股票数: {len(tracked_stocks)} 只",
            f"   胜率 (总收益为正): {win_rate:.1f}%",
            f"   平均收益率: {avg_return:+.2f}%",
            "",
            "**【个股明细】**",
        ]

        for stock in tracked_stocks:
            emoji = ['1️⃣', '2️⃣', '3️⃣'][stock['rank']-1] if stock['rank'] <= 3 else f"{stock['rank']}."
            win_mark = "✅" if stock['is_win'] else "❌"
            lines.append(f"\n{emoji} **{stock['ts_code']} {stock['stock_name']}**")
            lines.append(f"   {win_mark} 买入价: {stock['t1_open']:.2f}")
            lines.append(f"   总收益: {stock['return_pct']:+.2f}% | 总盈利: {stock['final_profit']:.2f}元/股")
            lines.append(f"   剩余仓位: {stock['shares_held']*100:.0f}% | 跟踪天数: {stock['days_tracked']}天")
            
            # 添加卖出历史
            sell_history = stock.get('sell_history', [])
            if sell_history:
                lines.append("   ")
                lines.append("   🔍 卖出历史:")
                for i, sell in enumerate(sell_history, 1):
                    limit_mark = "✅涨停" if sell['is_limit_up'] else "❌未涨停"
                    lines.append(f"   {i}. 📅 {sell['date']}: 卖出{sell['ratio']*100:.0f}% @ {sell['price']:.2f}, 盈利{sell['profit']:.2f}元/股 {limit_mark}")
            else:
                lines.append("   🔍 卖出历史: 未卖出，继续持有")

        lines.extend([
            "",
            "---",
            "⚠️ 策略规则: T+2日涨停卖一半，否则全卖；后续交易日涨停继续持有，否则卖出剩余仓位",
            f"📅 统计日期: {t2_day}"
        ])

        message = '\n'.join(lines)
        date_str = f"{t2_day[:4]}-{t2_day[4:6]}-{t2_day[6:]}"
        return self._save_message(message, 'track', date_str)
    
    def _format_t_day_message(self, stocks: List[Dict], sentiment: Dict, date: str, win_rate: float = None, hot_sectors: List[str] = None) -> str:
        """格式化T日选股消息为文本（包含详细因子数值供审核）"""
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        suggested_position = sentiment.get('suggested_position', 0.5)
        risk_score = sentiment.get('risk_score', 5)
        
        # 胜率显示逻辑（与 Feishu 消息一致）
        if win_rate is None:
            win_rate_text = "60.0% (默认)"
        elif win_rate < 0:
            win_rate_text = "数据不足 (需至少10次回测)"
        else:
            win_rate_text = f"{win_rate*100:.1f}%"
        
        risk_desc = "高风险" if risk_score >= 8 else "风险偏高" if risk_score >= 6 else "风险适中" if risk_score >= 4 else "风险较低"
        
        # 热点板块信息
        hot_sectors_text = "、".join(hot_sectors) if hot_sectors else "暂无"
        
        lines = [
            f"📊 **T01龙头战法 - {date} 晚间选股结果**",
            "",
            f"**市场情绪**: {sentiment_stage}，涨停{zt_num}家，跌停{dt_num}家",
            f"**建议仓位**: {suggested_position*100:.0f}%",
            f"**宏观风险**: 评分 {risk_score}/10 ({risk_desc})",
            f"**热点板块**: {hot_sectors_text}（AI推荐）",
            "",
            "**明日观察标的（前10名）**:",
        ]
        
        # 角色标签图标映射
        role_emoji = {
            '板块龙头': '👑',
            '前排跟随': '🥈',
            '后排跟风': '🥉',
            '独立强势': '🌟'
        }
        
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        for i, stock in enumerate(stocks[:10]):
            emoji = emojis[i] if i < 10 else f"{i+1}."
            ai_mark = ' 🤖【AI推荐】' if stock.get('unifuncs_recommended') else ''
            raw = stock.get('raw_values', {})
            
            # 强制显示角色标签
            role_label = stock.get('sector_role_label', '独立强势')
            role_icon = role_emoji.get(role_label, '🔹')
            role_mark = f" 【{role_icon}{role_label}】"
            
            # mx_search 增强信息
            limit_reason = stock.get('limit_reason', '')
            risk_alert = stock.get('risk_alert', False)
            risk_type = stock.get('risk_type', '')
            risk_details = stock.get('risk_details', '')
            
            lines.append(f"\n{emoji} **{stock['ts_code']} {stock['stock_name']}** - 总分: {self._fmt(stock['total_score'])}{ai_mark}{role_mark}")
            lines.append(f"   行业: {stock.get('sector', '-')} | {stock.get('reason', '-')}")
            
            # 显示涨停原因（如果有）
            if limit_reason:
                lines.append(f"\n   📰 【涨停原因】: {limit_reason[:120]}...")
            
            # 显示风险提示（如果有）
            if risk_alert:
                lines.append(f"\n   ⚠️ 【风险提醒】: {risk_type}")
                lines.append(f"      {risk_details[:100]}...")
            
            # 添加所有因子详细数值供审核（使用 _fmt 格式化）
            lines.append(f"\n   【原始指标数值】")
            lines.append(f"   1️⃣ 涨停质量: 首次涨停={raw.get('first_limit_time', '-')}, 炸板={raw.get('limit_times', '-')}, 连板={raw.get('consecutive_limit', '-')} → 得分:{self._fmt(stock.get('limit_quality_score'))}")
            lines.append(f"   2️⃣ 封成比: {self._fmt(raw.get('seal_ratio'))} → 得分:{self._fmt(stock.get('seal_ratio_score'))}")
            lines.append(f"   3️⃣ 封流比: {self._fmt(raw.get('seal_flow_ratio'))} → 得分:{self._fmt(stock.get('seal_flow_ratio_score'))}")
            lines.append(f"   4️⃣ 量比: {self._fmt(raw.get('volume_ratio'))} → 得分:{self._fmt(stock.get('volume_ratio_score'))}")
            lines.append(f"   5️⃣ 真实换手率: {self._fmt(raw.get('real_turnover_rate'))}% → 得分:{self._fmt(stock.get('turnover_rate_score'))}")
            lines.append(f"   6️⃣ 龙虎榜净买入: {raw.get('net_buy', 0):.0f}万 → 得分:{self._fmt(stock.get('dragon_tiger_score'))}")
            lines.append(f"   7️⃣ 主力净占比: {self._fmt(raw.get('main_net_ratio'))}% → 得分:{self._fmt(stock.get('money_flow_score'))}")
            lines.append(f"   8️⃣ 成交额排名: 第{raw.get('amount_rank', '-')}名 → 得分:{self._fmt(stock.get('amount_rank_score'))}")
            lines.append(f"   9️⃣ 板块热度: 板块涨停{raw.get('sector_zt_count', '-')}只 → 得分:{self._fmt(stock.get('sector_heat_score'))}")
            lines.append(f"   🔟 Bias MA3: {self._fmt(raw.get('bias_ma3'))}% → 得分:{self._fmt(stock.get('bias_ma3_score'))}")
            lines.append(f"   1️⃣1️⃣ 舆情分析: {self._fmt(stock.get('sentiment_score'))}分")
            
            lines.append(f"\n   【评分明细】")
            lines.append(f"   涨停:{self._fmt(stock.get('limit_quality_score'))} | 封成比:{self._fmt(stock.get('seal_ratio_score'))} | 封流比:{self._fmt(stock.get('seal_flow_ratio_score'))} | 量比:{self._fmt(stock.get('volume_ratio_score'))} | 换手:{self._fmt(stock.get('turnover_rate_score'))} | 龙虎榜:{self._fmt(stock.get('dragon_tiger_score'))} | 资金流:{self._fmt(stock.get('money_flow_score'))} | 成交额:{self._fmt(stock.get('amount_rank_score'))} | 板块:{self._fmt(stock.get('sector_heat_score'))} | Bias:{self._fmt(stock.get('bias_ma3_score'))} | 舆情:{self._fmt(stock.get('sentiment_score'))}")
        
        lines.extend([
            "",
            "---",
            "⚠️ 以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。",
            f"📅 选股时间: {date} 20:00",
            f"🤖 策略胜率: {win_rate_text}"
        ])
        
        return '\n'.join(lines)
    
    def _format_t1_auction_message(self, stocks: List[Dict], sentiment: Dict, date: str, market_risk: float = 0) -> str:
        """格式化T+1竞价选股消息为文本（包含详细竞价指标供审核）"""
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        
        risk_desc = "高风险，建议观望" if market_risk >= 8 else "风险偏高，谨慎操作" if market_risk >= 6 else "风险适中" if market_risk >= 4 else "风险较低"
        
        lines = [
            f"🔥 **T01龙头战法 - {date} 竞价精选结果**",
            "",
            f"**市场情绪**: {sentiment_stage}，涨停{zt_num}家，跌停{dt_num}家",
            f"**市场风险**: 评分 {market_risk}/10 ({risk_desc})",
            "",
            "**竞价精选标的**:",
        ]
        
        emojis = ['1️⃣', '2️⃣', '3️⃣']
        for i, stock in enumerate(stocks[:3]):
            emoji = emojis[i] if i < 3 else f"{i+1}."
            wts_mark = ' 🔥【弱转强】' if stock.get('is_weak_to_strong') else ''
            raw = stock.get('raw_values', {})
            
            lines.append(f"\n{emoji} **{stock['ts_code']} {stock['stock_name']}** - 综合得分: {self._fmt(stock.get('final_score', 0))}{wts_mark}")
            lines.append(f"   行业: {stock.get('sector', '-')} | {stock.get('reason', '-')}")
            
            # 添加所有竞价因子详细数值供审核（使用 _fmt 格式化）
            lines.append(f"\n   【竞价原始指标数值】")
            lines.append(f"   1️⃣ 竞价价格: {raw.get('auction_price', '-')}元")
            lines.append(f"   2️⃣ 竞价涨幅: {self._fmt(raw.get('auction_pct_chg', 0))}% → 得分:{self._fmt(stock.get('auction_score'))}")
            lines.append(f"   3️⃣ 竞价成交量: {raw.get('auction_vol', 0)/10000:.0f}万手")
            lines.append(f"   4️⃣ 竞价金额: {raw.get('auction_amount', 0):.0f}万元")
            lines.append(f"   5️⃣ 竞价换手率: {self._fmt(raw.get('auction_turnover', 0), 4)}%")
            lines.append(f"   6️⃣ 竞价量比: {self._fmt(raw.get('auction_volume_ratio'))}")
            lines.append(f"   7️⃣ 竞价爆量比: {self._fmt(raw.get('auction_burst_ratio'), 4)}")
            lines.append(f"   8️⃣ 昨日收盘价: {raw.get('pre_close', '-')}元")
            lines.append(f"   9️⃣ 流通股本: {raw.get('float_share', 0):.0f}万股")
            lines.append(f"   🔟 T日得分: {self._fmt(stock.get('t_day_score', 0))}")
            lines.append(f"   1️⃣1️⃣ 是否弱转强: {'✅是' if stock.get('is_weak_to_strong') else '❌否'}")
            
            lines.append(f"\n   【竞价评分明细】")
            lines.append(f"   竞价:{self._fmt(stock.get('auction_score'))} | T日基础:{self._fmt(stock.get('t_day_score'))} | 板块:{self._fmt(stock.get('sector_score'))} | 风险调整:{self._fmt(stock.get('risk_adjustment'))} | 最终:{self._fmt(stock.get('final_score'))}")
            
            lines.append(f"\n   【操作建议】")
            lines.append(f"   建议仓位: {stock.get('suggested_position', 0.3)*100:.0f}%")
        
        lines.extend([
            "",
            "---",
            "⚠️ 以上内容仅供参考，不构成投资建议。",
            f"📅 竞价时间: {date} 09:25",
            "⏰ 操作建议: 9:30开盘前5分钟观察，符合条件的可轻仓跟进"
        ])
        
        return '\n'.join(lines)
    
    def _save_message(self, content: str, msg_type: str, date: str) -> bool:
        """保存消息到文件"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.message_dir}/{msg_type}_{date}_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 消息已保存到: {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存消息失败: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """保存简单文本消息"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.message_dir}/text_{timestamp}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"✅ 消息已保存到: {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存消息失败: {e}")
            return False


class MockMessenger:
    """模拟消息推送（用于测试）"""
    
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, date: str = None, win_rate: float = None, hot_sectors: List[str] = None) -> bool:
        """模拟发送T日结果"""
        print("\n" + "="*60)
        print(f"T01龙头战法 - {date or datetime.now().strftime('%Y-%m-%d')} 晚间初选结果")
        print("="*60)
        
        print(f"\n【市场情绪】{sentiment.get('sentiment_stage', '混沌')}，涨停{sentiment.get('zt_num', 0)}家，跌停{sentiment.get('dt_num', 0)}家")
        print(f"【建议仓位】{sentiment.get('suggested_position', 0.5)*100:.0f}%")
        print(f"【宏观风险】评分: {sentiment.get('risk_score', 5)}/10")
        
        # 热点板块
        hot_sectors_text = "、".join(hot_sectors) if hot_sectors else "暂无"
        print(f"【热点板块】{hot_sectors_text}（AI推荐）")
        
        print("\n【明日观察标的】")
        for i, stock in enumerate(stocks[:10]):
            emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][i]
            ai_mark = ' 🤖' if stock.get('unifuncs_recommended') else ''
            print(f"{emoji} {stock['ts_code']} {stock['stock_name']} - 得分: {stock['total_score']}{ai_mark}")
            print(f"   {stock.get('reason', '-')}")
        
        return True
    
    def send_t1_auction_result(self, stocks: List[Dict], sentiment: Dict,
                               date: str = None, market_risk: float = 0) -> bool:
        """模拟发送T+1竞价结果"""
        print("\n" + "="*60)
        print(f"T01龙头战法 - {date or datetime.now().strftime('%Y-%m-%d')} 竞价精选股票")
        print("="*60)

        print(f"\n【市场风险】评分: {market_risk}/10")

        print("\n【精选标的】")
        for i, stock in enumerate(stocks[:3]):
            emoji = ['1️⃣', '2️⃣', '3️⃣'][i] if i < 3 else f'{i+1}.'
            wts_mark = ' 🔥【弱转强】' if stock.get('is_weak_to_strong') else ''
            print(f"{emoji} {stock['ts_code']} {stock['stock_name']} - 得分: {stock.get('final_score', 0)}{wts_mark}")
            print(f"   竞价涨幅: {stock.get('raw_values', {}).get('auction_pct_chg', 0):.2f}%")
            print(f"   {stock.get('reason', '-')}")

        return True

    def send_track_result(self, tracked_stocks: List[Dict], win_rate: float,
                          avg_return: float, t1_day: str, t2_day: str) -> bool:
        """模拟发送跟踪结果"""
        print("\n" + "="*60)
        print(f"T01龙头战法 - T+1竞价选股 T+2 跟踪报告")
        print("="*60)
        print(f"\n统计周期: {t1_day} -> {t2_day}")
        print(f"\n【收益统计】")
        print(f"   跟踪股票数: {len(tracked_stocks)} 只")
        print(f"   胜率 (>3%): {win_rate:.1f}%")
        print(f"   平均收益率: {avg_return:.2f}%")
        print(f"\n【个股明细】")
        for stock in tracked_stocks:
            emoji = ['1️⃣', '2️⃣', '3️⃣'][stock['rank']-1] if stock['rank'] <= 3 else f"{stock['rank']}."
            win_mark = "✅" if stock['is_win'] else "❌"
            print(f"{emoji} {stock['ts_code']} {stock['stock_name']}")
            print(f"   {win_mark} 买入: {stock['t1_open']:.2f} -> 卖出: {stock['t2_close']:.2f}, 收益: {stock['return_pct']:+.2f}%")
        return True


def get_messenger(use_mock: bool = False, use_feishu_api: bool = True) -> object:
    """
    获取消息推送器
    
    优先级:
    1. use_mock=True -> MockMessenger (测试用)
    2. use_feishu_api=True -> FeishuApiMessenger (飞书API发送富文本/卡片消息，推荐)
    3. FEISHU_WEBHOOK_URL 配置 -> FeishuMessenger (Webhook)
    4. 无配置 -> FileMessenger (保存到文件)
    """
    if use_mock:
        return MockMessenger()
    
    # 优先使用飞书API发送富文本/卡片消息（效果最好）
    if use_feishu_api:
        return FeishuApiMessenger()
    
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
    if webhook_url:
        return FeishuMessenger(webhook_url)
    
    # 无配置时使用文件消息推送
    print("⚠️ 未配置飞书Webhook，消息将保存到文件")
    return FileMessenger()


if __name__ == '__main__':
    # 测试消息格式化
    messenger = MockMessenger()
    
    test_stocks = [
        {
            'ts_code': '000001.SZ',
            'stock_name': '平安银行',
            'total_score': 87.5,
            'sector': '银行',
            'reason': '涨停质量优秀 + 封流比高',
            'unifuncs_recommended': True,
            'raw_values': {
                'first_limit_time': '09:45:00',
                'seal_ratio': 0.35,
                'seal_flow_ratio': 0.08,
                'volume_ratio': 2.5,
                'real_turnover_rate': 12.5,
                'net_buy': 5000,
                'main_net_ratio': 15.2,
                'bias_ma3': 4.2
            }
        }
    ]
    
    test_sentiment = {
        'zt_num': 85,
        'dt_num': 3,
        'sentiment_stage': '主升',
        'risk_score': 4,
        'suggested_position': 0.6
    }
    
    messenger.send_t_day_result(test_stocks, test_sentiment, '2026-03-09')
