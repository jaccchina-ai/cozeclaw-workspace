"""
T01 选股系统 - 因子计算引擎

负责协调整个因子计算流程
"""

import logging
from typing import Dict, List, Type, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from .base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class FactorEngine:
    """因子计算引擎"""
    
    def __init__(self, factor_classes: Dict[str, Type[BaseFactor]], 
                 weights: Optional[Dict[str, float]] = None,
                 config_path: Optional[str] = None):
        self.factor_classes = factor_classes
        self.weights = weights or {}
        self.config_path = config_path
        self.factors: Dict[str, BaseFactor] = {}
        
        self._init_factors()
        self._validate_weights()
    
    def _init_factors(self):
        """初始化所有因子实例"""
        for factor_name, factor_class in self.factor_classes.items():
            try:
                self.factors[factor_name] = factor_class()
                logger.info(f"初始化因子成功: {factor_name}")
            except Exception as e:
                logger.error(f"初始化因子失败: {factor_name}, 错误: {e}")
    
    def _validate_weights(self):
        """验证因子权重配置"""
        total_weight = sum(self.weights.values())
        if abs(total_weight - 100) > 0.01:
            logger.warning(f"因子权重总和不为100，当前总和: {total_weight:.2f}")
    
    def calculate_single_factor(self, factor_name: str, data: Dict[str, Any]) -> FactorResult:
        """计算单个因子"""
        if factor_name not in self.factors:
            return FactorResult(
                factor_name=factor_name,
                score=0,
                raw_values={},
                is_valid=False,
                error_message=f"因子 {factor_name} 不存在"
            )
            
        factor = self.factors[factor_name]
        
        try:
            # 数据预处理
            processed_data = factor.pre_process(data)
            
            # 计算因子得分
            result = factor.calculate(processed_data)
            
            # 结果后处理
            final_result = factor.post_process(result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"计算因子 {factor_name} 失败: {e}")
            return FactorResult(
                factor_name=factor_name,
                score=0,
                raw_values={},
                is_valid=False,
                error_message=str(e)
            )
    
    def calculate_all_factors(self, data: Dict[str, Any], 
                            parallel: bool = True) -> Dict[str, FactorResult]:
        """计算所有因子"""
        results = {}
        
        if parallel and len(self.factors) > 1:
            # 并行计算
            with ThreadPoolExecutor(max_workers=min(len(self.factors), 8)) as executor:
                futures = {
                    executor.submit(self.calculate_single_factor, factor_name, data): factor_name
                    for factor_name in self.factors
                }
                
                for future in as_completed(futures):
                    factor_name = futures[future]
                    try:
                        results[factor_name] = future.result()
                    except Exception as e:
                        logger.error(f"并行计算因子 {factor_name} 失败: {e}")
                        results[factor_name] = FactorResult(
                            factor_name=factor_name,
                            score=0,
                            raw_values={},
                            is_valid=False,
                            error_message=str(e)
                        )
        else:
            # 串行计算
            for factor_name in self.factors:
                results[factor_name] = self.calculate_single_factor(factor_name, data)
        
        return results
    
    def calculate_total_score(self, factor_results: Dict[str, FactorResult]) -> float:
        """计算加权总分"""
        total_score = 0.0
        total_weight = 0.0
        
        for factor_name, result in factor_results.items():
            if not result.is_valid:
                continue
                
            weight = self.weights.get(factor_name, 1.0)
            total_score += result.score * weight
            total_weight += weight
        
        if total_weight == 0:
            logger.warning("所有因子计算结果无效，总分返回0")
            return 0.0
        
        return total_score / total_weight
    
    def get_factor_weights(self) -> Dict[str, float]:
        """获取因子权重配置"""
        return self.weights.copy()
    
    def update_factor_weight(self, factor_name: str, weight: float):
        """更新因子权重"""
        if factor_name in self.weights:
            self.weights[factor_name] = weight
            self._validate_weights()
            logger.info(f"更新因子权重: {factor_name} = {weight}")
        else:
            logger.warning(f"因子 {factor_name} 不存在，无法更新权重")
    
    def calculate_factor_ic(self, stock_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算因子IC值"""
        # 这里可以实现因子IC值计算逻辑
        # IC值用于衡量因子的有效性
        pass
