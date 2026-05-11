#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动添加龙虎榜因子到选股系统
"""

import os
import sys

def find_factor_weights():
    """
    查找FactorWeights类的定义
    """
    scoring_model_path = os.path.join(os.path.dirname(__file__), 'scoring_model.py')
    
    with open(scoring_model_path, 'r') as f:
        content = f.read()
    
    # 查找所有class定义
    import re
    class_patterns = re.findall(r'class\s+(\w+)\s*(\(.*?\))?:', content)
    
    print("\n找到的类定义:")
    for class_name, base in class_patterns:
        print(f"  - {class_name}{base}")
    
    # 查找Factor相关的类
    factor_classes = [name for name, _ in class_patterns if 'Factor' in name or 'Weight' in name]
    
    if factor_classes:
        print("\n找到的因子相关类:")
        for class_name in factor_classes:
            print(f"  - {class_name}")


def manual_add_dragon_tiger_factor():
    """
    手动添加龙虎榜因子到scoring_model.py
    """
    print("="*60)
    print("手动添加龙虎榜因子到选股系统")
    print("="*60)
    
    # 1. 添加FactorWeights
    print("\n1. 添加龙虎榜因子权重参数:")
    
    if not os.path.exists('scoring_model.py'):
        print("❌ scoring_model.py 不存在")
        return False
    
    with open('scoring_model.py', 'r') as f:
        content = f.read()
    
    # 检查是否已有dragon_tiger
    if 'dragon_tiger' in content:
        print("✅ 龙虎榜因子已存在于scoring_model.py中")
    else:
        print("⚠️  未找到龙虎榜因子，准备手动添加")
        print("\n请手动添加以下代码到FactorWeights类:")
        print("```python")
        print("dragon_tiger: float = 15.0  # 龙虎榜因子权重")
        print("```")
    
    # 2. 添加到评分模型
    print("\n2. 在评分模型中添加龙虎榜因子计算:")
    print("\n请在calculate_total_score方法中添加以下代码:")
    print("```python")
    print("# 计算龙虎榜因子得分")
    print("try:")
    print("    from dragon_tiger.integration import DragonTigerIntegration")
    print("    integration = DragonTigerIntegration()")
    print("    dragon_tiger_score = integration.get_dragon_tiger_score(stock_data)")
    print("    factor_scores['dragon_tiger'] = dragon_tiger_score * self.factor_weights.dragon_tiger")
    print("except Exception as e:")
    print("    print(f'龙虎榜因子计算失败: {e}')")
    print("    factor_scores['dragon_tiger'] = 0")
    print("```")
    
    # 3. 添加到选股引擎
    print("\n3. 在选股引擎中添加龙虎榜因子处理:")
    print("\n请在run_t_day_selection函数中添加以下代码:")
    print("```python")
    print("# 应用龙虎榜因子筛选")
    print("try:")
    print("    from dragon_tiger.integration import DragonTigerIntegration")
    print("    integration = DragonTigerIntegration()")
    print("    ")
    print("    print(\"\\n📊 应用龙虎榜因子筛选...\")")
    print("    candidates = integration.filter_by_dragon_tiger(candidates, threshold=50)")
    print("    print(f\"✅ 龙虎榜因子筛选完成，剩余 {len(candidates)} 只股票\")")
    print("except Exception as e:")
    print("    print(f'龙虎榜因子筛选失败: {e}')")
    print("```")
    
    # 创建示例集成文件
    create_example_integration()
    
    return True


def create_example_integration():
    """
    创建示例集成代码文件
    """
    print("\n4. 创建示例集成代码文件:")
    
    example_content = '''#!/usr/bin/env python3
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
        
        print("\n📊 应用龙虎榜因子筛选...")
        candidates = integration.filter_by_dragon_tiger(candidates, threshold=50)
        print(f"✅ 龙虎榜因子筛选完成，剩余 {len(candidates)} 只股票")
    except Exception as e:
        print(f'龙虎榜因子筛选失败: {e}')
    
    # 剩余选股逻辑...
'''
    
    with open('dragon_tiger_integration_example.py', 'w') as f:
        f.write(example_content)
    
    print("✅ 已创建示例集成代码文件: dragon_tiger_integration_example.py")


if __name__ == '__main__':
    print("📌 准备手动添加龙虎榜因子到选股系统")
    find_factor_weights()
    manual_add_dragon_tiger_factor()
    
    print("\n" + "="*60)
    print("手动添加完成！")
    print("📌 请按照上述说明手动修改代码")
    print("📌 或参考 dragon_tiger_integration_example.py 文件")
