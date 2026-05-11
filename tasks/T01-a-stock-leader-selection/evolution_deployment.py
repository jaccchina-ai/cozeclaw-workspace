#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - 策略进化自动部署
自动更新策略权重并重启系统
"""

import os
import json
import subprocess
import traceback
from datetime import datetime

def load_best_weights():
    """加载最佳策略权重"""
    result_dir = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/evolution_results'
    
    best_result = None
    best_win_rate = 0
    
    # 遍历所有进化结果
    for filename in os.listdir(result_dir):
        if filename.endswith('_result.json'):
            file_path = os.path.join(result_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    
                    win_rate = result.get('win_rate', 0)
                    if win_rate > best_win_rate:
                        best_win_rate = win_rate
                        best_result = result
                        
            except Exception as e:
                print(f"加载 {filename} 失败: {e}")
    
    return best_result

def update_strategy_config(best_result):
    """更新策略配置"""
    if not best_result:
        print("无最佳策略数据")
        return False
    
    best_weights = best_result.get('weights', {})
    if not best_weights:
        print("无策略权重数据")
        return False
    
    # 更新策略权重配置
    config_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/strategy/config/factor_weights.json'
    
    try:
        # 读取当前配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 保存旧权重作为备份
        backup_dir = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/weight_backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_file = os.path.join(backup_dir, f"weights_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 更新新权重
        config['weights'] = best_weights
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 策略配置已更新")
        print(f"旧权重已备份到: {backup_file}")
        print(f"新权重: {best_weights}")
        
        return True
        
    except Exception as e:
        print(f"更新策略配置失败: {e}")
        traceback.print_exc()
        return False

def restart_scheduler():
    """重启选股系统调度器"""
    print("\n重启选股系统调度器...")
    
    try:
        # 停止运行中的调度器
        subprocess.run(['pkill', '-f', 'main.py.*schedule'], capture_output=True)
        subprocess.run(['pkill', '-f', 't01_scheduler.py'], capture_output=True)
        time.sleep(5)
        
        # 启动新的调度器
        scheduler_cmd = 'nohup python3 /workspace/projects/workspace/tasks/T01-a-stock-leader-selection/main.py schedule > /dev/null 2>&1 &'
        subprocess.run(scheduler_cmd, shell=True)
        
        print("✅ 选股系统调度器已重启")
        return True
        
    except Exception as e:
        print(f"重启调度器失败: {e}")
        traceback.print_exc()
        return False

def verify_update():
    """验证更新是否成功"""
    print("\n验证策略更新...")
    
    try:
        # 加载更新后的权重
        config_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/strategy/config/factor_weights.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"当前策略权重: {config.get('weights', {})}")
        print("✅ 策略更新验证成功")
        return True
        
    except Exception as e:
        print(f"验证更新失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print(f"{'='*60}")
    print(f"T01 策略进化自动部署")
    print(f"时间: {datetime.now()}")
    print(f"{'='*60}")
    
    try:
        # 1. 加载最佳策略
        best_result = load_best_weights()
        if not best_result:
            print("❌ 未找到最佳策略")
            return
        
        print(f"\n找到最佳策略:")
        print(f"胜率: {best_result.get('win_rate', 0)*100:.1f}%")
        print(f"平均收益: {best_result.get('avg_return', 0):+.2f}%")
        
        # 2. 更新策略配置
        if not update_strategy_config(best_result):
            print("❌ 更新策略配置失败")
            return
        
        # 3. 重启调度器
        if not restart_scheduler():
            print("⚠️ 重启调度器失败，但策略配置已更新")
        
        # 4. 验证更新
        if not verify_update():
            print("❌ 策略更新验证失败")
            return
        
        print(f"\n{'='*60}")
        print(f"✅ 策略进化自动部署完成")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ 自动部署失败: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    import time
    main()