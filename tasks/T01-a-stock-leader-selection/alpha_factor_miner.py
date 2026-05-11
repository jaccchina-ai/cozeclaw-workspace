#!/usr/bin/env python3
"""
T01 Phase 5: Alpha挖掘新因子
功能: 自动发现和验证新的有效选股因子
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler
import itertools
from datetime import datetime, timedelta

class AlphaFactorMiner:
    def __init__(self, db_path='database/t01_stocks.db'):
        self.conn = sqlite3.connect(db_path)
        self.scaler = StandardScaler()
        self.factors = []
        self.validated_factors = []
        
    def load_training_data(self):
        """加载训练数据"""
        # 先从tracked_results获取所有有效记录
        query = """
        SELECT 
            tr.t_day as trade_date,
            tr.ts_code,
            tr.return_pct as target,
            tr.stock_name,
            tr.t1_open,
            tr.t2_close
        FROM tracked_results tr
        WHERE tr.return_pct IS NOT NULL
        """
        df = pd.read_sql(query, self.conn)
        
        # 添加基础计算字段
        df['price_change'] = df['t2_close'] - df['t1_open']
        df['profit_ratio'] = df['price_change'] / df['t1_open']
        
        print(f"✅ 加载 {len(df)} 条训练数据")
        return df
        
    def generate_candidate_factors(self, df):
        """生成候选因子"""
        print("\n🧬 生成候选因子...")
        
        # 从stock_factor_scores获取因子数据
        fs_query = """
        SELECT * FROM stock_factor_scores 
        WHERE trade_date IN ({}) AND ts_code IN ({})
        """.format(
            ','.join(['?']*len(df['trade_date'].unique())),
            ','.join(['?']*len(df['ts_code'].unique()))
        )
        params = list(df['trade_date'].unique()) + list(df['ts_code'].unique())
        factor_df = pd.read_sql(fs_query, self.conn, params=params)
        
        # 合并因子数据
        df = pd.merge(df, factor_df, how='left', 
                     left_on=['trade_date', 'ts_code'],
                     right_on=['trade_date', 'ts_code'])
        
        # 生成衍生因子
        # 因子组合
        if 'limit_quality_score' in df.columns and 'seal_ratio_score' in df.columns:
            df['limit_seal_combined'] = df['limit_quality_score'] * df['seal_ratio_score']
            df['seal_money_combined'] = df['seal_ratio_score'] * df['money_flow_score'].fillna(0)
            df['volume_turnover_combined'] = df['volume_ratio_score'] * df['turnover_rate_score']
            
        # 因子比例
        if 'seal_ratio_score' in df.columns and 'seal_flow_ratio_score' in df.columns:
            df['seal_ratio_diff'] = df['seal_ratio_score'] - df['seal_flow_ratio_score']
            df['seal_ratio_ratio'] = df['seal_ratio_score'] / (df['seal_flow_ratio_score'] + 0.0001)
            
        # 板块联动增强因子
        if 'sector_linkage_score' in df.columns:
            df['sector_limit_combined'] = df['sector_linkage_score'] * df['limit_quality_score'].fillna(0)
            df['sector_money_combined'] = df['sector_linkage_score'] * df['money_flow_score'].fillna(0)
            
        # 资金流入时序因子（模拟）
        df['morning_money_sim'] = df['money_flow_score'].fillna(0) * 0.6
        df['afternoon_money_sim'] = df['money_flow_score'].fillna(0) * 0.4
        df['money_persistence_sim'] = df['money_flow_score'].fillna(0).rolling(3).mean()
        
        # 市场微观结构因子（模拟）
        if 'turnover_rate_score' in df.columns:
            df['order_imbalance_sim'] = df['turnover_rate_score'] - df['volume_ratio_score'].fillna(0)
            df['large_order_ratio_sim'] = df['turnover_rate_score'] / (df['volume_ratio_score'].fillna(0) + 0.0001)
        
        # 收集所有候选因子
        candidate_factors = []
        
        # 原始因子
        original_factors = [
            'limit_quality_score', 'seal_ratio_score', 'seal_flow_ratio_score',
            'volume_ratio_score', 'turnover_rate_score', 'dragon_tiger_score',
            'money_flow_score', 'amount_rank_score', 'sector_heat_score',
            'bias_ma3_score', 'sentiment_score', 'sector_linkage_score'
        ]
        
        for factor in original_factors:
            if factor in df.columns and not df[factor].isna().all():
                candidate_factors.append(factor)
        
        # 衍生因子
        derived_factors = [
            'limit_seal_combined', 'seal_money_combined', 'volume_turnover_combined',
            'seal_ratio_diff', 'seal_ratio_ratio',
            'sector_limit_combined', 'sector_money_combined',
            'morning_money_sim', 'afternoon_money_sim', 'money_persistence_sim',
            'order_imbalance_sim', 'large_order_ratio_sim'
        ]
        
        for factor in derived_factors:
            if factor in df.columns and not df[factor].isna().all():
                candidate_factors.append(factor)
        
        self.factors = candidate_factors
        print(f"✅ 生成 {len(candidate_factors)} 个候选因子")
        
        return df
        
    def validate_factors(self, df):
        """验证因子有效性"""
        print("\n🔬 验证因子有效性...")
        
        X = df[self.factors].fillna(0)
        y = df['target']
        
        # 标准化数据
        X_scaled = self.scaler.fit_transform(X)
        
        # 计算互信息
        mi_scores = mutual_info_regression(X_scaled, y)
        mi_df = pd.DataFrame({
            'factor': self.factors,
            'mi_score': mi_scores
        }).sort_values('mi_score', ascending=False)
        
        # 训练随机森林计算特征重要性
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X_scaled, y)
        
        importances_df = pd.DataFrame({
            'factor': self.factors,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # 合并结果
        validation_df = pd.merge(mi_df, importances_df, on='factor')
        validation_df['combined_score'] = validation_df['mi_score'] * 0.4 + validation_df['importance'] * 0.6
        validation_df = validation_df.sort_values('combined_score', ascending=False)
        
        # 筛选有效因子 (combined_score > 0.01)
        valid_factors = validation_df[validation_df['combined_score'] > 0.01].copy()
        valid_factors['ic_value'] = valid_factors.apply(
            lambda row: self.calculate_ic(df, row['factor']), axis=1
        )
        
        self.validated_factors = valid_factors.to_dict('records')
        
        print(f"\n🏆 验证通过 {len(valid_factors)} 个有效因子:")
        for i, row in valid_factors.head(10).iterrows():
            print(f"{i+1}. {row['factor']}: IC={row['ic_value']:.4f}, MI={row['mi_score']:.4f}, Importance={row['importance']:.4f}")
            
        return validation_df
        
    def calculate_ic(self, df, factor_name):
        """计算因子IC值"""
        if factor_name not in df.columns:
            return 0
            
        factor = df[factor_name].fillna(0)
        target = df['target']
        
        # 处理极端值
        q1, q3 = factor.quantile([0.05, 0.95])
        factor_clipped = np.clip(factor, q1, q3)
        
        # 计算秩相关系数
        return df[[factor_name, 'target']].corr(method='spearman').iloc[0, 1]
        
    def save_factor_templates(self, validation_df):
        """保存因子模板到数据库"""
        print("\n💾 保存有效因子模板...")
        
        # 创建因子表（如果不存在）
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alpha_factors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factor_name VARCHAR(50) UNIQUE,
            factor_formula TEXT,
            ic_value FLOAT,
            importance FLOAT,
            combined_score FLOAT,
            created_at DATETIME,
            last_updated DATETIME
        )
        """)
        
        # 保存因子
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for _, row in validation_df.iterrows():
            if row['combined_score'] > 0.005:
                try:
                    cursor.execute("""
                    INSERT OR REPLACE INTO alpha_factors 
                    (factor_name, factor_formula, ic_value, importance, combined_score, created_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row['factor'],
                        f"自动生成因子 ({row['mi_score']:.3f}, {row['importance']:.3f})",
                        row['ic_value'] if 'ic_value' in row else 0,
                        row['importance'],
                        row['combined_score'],
                        now,
                        now
                    ))
                except Exception as e:
                    print(f"⚠️ 保存因子 {row['factor']} 失败: {e}")
        
        self.conn.commit()
        print(f"✅ 保存 {len(validation_df[validation_df['combined_score'] > 0.005])} 个因子模板")
        
    def generate_report(self, validation_df):
        """生成Alpha因子挖掘报告"""
        report = """
# 🚀 T01 Phase 5: Alpha因子挖掘报告

## 🎯 核心发现
"""
        
        top_factors = validation_df.head(10)
        report += f"\n## 🏆 前10个有效因子\n"
        for i, row in top_factors.iterrows():
            report += f"{i+1}. **{row['factor']}**\n"
            report += f"   - 互信息得分: {row['mi_score']:.4f}\n"
            report += f"   - 特征重要性: {row['importance']:.4f}\n"
            report += f"   - 综合得分: {row['combined_score']:.4f}\n\n"
        
        # 因子分类统计
        report += "\n## 📊 因子类型分布\n"
        factor_types = {
            '价格成交量': ['vol_price_ratio', 'amount_vol_ratio', 'price_range', 'close_change_ratio'],
            '技术指标': ['ma5_bias', 'ma10_bias', 'volatility', 'volume_trend'],
            '资金流': ['net_mf_ratio', 'large_buy_ratio', 'small_sell_ratio', 'order_imbalance'],
            '龙虎榜': ['dragon_tiger_ratio', 'net_buy_ratio'],
            '涨跌停': ['limit_duration', 'seal_strength'],
            '板块联动': ['sector_zt_ratio', 'stock_sector_lead']
        }
        
        for type_name, factors in factor_types.items():
            count = sum(1 for f in factors if f in validation_df['factor'].values)
            report += f"- {type_name}: {count} 个有效因子\n"
        
        # 建议
        report += "\n## 💡 集成建议\n"
        report += "1. 将前5个高综合得分因子加入选股模型\n"
        report += "2. 针对不同市场环境设计因子组合\n"
        report += "3. 定期重新验证因子有效性\n"
        report += "4. 考虑因子正交化处理\n"
        
        # 保存报告
        with open('alpha_factor_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("\n📝 Alpha因子报告已保存: alpha_factor_report.md")
        
        return report
        
    def close(self):
        """关闭数据库连接"""
        self.conn.close()

if __name__ == "__main__":
    print("\n🚀 T01 Phase 5: Alpha因子挖掘模块初始化")
    print("="*60)
    
    try:
        miner = AlphaFactorMiner()
        
        print("\n📥 加载训练数据...")
        df = miner.load_training_data()
        
        if len(df) < 20:
            print("⚠️ 交易数据不足，无法进行有效因子挖掘")
            miner.close()
            exit(0)
            
        df = miner.generate_candidate_factors(df)
        validation_df = miner.validate_factors(df)
        
        print("\n💾 保存因子模板...")
        miner.save_factor_templates(validation_df)
        
        print("\n📝 生成挖掘报告...")
        report = miner.generate_report(validation_df)
        
        print("\n🎉 Phase 5 Alpha因子挖掘模块集成完成!")
        print("\n📋 下一步行动:")
        print("1. 查看 alpha_factor_report.md 获取详细分析")
        print("2. 选择高综合得分因子集成到选股模型")
        print("3. 定期运行因子再验证")
        
    except Exception as e:
        print(f"\n❌ 因子挖掘失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        miner.close()