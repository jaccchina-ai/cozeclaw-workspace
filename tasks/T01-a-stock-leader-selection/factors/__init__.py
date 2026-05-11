"""
T01 选股系统 - 因子模块入口
"""

__version__ = "1.0.0"
__author__ = "T01 选股系统开发团队"

# 基础类导出
from .base.base_factor import BaseFactor, FactorResult
from .base.factor_engine import FactorEngine

# 已实现的因子
from .calculations.limit_quality import LimitQualityFactor
from .calculations.seal_ratio import SealRatioFactor

# 因子映射
FACTOR_CLASSES = {
    'limit_quality': LimitQualityFactor,
    'seal_ratio': SealRatioFactor,
    # 其他因子将在后续添加
}

# 默认因子权重
DEFAULT_FACTOR_WEIGHTS = {
    'limit_quality': 12.0,
    'seal_ratio': 10.0,
    'seal_flow_ratio': 12.0,
    'volume_ratio': 8.0,
    'turnover_rate': 8.0,
    'dragon_tiger': 12.0,
    'money_flow': 10.0,
    'amount_rank': 8.0,
    'sector_heat': 8.0,
    'bias_ma3': 6.0,
    'sentiment': 6.0,
    'sector_linkage': 10.0,
}


def create_factor_engine(config_path: str = None) -> FactorEngine:
    """创建因子计算引擎"""
    return FactorEngine(
        factor_classes=FACTOR_CLASSES,
        weights=DEFAULT_FACTOR_WEIGHTS,
        config_path=config_path
    )


def get_factor_list() -> list:
    """获取已实现的因子列表"""
    return list(FACTOR_CLASSES.keys())
