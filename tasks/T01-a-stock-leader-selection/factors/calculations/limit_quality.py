"""
T01 选股系统 - 涨停质量因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class LimitQualityFactor(BaseFactor):
    """涨停质量因子"""
    
    def _init_default_config(self):
        """初始化默认配置"""
        self.config.setdefault('first_limit_time_weights', {
            '10:00': 10,
            '11:00': 8,
            '13:30': 5,
            '14:30': 3,
            '23:59': 1
        })
        
        self.config.setdefault('limit_times_weights', {
            0: 10,
            1: 7,
            2: 4,
            3: -1
        })
        
        self.config.setdefault('consecutive_limit_weights', {
            1: 6,
            2: 10,
            3: 8,
            4: 5,
            5: -1
        })
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        """计算涨停质量因子得分"""
        try:
            first_limit_time = data.get('first_limit_time', '')
            limit_times = int(data.get('limit_times', 0))
            consecutive_limit = int(data.get('consecutive_limit', 1))
            
            raw_values = {
                'first_limit_time': first_limit_time,
                'limit_times': limit_times,
                'consecutive_limit': consecutive_limit
            }
            
            # 首次涨停时间评分
            time_score = self._calculate_time_score(first_limit_time)
            
            # 炸板次数评分
            times_score = self._calculate_limit_times_score(limit_times)
            if times_score < 0:
                return FactorResult(
                    factor_name='limit_quality',
                    score=0,
                    raw_values=raw_values,
                    is_valid=False,
                    error_message='炸板次数过多'
                )
            
            # 连板数评分
            board_score = self._calculate_consecutive_limit_score(consecutive_limit)
            if board_score < 0:
                return FactorResult(
                    factor_name='limit_quality',
                    score=0,
                    raw_values=raw_values,
                    is_valid=False,
                    error_message='连板数不符合要求'
                )
            
            # 综合得分
            score = (time_score + times_score + board_score) / 3
            
            return FactorResult(
                factor_name='limit_quality',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f"计算涨停质量因子失败: {e}")
            return FactorResult(
                factor_name='limit_quality',
                score=0,
                raw_values={},
                is_valid=False,
                error_message=str(e)
            )
    
    def _calculate_time_score(self, first_limit_time: str) -> float:
        """计算首次涨停时间得分"""
        if not first_limit_time:
            return 5.0
        
        try:
            # 处理时间格式，支持 HH:MM:SS 或 HH:MM
            if ':' in first_limit_time:
                parts = first_limit_time.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                hour_min = hour * 100 + minute
            else:
                hour_min = int(first_limit_time)
            
            # 找到对应的评分阈值
            time_weights = sorted(
                self.config['first_limit_time_weights'].items(),
                key=lambda x: int(x[0].replace(':', ''))
            )
            
            for time_threshold, score in time_weights:
                threshold_min = int(time_threshold.replace(':', ''))
                if hour_min <= threshold_min:
                    return score
            
            return 1.0
            
        except Exception as e:
            logger.warning(f"解析涨停时间失败: {e}")
            return 5.0
    
    def _calculate_limit_times_score(self, limit_times: int) -> float:
        """计算炸板次数得分"""
        max_limit_times = max(self.config['limit_times_weights'].keys())
        return self.config['limit_times_weights'].get(min(limit_times, max_limit_times), -1)
    
    def _calculate_consecutive_limit_score(self, consecutive_limit: int) -> float:
        """计算连板数得分"""
        max_consecutive = max(self.config['consecutive_limit_weights'].keys())
        return self.config['consecutive_limit_weights'].get(min(consecutive_limit, max_consecutive), -1)
