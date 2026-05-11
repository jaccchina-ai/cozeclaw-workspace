#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜因子集成示例代码
"""

# 1. 因子权重配置示例
# 在scoring_model.py中添加:
class FactorWeights:
    # 现有因子...
    dragon_tiger: float = 15.0  # 龙虎榜因子权重


# 2. 评分模型集成示例
# 在calculate_total_score方法中添加:
from dragon_tiger.integration import DragonTigerIntegration

def calculate_total_score(self, stock_data: dict) -> StockScore:
    factor_scores = {}
    
    # 计算龙虎榜因子得分
    try:
        integration = DragonTigerIntegration()
        dragon_tiger_score = integration.get_dragon_tiger_score(stock_data)
        factor_scores['dragon_tiger'] = dragon_tiger_score * self.factor_weights.dragon_tiger
    except Exception as e:
        print(f'龙虎榜因子计算失败: {e}')
        factor_scores['dragon_tiger'] = 0
    
    # 其他因子计算...
    
    total_score = sum(factor_scores.values())
    return StockScore(
        total_score=total_score,
        factor_scores=factor_scores
    )


# 3. 选股引擎集成示例
# 在run_t_day_selection函数中添加:
def run_t_day_selection(date: str = None) -> SelectionResult:
    # 现有选股逻辑...
    
    # 应用龙虎榜因子筛选
    try:
        from dragon_tiger.integration import DragonTigerIntegration
        integration = DragonTigerIntegration()
        
        print("
📊 应用龙虎榜因子筛选...")
        candidates = integration.filter_by_dragon_tiger(candidates, threshold=50)
        print(f"✅ 龙虎榜因子筛选完成，剩余 {len(candidates)} 只股票")
    except Exception as e:
        print(f'龙虎榜因子筛选失败: {e}')
    
    # 剩余选股逻辑...
