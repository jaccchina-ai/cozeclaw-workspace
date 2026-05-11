#!/usr/bin/env python3
"""
T01 Phase 4: 深度归因分析模块
功能: 使用SHAP值分析因子对收益的贡献，识别盈利/亏损模式
"""

import pandas as pd
import numpy as np
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

class AttributionAnalyzer:
    def __init__(self, db_path='database/t01_stocks.db'):
        self.conn = sqlite3.connect(db_path)
        self.models = {}
        self.scaler = StandardScaler()
        
    def load_data(self):
        """加载交易数据和因子数据"""
        query = """
        SELECT 
            ts.t_day as trade_date, 
            ts.ts_code, 
            ts.return_pct as profit_pct,
            fs.*
        FROM tracked_results ts
        JOIN stock_factor_scores fs ON ts.ts_code = fs.ts_code AND ts.t_day = fs.trade_date
        WHERE ts.return_pct IS NOT NULL
        """
        df = pd.read_sql(query, self.conn)
        
        # 提取因子列
        factor_cols = [col for col in df.columns if col.endswith('_score') and not col.startswith('profit')]
        
        return df, factor_cols
        
    def train_models(self, df, factor_cols):
        """训练收益预测模型"""
        X = df[factor_cols]
        y = df['profit_pct']
        
        # 标准化数据
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练随机森林模型
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X_scaled, y)
        
        # 训练KMeans聚类模型
        kmeans = KMeans(n_clusters=3, random_state=42)
        df['cluster'] = kmeans.fit_predict(X_scaled)
        
        self.models['rf'] = rf
        self.models['kmeans'] = kmeans
        
        return rf, kmeans
        
    def analyze_shap(self, rf, X):
        """SHAP值分析"""
        explainer = shap.TreeExplainer(rf)
        shap_values = explainer.shap_values(X)
        
        return explainer, shap_values
        
    def generate_report(self, df, factor_cols, explainer, shap_values):
        """生成归因分析报告"""
        report = """
# 📊 T01 策略深度归因分析报告

## 🎯 核心发现
"""
        
        # 因子重要性 - 使用SHAP值计算
        shap_importances = pd.DataFrame({
            'factor': factor_cols,
            'importance': np.mean(np.abs(shap_values), axis=0)
        }).sort_values('importance', ascending=False)
        
        report += "\n## 🏆 因子重要性排名\n"
        for i, row in shap_importances.iterrows():
            report += f"{i+1}. {row['factor']}: {row['importance']:.4f}\n"
        
        # 聚类分析
        cluster_analysis = df.groupby('cluster')['profit_pct'].agg(['mean', 'count', 'std'])
        report += "\n## 🔍 交易类型聚类\n"
        for cluster, row in cluster_analysis.iterrows():
            report += f"\n### Cluster {cluster}: {row['count']} 笔交易\n"
            report += f"   平均收益率: {row['mean']:.2f}%\n"
            report += f"   收益率波动: {row['std']:.2f}%\n"
        
        return report
        
    def save_visualizations(self, shap_values, X, factor_cols):
        """保存可视化结果"""
        # SHAP汇总图
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X, feature_names=factor_cols, plot_type="bar")
        plt.savefig('shap_summary.png', bbox_inches='tight')
        plt.close()
        
        # SHAP beeswarm图
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X, feature_names=factor_cols)
        plt.savefig('shap_beeswarm.png', bbox_inches='tight')
        plt.close()
        
    def close(self):
        """关闭数据库连接"""
        self.conn.close()

if __name__ == "__main__":
    print("🚀 T01 Phase 4: 深度归因分析模块初始化")
    
    analyzer = AttributionAnalyzer()
    
    try:
        print("📥 加载交易数据...")
        df, factor_cols = analyzer.load_data()
        
        if len(df) < 30:
            print(f"⚠️ 交易数据不足 ({len(df)}条)，请至少积累30条交易数据后再运行")
            analyzer.close()
            exit(0)
        
        print(f"✅ 加载 {len(df)} 条交易数据，{len(factor_cols)} 个因子")
        
        print("🧠 训练分析模型...")
        rf, kmeans = analyzer.train_models(df, factor_cols)
        print("✅ 模型训练完成")
        
        print("🔍 生成SHAP归因分析...")
        X_scaled = analyzer.scaler.transform(df[factor_cols])
        explainer, shap_values = analyzer.analyze_shap(rf, X_scaled)
        print("✅ SHAP分析完成")
        
        print("📝 生成分析报告...")
        report = analyzer.generate_report(df, factor_cols, explainer, shap_values)
        
        # 保存报告
        with open('attribution_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("✅ 归因报告已保存: attribution_report.md")
        
        print("🎨 生成可视化结果...")
        analyzer.save_visualizations(shap_values, X_scaled, factor_cols)
        print("✅ 可视化结果已保存")
        
        print("\n🎉 Phase 4 深度归因分析模块集成完成!")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()