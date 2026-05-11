#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在选股系统中集成龙虎榜因子
"""

import os
import sys
import re

def update_factor_weights():
    """
    在FactorWeights类中添加dragon_tiger权重参数
    """
    print("\n1. 添加龙虎榜因子权重参数:")
    
    # 找到scoring_model.py文件
    scoring_model_path = os.path.join(os.path.dirname(__file__), 'scoring_model.py')
    
    with open(scoring_model_path, 'r') as f:
        content = f.read()
    
    # 查找FactorWeights类
    pattern = r'class FactorWeights\(BaseModel\):(.*?)(class|def|$)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        class_content = match.group(1)
        
        # 检查是否已存在dragon_tiger
        if 'dragon_tiger' in class_content:
            print("✅ 龙虎榜因子权重参数已存在")
            return True
        
        # 添加dragon_tiger参数
        new_content = class_content.rstrip()
        new_content += "\n    dragon_tiger: float = 15.0  # 龙虎榜因子权重\n\n"
        
        # 替换原类内容
        new_content = re.sub(pattern, rf'class FactorWeights(BaseModel):{new_content}\g<2>', content, flags=re.DOTALL)
        
        with open(scoring_model_path, 'w') as f:
            f.write(new_content)
        
        print("✅ 已添加龙虎榜因子权重参数，默认权重: 15.0")
        return True
    else:
        print("❌ 未找到FactorWeights类")
        return False

def update_scoring_model():
    """
    在ScoringModel中添加龙虎榜因子计算
    """
    print("\n2. 在评分模型中添加龙虎榜因子计算:")
    
    scoring_model_path = os.path.join(os.path.dirname(__file__), 'scoring_model.py')
    
    with open(scoring_model_path, 'r') as f:
        content = f.read()
    
    # 检查是否已包含龙虎榜计算
    if 'dragon_tiger' in content:
        print("✅ 评分模型中已包含龙虎榜因子计算")
        return True
    
    # 查找calculate_total_score方法
    pattern = r'def calculate_total_score\(self, stock_data: dict\) -> StockScore:(.*?)return(.*?)Score' 
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        method_content = match.group(0)
        
        # 添加龙虎榜因子计算逻辑
        dragon_tiger_code = '''\n        # 计算龙虎榜因子得分
        try:
            from dragon_tiger.integration import DragonTigerIntegration
            integration = DragonTigerIntegration()
            dragon_tiger_score = integration.get_dragon_tiger_score(stock_data)
            factor_scores['dragon_tiger'] = dragon_tiger_score * self.factor_weights.dragon_tiger
        except Exception as e:
            print(f"龙虎榜因子计算失败: {e}")
            factor_scores['dragon_tiger'] = 0
        '''
        
        # 在返回前添加龙虎榜计算
        if 'factor_scores' in method_content:
            # 找到factor_scores定义的位置
            factor_pattern = r'factor_scores =\s*\{'
            factor_match = re.search(factor_pattern, method_content)
            
            if factor_match:
                # 插入在factor_scores定义之后
                new_method = method_content[:factor_match.end()] + dragon_tiger_code + method_content[factor_match.end():]
                new_content = content.replace(method_content, new_method)
                
                with open(scoring_model_path, 'w') as f:
                    f.write(new_content)
                
                print("✅ 已在评分模型中添加龙虎榜因子计算")
                return True
            else:
                print("❌ 未找到factor_scores定义")
                return False
        else:
            print("❌ 方法中不包含factor_scores")
            return False
    else:
        print("❌ 未找到calculate_total_score方法")
        return False

def update_selection_engine():
    """
    在run_t_day_selection函数中添加龙虎榜因子处理
    """
    print("\n3. 在选股引擎中添加龙虎榜因子处理:")
    
    selection_engine_path = os.path.join(os.path.dirname(__file__), 'selection_engine.py')
    
    with open(selection_engine_path, 'r') as f:
        content = f.read()
    
    # 检查是否已包含龙虎榜处理
    if 'dragon_tiger' in content.lower():
        print("✅ 选股引擎中已包含龙虎榜因子处理")
        return True
    
    # 查找run_t_day_selection函数
    pattern = r'def run_t_day_selection\(date: str = None\)(.*?)return (.*?)SelectionResult'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        function_content = match.group(0)
        
        # 添加龙虎榜筛选逻辑
        dragon_tiger_code = '''\n    # 应用龙虎榜因子筛选
    try:
        from dragon_tiger.integration import DragonTigerIntegration
        integration = DragonTigerIntegration()
        
        print("\n📊 应用龙虎榜因子筛选...")
        candidates = integration.filter_by_dragon_tiger(candidates, threshold=50)
        print(f"✅ 龙虎榜因子筛选完成，剩余 {len(candidates)} 只股票")
    except Exception as e:
        print(f"龙虎榜因子筛选失败: {e}")
    '''
        
        # 找到候选人筛选的部分
        if 'candidates =' in function_content:
            # 在第一次候选人筛选后添加
            candidate_pattern = r'candidates\s*=\s*.+'
            candidate_matches = re.findall(candidate_pattern, function_content)
            
            if candidate_matches:
                last_match = candidate_matches[-1]
                # 在最后一次候选人赋值后添加
                new_function = function_content.replace(last_match, last_match + dragon_tiger_code)
                new_content = content.replace(function_content, new_function)
                
                with open(selection_engine_path, 'w') as f:
                    f.write(new_content)
                
                print("✅ 已在选股引擎中添加龙虎榜因子处理")
                return True
            else:
                print("❌ 未找到候选人赋值语句")
                return False
        else:
            print("❌ 函数中不包含候选人筛选")
            return False
    else:
        print("❌ 未找到run_t_day_selection函数")
        return False

def main():
    """
    主集成函数
    """
    print("="*60)
    print("在选股系统中集成龙虎榜因子")
    print("="*60)
    
    # 步骤1: 添加因子权重
    success1 = update_factor_weights()
    
    # 步骤2: 更新评分模型
    success2 = update_scoring_model()
    
    # 步骤3: 更新选股引擎
    success3 = update_selection_engine()
    
    print("\n" + "="*60)
    print("集成完成总结:")
    
    all_success = success1 and success2 and success3
    
    if success1:
        print("✅ 因子权重配置完成")
    else:
        print("❌ 因子权重配置失败")
        
    if success2:
        print("✅ 评分模型集成完成")
    else:
        print("❌ 评分模型集成失败")
        
    if success3:
        print("✅ 选股引擎集成完成")
    else:
        print("❌ 选股引擎集成失败")
    
    print("\n" + "="*60)
    if all_success:
        print("🎉 龙虎榜因子已成功集成到选股系统中！")
        print("📌 可直接运行选股系统使用龙虎榜因子")
        print("📌 默认权重: 15.0，可在FactorWeights中调整")
    else:
        print("⚠️  部分集成步骤失败，请手动检查并修复")
        print("📌 可手动添加龙虎榜因子到选股系统")

if __name__ == '__main__':
    main()
