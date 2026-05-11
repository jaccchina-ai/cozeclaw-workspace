#!/usr/bin/env python3
"""
FactorICMonitor模块 - 计算和监控因子IC值
使用 PostgreSQL 数据库

使用方法:
    python3 factor_ic_check.py              # 计算最近10天的IC值
    python3 factor_ic_check.py --days 30  # 计算最近30天的IC值
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from database.models import init_db, get_session
from sqlalchemy import text


class FactorICMonitor:
    """因子IC值监控器"""
    
    def __init__(self):
        init_db()
        self.session = get_session()
    
    def get_factor_data(self, days: int = 10) -> pd.DataFrame:
        """获取因子评分数据"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        query = text("""
            SELECT 
                s.ts_code,
                s.trade_date,
                s.total_score,
                s.limit_quality_score,
                s.seal_ratio_score,
                s.seal_flow_ratio_score,
                s.volume_ratio_score,
                s.turnover_rate_score,
                s.dragon_tiger_score,
                s.money_flow_score,
                s.amount_rank_score,
                s.sector_heat_score,
                s.bias_ma3_score,
                s.sentiment_score,
                s.sector_linkage_score,
                (t.t2_close / t.t1_open - 1) * 100 as return_pct
            FROM stock_factor_scores s
            JOIN tracked_results t ON s.ts_code = t.ts_code AND s.trade_date = t.t_day
            WHERE s.trade_date >= :start_date AND s.trade_date <= :end_date
            ORDER BY s.trade_date DESC
        """)
        
        try:
            result = self.session.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            rows = result.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame([dict(row._mapping) for row in rows])
            return df
        except Exception as e:
            print(f"获取因子数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_ic_values(self, df: pd.DataFrame) -> dict:
        """计算因子IC值"""
        if df.empty or 'return_pct' not in df.columns:
            return {}
        
        ic_values = {}
        
        factor_columns = [
            'total_score',
            'limit_quality_score',
            'seal_ratio_score',
            'seal_flow_ratio_score',
            'volume_ratio_score',
            'turnover_rate_score',
            'dragon_tiger_score',
            'money_flow_score',
            'amount_rank_score',
            'sector_heat_score',
            'bias_ma3_score',
            'sentiment_score',
            'sector_linkage_score'
        ]
        
        for factor in factor_columns:
            if factor in df.columns:
                # 移除 NaN 值
                valid_data = df[[factor, 'return_pct']].dropna()
                if len(valid_data) > 2:
                    ic = valid_data[factor].corr(valid_data['return_pct'])
                    ic_values[factor] = round(ic, 4) if not np.isnan(ic) else 0
        
        return ic_values
    
    def calculate_rank_ic(self, df: pd.DataFrame) -> dict:
        """计算 Rank IC 值（Spearman相关系数）"""
        if df.empty or 'return_pct' not in df.columns:
            return {}
        
        rank_ic_values = {}
        
        factor_columns = [
            'total_score',
            'limit_quality_score',
            'seal_ratio_score',
            'seal_flow_ratio_score',
            'volume_ratio_score',
            'turnover_rate_score',
            'dragon_tiger_score',
            'money_flow_score',
            'amount_rank_score',
            'sector_heat_score',
            'bias_ma3_score',
            'sentiment_score',
            'sector_linkage_score'
        ]
        
        for factor in factor_columns:
            if factor in df.columns:
                valid_data = df[[factor, 'return_pct']].dropna()
                if len(valid_data) > 2:
                    # Spearman 相关系数
                    ic, p_value = self._spearman_corr(valid_data[factor], valid_data['return_pct'])
                    rank_ic_values[factor] = round(ic, 4) if not np.isnan(ic) else 0
        
        return rank_ic_values
    
    def _spearman_corr(self, x: pd.Series, y: pd.Series) -> tuple:
        """计算 Spearman 相关系数"""
        try:
            from scipy import stats
            corr, p_value = stats.spearmanr(x, y)
            return corr, p_value
        except:
            return 0, 1
    
    def get_sample_stats(self) -> dict:
        """获取样本统计"""
        stats = {}
        
        try:
            # 样本总数
            result = self.session.execute(text('SELECT COUNT(*) FROM tracked_results'))
            stats['total_samples'] = result.fetchone()[0]
            
            # 日期范围
            result = self.session.execute(text('SELECT MIN(t_day), MAX(t_day) FROM tracked_results'))
            row = result.fetchone()
            stats['date_range'] = f"{row[0]} ~ {row[1]}"
            
        except Exception as e:
            print(f"获取样本统计失败: {e}")
        
        return stats
    
    def analyze_ic_values(self, ic_values: dict, rank_ic_values: dict = None):
        """分析 IC 值并输出报告"""
        print("\n" + "="*70)
        print("📊 因子 IC 值分析报告")
        print("="*70)
        
        if not ic_values:
            print("\n⚠️ 没有足够的数据计算 IC 值")
            print("   可能原因:")
            print("   1. stock_factor_scores 表中无数据")
            print("   2. tracked_results 表中无对应数据")
            print("   3. 数据日期范围不匹配")
            return
        
        # IC 值统计
        valid_ics = [v for v in ic_values.values() if v != 0]
        if valid_ics:
            print(f"\n📈 IC 值统计:")
            print(f"   平均 IC: {np.mean(valid_ics):.4f}")
            print(f"   IC 标准差: {np.std(valid_ics):.4f}")
            print(f"   IC 范围: [{min(valid_ics):.4f}, {max(valid_ics):.4f}]")
        
        # 因子 IC 值详情
        print(f"\n📋 各因子 IC 值:")
        print("-"*70)
        print(f"{'因子名称':<25} {'IC值':>10} {'有效性':>10} {'Rank IC':>10}")
        print("-"*70)
        
        for factor in sorted(ic_values.keys(), key=lambda x: abs(ic_values.get(x, 0)), reverse=True):
            ic = ic_values.get(factor, 0)
            rank_ic = rank_ic_values.get(factor, '-') if rank_ic_values else '-'
            
            # 判断有效性
            if abs(ic) >= 0.05:
                validity = "✅ 强效"
            elif abs(ic) >= 0.02:
                validity = "⚠️ 中效"
            elif abs(ic) >= 0.01:
                validity = "📊 弱效"
            else:
                validity = "❌ 低效"
            
            # 格式化 Rank IC
            rank_ic_str = f"{rank_ic:>10.4f}" if isinstance(rank_ic, (int, float)) else f"{rank_ic:>10}"
            
            print(f"{factor:<25} {ic:>10.4f} {validity:>10} {rank_ic_str}")
        
        print("-"*70)
        
        # 分析结论
        print("\n💡 分析结论:")
        
        # 找出最有效的因子
        if ic_values:
            best_factor = max(ic_values.items(), key=lambda x: abs(x[1]) if x[1] else 0)
            print(f"   • 最有效因子: {best_factor[0]} (IC={best_factor[1]:.4f})")
            
            # 找出最无效的因子
            worst_factor = min(ic_values.items(), key=lambda x: abs(x[1]) if x[1] else float('inf'))
            if worst_factor[1] != 0:
                print(f"   • 最无效因子: {worst_factor[0]} (IC={worst_factor[1]:.4f})")
            
            # 检查整体有效性
            avg_ic = np.mean([v for v in ic_values.values() if v != 0]) if valid_ics else 0
            if avg_ic >= 0.03:
                print(f"   • 整体评价: ✅ 因子体系有效 (平均IC={avg_ic:.4f})")
            elif avg_ic >= 0.01:
                print(f"   • 整体评价: ⚠️ 因子体系效果一般 (平均IC={avg_ic:.4f})")
            else:
                print(f"   • 整体评价: ❌ 因子体系可能需要优化")
        
        # 检查是否所有 IC 都接近 0
        if valid_ics and all(abs(ic) < 0.01 for ic in valid_ics):
            print("\n🚨 警告: 所有因子 IC 值均较低，因子可能失效!")
            print("   建议:")
            print("   1. 检查因子计算逻辑")
            print("   2. 验证数据源准确性")
            print("   3. 考虑引入新因子")
    
    def run(self, days: int = 10):
        """运行 IC 分析"""
        print(f"\n🔍 正在计算最近 {days} 天的因子 IC 值...")
        
        # 获取数据
        df = self.get_factor_data(days)
        
        if df.empty:
            print("❌ 没有找到匹配的因子和收益数据")
            
            # 输出样本统计
            stats = self.get_sample_stats()
            if stats:
                print(f"\n📊 当前样本统计:")
                print(f"   跟踪样本总数: {stats.get('total_samples', 0)}")
                print(f"   跟踪日期范围: {stats.get('date_range', 'N/A')}")
            
            # 检查数据
            self._check_data_status()
            return
        
        print(f"✅ 获取到 {len(df)} 条匹配记录")
        
        # 计算 IC 值
        ic_values = self.calculate_ic_values(df)
        
        # 计算 Rank IC
        rank_ic_values = self.calculate_rank_ic(df)
        
        # 分析输出
        self.analyze_ic_values(ic_values, rank_ic_values)
    
    def _check_data_status(self):
        """检查数据状态"""
        print("\n🔍 数据状态检查:")
        
        try:
            # 检查因子评分表
            result = self.session.execute(text('SELECT COUNT(*) FROM stock_factor_scores'))
            factor_count = result.fetchone()[0]
            print(f"   • stock_factor_scores: {factor_count} 条")
            
            # 检查跟踪结果表
            result = self.session.execute(text('SELECT COUNT(*) FROM tracked_results'))
            track_count = result.fetchone()[0]
            print(f"   • tracked_results: {track_count} 条")
            
        except Exception as e:
            print(f"   检查失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='因子IC值分析工具')
    parser.add_argument('--days', '-d', type=int, default=10, help='计算天数 (默认10天)')
    args = parser.parse_args()
    
    monitor = FactorICMonitor()
    monitor.run(days=args.days)


if __name__ == '__main__':
    main()
