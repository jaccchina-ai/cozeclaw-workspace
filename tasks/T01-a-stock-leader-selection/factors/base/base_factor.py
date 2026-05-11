"""
T01 选股系统 - 因子基类

定义所有因子的统一接口和基础功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple, Any, Optional
import yaml
import logging


logger = logging.getLogger(__name__)


@dataclass
class FactorResult:
    """因子计算结果"""
    factor_name: str
    score: float
    raw_values: Dict[str, Any]
    is_valid: bool = True
    error_message: str = ""


class BaseFactor(ABC):
    """所有因子的基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._validate_config()
        self._init_default_config()
    
    def _init_default_config(self):
        """初始化默认配置"""
        pass
    
    def _validate_config(self):
        """验证配置有效性"""
        pass
    
    @abstractmethod
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        """
        计算因子得分
        
        Args:
            data: 计算所需的原始数据
            
        Returns:
            FactorResult: 因子计算结果
        """
        pass
    
    def pre_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """数据预处理"""
        return data
    
    def post_process(self, result: FactorResult) -> FactorResult:
        """结果后处理"""
        # 确保分数在合理范围内
        result.score = max(0, min(10, result.score))
        return result
    
    def _load_config_from_file(self, config_path: str) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
            return {}
