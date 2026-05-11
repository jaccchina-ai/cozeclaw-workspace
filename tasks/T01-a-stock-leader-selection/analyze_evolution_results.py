#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 策略进化结果分析
分析进化结果，选择最佳策略参数
"""

import os
import json
import traceback
from datetime import datetime

def load_evolution_results():
    """加载策略进化结果"""
    result_dir = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/evolution_results'
    
    results = []
    
    # 加载所有进化结果文件
    for filename in os.listdir(result_dir):
        if filename.endswith('_result.json'):
            file_path = os.path.join(result_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    results.append(result)
            except Exception as e:
                print(f"加载 {filename} 失败: {e}")
    
    return results

def analyze_evolution_results(results):
    """分析进化结果"""
    if not results:
        print("无进化结果数据")
        return None
    
    print("=== 策略进化结果分析 ===")
    print(f"共分析 {len(results)} 次进化结果")
    
    # 按胜率排序
    sorted_results = sorted(results, key=lambda x: x.get('win_rate', 0), reverse=True)
    
    # 显示前5个最佳结果
    print(f"\n=== 前5最佳策略 ===")
    for i, result in enumerate(sorted_results[:5]):
        print(f"\n第{i+1}名 - 胜率: {result.get('win_rate', 0)*100:.1f}%")
        print(f"  平均收益: {result.get('avg_return', 0):+.2f}%")
        print(f"  最大回撤: {result.get('max_drawdown', 0):.2f}%")
        print(f"  进化迭代: {result.get('iteration', 0)} 代")
        print(f"  权重参数: {result.get('weights', {})}")
    
    # 统计每个因子的平均权重
    all_weights = []
    for result in results:
        weights = result.get('weights', {})
        if weights:
            all_weights.append(weights)
    
    if all_weights:
        print(f"\n=== 因子权重统计 ===")
        # 计算每个因子的平均权重
        factor_avg = {}
        factor_count = {}
        
        for weights in all_weights:
            for factor, weight in weights.items():
                if factor not in factor_avg:
                    factor_avg[factor] = 0
                    factor_count[factor] = 0
                factor_avg[factor] += weight
                factor_count[factor] += 1
        
        # 计算平均值
        for factor in factor_avg:
            factor_avg[factor] = factor_avg[factor] / factor_count[factor]
        
        # 排序显示
        sorted_factors = sorted(factor_avg.items(), key=lambda x: x[1], reverse=True)
        for factor, avg_weight in sorted_factors:
            print(f"  {factor}: {avg_weight:.2f} (出现 {factor_count[factor]} 次)")
    
    # 返回最佳策略
    best_result = sorted_results[0]
    print(f"\n=== 最佳策略 ===")
    print(f"胜率: {best_result.get('win_rate', 0)*100:.1f}%")
    print(f"平均收益: {best_result.get('avg_return', 0):+.2f}%")
    print(f"最佳权重: {best_result.get('weights', {})}")
    
    return best_result

def update_strategy_config(best_result):
    """更新策略配置"""
    if not best_result:
        print("无最佳策略可更新")
        return False
    
    config_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/strategy/config/factor_weights.json'
    
    try:
        # 读取当前配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 更新权重
        new_weights = best_result.get('weights', {})
        if new_weights:
            config['weights'] = new_weights
            
            # 保存更新
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ 策略配置已更新")
            print(f"新权重: {new_weights}")
            return True
        else:
            print("无权重数据可更新")
            return False
            
    except FileNotFoundError:
        print(f"配置文件 {config_path} 不存在")
        return False
    except Exception as e:
        print(f"更新配置失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 T01 策略进化结果分析")
    print(f"时间: {datetime.now()}")
    
    try:
        # 加载进化结果
        results = load_evolution_results()
        
        # 分析结果
        best_result = analyze_evolution_results(results)
        
        # 更新策略配置
        if best_result and update_strategy_config(best_result):
            print("\n✅ 策略进化分析完成，最佳策略已应用")
        else:
            print("\n⚠️ 未更新策略配置")
            
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()