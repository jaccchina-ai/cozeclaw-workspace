# 因子计算逻辑重构方案

## 🎯 重构目标

1. **模块化架构**：将因子计算逻辑拆分为独立模块，提高可维护性和可扩展性
2. **可配置化**：实现因子参数的动态配置，支持快速调整策略
3. **可测试性**：为每个因子设计独立测试用例，确保计算准确性
4. **性能优化**：优化计算效率，支持大规模数据快速处理
5. **统一接口**：标准化因子计算接口，便于新因子快速接入

## 🏗️ 重构架构设计

### 1. 核心模块拆分

```
factors/
├── __init__.py
├── base/                  # 基础框架
│   ├── base_factor.py     # 因子基类
│   ├── factor_engine.py   # 因子计算引擎
│   └── data_provider.py   # 数据提供接口
├── calculations/          # 因子计算实现
│   ├── limit_quality.py   # 涨停质量因子
│   ├── seal_ratio.py      # 封成比因子
│   ├── seal_flow_ratio.py # 封流比因子
│   ├── volume_ratio.py    # 量比因子
│   ├── turnover_rate.py   # 换手率因子
│   ├── dragon_tiger.py    # 龙虎榜因子
│   ├── money_flow.py      # 资金流因子
│   ├── amount_rank.py     # 成交金额排名因子
│   ├── sector_heat.py     # 板块热度因子
│   ├── bias_ma3.py        # MA3乖离率因子
│   ├── sentiment.py       # 舆情分析因子
│   └── sector_linkage.py  # 板块联动因子
├── config/                # 配置文件
│   ├── factor_weights.yaml # 因子权重配置
│   └── factor_rules.yaml  # 因子计算规则配置
└── tests/                 # 测试用例
    ├── test_limit_quality.py
    ├── test_seal_ratio.py
    └── ...
```

### 2. 核心类设计

#### 2.1 因子基类 (BaseFactor)
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple, Any

