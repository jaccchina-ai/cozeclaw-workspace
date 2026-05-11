"""
T01 选股系统 - 封成比因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class SealRatioFactor(BaseFactor):
    """封成比因子"""
    
    def _init_default_config(self):
        """初始化默认配置"""
        self.config.setdefault('scoring_rules', [
            {'threshold': 1.0, 'score': 10},
            {'threshold': 0.5, 'score': 8},
            {'threshold': 0.3, 'score': 6},
            {'threshold': 0.1, 'score': 4},
            {'threshold': 0.0, 'score': 2}
        ])
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        """计算封成比因子得分"""
        try:
            # 封单金额 (万元)
            seal_amount = float(data.get('seal_amount', 0) or data.get('fd_amount', 0) or 0)
            # 成交金额 (万元)
            deal_amount = float(data.get('amount', 0) or 0)
            
            raw_values = {
                'seal_amount': seal_amount,
                'deal_amount': deal_amount,
                'seal_ratio': 0.0
            }
            
            if deal_amount <= 0:
                return FactorResult(
                    factor_name='seal_ratio',
                    score=0,
                    raw_values=raw_values,
                    is_valid=False,
                    error_message='成交金额为0'
                )
            
            # 计算封成比
            seal_ratio = seal_amount / deal_amount
            raw_values['seal_ratio'] = round(seal_ratio, 4)
            
            # 根据规则计算得分
            score = self._calculate_score(seal_ratio)
            
            return FactorResult(
                factor_name='seal_ratio',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f"计算封成比因子失败: {e}")
            return FactorResult(
                factor_name='seal_ratio',
                score=0,
                raw_values={},
                is_valid=False,
                error_message=str(e)
            )
    
    def _calculate_score(self, seal_ratio: float) -> float:
        """根据封成比计算得分"""
        # 按阈值从高到低排序
        sorted_rules = sorted(self.config['scoring_rules'], 
                           key=lambda x: x['threshold'], reverse=True)
        
        for rule in sorted_rules:
            if seal_ratio >= rule['threshold']:
                return rule['score']
        
        return 2.0
