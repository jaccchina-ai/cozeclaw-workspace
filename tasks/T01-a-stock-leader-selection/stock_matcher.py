#!/usr/bin/env python3
"""
股票智能匹配模块
基于多维度增强Unifuncs推荐与选股结果的匹配度
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class MatchResult:
    """匹配结果"""
    recommendation: Dict
    match_score: float
    match_reasons: List[str] = field(default_factory=list)

class StockMatcher:
    def __init__(self, config=None):
        self.config = config or {
            'sector_weight': 0.3,
            'market_cap_weight': 0.2,
            'name_weight': 0.2,
            'code_weight': 0.2,
            'industry_weight': 0.1,
            'threshold': 0.3  # 匹配度阈值
        }
    
    def _code_match(self, stock_code: str, rec_code: str) -> float:
        """股票代码匹配"""
        # 去除后缀，只匹配数字部分
        stock_code_clean = stock_code.split('.')[0]
        rec_code_clean = rec_code.split('.')[0]
        
        if stock_code_clean == rec_code_clean:
            return 1.0
        return 0.0
    
    def _name_match(self, stock_name: str, rec_name: str) -> float:
        """股票名称匹配"""
        if not stock_name or not rec_name:
            return 0.0
            
        # 去除特殊字符
        clean_name1 = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', stock_name)
        clean_name2 = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', rec_name)
        
        # 完全匹配
        if clean_name1 == clean_name2:
            return 1.0
            
        # 子串匹配
        if clean_name1 in clean_name2 or clean_name2 in clean_name1:
            return 0.7
            
        # 关键词匹配（提取前2个汉字）
        chars1 = list(clean_name1[:2])
        chars2 = list(clean_name2[:2])
        match_chars = set(chars1) & set(chars2)
        if match_chars:
            return len(match_chars) / 2
            
        return 0.0
    
    def _sector_match(self, stock_sector: str, rec_sector: str) -> float:
        """板块匹配"""
        if not stock_sector or not rec_sector:
            return 0.0
            
        if stock_sector == rec_sector:
            return 1.0
            
        # 板块别名匹配（需要扩展字典）
        sector_aliases = {
            '电力': ['绿色电力', '电力行业', '电力设备'],
            '通信': ['通信设备', '通信服务', '5G'],
            '军工': ['国防军工', '航空航天', '地面兵装'],
            '半导体': ['芯片', '集成电路', '半导体设备']
        }
        
        if stock_sector in sector_aliases:
            if rec_sector in sector_aliases[stock_sector]:
                return 0.8
                
        if rec_sector in sector_aliases:
            if stock_sector in sector_aliases[rec_sector]:
                return 0.8
                
        return 0.0
    
    def _market_cap_match(self, stock_mv: float, rec_mv: float, tolerance=0.3) -> float:
        """市值匹配"""
        if stock_mv <= 0 or rec_mv <= 0:
            return 0.5  # 无法获取市值时给予中等匹配度
            
        # 计算相对误差
        ratio = stock_mv / rec_mv
        if 1 - tolerance <= ratio <= 1 + tolerance:
            return 1.0
            
        # 超出范围但仍在2倍以内
        if 0.5 <= ratio <= 2.0:
            return 0.5
            
        return 0.0
    
    def _industry_match(self, stock_industry: str, rec_industry: str) -> float:
        """行业匹配"""
        if not stock_industry or not rec_industry:
            return 0.0
            
        if stock_industry == rec_industry:
            return 1.0
            
        # 模糊匹配（行业包含关系）
        if stock_industry in rec_industry or rec_industry in stock_industry:
            return 0.7
            
        return 0.0
    
    def calculate_match_score(self, stock: Dict, recommendation: Dict) -> MatchResult:
        """计算匹配度得分"""
        reasons = []
        scores = []
        
        # 代码匹配
        code_score = self._code_match(stock['ts_code'], recommendation['ts_code'])
        scores.append(code_score * self.config['code_weight'])
        if code_score > 0.9:
            reasons.append("代码完全匹配")
        
        # 名称匹配
        name_score = self._name_match(stock['stock_name'], recommendation.get('name', ''))
        scores.append(name_score * self.config['name_weight'])
        if name_score > 0.7:
            reasons.append("名称高度匹配")
        elif name_score > 0.3:
            reasons.append("名称部分匹配")
            
        # 板块匹配
        sector_score = self._sector_match(stock.get('sector', ''), recommendation.get('sector', ''))
        scores.append(sector_score * self.config['sector_weight'])
        if sector_score > 0.8:
            reasons.append("板块匹配")
            
        # 市值匹配
        stock_mv = stock.get('raw_values', {}).get('float_mv', 0) if stock.get('raw_values') else 0
        rec_mv = recommendation.get('market_cap', 0)
        market_cap_score = self._market_cap_match(stock_mv, rec_mv)
        scores.append(market_cap_score * self.config['market_cap_weight'])
        if market_cap_score > 0.9:
            reasons.append("市值匹配")
        elif market_cap_score > 0.5:
            reasons.append("市值接近")
            
        # 行业匹配
        industry_score = self._industry_match(stock.get('industry', ''), recommendation.get('industry', ''))
        scores.append(industry_score * self.config['industry_weight'])
        if industry_score > 0.8:
            reasons.append("行业匹配")
            
        # 总得分
        total_score = sum(scores)
        
        return MatchResult(
            recommendation=recommendation,
            match_score=total_score,
            match_reasons=reasons
        )
    
    def find_best_match(self, stock: Dict, recommendations: List[Dict]) -> Optional[MatchResult]:
        """找到最匹配的推荐股票"""
        best_match = None
        best_score = 0
        
        for rec in recommendations:
            match_result = self.calculate_match_score(stock, rec)
            
            # 代码完全匹配直接返回
            if match_result.match_score >= 0.9:
                return match_result
            
            if match_result.match_score > best_score:
                best_score = match_result.match_score
                best_match = match_result
        
        if best_match and best_match.match_score >= self.config['threshold']:
            return best_match
            
        return None
    
    def batch_match(self, stocks: List[Dict], recommendations: List[Dict]) -> List[Dict]:
        """批量匹配"""
        matched_stocks = []
        
        for stock in stocks:
            matched_stock = stock.copy()
            best_match = self.find_best_match(stock, recommendations)
            
            if best_match:
                matched_stock['unifuncs_recommended'] = True
                matched_stock['unifuncs_match_score'] = best_match.match_score
                matched_stock['unifuncs_reason'] = best_match.recommendation.get('reason', '')
                matched_stock['unifuncs_match_reasons'] = best_match.match_reasons
            else:
                matched_stock['unifuncs_recommended'] = False
                
            matched_stocks.append(matched_stock)
            
        return matched_stocks


def main():
    """测试匹配功能"""
    matcher = StockMatcher()
    
    # 测试数据
    test_stock = {
        'ts_code': '601606.SH',
        'stock_name': '长城军工',
        'sector': '国防军工',
        'industry': '地面兵装',
        'raw_values': {'float_mv': 313.37 * 100000000}
    }
    
    test_recommendations = [
        {
            'ts_code': '601606.SH',
            'name': '长城军工',
            'sector': '地面兵装',
            'industry': '国防军工',
            'market_cap': 313.37 * 100000000,
            'reason': '兵装重组概念龙头'
        },
        {
            'ts_code': '600032.SH',
            'name': '浙江新能',
            'sector': '电力',
            'industry': '水电',
            'market_cap': 313.09 * 100000000,
            'reason': '绿电概念核心标的'
        },
        {
            'ts_code': '002491.SZ',
            'name': '通鼎互联',
            'sector': '通信设备',
            'industry': '5G',
            'market_cap': 134.12 * 100000000,
            'reason': '光纤概念活跃标的'
        }
    ]
    
    print("=== 股票匹配测试 ===")
    result = matcher.find_best_match(test_stock, test_recommendations)
    if result:
        print(f"最佳匹配: {result.recommendation['name']}")
        print(f"匹配度: {result.match_score:.3f}")
        print(f"匹配理由: {', '.join(result.match_reasons)}")
    else:
        print("未找到匹配项")


if __name__ == '__main__':
    main()