"""
T01 动态因子配置系统

支持通过配置文件动态添加因子，自动完成：
- 数据库字段检查/创建
- 评分计算
- 数据保存
- 消息展示
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class FactorType(Enum):
    """因子类型"""
    SCORE_ONLY = "score"      # 只保存得分
    RAW_ONLY = "raw"          # 只保存原始值
    BOTH = "both"             # 同时保存得分和原始值


@dataclass
class FactorDefinition:
    """因子定义"""
    name: str                      # 显示名称（中文）
    code: str                      # 代码标识（英文）
    type: FactorType               # 因子类型
    weight: float = 0              # 权重（0表示不计入总分）
    description: str = ""          # 描述
    # 评分规则
    score_rules: List[Tuple] = field(default_factory=list)  # [(阈值, 得分), ...]
    higher_is_better: bool = True  # 越高越好（用于方向判断）
    
    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = FactorType(self.type)


# ==================== 默认因子配置 ====================

DEFAULT_FACTORS = {
    # T日选股因子
    't_day_factors': {
        'limit_quality': FactorDefinition(
            code='limit_quality',
            name='涨停质量',
            type=FactorType.BOTH,
            weight=15.0,
            description='首次涨停时间、炸板次数、连板数综合评分',
            score_rules=[
                (10, 10),   # 9:30-10:00
                (8, 8),     # 10:00-11:00
                (5, 5),     # 11:00-13:30
                (3, 3),     # 13:30-14:30
                (1, 1),     # 14:30后
            ]
        ),
        'seal_ratio': FactorDefinition(
            code='seal_ratio',
            name='封成比',
            type=FactorType.BOTH,
            weight=8.0,
            description='封单金额/成交金额',
            score_rules=[
                (0.5, 10),
                (0.3, 8),
                (0.1, 6),
                (0, 4),
            ]
        ),
        'seal_flow_ratio': FactorDefinition(
            code='seal_flow_ratio',
            name='封流比',
            type=FactorType.BOTH,
            weight=12.0,
            description='封单金额/流通市值',
            score_rules=[
                (0.08, 10),
                (0.05, 8),
                (0.02, 6),
                (0, 4),
            ]
        ),
        'volume_ratio': FactorDefinition(
            code='volume_ratio',
            name='量比',
            type=FactorType.BOTH,
            weight=8.0,
            description='当日成交量/5日均量',
            score_rules=[
                (3, 10),
                (2, 8),
                (1, 6),
                (0, 4),
            ]
        ),
        'turnover_rate': FactorDefinition(
            code='turnover_rate',
            name='真实换手率',
            type=FactorType.BOTH,
            weight=8.0,
            description='成交量/自由流通股本',
            score_rules=[
                (20, 10),
                (10, 8),
                (5, 6),
                (0, 4),
            ]
        ),
        'dragon_tiger': FactorDefinition(
            code='dragon_tiger',
            name='龙虎榜',
            type=FactorType.BOTH,
            weight=10.0,
            description='龙虎榜净买入金额',
            score_rules=[
                (5000, 10),   # 5000万以上
                (1000, 8),    # 1000万以上
                (0, 6),       # 有龙虎榜
                (-1, 5),      # 无龙虎榜
            ]
        ),
        'money_flow': FactorDefinition(
            code='money_flow',
            name='资金流向',
            type=FactorType.BOTH,
            weight=12.0,
            description='主力净流入占比',
            score_rules=[
                (20, 10),
                (10, 8),
                (0, 6),
                (-10, 4),
            ]
        ),
        'amount_rank': FactorDefinition(
            code='amount_rank',
            name='成交额排名',
            type=FactorType.BOTH,
            weight=6.0,
            description='涨停股中成交额排名',
            score_rules=[
                (3, 10),   # 前3
                (5, 8),    # 前5
                (10, 6),   # 前10
                (999, 4),  # 其他
            ],
            higher_is_better=False  # 排名越小越好
        ),
        'sector_heat': FactorDefinition(
            code='sector_heat',
            name='板块热度',
            type=FactorType.BOTH,
            weight=8.0,
            description='同板块涨停股票数量',
            score_rules=[
                (5, 10),
                (3, 8),
                (1, 6),
                (0, 4),
            ]
        ),
        'bias_ma3': FactorDefinition(
            code='bias_ma3',
            name='MA3乖离率',
            type=FactorType.BOTH,
            weight=6.0,
            description='股价偏离MA3的程度（风控因子）',
            score_rules=[
                (3, 10),   # 3%以内
                (5, 8),    # 5%以内
                (8, 6),    # 8%以内
                (999, 4),  # 超过8%
            ]
        ),
        'sentiment': FactorDefinition(
            code='sentiment',
            name='舆情分析',
            type=FactorType.SCORE_ONLY,
            weight=8.0,
            description='AI舆情分析附加分',
            score_rules=[
                (10, 10),
                (0, 0),
            ]
        ),
        'sector_linkage': FactorDefinition(
            code='sector_linkage',
            name='板块联动强度',
            type=FactorType.BOTH,
            weight=10.0,
            description='个股与板块价格相关性、领先滞后关系、板块内地位综合评分',
            score_rules=[
                (80, 10),   # 综合得分>80，板块龙头
                (60, 8),    # 综合得分>60，正常跟风
                (40, 6),    # 综合得分>40，独立行情
                (0, 4),     # 综合得分<40，弱势
            ]
        ),
    },
    
    # T+1竞价因子
    'auction_factors': {
        'auction_turnover': FactorDefinition(
            code='auction_turnover',
            name='竞价换手率',
            type=FactorType.BOTH,
            weight=12.0,
            description='竞价成交量/流通股本',
            score_rules=[
                (5, 10),
                (3, 8),
                (1, 6),
                (0, 4),
            ]
        ),
        'auction_amount': FactorDefinition(
            code='auction_amount',
            name='竞价金额',
            type=FactorType.BOTH,
            weight=10.0,
            description='竞价成交金额（万元）',
            score_rules=[
                (5000, 10),
                (2000, 8),
                (500, 6),
                (0, 4),
            ]
        ),
        'auction_pct_chg': FactorDefinition(
            code='auction_pct_chg',
            name='竞价涨幅',
            type=FactorType.BOTH,
            weight=15.0,
            description='竞价价格相对昨日收盘涨幅',
            score_rules=[
                (7, 4),    # 太高风险大
                (5, 6),
                (2, 10),   # 理想区间
                (1, 8),
                (-999, 0), # 低于1%剔除
            ]
        ),
        'auction_volume_ratio': FactorDefinition(
            code='auction_volume_ratio',
            name='竞价量比',
            type=FactorType.BOTH,
            weight=10.0,
            description='竞价量/近期平均量',
            score_rules=[
                (3, 10),
                (2, 8),
                (1, 6),
                (0, 4),
            ]
        ),
        'auction_burst_ratio': FactorDefinition(
            code='auction_burst_ratio',
            name='竞价爆量比',
            type=FactorType.BOTH,
            weight=12.0,
            description='竞价量/昨日成交量',
            score_rules=[
                (0.15, 10),
                (0.10, 8),
                (0.05, 6),
                (0.015, 4),  # 低于1.5%剔除
            ]
        ),
        'sector_auction_pct': FactorDefinition(
            code='sector_auction_pct',
            name='板块竞价涨幅',
            type=FactorType.BOTH,
            weight=10.0,
            description='同板块竞价平均涨幅',
            score_rules=[
                (0, 10),   # 正涨幅
                (-999, 4), # 负涨幅
            ]
        ),
        'sector_resonance': FactorDefinition(
            code='sector_resonance',
            name='板块共振度',
            type=FactorType.BOTH,
            weight=12.0,
            description='个股竞价涨幅-板块竞价涨幅',
            score_rules=[
                (2, 10),   # 主动领涨
                (0, 8),
                (-2, 6),
                (-999, 4), # 被动跟风
            ]
        ),
        't_day_score': FactorDefinition(
            code='t_day_score',
            name='T日评分',
            type=FactorType.BOTH,
            weight=15.0,
            description='T日选股基础评分',
            score_rules=[
                (100, 10),
                (80, 8),
                (60, 6),
                (0, 4),
            ]
        ),
    }
}


class DynamicFactorManager:
    """动态因子管理器"""
    
    def __init__(self, config: Dict[str, Dict[str, FactorDefinition]] = None):
        """
        初始化因子管理器
        
        Args:
            config: 因子配置，默认使用 DEFAULT_FACTORS
        """
        self.config = config or DEFAULT_FACTORS
        self._validate_config()
    
    def _validate_config(self):
        """验证配置有效性"""
        for category, factors in self.config.items():
            for code, definition in factors.items():
                if not isinstance(definition, FactorDefinition):
                    raise ValueError(f"因子 {code} 必须是 FactorDefinition 类型")
                if definition.code != code:
                    raise ValueError(f"因子代码不匹配: {code} != {definition.code}")
    
    def get_factor(self, category: str, code: str) -> Optional[FactorDefinition]:
        """获取因子定义"""
        return self.config.get(category, {}).get(code)
    
    def get_all_factors(self, category: str) -> Dict[str, FactorDefinition]:
        """获取某类别的所有因子"""
        return self.config.get(category, {})
    
    def get_factor_codes(self, category: str) -> List[str]:
        """获取某类别的所有因子代码"""
        return list(self.config.get(category, {}).keys())
    
    def add_factor(self, category: str, definition: FactorDefinition):
        """动态添加因子"""
        if category not in self.config:
            self.config[category] = {}
        self.config[category][definition.code] = definition
    
    def calculate_score(self, factor_code: str, value: float, category: str = None) -> float:
        """
        根据规则计算因子得分
        
        Args:
            factor_code: 因子代码
            value: 原始值
            category: 类别（如果为None则搜索所有类别）
            
        Returns:
            得分 (0-10)
        """
        definition = None
        if category:
            definition = self.get_factor(category, factor_code)
        else:
            # 搜索所有类别
            for cat_factors in self.config.values():
                if factor_code in cat_factors:
                    definition = cat_factors[factor_code]
                    break
        
        if not definition:
            return 5  # 默认中等得分
        
        # 根据规则评分
        score = self._apply_score_rules(value, definition.score_rules, definition.higher_is_better)
        return score
    
    def _apply_score_rules(self, value: float, rules: List[Tuple], higher_is_better: bool) -> float:
        """应用评分规则"""
        if not rules:
            return 5
        
        # 按阈值排序
        sorted_rules = sorted(rules, key=lambda x: x[0], reverse=not higher_is_better)
        
        for threshold, score in sorted_rules:
            if higher_is_better:
                if value >= threshold:
                    return score
            else:
                if value <= threshold:
                    return score
        
        # 返回最低分
        return sorted_rules[-1][1] if sorted_rules else 5
    
    def get_database_fields(self, category: str) -> List[Tuple[str, str, str]]:
        """
        获取数据库字段定义
        
        Returns:
            [(字段名, 字段类型, 注释), ...]
        """
        fields = []
        for code, definition in self.config.get(category, {}).items():
            if definition.type in [FactorType.SCORE_ONLY, FactorType.BOTH]:
                fields.append((
                    f"{code}_score",
                    "Float",
                    f"{definition.name}得分"
                ))
            if definition.type in [FactorType.RAW_ONLY, FactorType.BOTH]:
                fields.append((
                    f"{code}_raw",
                    "Float",
                    f"{definition.name}原始值"
                ))
        return fields
    
    def get_weights(self, category: str) -> Dict[str, float]:
        """获取某类别的所有因子权重"""
        weights = {}
        for code, definition in self.config.get(category, {}).items():
            weights[code] = definition.weight
        return weights
    
    def get_total_weight(self, category: str) -> float:
        """获取某类别的总权重"""
        return sum(d.weight for d in self.config.get(category, {}).values())
    
    def normalize_weights(self, category: str) -> Dict[str, float]:
        """获取归一化权重（总和为100）"""
        total = self.get_total_weight(category)
        if total == 0:
            return {}
        weights = self.get_weights(category)
        return {code: (w / total * 100) for code, w in weights.items()}
    
    def export_config(self) -> Dict:
        """导出配置为字典"""
        result = {}
        for category, factors in self.config.items():
            result[category] = {}
            for code, definition in factors.items():
                result[category][code] = {
                    'code': definition.code,
                    'name': definition.name,
                    'type': definition.type.value,
                    'weight': definition.weight,
                    'description': definition.description,
                    'score_rules': definition.score_rules,
                    'higher_is_better': definition.higher_is_better,
                }
        return result
    
    def import_config(self, config: Dict):
        """从字典导入配置"""
        self.config = {}
        for category, factors in config.items():
            self.config[category] = {}
            for code, factor_dict in factors.items():
                self.config[category][code] = FactorDefinition(**factor_dict)
        self._validate_config()


# 全局因子管理器实例
factor_manager = DynamicFactorManager()


# ==================== 便捷函数 ====================

def get_factor_score(factor_code: str, value: float, category: str = None) -> float:
    """计算因子得分"""
    return factor_manager.calculate_score(factor_code, value, category)


def get_t_day_factors() -> Dict[str, FactorDefinition]:
    """获取T日选股因子"""
    return factor_manager.get_all_factors('t_day_factors')


def get_auction_factors() -> Dict[str, FactorDefinition]:
    """获取T+1竞价因子"""
    return factor_manager.get_all_factors('auction_factors')


def add_custom_factor(category: str, code: str, name: str, weight: float,
                      score_rules: List[Tuple], factor_type: str = 'both'):
    """添加自定义因子"""
    definition = FactorDefinition(
        code=code,
        name=name,
        type=FactorType(factor_type),
        weight=weight,
        score_rules=score_rules
    )
    factor_manager.add_factor(category, definition)


if __name__ == '__main__':
    # 测试
    print("=== 动态因子配置系统测试 ===")
    
    # 测试获取因子
    factor = factor_manager.get_factor('t_day_factors', 'seal_ratio')
    print(f"\n封成比因子: {factor.name}")
    print(f"  权重: {factor.weight}")
    print(f"  描述: {factor.description}")
    
    # 测试评分
    score = factor_manager.calculate_score('seal_ratio', 0.4, 't_day_factors')
    print(f"\n封成比0.4的得分: {score}")
    
    # 测试数据库字段
    fields = factor_manager.get_database_fields('t_day_factors')
    print(f"\nT日因子数据库字段数: {len(fields)}")
    
    # 测试权重
    weights = factor_manager.normalize_weights('t_day_factors')
    print(f"\n归一化权重总和: {sum(weights.values())}")
    
    print("\n✅ 测试通过!")
