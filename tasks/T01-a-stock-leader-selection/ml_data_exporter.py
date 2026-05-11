"""
T01 选股系统 - 机器学习数据导出工具

提供数据导出、分析和特征工程功能
优先使用 PostgreSQL（外部持久化），SQLite 作为备用
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from database.db_config import DB_TYPE, POSTGRES_CONFIG, SQLITE_DB_PATH
from database.sqlite_manager import get_sqlite_manager


class MLDataExporter:
    """机器学习数据导出器 - 优先 PostgreSQL"""
    
    def __init__(self):
        self.db_type = DB_TYPE
        self.db_path = SQLITE_DB_PATH
        self.db = get_sqlite_manager()
    
    def _get_connection(self):
        """
        获取数据库连接，SQLite 优先（用户选择）
        
        Returns:
            连接对象和数据库类型
        """
        # 优先使用 SQLite（用户选择）
        try:
            conn = sqlite3.connect(self.db_path)
            print(f"[ML数据导出] ✅ 使用 SQLite 数据库")
            return conn, 'sqlite'
        except Exception as e:
            print(f"[ML数据导出] ❌ SQLite 连接失败: {e}")
            return None, None
    
    def export_training_data(self, start_date: str = None, end_date: str = None, 
                            output_format: str = 'dataframe') -> pd.DataFrame:
        """
        导出机器学习训练数据（支持双数据库回退）
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            output_format: 输出格式 ('dataframe', 'csv', 'json')
            
        Returns:
            训练数据 DataFrame
        """
        conn, db_type = self._get_connection()
        if conn is None:
            print("❌ 无法连接到任何数据库")
            return pd.DataFrame()
        
        # 构建查询
        query = '''
            SELECT 
                -- 日期标识
                t_day, t1_day, t2_day, ts_code, stock_name,
                
                -- T日因子评分 (12个特征)
                t_limit_quality_score,
                t_seal_ratio_score,
                t_seal_flow_ratio_score,
                t_volume_ratio_score,
                t_turnover_rate_score,
                t_dragon_tiger_score,
                t_money_flow_score,
                t_amount_rank_score,
                t_sector_heat_score,
                t_bias_ma3_score,
                t_sentiment_score,
                t_sector_linkage_score,
                t_total_score,
                
                -- T日原始值 (11个特征)
                t_limit_times,
                t_seal_ratio,
                t_seal_flow_ratio,
                t_volume_ratio,
                t_turnover_rate,
                t_net_buy_amount,
                t_main_net_inflow,
                t_amount_rank,
                t_sector_zt_count,
                t_bias_ma3,
                
                -- T+1竞价因子 (9个特征)
                t1_auction_price,
                t1_auction_pct_chg,
                t1_auction_turnover,
                t1_auction_volume_ratio,
                t1_auction_burst_ratio,
                t1_sector_resonance,
                t1_auction_score,
                t1_final_score,
                t1_is_weak_to_strong,
                
                -- T+2收益标签 (目标变量)
                t1_open,
                t2_close,
                return_pct,
                is_win,
                
                -- 选股排名
                t1_auction_rank,
                
                -- 板块信息
                sector,
                sector_role_label
                
            FROM ml_training_records
            WHERE 1=1
        '''
        
        if start_date:
            query += f" AND t1_day >= '{start_date}'"
        if end_date:
            query += f" AND t1_day <= '{end_date}'"
        
        query += " ORDER BY t1_day, t1_auction_rank"
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        print(f"✅ 导出训练数据: {len(df)} 条记录 (来源: {db_type})")
        
        if output_format == 'csv':
            output_path = f'/tmp/ml_training_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            df.to_csv(output_path, index=False)
            print(f"✅ 已保存到: {output_path}")
        elif output_format == 'json':
            output_path = f'/tmp/ml_training_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            df.to_json(output_path, orient='records', force_ascii=False)
            print(f"✅ 已保存到: {output_path}")
        
        return df
    
    def get_feature_columns(self) -> Tuple[List[str], List[str], str]:
        """
        获取特征列名和目标列名
        
        Returns:
            (评分特征列, 原始值特征列, 目标列)
        """
        score_features = [
            't_limit_quality_score',
            't_seal_ratio_score',
            't_seal_flow_ratio_score',
            't_volume_ratio_score',
            't_turnover_rate_score',
            't_dragon_tiger_score',
            't_money_flow_score',
            't_amount_rank_score',
            't_sector_heat_score',
            't_bias_ma3_score',
            't_sentiment_score',
            't_sector_linkage_score',
            't1_auction_score',
            't1_final_score',
        ]
        
        raw_features = [
            't_limit_times',
            't_seal_ratio',
            't_seal_flow_ratio',
            't_volume_ratio',
            't_turnover_rate',
            't_net_buy_amount',
            't_main_net_inflow',
            't_amount_rank',
            't_sector_zt_count',
            't_bias_ma3',
            't1_auction_pct_chg',
            't1_auction_turnover',
            't1_auction_volume_ratio',
            't1_auction_burst_ratio',
            't1_sector_resonance',
        ]
        
        target_col = 'is_win'  # 目标变量: 是否盈利 (>3%)
        
        return score_features, raw_features, target_col
    
    def analyze_feature_importance(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        分析特征与目标变量的相关性
        
        Args:
            df: 训练数据 DataFrame (如果为None则从数据库加载)
            
        Returns:
            特征相关性 DataFrame
        """
        if df is None:
            df = self.export_training_data()
        
        if df.empty:
            print("⚠️ 无训练数据")
            return pd.DataFrame()
        
        score_features, raw_features, target_col = self.get_feature_columns()
        all_features = score_features + raw_features
        
        # 计算与目标变量的相关性
        correlations = []
        for feat in all_features:
            if feat in df.columns:
                corr = df[feat].corr(df[target_col].astype(int))
                correlations.append({
                    'feature': feat,
                    'correlation': corr,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0
                })
        
        corr_df = pd.DataFrame(correlations)
        corr_df = corr_df.sort_values('abs_correlation', ascending=False)
        
        print("\n📊 特征与目标变量相关性 (降序):")
        print("-" * 50)
        for _, row in corr_df.iterrows():
            print(f"   {row['feature']}: {row['correlation']:.4f}")
        
        return corr_df
    
    def get_statistics(self) -> Dict:
        """
        获取训练数据统计信息（支持双数据库回退）
        
        Returns:
            统计信息字典
        """
        conn, db_type = self._get_connection()
        if conn is None:
            return {
                'total_records': 0,
                'date_range': '无数据',
                'win_rate': 0,
                'avg_return': 0,
                't_factor_completeness': 0,
                't1_factor_completeness': 0,
                'database': '无可用数据库'
            }
        
        cursor = conn.cursor()
        stats = {'database': db_type}
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM ml_training_records')
        stats['total_records'] = cursor.fetchone()[0]
        
        # 日期范围
        cursor.execute('SELECT MIN(t1_day), MAX(t1_day) FROM ml_training_records')
        min_date, max_date = cursor.fetchone()
        stats['date_range'] = f"{min_date} ~ {max_date}" if min_date else "无数据"
        
        # 胜率统计
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                AVG(return_pct) as avg_return
            FROM ml_training_records
        ''')
        result = cursor.fetchone()
        total, wins, avg_return = result[0], result[1], result[2]
        stats['win_rate'] = wins / total * 100 if total > 0 else 0
        stats['avg_return'] = avg_return or 0
        
        # 因子完整性
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN t_limit_quality_score > 0 THEN 1 ELSE 0 END) as t_factors,
                SUM(CASE WHEN t1_auction_score > 0 THEN 1 ELSE 0 END) as t1_factors,
                COUNT(*) as total
            FROM ml_training_records
        ''')
        result = cursor.fetchone()
        t_factors, t1_factors, total = result[0] or 0, result[1] or 0, result[2] or 0
        stats['t_factor_completeness'] = t_factors / total * 100 if total > 0 else 0
        stats['t1_factor_completeness'] = t1_factors / total * 100 if total > 0 else 0
        
        conn.close()
        
        return stats
    
    def print_report(self):
        """打印训练数据报告"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 机器学习训练数据报告")
        print("="*60)
        print(f"  数据来源: {stats.get('database', 'unknown')}")
        print(f"  总记录数: {stats['total_records']}")
        print(f"  日期范围: {stats['date_range']}")
        print(f"  胜率: {stats['win_rate']:.1f}%")
        print(f"  平均收益: {stats['avg_return']:.2f}%")
        print(f"  T日因子完整率: {stats['t_factor_completeness']:.1f}%")
        print(f"  T+1因子完整率: {stats['t1_factor_completeness']:.1f}%")
        print("="*60)
        
        # 特征维度说明
        print("\n📋 特征维度:")
        print("  - T日因子评分: 12个 (涨停质量、封成比、封流比、量比、换手率、龙虎榜、资金流向、成交额排名、板块热度、MA3乖离率、舆情、板块联动)")
        print("  - T日原始值: 11个 (涨停时间、炸板次数、封成比、封流比、量比、换手率、龙虎榜净买入、主力净流入、成交额排名、板块涨停数、MA3乖离率)")
        print("  - T+1竞价因子: 9个 (竞价价格、竞价涨跌幅、竞价换手率、竞价量比、竞价爆量比、板块共振度、竞价评分、最终评分、是否弱转强)")
        print("  - 目标变量: is_win (收益率 > 3% 为 True)")
        
        # 导出示例
        print("\n💡 导出示例:")
        print("  python3 ml_data_exporter.py --export --format csv")
        print("  python3 ml_data_exporter.py --analyze")
        print("  python3 ml_data_exporter.py --stats")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='T01 机器学习数据导出工具')
    
    parser.add_argument('--export', action='store_true', help='导出训练数据')
    parser.add_argument('--analyze', action='store_true', help='分析特征相关性')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--start-date', type=str, help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', type=str, help='结束日期 YYYYMMDD')
    parser.add_argument('--format', type=str, default='dataframe', 
                       choices=['dataframe', 'csv', 'json'],
                       help='输出格式')
    
    args = parser.parse_args()
    
    exporter = MLDataExporter()
    
    if args.export:
        df = exporter.export_training_data(
            start_date=args.start_date,
            end_date=args.end_date,
            output_format=args.format
        )
        if args.format == 'dataframe':
            print(df.head())
    
    elif args.analyze:
        df = exporter.export_training_data()
        exporter.analyze_feature_importance(df)
    
    elif args.stats:
        exporter.print_report()
    
    else:
        exporter.print_report()


if __name__ == '__main__':
    main()
