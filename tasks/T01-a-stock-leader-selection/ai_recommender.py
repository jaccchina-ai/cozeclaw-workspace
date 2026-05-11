"""
T01 选股系统 - AI 推荐备用模块

当 Unifuncs 不可用时，使用 OpenRouter 进行股票推荐
"""

import os
import sys
import json
import requests
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))


class OpenRouterRecommender:
    """
    使用 OpenRouter API 进行股票推荐
    作为 Unifuncs 的备用方案
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY', '')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "coze/deepseek-r1-250528"  # 使用 DeepSeek-R1 进行推理
    
    def get_recommendations(self, stocks: List[Dict], date: str) -> Dict[str, float]:
        """
        获取股票推荐
        
        Args:
            stocks: 股票列表
            date: 日期
            
        Returns:
            {ts_code: score}
        """
        scores = {}
        
        if not self.api_key:
            print("   ⚠️ OpenRouter API Key 未配置")
            return scores
        
        try:
            # 构建股票列表
            stock_list = "\n".join([f"{s['ts_code']} {s['stock_name']}" for s in stocks[:20]])
            
            # 构建提示词
            prompt = f"""作为A股短线交易专家，请分析以下今日涨停股票，预测下一个交易日（T+1）继续涨停概率最大的3只股票。

股票列表：
{stock_list}

请只返回以下格式（不要其他解释）：
1. 股票代码 - 理由（30字内）
2. 股票代码 - 理由（30字内）
3. 股票代码 - 理由（30字内）"""

            print(f"   调用 OpenRouter 分析 {len(stocks[:20])} 只股票...")
            
            # 调用 OpenRouter API
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://t01.jaccoffice.com",
                    "X-Title": "T01 Stock Selection"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                
                print(f"   ✅ OpenRouter 分析完成")
                print(f"   答案: {answer[:200]}...")
                
                # 解析股票代码
                import re
                pattern = r'(\d{6}\.(?:SZ|SH|BJ))'
                matches = re.findall(pattern, answer)
                
                print(f"   找到股票代码: {matches}")
                
                # 为匹配的股票加分
                for ts_code in matches[:3]:
                    if any(s['ts_code'] == ts_code for s in stocks):
                        scores[ts_code] = 10
                        print(f"   🤖 AI推荐: {ts_code}")
            else:
                print(f"   ❌ OpenRouter API 错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ OpenRouter 调用失败: {e}")
        
        return scores


def get_ai_recommendations(stocks: List[Dict], date: str) -> Dict[str, float]:
    """
    获取 AI 推荐（优先 Unifuncs，失败则使用 OpenRouter）
    
    Args:
        stocks: 股票列表
        date: 日期
        
    Returns:
        {ts_code: score}
    """
    scores = {}
    
    # 首先尝试 Unifuncs
    try:
        from unifuncs_client import UnifuncsClient
        
        client = UnifuncsClient()
        stock_list = "\n".join([f"{s['ts_code']} {s['stock_name']}" for s in stocks[:20]])
        
        output_prompt = f"""请对以下今日涨停股票进行深度研究分析，预测下一个交易日（T+1）继续涨停概率最大的3只股票：

股票列表：
{stock_list}

请只返回以下格式：
1. 股票代码 股票名称 - 理由
2. 股票代码 股票名称 - 理由
3. 股票代码 股票名称 - 理由"""

        print("   尝试 Unifuncs...")
        result = client.get_report(output_prompt=output_prompt, timeout=30, poll_interval=2)
        answer = result.answer or result.summary or ""
        
        if answer and len(answer) > 50:  # 内容有效
            import re
            pattern = r'(\d{6}\.(?:SZ|SH|BJ))'
            matches = re.findall(pattern, answer)
            
            for ts_code in matches[:3]:
                if any(s['ts_code'] == ts_code for s in stocks):
                    scores[ts_code] = 10
                    print(f"   🤖 Unifuncs推荐: {ts_code}")
            
            if scores:
                print("   ✅ Unifuncs 成功")
                return scores
    except Exception as e:
        print(f"   ⚠️ Unifuncs 失败: {e}")
    
    # Unifuncs 失败，使用 OpenRouter 备用
    print("   切换到 OpenRouter 备用...")
    recommender = OpenRouterRecommender()
    return recommender.get_recommendations(stocks, date)


if __name__ == '__main__':
    # 测试
    test_stocks = [
        {'ts_code': '300246.SZ', 'stock_name': '宝莱特'},
        {'ts_code': '000545.SZ', 'stock_name': '金浦钛业'},
        {'ts_code': '601016.SH', 'stock_name': '节能风电'},
    ]
    
    scores = get_ai_recommendations(test_stocks, '20260312')
    print(f"\n最终结果: {scores}")
