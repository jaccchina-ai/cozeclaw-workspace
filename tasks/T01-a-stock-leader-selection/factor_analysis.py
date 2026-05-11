#!/usr/bin/env python3
"""FactorICMonitor模块 - 计算和监控因子IC值"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FactorICMonitor:
    def __init__(self):
        self.db_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db'
        
    def get_latest_ic_values(self):
        """获取最近的因子IC值"""
        conn = sqlite3.connect(self.db_path)
        
        # 获取最近10天的因子数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        query = f"""
        SELECT s.ts_code, s.trade_date, s.total_score, 
               (t.t2_close / t.t1_open - 1) * 100 as return_pct
        FROM stock_factor_scores s
        JOIN tracked_results t ON s.ts_code = t.ts_code AND s.trade_date = t.t_day
        WHERE s.trade_date >= '{start_date}' AND s.trade_date <= '{end_date}'
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if len(df) == 0:
            return {}
        
        # 计算各因子IC值
        ic_values = {}
        
        # 先计算总得分的IC
        if 'total_score' in df.columns:
            ic = df['total_score'].corr(df['return_pct'])
            ic_values['total_score'] = ic
        
        # 计算其他单个因子的IC
        factor_columns = [
            'limit_quality_score', 'seal_ratio_score', 'seal_flow_ratio_score',
            'volume_ratio_score', 'turnover_rate_score', 'dragon_tiger_score',
            'money_flow_score', 'amount_rank_score', 'sector_heat_score',
            'bias_ma3_score', 'sentiment_score', 'sector_linkage_score'
        ]
        
        for factor in factor_columns:
            if factor in df.columns:
                ic = df[factor].corr(df['return_pct'])
                ic_values[factor] = ic
        
        return ic_values
    
    def monitor_ic_values(self):
        """监控因子IC值并输出结果"""
        ic_values = self.get_latest_ic_values()
        
        print('=== 因子IC值监控 ===')
        print(f'计算日期范围: {datetime.now() - timedelta(days=10)} 至 {datetime.now()}')
        print(f'总交易样本数: {self._get_sample_count()}')
        print()
        
        if not ic_values:
            print('⚠️ 没有足够的数据计算IC值')
            return
        
        for factor, ic in ic_values.items():
            status = '✅' if abs(ic) >= 0.02 else '⚠️'
            print(f'{status} {factor}: {ic:.4f}')
        
        # 检查是否所有IC值为0
        all_zero = all(ic == 0 for ic in ic_values.values())
        if all_zero:
            print()
            print('🚨 告警: 所有因子IC值均为0，因子完全失效！')
            print('建议:')
            print('1. 检查因子计算逻辑是否正确')
            print('2. 验证数据源是否正常')
            print('3. 重新评估因子有效性')
    
    def _get_sample_count(self):
        """获取样本数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tracked_results')
        count = cursor.fetchone()[0]
        conn.close()
        return count

if __name__ == '__main__':
    monitor = FactorICMonitor()
    monitor.monitor_ic_values()