"""
T01 选股系统 - 消息推送模块

飞书消息推送和格式化
"""

import os
import json
import requests
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
        
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, date: str = None, win_rate: float = None) -> bool:
        """
        发送T日选股结果
        
        Args:
            stocks: 选股结果列表
            sentiment: 市场情绪数据
            date: 日期
            win_rate: 策略胜率（动态计算）
            
        Returns:
            是否发送成功
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        message = self._format_t_day_message(stocks, sentiment, date, win_rate)
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
    
    def _format_t_day_message(self, stocks: List[Dict], sentiment: Dict, date: str, win_rate: float = None) -> Dict:
        """格式化T日选股消息"""
        
        # 市场情绪部分
        zt_num = sentiment.get('zt_num', 0)
        dt_num = sentiment.get('dt_num', 0)
        fb_ratio = sentiment.get('fb_ratio', 0)
        sentiment_stage = sentiment.get('sentiment_stage', '混沌')
        suggested_position = sentiment.get('suggested_position', 0.5)
        risk_score = sentiment.get('risk_score', 5)
        
        # 动态胜率（如果没有传入则使用默认值）
        strategy_win_rate = win_rate if win_rate is not None else 0.6
        
        # 风险描述
        risk_desc = self._get_risk_description(risk_score)
        
        # 股票列表部分
        stock_cards = []
        for i, stock in enumerate(stocks):
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][i]
            unifuncs_mark = ' 🤖【AI推荐】' if stock.get('unifuncs_recommended') else ''
            
            raw = stock.get('raw_values', {})
            
            card = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{rank_emoji} {stock['ts_code']} {stock['stock_name']}**{unifuncs_mark}\n得分: {stock['total_score']} | {stock.get('sector', '-')}"
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
        
        # 因子详情部分
        factor_cards = []
        rank_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        for i, stock in enumerate(stocks):
            rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
            raw = stock.get('raw_values', {})
            
            factor_text = f"""**{rank_emoji} {stock['ts_code']} {stock['stock_name']}** - 得分: {stock['total_score']}

1. 首次涨停时间: {raw.get('first_limit_time', '-')}
2. 封成比: {raw.get('seal_ratio', '-')}
3. 封流比: {raw.get('seal_flow_ratio', '-')}
4. 量比: {raw.get('volume_ratio', '-')}
5. 真实换手率: {raw.get('real_turnover_rate', '-')}%
6. 龙虎榜净买入: {raw.get('net_buy', 0):.0f}万
7. 主力净占比: {raw.get('main_net_ratio', '-')}%
8. Bias MA3: {raw.get('bias_ma3', '-')}%"""
            
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
                            "content": f"**【策略胜率】** {strategy_win_rate*100:.1f}%"
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
            unifuncs_mark = ' 🤖【AI推荐】' if stock.get('unifuncs_recommended') else ''
            
            raw = stock.get('raw_values', {})
            is_wts = stock.get('is_weak_to_strong', False)
            wts_mark = ' 🔥【弱转强】' if is_wts else ''
            
            card = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{rank_emoji} {stock['ts_code']} {stock['stock_name']}**{unifuncs_mark}{wts_mark}\n得分: {stock.get('final_score', 0)} | {stock.get('sector', '-')}"
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
        
        # 因子详情部分
        factor_cards = []
        for i, stock in enumerate(stocks):
            rank_emoji = ['1️⃣', '2️⃣', '3️⃣'][i] if i < 3 else f'{i+1}.'
            raw = stock.get('raw_values', {})
            
            factor_text = f"""**{rank_emoji} {stock['ts_code']} {stock['stock_name']}** - 得分: {stock.get('final_score', 0)}

1. 竞价换手率: {raw.get('auction_turnover', '-')}%
2. 竞价金额: {raw.get('auction_amount', 0):.0f}万
3. 竞价涨幅: {raw.get('auction_pct_chg', 0):.2f}%
4. 竞价量比: {raw.get('auction_volume_ratio', '-')}
5. 竞价爆量比: {raw.get('auction_burst_ratio', '-')}
6. 板块竞价涨幅: {raw.get('sector_auction_pct', '-')}%
7. 板块共振度: {raw.get('sector_resonance', '-')}"""
            
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


class MockMessenger:
    """模拟消息推送（用于测试）"""
    
    def send_t_day_result(self, stocks: List[Dict], sentiment: Dict, date: str = None) -> bool:
        """模拟发送T日结果"""
        print("\n" + "="*60)
        print(f"T01龙头战法 - {date or datetime.now().strftime('%Y-%m-%d')} 晚间初选结果")
        print("="*60)
        
        print(f"\n【市场情绪】{sentiment.get('sentiment_stage', '混沌')}，涨停{sentiment.get('zt_num', 0)}家，跌停{sentiment.get('dt_num', 0)}家")
        print(f"【建议仓位】{sentiment.get('suggested_position', 0.5)*100:.0f}%")
        print(f"【宏观风险】评分: {sentiment.get('risk_score', 5)}/10")
        
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


def get_messenger(use_mock: bool = False) -> object:
    """获取消息推送器"""
    if use_mock:
        return MockMessenger()
    return FeishuMessenger()


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
