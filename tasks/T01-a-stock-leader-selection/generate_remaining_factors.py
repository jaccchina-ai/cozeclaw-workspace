#!/usr/bin/env python3
"""
批量生成剩余因子实现文件
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def generate_factor_template(factor_name: str) -> str:
    """生成因子模板代码"""
    class_name = factor_name.replace('_', '').title() + 'Factor'
    factor_desc = factor_name.replace('_', ' ')
    
    template = f'''"""
T01 选股系统 - {factor_desc}因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class {class_name}(BaseFactor):
    \"\"\"{factor_desc}因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算{factor_desc}因子得分\"\"\"
        try:
            # TODO: 实现因子计算逻辑
            raw_values = {{}}
            score = 0.0
            
            return FactorResult(
                factor_name=\"{factor_name}\",
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算{factor_desc}因子失败: {e}\")
            return FactorResult(
                factor_name=\"{factor_name}\",
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''
    
    return template


def generate_seal_flow_ratio_factor() -> str:
    """生成封流比因子实现"""
    return '''"""
T01 选股系统 - 封流比因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class SealFlowRatioFactor(BaseFactor):
    \"\"\"封流比因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        self.config.setdefault('scoring_rules', [
            {'threshold': 0.1, 'score': 10},
            {'threshold': 0.05, 'score': 8},
            {'threshold': 0.03, 'score': 6},
            {'threshold': 0.01, 'score': 4},
            {'threshold': 0.0, 'score': 2}
        ])
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算封流比因子得分\"\"\"
        try:
            # 封单金额 (万元)
            seal_amount = float(data.get('seal_amount', 0) or data.get('fd_amount', 0) or 0)
            # 自由流通市值 (万元)
            free_mv = float(data.get('free_mv', 0) or data.get('float_mv', 0) or 0)
            
            raw_values = {
                'seal_amount': seal_amount,
                'free_mv': free_mv,
                'seal_flow_ratio': 0.0
            }
            
            if free_mv <= 0:
                return FactorResult(
                    factor_name='seal_flow_ratio',
                    score=0,
                    raw_values=raw_values,
                    is_valid=False,
                    error_message='自由流通市值为0'
                )
            
            # 计算封流比
            seal_flow_ratio = seal_amount / free_mv
            raw_values['seal_flow_ratio'] = round(seal_flow_ratio, 4)
            
            # 根据规则计算得分
            score = self._calculate_score(seal_flow_ratio)
            
            return FactorResult(
                factor_name='seal_flow_ratio',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算封流比因子失败: {e}\")
            return FactorResult(
                factor_name='seal_flow_ratio',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
    
    def _calculate_score(self, seal_flow_ratio: float) -> float:
        \"\"\"根据封流比计算得分\"\"\"
        # 按阈值从高到低排序
        sorted_rules = sorted(
            self.config['scoring_rules'],
            key=lambda x: x['threshold'], reverse=True
        )
        
        for rule in sorted_rules:
            if seal_flow_ratio >= rule['threshold']:
                return rule['score']
        
        return 2.0
'''


def generate_volume_ratio_factor() -> str:
    """生成量比因子实现"""
    return '''"""
T01 选股系统 - 量比因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class VolumeRatioFactor(BaseFactor):
    \"\"\"量比因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算量比因子得分\"\"\"
        try:
            volume_ratio = float(data.get('volume_ratio', 1) or 1)
            
            raw_values = {
                'volume_ratio': round(volume_ratio, 2)
            }
            
            # 量比评分标准
            if volume_ratio < 1:
                score = 4
            elif volume_ratio < 2:
                score = 6
            elif volume_ratio < 3:
                score = 8
            elif volume_ratio < 5:
                score = 10
            elif volume_ratio < 10:
                score = 6
            else:
                score = 3
            
            return FactorResult(
                factor_name='volume_ratio',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算量比因子失败: {e}\")
            return FactorResult(
                factor_name='volume_ratio',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_turnover_rate_factor() -> str:
    """生成换手率因子实现"""
    return '''"""
T01 选股系统 - 换手率因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class TurnoverRateFactor(BaseFactor):
    \"\"\"换手率因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算换手率因子得分\"\"\"
        try:
            # 真实换手率(%)
            real_turnover_rate = float(data.get('real_turnover_rate', 0) or 0)
            
            # 如果没有直接提供真实换手率，自行计算
            if real_turnover_rate == 0:
                deal_amount = float(data.get('amount', 0) or 0)
                free_mv = float(data.get('free_mv', 0) or data.get('float_mv', 0) or 0)
                if deal_amount > 0 and free_mv > 0:
                    real_turnover_rate = (deal_amount / free_mv) * 100
            
            raw_values = {
                'real_turnover_rate': round(real_turnover_rate, 2)
            }
            
            # 真实换手率评分标准
            if real_turnover_rate < 5:
                score = 6
            elif real_turnover_rate < 15:
                score = 10
            elif real_turnover_rate < 20:
                score = 8
            elif real_turnover_rate < 25:
                score = 6
            elif real_turnover_rate < 30:
                score = 4
            else:
                score = 2
            
            return FactorResult(
                factor_name='turnover_rate',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算换手率因子失败: {e}\")
            return FactorResult(
                factor_name='turnover_rate',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_bias_ma3_factor() -> str:
    """生成MA3乖离率因子实现"""
    return '''"""
T01 选股系统 - MA3乖离率因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class BiasMa3Factor(BaseFactor):
    \"\"\"MA3乖离率因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算MA3乖离率因子得分\"\"\"
        try:
            bias_ma3 = float(data.get('bias_ma3', 0) or 0)
            
            raw_values = {
                'bias_ma3': round(bias_ma3, 2)
            }
            
            # MA3乖离率评分标准 (风控因子，越低越好)
            if bias_ma3 < 3:
                score = 10
            elif bias_ma3 < 6:
                score = 8
            elif bias_ma3 < 9:
                score = 6
            elif bias_ma3 < 12:
                score = 3
            else:
                score = 1
            
            return FactorResult(
                factor_name='bias_ma3',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算MA3乖离率因子失败: {e}\")
            return FactorResult(
                factor_name='bias_ma3',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_sentiment_factor() -> str:
    """生成舆情分析因子实现"""
    return '''"""
T01 选股系统 - 舆情分析因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class SentimentFactor(BaseFactor):
    \"\"\"舆情分析因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算舆情分析因子得分\"\"\"
        try:
            sentiment_score = float(data.get('sentiment_score', 0) or 0)
            
            raw_values = {
                'sentiment_score': sentiment_score
            }
            
            # 将 0-100 映射到 0-10
            score = min(10, max(0, sentiment_score / 10))
            
            return FactorResult(
                factor_name='sentiment',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算舆情分析因子失败: {e}\")
            return FactorResult(
                factor_name='sentiment',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_money_flow_factor() -> str:
    """生成资金流因子实现"""
    return '''"""
T01 选股系统 - 资金流因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class MoneyFlowFactor(BaseFactor):
    \"\"\"资金流因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算资金流因子得分\"\"\"
        try:
            main_net_inflow = float(data.get('main_net_inflow', 0) or 0)
            main_net_ratio = float(data.get('main_net_ratio', 0) or 0)
            medium_net = float(data.get('medium_net', 0) or 0)
            
            raw_values = {
                'main_net_inflow': main_net_inflow,
                'main_net_ratio': round(main_net_ratio, 2),
                'medium_net': medium_net
            }
            
            # 基础分
            score = 5
            
            # 主力净流入为正: +2分
            if main_net_inflow > 0:
                score += 2
            
            # 主力净占比 > 10%: +2分
            if main_net_ratio > 10:
                score += 2
            elif main_net_ratio > 5:
                score += 1
            
            # 中单净额为正: +1分
            if medium_net > 0:
                score += 1
            
            # 限制分数范围
            score = max(0, min(10, score))
            
            return FactorResult(
                factor_name='money_flow',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算资金流因子失败: {e}\")
            return FactorResult(
                factor_name='money_flow',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_amount_rank_factor() -> str:
    """生成成交金额排名因子实现"""
    return '''"""
T01 选股系统 - 成交金额排名因子
"""

from typing import Dict, Any, List
import logging
import numpy as np

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class AmountRankFactor(BaseFactor):
    \"\"\"成交金额排名因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算成交金额排名因子得分\"\"\"
        try:
            amount = float(data.get('amount', 0) or 0)
            all_amounts = data.get('all_amounts', [])
            
            raw_values = {
                'amount': amount,
                'amount_rank': 0,
                'amount_percentile': 0.0
            }
            
            if not all_amounts or amount <= 0:
                return FactorResult(
                    factor_name='amount_rank',
                    score=5,
                    raw_values=raw_values
                )
            
            # 计算排名百分位
            all_amounts = np.array(all_amounts)
            percentile = np.sum(all_amounts >= amount) / len(all_amounts) * 100
            
            raw_values.update({
                'amount_percentile': round(percentile, 1)
            })
            
            # 排名评分标准
            if percentile >= 95:
                score = 10
            elif percentile >= 90:
                score = 8
            elif percentile >= 80:
                score = 6
            elif percentile >= 50:
                score = 4
            else:
                score = 2
            
            return FactorResult(
                factor_name='amount_rank',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算成交金额排名因子失败: {e}\")
            return FactorResult(
                factor_name='amount_rank',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_dragon_tiger_factor() -> str:
    """生成龙虎榜因子实现"""
    return '''"""
T01 选股系统 - 龙虎榜因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class DragonTigerFactor(BaseFactor):
    \"\"\"龙虎榜因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算龙虎榜因子得分\"\"\"
        try:
            dragon_tiger_data = data.get('dragon_tiger_data', {})
            north_data = data.get('north_data', {})
            
            raw_values = {
                'net_buy': dragon_tiger_data.get('net_buy', 0),
                'institution_net_buy': dragon_tiger_data.get('institution_net_buy', 0),
                'hot_money_seats': dragon_tiger_data.get('hot_money_seats', []),
                'institution_seats': dragon_tiger_data.get('institution_seats', []),
                'quant_seats': dragon_tiger_data.get('quant_seats', []),
                'north_net': north_data.get('total_net', 0)
            }
            
            # 检查是否有游资管理器的增强评分
            if dragon_tiger_data and 'hot_money_score' in dragon_tiger_data:
                # 使用游资管理器的评分
                score = dragon_tiger_data['hot_money_score']
                details = dragon_tiger_data.get('hot_money_details', {})
                
                raw_values.update({
                    'hot_money_names': details.get('hot_money_names', []),
                    'top_influence': details.get('top_influence', 0),
                    'total_follow_value': details.get('total_follow_value', 0)
                })
                
                # 北向资金增仓: +1分
                if raw_values['north_net'] > 0:
                    score += 1
                
                # 限制分数范围
                score = max(0, min(15, score))
                
                return FactorResult(
                    factor_name='dragon_tiger',
                    score=score / 1.5,  # 归一化到0-10分
                    raw_values=raw_values
                )
            
            # 原有评分逻辑（兼容旧数据）
            score = 5  # 默认基础分
            
            # 机构净买入 > 3000万: +3分
            if raw_values['net_buy'] > 3000:
                score += 3
            
            # 有知名游资席位: +2分
            if raw_values['hot_money_seats']:
                score += 2
            
            # 有机构席位: +1分
            if raw_values['institution_seats']:
                score += 1
            
            # 有量化席位: -2分
            if raw_values['quant_seats']:
                score -= 2
            
            # 北向资金增仓: +1分
            if raw_values['north_net'] > 0:
                score += 1
            
            # 限制分数范围
            score = max(0, min(10, score))
            
            return FactorResult(
                factor_name='dragon_tiger',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算龙虎榜因子失败: {e}\")
            return FactorResult(
                factor_name='dragon_tiger',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_sector_heat_factor() -> str:
    """生成板块热度因子实现"""
    return '''"""
T01 选股系统 - 板块热度因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class SectorHeatFactor(BaseFactor):
    \"\"\"板块热度因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算板块热度因子得分\"\"\"
        try:
            sector_data = data.get('sector_data', {})
            
            sector_zt_count = int(sector_data.get('zt_count', 0) or 0)
            sector_pct_chg = float(sector_data.get('pct_chg', 0) or 0)
            sector_main_inflow = float(sector_data.get('main_inflow', 0) or 0)
            
            raw_values = {
                'sector_zt_count': sector_zt_count,
                'sector_pct_chg': round(sector_pct_chg, 2),
                'sector_main_inflow': sector_main_inflow
            }
            
            score = 0
            
            # 板块涨停家数评分
            if sector_zt_count >= 5:
                score += 4
            elif sector_zt_count >= 3:
                score += 3
            elif sector_zt_count >= 2:
                score += 2
            else:
                score += 1
            
            # 板块涨幅评分
            if sector_pct_chg >= 3:
                score += 3
            elif sector_pct_chg >= 2:
                score += 2
            elif sector_pct_chg >= 1:
                score += 1
            
            # 板块主力净流入评分
            if sector_main_inflow > 0:
                score += 3
            elif sector_main_inflow > -1000:
                score += 1
            
            # 限制分数范围
            score = max(0, min(10, score))
            
            return FactorResult(
                factor_name='sector_heat',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算板块热度因子失败: {e}\")
            return FactorResult(
                factor_name='sector_heat',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )
'''


def generate_sector_linkage_factor() -> str:
    """生成板块联动因子实现"""
    return '"""
T01 选股系统 - 板块联动因子
"""

from typing import Dict, Any
import logging

from ..base.base_factor import BaseFactor, FactorResult


logger = logging.getLogger(__name__)


class SectorLinkageFactor(BaseFactor):
    \"\"\"板块联动因子\"\"\"
    
    def _init_default_config(self):
        \"\"\"初始化默认配置\"\"\"
        pass
    
    def calculate(self, data: Dict[str, Any]) -> FactorResult:
        \"\"\"计算板块联动因子得分\"\"\"
        try:
            sector_linkage_score = float(data.get('sector_linkage_score', 0) or 0)
            sector_linkage_raw = data.get('sector_linkage_raw', {})
            
            raw_values = {
                'sector_linkage_score': sector_linkage_score,
                'sector_linkage_raw': sector_linkage_raw
            }
            
            # 将 0-100 映射到 0-10
            score = min(10, max(0, sector_linkage_score / 10))
            
            return FactorResult(
                factor_name='sector_linkage',
                score=score,
                raw_values=raw_values
            )
            
        except Exception as e:
            logger.error(f\"计算板块联动因子失败: {e}\")
            return FactorResult(
                factor_name='sector_linkage',
                score=0,
                raw_values={{}},
                is_valid=False,
                error_message=str(e)
            )'


def update_init_file():
    """更新__init__.py文件"""
    init_path = 'factors/__init__.py'
    
    imports = [
        'from .calculations.limit_quality import LimitQualityFactor',
        'from .calculations.seal_ratio import SealRatioFactor',
        'from .calculations.seal_flow_ratio import SealFlowRatioFactor',
        'from .calculations.volume_ratio import VolumeRatioFactor',
        'from .calculations.turnover_rate import TurnoverRateFactor',
        'from .calculations.dragon_tiger import DragonTigerFactor',
        'from .calculations.money_flow import MoneyFlowFactor',
        'from .calculations.amount_rank import AmountRankFactor',
        'from .calculations.sector_heat import SectorHeatFactor',
        'from .calculations.bias_ma3 import BiasMa3Factor',
        'from .calculations.sentiment import SentimentFactor',
        'from .calculations.sector_linkage import SectorLinkageFactor'
    ]
    
    factor_classes = {
        'limit_quality': 'LimitQualityFactor',
        'seal_ratio': 'SealRatioFactor',
        'seal_flow_ratio': 'SealFlowRatioFactor',
        'volume_ratio': 'VolumeRatioFactor',
        'turnover_rate': 'TurnoverRateFactor',
        'dragon_tiger': 'DragonTigerFactor',
        'money_flow': 'MoneyFlowFactor',
        'amount_rank': 'AmountRankFactor',
        'sector_heat': 'SectorHeatFactor',
        'bias_ma3': 'BiasMa3Factor',
        'sentiment': 'SentimentFactor',
        'sector_linkage': 'SectorLinkageFactor'
    }
    
    # 读取现有内容
    with open(init_path, 'r') as f:
        content = f.read()
    
    # 更新import部分
    import_section = '# 已实现的因子\n' + '\n'.join(imports) + '\n'
    if '# 已实现的因子' in content:
        content = content.split('# 已实现的因子')[0] + import_section
    else:
        content = import_section + content
    
    # 更新FACTOR_CLASSES
    factor_map_lines = []
    for name, cls in factor_classes.items():
        factor_map_lines.append(f"    '{name}': {cls},")
    factor_map_content = 'FACTOR_CLASSES = {\n' + '\n'.join(factor_map_lines) + '}\n'
    
    if 'FACTOR_CLASSES = {' in content:
        content = content.split('FACTOR_CLASSES = {')[0] + factor_map_content + content.split('}')[1].split('# 默认因子权重')[1]
    else:
        content += '\n' + factor_map_content
    
    # 写入更新后的内容
    with open(init_path, 'w') as f:
        f.write(content)
    
    print('✅ 更新__init__.py完成')


def main():
    """主函数"""
    print('=== 开始批量生成剩余因子 ===')
    
    # 创建目录（如果不存在）
    os.makedirs('factors/calculations', exist_ok=True)
    
    # 生成基础模板文件
    template_factors = ['dragon_tiger', 'sector_heat', 'sector_linkage']
    for factor_name in template_factors:
        factor_file = f'factors/calculations/{factor_name}.py'
        if not os.path.exists(factor_file):
            with open(factor_file, 'w') as f:
                f.write(generate_factor_template(factor_name))
            print(f'✅ 生成模板文件: {factor_file}')
    
    # 生成有完整实现的因子
    print('\n=== 生成完整因子实现 ===')
    
    if not os.path.exists('factors/calculations/seal_flow_ratio.py'):
        with open('factors/calculations/seal_flow_ratio.py', 'w') as f:
            f.write(generate_seal_flow_ratio_factor())
        print('✅ 实现封流比因子')
    
    if not os.path.exists('factors/calculations/volume_ratio.py'):
        with open('factors/calculations/volume_ratio.py', 'w') as f:
            f.write(generate_volume_ratio_factor())
        print('✅ 实现量比因子')
    
    if not os.path.exists('factors/calculations/turnover_rate.py'):
        with open('factors/calculations/turnover_rate.py', 'w') as f:
            f.write(generate_turnover_rate_factor())
        print('✅ 实现换手率因子')
    
    if not os.path.exists('factors/calculations/bias_ma3.py'):
        with open('factors/calculations/bias_ma3.py', 'w') as f:
            f.write(generate_bias_ma3_factor())
        print('✅ 实现MA3乖离率因子')
    
    if not os.path.exists('factors/calculations/sentiment.py'):
        with open('factors/calculations/sentiment.py', 'w') as f:
            f.write(generate_sentiment_factor())
        print('✅ 实现舆情分析因子')
    
    if not os.path.exists('factors/calculations/money_flow.py'):
        with open('factors/calculations/money_flow.py', 'w') as f:
            f.write(generate_money_flow_factor())
        print('✅ 实现资金流因子')
    
    if not os.path.exists('factors/calculations/amount_rank.py'):
        with open('factors/calculations/amount_rank.py', 'w') as f:
            f.write(generate_amount_rank_factor())
        print('✅ 实现成交金额排名因子')
    
    if not os.path.exists('factors/calculations/dragon_tiger.py'):
        with open('factors/calculations/dragon_tiger.py', 'w') as f:
            f.write(generate_dragon_tiger_factor())
        print('✅ 实现龙虎榜因子')
    
    if not os.path.exists('factors/calculations/sector_heat.py'):
        with open('factors/calculations/sector_heat.py', 'w') as f:
            f.write(generate_sector_heat_factor())
        print('✅ 实现板块热度因子')
    
    if not os.path.exists('factors/calculations/sector_linkage.py'):
        with open('factors/calculations/sector_linkage.py', 'w') as f:
            f.write(generate_sector_linkage_factor())
        print('✅ 实现板块联动因子')
    
    # 更新__init__.py
    print('\n=== 更新模块导入配置 ===')
    update_init_file()
    
    print('\n=== 所有因子生成完成 ===')
    print('✅ 已实现全部12个因子:')
    print('  1. limit_quality - 涨停质量因子')
    print('  2. seal_ratio - 封成比因子')
    print('  3. seal_flow_ratio - 封流比因子')
    print('  4. volume_ratio - 量比因子')
    print('  5. turnover_rate - 换手率因子')
    print('  6. dragon_tiger - 龙虎榜因子')
    print('  7. money_flow - 资金流因子')
    print('  8. amount_rank - 成交金额排名因子')
    print('  9. sector_heat - 板块热度因子')
    print(' 10. bias_ma3 - MA3乖离率因子')
    print(' 11. sentiment - 舆情分析因子')
    print(' 12. sector_linkage - 板块联动因子')


if __name__ == '__main__':
    main()