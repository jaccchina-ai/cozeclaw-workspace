#!/usr/bin/env python3
"""
T01 选股系统 - 因子重构测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factors import create_factor_engine, FactorResult


def test_limit_quality_factor():
    """测试涨停质量因子"""
    print("\n=== 测试涨停质量因子 ===")
    
    engine = create_factor_engine()
    
    # 测试用例1: 优质涨停
    test_data1 = {
        'first_limit_time': '09:45:00',
        'limit_times': 0,
        'consecutive_limit': 2
    }
    
    result1 = engine.calculate_single_factor('limit_quality', test_data1)
    print(f"测试用例1 - 优质涨停:")
    print(f"  得分: {result1.score:.2f}")
    print(f"  原始值: {result1.raw_values}")
    print(f"  有效: {result1.is_valid}")
    
    # 测试用例2: 炸板股票
    test_data2 = {
        'first_limit_time': '10:30:00',
        'limit_times': 3,
        'consecutive_limit': 1
    }
    
    result2 = engine.calculate_single_factor('limit_quality', test_data2)
    print(f"\n测试用例2 - 炸板股票:")
    print(f"  得分: {result2.score:.2f}")
    print(f"  原始值: {result2.raw_values}")
    print(f"  有效: {result2.is_valid}")
    print(f"  错误信息: {result2.error_message}")
    
    # 测试用例3: 连板过多
    test_data3 = {
        'first_limit_time': '09:50:00',
        'limit_times': 0,
        'consecutive_limit': 5
    }
    
    result3 = engine.calculate_single_factor('limit_quality', test_data3)
    print(f"\n测试用例3 - 连板过多:")
    print(f"  得分: {result3.score:.2f}")
    print(f"  原始值: {result3.raw_values}")
    print(f"  有效: {result3.is_valid}")
    print(f"  错误信息: {result3.error_message}")


def test_seal_ratio_factor():
    """测试封成比因子"""
    print("\n=== 测试封成比因子 ===")
    
    engine = create_factor_engine()
    
    # 测试用例1: 高封成比
    test_data1 = {
        'seal_amount': 10000,  # 1亿封单
        'amount': 5000        # 5千万成交
    }
    
    result1 = engine.calculate_single_factor('seal_ratio', test_data1)
    print(f"测试用例1 - 高封成比:")
    print(f"  得分: {result1.score:.2f}")
    print(f"  封成比: {result1.raw_values['seal_ratio']:.4f}")
    print(f"  有效: {result1.is_valid}")
    
    # 测试用例2: 中等封成比
    test_data2 = {
        'seal_amount': 2500,
        'amount': 5000
    }
    
    result2 = engine.calculate_single_factor('seal_ratio', test_data2)
    print(f"\n测试用例2 - 中等封成比:")
    print(f"  得分: {result2.score:.2f}")
    print(f"  封成比: {result2.raw_values['seal_ratio']:.4f}")
    print(f"  有效: {result2.is_valid}")
    
    # 测试用例3: 低封成比
    test_data3 = {
        'seal_amount': 500,
        'amount': 5000
    }
    
    result3 = engine.calculate_single_factor('seal_ratio', test_data3)
    print(f"\n测试用例3 - 低封成比:")
    print(f"  得分: {result3.score:.2f}")
    print(f"  封成比: {result3.raw_values['seal_ratio']:.4f}")
    print(f"  有效: {result3.is_valid}")


def test_parallel_calculation():
    """测试并行计算"""
    print("\n=== 测试并行计算 ===")
    
    engine = create_factor_engine()
    
    test_data = {
        'first_limit_time': '09:45:00',
        'limit_times': 0,
        'consecutive_limit': 2,
        'seal_amount': 10000,
        'amount': 5000
    }
    
    print("并行计算所有因子...")
    results = engine.calculate_all_factors(test_data, parallel=True)
    
    for factor_name, result in results.items():
        if result.is_valid:
            print(f"  {factor_name}: {result.score:.2f}")
        else:
            print(f"  {factor_name}: 无效 ({result.error_message})")
    
    # 计算总分
    total_score = engine.calculate_total_score(results)
    print(f"\n综合总分: {total_score:.2f}")


def test_factor_engine_integration():
    """测试因子引擎集成"""
    print("\n=== 测试因子引擎集成 ===")
    
    engine = create_factor_engine()
    
    # 测试更新权重
    print(f"当前权重: {engine.get_factor_weights()['limit_quality']}")
    engine.update_factor_weight('limit_quality', 15.0)
    print(f"更新后权重: {engine.get_factor_weights()['limit_quality']}")
    
    # 测试因子列表
    print(f"\n已实现因子: {engine.factors.keys()}")


if __name__ == '__main__':
    print("T01 选股系统 - 因子重构测试")
    print("=" * 40)
    
    try:
        test_limit_quality_factor()
        test_seal_ratio_factor()
        test_parallel_calculation()
        test_factor_engine_integration()
        
        print("\n" + "=" * 40)
        print("测试完成!")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)