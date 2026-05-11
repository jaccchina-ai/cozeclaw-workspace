#!/usr/bin/env python3
"""
动态因子配置系统 - 使用示例

演示如何添加新因子并自动保存数据
"""

import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from factor_config import (
    factor_manager, FactorDefinition, FactorType,
    add_custom_factor, get_factor_score
)
from dynamic_db_migrate import migrate_database


def example_1_view_existing_factors():
    """示例1：查看现有因子"""
    print("=" * 60)
    print("示例1：查看现有因子配置")
    print("=" * 60)
    
    # 获取T日因子
    t_day_factors = factor_manager.get_all_factors('t_day_factors')
    print(f"\nT日选股因子 ({len(t_day_factors)} 个):")
    for code, factor in t_day_factors.items():
        print(f"  {code:20s} | {factor.name:12s} | 权重: {factor.weight:5.1f} | 类型: {factor.type.value}")
    
    # 获取归一化权重
    weights = factor_manager.normalize_weights('t_day_factors')
    print(f"\n归一化权重总和: {sum(weights.values()):.1f}%")
    
    # 获取竞价因子
    auction_factors = factor_manager.get_all_factors('auction_factors')
    print(f"\nT+1竞价因子 ({len(auction_factors)} 个):")
    for code, factor in auction_factors.items():
        print(f"  {code:20s} | {factor.name:12s} | 权重: {factor.weight:5.1f}")


def example_2_add_new_factor():
    """示例2：添加新因子"""
    print("\n" + "=" * 60)
    print("示例2：添加新因子 '市盈率'")
    print("=" * 60)
    
    # 定义新因子
    pe_factor = FactorDefinition(
        code='pe_ratio',
        name='市盈率',
        type=FactorType.BOTH,  # 保存得分和原始值
        weight=5.0,
        description='市盈率估值指标（越低越好）',
        score_rules=[
            (10, 10),    # PE <= 10，得10分（低估）
            (20, 8),     # PE <= 20，得8分
            (30, 6),     # PE <= 30，得6分
            (50, 4),     # PE <= 50，得4分
            (999, 2),    # PE > 50，得2分（高估）
        ],
        higher_is_better=False  # 越低越好
    )
    
    # 添加到配置
    factor_manager.add_factor('t_day_factors', pe_factor)
    
    print(f"\n✅ 已添加因子: {pe_factor.name} (code: {pe_factor.code})")
    print(f"   权重: {pe_factor.weight}")
    print(f"   类型: {pe_factor.type.value}")
    
    # 查看更新后的因子列表
    updated_factors = factor_manager.get_all_factors('t_day_factors')
    print(f"\n更新后T日因子数量: {len(updated_factors)}")
    
    # 测试评分
    test_values = [8, 15, 25, 40, 60]
    print(f"\n评分测试:")
    for val in test_values:
        score = factor_manager.calculate_score('pe_ratio', val, 't_day_factors')
        print(f"  PE = {val:2d} -> 得分: {score}")


def example_3_database_migration():
    """示例3：数据库迁移"""
    print("\n" + "=" * 60)
    print("示例3：数据库迁移")
    print("=" * 60)
    
    print("\n执行数据库迁移...")
    print("(这会检查现有表结构并添加缺失的字段)")
    
    # 执行迁移
    success = migrate_database()
    
    if success:
        print("\n✅ 数据库迁移成功!")
    else:
        print("\n⚠️ 数据库结构不完整")


def example_4_calculate_scores():
    """示例4：计算因子得分"""
    print("\n" + "=" * 60)
    print("示例4：计算因子得分")
    print("=" * 60)
    
    # 测试不同因子的评分
    test_cases = [
        ('seal_ratio', 0.5, 't_day_factors', '封成比'),
        ('seal_ratio', 0.2, 't_day_factors', '封成比'),
        ('volume_ratio', 3.5, 't_day_factors', '量比'),
        ('volume_ratio', 1.5, 't_day_factors', '量比'),
        ('auction_pct_chg', 3.0, 'auction_factors', '竞价涨幅'),
        ('auction_pct_chg', 8.0, 'auction_factors', '竞价涨幅'),
    ]
    
    print("\n评分计算测试:")
    for code, value, category, name in test_cases:
        score = factor_manager.calculate_score(code, value, category)
        print(f"  {name:10s} ({code:20s}) = {value:6.2f} -> 得分: {score:.1f}")


def example_5_export_import_config():
    """示例5：导出/导入配置"""
    print("\n" + "=" * 60)
    print("示例5：导出配置")
    print("=" * 60)
    
    # 导出配置
    config = factor_manager.export_config()
    
    print(f"\n配置包含类别:")
    for category in config.keys():
        factor_count = len(config[category])
        print(f"  - {category}: {factor_count} 个因子")
    
    # 显示第一个因子的配置
    first_category = list(config.keys())[0]
    first_factor = list(config[first_category].keys())[0]
    print(f"\n示例因子配置 ({first_factor}):")
    import json
    print(json.dumps(config[first_category][first_factor], indent=2, ensure_ascii=False))


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" " * 20 + "动态因子配置系统 - 使用示例")
    print("=" * 70)
    
    # 运行示例
    example_1_view_existing_factors()
    example_2_add_new_factor()
    # example_3_database_migration()  # 注释掉，避免实际修改数据库
    example_4_calculate_scores()
    example_5_export_import_config()
    
    print("\n" + "=" * 70)
    print("示例运行完成!")
    print("=" * 70)
    print("\n使用指南: DYNAMIC_FACTOR_GUIDE.md")