class BaseFactor(ABC):
    """所有因子的基类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._validate_config()
    
    def _validate_config(self):
        """验证配置有效性"""
        pass
    
    @abstractmethod
    def calculate(self, data: Dict) -> Tuple[float, Dict]:
        """
        计算因子得分
        
        Args:
            data: 计算所需的数据
            
        Returns:
            (得分, 原始值字典)
        """
        pass
    
    def pre_process(self, data: Dict) -> Dict:
        """数据预处理"""
        return data
    
    def post_process(self, score: float, raw_values: Dict) -> Tuple[float, Dict]:
        """结果后处理"""
        return score, raw_values
```

#### 2.2 因子计算引擎 (FactorEngine)
```python
from typing import Dict, List, Type
from .base_factor import BaseFactor

class FactorEngine:
    """因子计算引擎"""
    
    def __init__(self, factor_classes: Dict[str, Type[BaseFactor]], 
                 weights: Dict[str, float] = None):
        self.factors = {}
        self.weights = weights or {}
        self._init_factors(factor_classes)
    
    def _init_factors(self, factor_classes: Dict[str, Type[BaseFactor]]):
        """初始化所有因子实例"""
        for factor_name, factor_class in factor_classes.items():
            self.factors[factor_name] = factor_class()
    
    def calculate_single_factor(self, factor_name: str, data: Dict) -> Dict:
        """计算单个因子"""
        if factor_name not in self.factors:
            raise ValueError(f"因子 {factor_name} 不存在")
            
        factor = self.factors[factor_name]
        processed_data = factor.pre_process(data)
        score, raw_values = factor.calculate(processed_data)
        final_score, final_raw = factor.post_process(score, raw_values)
        
        return {
            'score': final_score,
            'raw_values': final_raw,
            'name': factor_name
        }
    
    def calculate_all_factors(self, data: Dict) -> Dict:
        """计算所有因子"""
        results = {}
        for factor_name in self.factors:
            try:
                results[factor_name] = self.calculate_single_factor(factor_name, data)
            except Exception as e:
                results[factor_name] = {
                    'score': 0,
                    'raw_values': {},
                    'name': factor_name,
                    'error': str(e)
                }
        return results
    
    def calculate_total_score(self, factor_results: Dict) -> float:
        """计算加权总分"""
        total_score = 0.0
        total_weight = 0.0
        
        for factor_name, result in factor_results.items():
            if 'error' in result:
                continue
                
            weight = self.weights.get(factor_name, 1.0)
            total_score += result['score'] * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
```

#### 2.3 具体因子实现示例
```python
from .base.base_factor import BaseFactor
from typing import Dict, Tuple

class LimitQualityFactor(BaseFactor):
    """涨停质量因子"""
    
    def _validate_config(self):
        """验证配置"""
        self.first_limit_time_weights = self.config.get(
            'first_limit_time_weights',
            {'10:00': 10, '11:00': 8, '13:30': 5, '14:30': 3, '23:59': 1}
        )
        self.limit_times_weights = self.config.get(
            'limit_times_weights',
            {0: 10, 1: 7, 2: 4, 3: -1}
        )
        self.consecutive_limit_weights = self.config.get(
            'consecutive_limit_weights',
            {1: 6, 2: 10, 3: 8, 4: 5, 5: -1}
        )
    
    def calculate(self, data: Dict) -> Tuple[float, Dict]:
        """计算涨停质量因子得分"""
        first_limit_time = data.get('first_limit_time', '')
        limit_times = data.get('limit_times', 0)
        consecutive_limit = data.get('consecutive_limit', 1)
        
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
            return -1, raw_values
            
        # 连板数评分
        board_score = self._calculate_consecutive_limit_score(consecutive_limit)
        if board_score < 0:
            return -1, raw_values
        
        # 综合得分
        score = (time_score + times_score + board_score) / 3
        
        return score, raw_values
    
    def _calculate_time_score(self, first_limit_time: str) -> float:
        """计算首次涨停时间得分"""
        if not first_limit_time:
            return 5
            
        try:
            hour_min = int(first_limit_time[:2] + first_limit_time[3:5])
            for time_threshold, score in self.first_limit_time_weights.items():
                threshold_min = int(time_threshold[:2] + time_threshold[3:5])
                if hour_min <= threshold_min:
                    return score
            return 1
        except:
            return 5
    
    def _calculate_limit_times_score(self, limit_times: int) -> float:
        """计算炸板次数得分"""
        return self.limit_times_weights.get(min(limit_times, 3), -1)
    
    def _calculate_consecutive_limit_score(self, consecutive_limit: int) -> float:
        """计算连板数得分"""
        return self.consecutive_limit_weights.get(min(consecutive_limit, 5), -1)
```

## 📋 配置文件设计

### 1. 因子权重配置 (factor_weights.yaml)
```yaml
factor_weights:
  limit_quality: 12.0      # 涨停质量
  seal_ratio: 10.0         # 封成比
  seal_flow_ratio: 12.0    # 封流比
  volume_ratio: 8.0        # 量比
  turnover_rate: 8.0       # 真实换手率
  dragon_tiger: 12.0       # 龙虎榜+北向资金
  money_flow: 10.0         # 个股资金结构
  amount_rank: 8.0         # 成交金额排名
  sector_heat: 8.0         # 热点板块
  bias_ma3: 6.0            # MA3乖离率(风控)
  sentiment: 6.0           # 舆情分析(附加)
  sector_linkage: 10.0     # 板块联动强度
```

### 2. 因子计算规则配置 (factor_rules.yaml)
```yaml
limit_quality:
  first_limit_time_weights:
    "10:00": 10
    "11:00": 8
    "13:30": 5
    "14:30": 3
    "23:59": 1
  limit_times_weights:
    0: 10
    1: 7
    2: 4
    3: -1
  consecutive_limit_weights:
    1: 6
    2: 10
    3: 8
    4: 5
    5: -1
    
volume_ratio:
  scoring_rules:
    "< 1": 4
    "< 2": 6
    "< 3": 8
    "< 5": 10
    "< 10": 6
    ">= 10": 3
```

## 🚀 重构实施计划

### 阶段1: 基础框架搭建 (1-2天)

1. 创建项目结构
2. 实现BaseFactor基类
3. 实现FactorEngine引擎
4. 实现配置文件加载机制

### 阶段2: 因子计算逻辑迁移 (3-5天)

1. 逐个迁移现有因子计算逻辑
2. 为每个因子编写单元测试
3. 验证计算结果与原逻辑一致性

### 阶段3: 集成测试与验证 (2-3天)

1. 集成所有因子模块
2. 与现有系统对接测试
3. 性能测试与优化

### 阶段4: 功能增强 (可选)

1. 实现因子IC值实时监控
2. 开发因子正交化模块
3. 增加多模型策略优化支持

## 📊 重构收益分析

### 1. 可维护性提升
- 因子代码分散到独立模块，便于定位和修改
- 统一的配置管理，策略调整无需修改代码
- 完善的测试用例，确保修改不会影响其他功能

### 2. 可扩展性增强
- 标准化的因子接口，新因子接入只需实现基类
- 模块化架构支持并行开发
- 配置化管理支持快速策略迭代

### 3. 性能优化
- 因子计算可以并行执行
- 数据缓存机制减少重复计算
- 内存使用优化支持更大数据量

### 4. 可观测性提升
- 每个因子计算过程可单独监控
- 详细的日志记录便于问题排查
- 因子IC值实时监控，及时发现因子失效

## ⚠️ 风险与应对

### 1. 计算结果一致性风险
- **应对**: 编写全面的测试用例，对比重构前后的计算结果

### 2. 性能退化风险
- **应对**: 进行性能测试，优化关键计算路径

### 3. 接口兼容风险
- **应对**: 设计兼容层，确保新架构可以平滑替代旧逻辑

### 4. 实施时间风险
- **应对**: 分阶段实施，每个阶段都进行充分测试和验证

## 🎉 重构后预期效果

1. **开发效率提升**: 新因子开发时间从3天缩短到1天
2. **维护成本降低**: 策略调整时间从几小时缩短到几分钟
3. **系统稳定性提升**: 完善的测试框架减少线上bug
4. **策略迭代加速**: 配置化管理支持快速策略实验
5. **团队协作增强**: 模块化架构支持并行开发和独立测试

---

## 📝 执行建议

1. **优先基础框架**: 先搭建稳定的基础框架，再迁移因子计算逻辑
2. **严格测试驱动**: 每个因子迁移都要有对应的测试用例
3. **渐进式迁移**: 可以先在部分功能中试用新架构，逐步替换旧逻辑
4. **性能监控**: 重构后持续监控系统性能，及时发现并解决性能瓶颈
5. **文档更新**: 及时更新技术文档，确保团队成员理解新架构

此重构方案在保持原有计算逻辑不变的基础上，通过模块化和配置化设计，显著提升系统的可维护性和可扩展性，为未来的策略优化和功能增强奠定坚实基础。