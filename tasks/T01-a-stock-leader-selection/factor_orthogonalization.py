"""
T01 选股系统 - 因子正交化模块

Phase 1: 解决因子多重共线性问题
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import sqlite3
import os


class FactorOrthogonalizer:
    """
    因子正交化处理器
    
    使用PCA或Gram-Schmidt方法消除因子间的多重共线性
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化正交化处理器
        
        Args:
            db_path: 数据库路径
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), 
                'database/t01_stocks.db'
            )
        self.db_path = db_path
        self.scaler = StandardScaler()
        self.pca = None
        self.factor_names = [
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
            'sentiment_score'
        ]
    
    def get_historical_factor_data(self, days: int = 30) -> pd.DataFrame:
        """
        获取历史因子数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            DataFrame: 因子数据
        """
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT 
            trade_date,
            ts_code,
            limit_quality_score,
            seal_ratio_score,
            seal_flow_ratio_score,
            volume_ratio_score,
            turnover_rate_score,
            dragon_tiger_score,
            money_flow_score,
            amount_rank_score,
            sector_heat_score,
            bias_ma3_score,
            sentiment_score,
            total_score
        FROM stock_factor_scores
        WHERE trade_date >= date('now', '-{days} days')
        ORDER BY trade_date DESC, total_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def calculate_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子相关性矩阵
        
        Args:
            df: 因子数据
            
        Returns:
            DataFrame: 相关性矩阵
        """
        factor_cols = [col for col in df.columns if col.endswith('_score')]
        correlation_matrix = df[factor_cols].corr()
        return correlation_matrix
    
    def find_high_correlations(self, correlation_matrix: pd.DataFrame, 
                               threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        找出高相关性的因子对
        
        Args:
            correlation_matrix: 相关性矩阵
            threshold: 相关性阈值
            
        Returns:
            List: [(因子1, 因子2, 相关系数), ...]
        """
        high_corr_pairs = []
        
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr = abs(correlation_matrix.iloc[i, j])
                if corr > threshold:
                    high_corr_pairs.append((
                        correlation_matrix.columns[i],
                        correlation_matrix.columns[j],
                        correlation_matrix.iloc[i, j]
                    ))
        
        # 按相关系数排序
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        return high_corr_pairs
    
    def orthogonalize_pca(self, df: pd.DataFrame, 
                          variance_threshold: float = 0.90) -> Tuple[pd.DataFrame, Dict]:
        """
        使用PCA进行因子正交化
        
        Args:
            df: 原始因子数据
            variance_threshold: 保留的方差比例
            
        Returns:
            (正交化后的数据, 统计信息)
        """
        factor_cols = [col for col in df.columns if col.endswith('_score')]
        factor_data = df[factor_cols].fillna(0)
        
        # 标准化
        scaled_data = self.scaler.fit_transform(factor_data)
        
        # PCA正交化
        self.pca = PCA(n_components=variance_threshold)
        orthogonal_data = self.pca.fit_transform(scaled_data)
        
        # 创建新的DataFrame
        n_components = orthogonal_data.shape[1]
        orthogonal_cols = [f'pca_factor_{i+1}' for i in range(n_components)]
        
        orthogonal_df = pd.DataFrame(
            orthogonal_data, 
            columns=orthogonal_cols,
            index=df.index
        )
        
        # 保留原始标识列
        for col in ['trade_date', 'ts_code']:
            if col in df.columns:
                orthogonal_df[col] = df[col].values
        
        # 统计信息
        stats = {
            'original_factors': len(factor_cols),
            'orthogonal_factors': n_components,
            'variance_explained': sum(self.pca.explained_variance_ratio_),
            'explained_variance_ratio': self.pca.explained_variance_ratio_.tolist(),
            'components': self.pca.components_.tolist()
        }
        
        return orthogonal_df, stats
    
    def orthogonalize_gram_schmidt(self, df: pd.DataFrame, 
                                   priority_order: List[str] = None) -> pd.DataFrame:
        """
        使用Gram-Schmidt正交化
        
        按优先级顺序正交化，保留重要因子的原始信息
        
        Args:
            df: 原始因子数据
            priority_order: 因子优先级顺序（默认按原始列顺序）
            
        Returns:
            DataFrame: 正交化后的数据
        """
        factor_cols = [col for col in df.columns if col.endswith('_score')]
        
        if priority_order is None:
            # 默认优先级：封单相关 > 资金相关 > 其他
            priority_order = [
                'seal_flow_ratio_score',  # 封流比（最重要）
                'seal_ratio_score',       # 封成比
                'money_flow_score',       # 资金流向
                'dragon_tiger_score',     # 龙虎榜
                'limit_quality_score',    # 涨停质量
                'volume_ratio_score',     # 量比
                'turnover_rate_score',    # 换手率
                'amount_rank_score',      # 成交额排名
                'sector_heat_score',      # 板块热度
                'bias_ma3_score',         # 乖离率
                'sentiment_score'         # 舆情
            ]
            # 只保留存在的列
            priority_order = [f for f in priority_order if f in factor_cols]
        
        # 获取因子数据
        X = df[priority_order].fillna(0).values
        n_samples, n_features = X.shape
        
        # Gram-Schmidt正交化
        Q = np.zeros((n_samples, n_features))
        
        for i in range(n_features):
            v = X[:, i].copy()
            
            # 减去在前面的正交向量上的投影
            for j in range(i):
                qj = Q[:, j]
                # 投影系数
                coef = np.dot(v, qj) / np.dot(qj, qj) if np.dot(qj, qj) > 0 else 0
                v = v - coef * qj
            
            # 归一化
            norm = np.linalg.norm(v)
            if norm > 0:
                Q[:, i] = v / norm
            else:
                Q[:, i] = v
        
        # 创建新的DataFrame
        orthogonal_cols = [f'orth_{col.replace("_score", "")}' for col in priority_order]
        orthogonal_df = pd.DataFrame(Q, columns=orthogonal_cols, index=df.index)
        
        # 保留原始标识列
        for col in ['trade_date', 'ts_code']:
            if col in df.columns:
                orthogonal_df[col] = df[col].values
        
        return orthogonal_df
    
    def inverse_transform_scores(self, orthogonal_scores: np.ndarray) -> Dict[str, float]:
        """
        将正交化后的分数转换回原始因子空间
        
        Args:
            orthogonal_scores: 正交化后的分数
            
        Returns:
            Dict: 各原始因子的重建分数
        """
        if self.pca is None:
            raise ValueError("PCA not fitted. Call orthogonalize_pca first.")
        
        # 逆变换
        reconstructed = self.pca.inverse_transform([orthogonal_scores])
        reconstructed = self.scaler.inverse_transform(reconstructed)[0]
        
        return dict(zip(self.factor_names, reconstructed))
    
    def analyze_and_report(self, days: int = 30) -> Dict:
        """
        分析因子相关性并生成报告
        
        Args:
            days: 分析最近多少天的数据
            
        Returns:
            Dict: 分析报告
        """
        print("\n" + "="*60)
        print("因子正交化分析报告")
        print("="*60)
        
        # 1. 获取数据
        df = self.get_historical_factor_data(days)
        print(f"\n📊 数据样本: {len(df)} 条记录")
        
        # 2. 计算相关性矩阵
        corr_matrix = self.calculate_correlation_matrix(df)
        print("\n📈 因子相关性矩阵:")
        print(corr_matrix.round(2))
        
        # 3. 找出高相关因子对
        high_corr = self.find_high_correlations(corr_matrix, threshold=0.5)
        print(f"\n⚠️ 高相关性因子对 (|r| > 0.5): {len(high_corr)} 对")
        for f1, f2, r in high_corr[:5]:  # 显示前5对
            print(f"   {f1} ↔ {f2}: {r:.3f}")
        
        # 4. PCA正交化
        orth_df, stats = self.orthogonalize_pca(df, variance_threshold=0.90)
        print(f"\n✅ PCA正交化结果:")
        print(f"   原始因子数: {stats['original_factors']}")
        print(f"   正交因子数: {stats['orthogonal_factors']}")
        print(f"   保留方差: {stats['variance_explained']*100:.1f}%")
        print(f"\n   各主成分方差解释比例:")
        for i, ratio in enumerate(stats['explained_variance_ratio'][:5]):
            print(f"     PC{i+1}: {ratio*100:.1f}%")
        
        # 5. 生成建议
        recommendations = []
        if high_corr:
            recommendations.append(f"发现 {len(high_corr)} 对高相关因子，建议进行正交化处理")
        if stats['orthogonal_factors'] < stats['original_factors']:
            recommendations.append(f"PCA降维可压缩至 {stats['orthogonal_factors']} 个独立因子")
        
        report = {
            'data_count': len(df),
            'correlation_matrix': corr_matrix.to_dict(),
            'high_correlations': high_corr,
            'pca_stats': stats,
            'recommendations': recommendations
        }
        
        return report


class OrthogonalScoringModel:
    """
    基于正交化因子的评分模型
    
    使用正交化后的因子进行评分，消除共线性影响
    """
    
    def __init__(self, orthogonalizer: FactorOrthogonalizer = None):
        self.orthogonalizer = orthogonalizer or FactorOrthogonalizer()
        self.weights = None  # 正交化因子的权重
    
    def fit(self, df: pd.DataFrame, returns: pd.Series = None):
        """
        拟合模型，学习正交化因子权重
        
        Args:
            df: 历史因子数据
            returns: 对应的收益率（用于优化权重）
        """
        # 正交化
        orth_df, stats = self.orthogonalizer.orthogonalize_pca(df)
        
        # 初始化权重（等权或基于方差解释比例）
        n_factors = stats['orthogonal_factors']
        self.weights = np.ones(n_factors) / n_factors
        
        # 如果有收益数据，可以使用回归优化权重
        if returns is not None and len(returns) == len(orth_df):
            from sklearn.linear_model import LinearRegression
            
            factor_cols = [c for c in orth_df.columns if c.startswith('pca_factor_')]
            X = orth_df[factor_cols].values
            y = returns.values
            
            model = LinearRegression()
            model.fit(X, y)
            
            # 归一化权重
            weights = np.abs(model.coef_)
            self.weights = weights / weights.sum()
    
    def score(self, factor_values: Dict[str, float]) -> float:
        """
        计算正交化后的综合评分
        
        Args:
            factor_values: 原始因子值字典
            
        Returns:
            float: 正交化后的综合评分
        """
        if self.weights is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # 转换为数组并标准化
        factor_array = np.array([
            factor_values.get(f, 0) for f in self.orthogonalizer.factor_names
        ]).reshape(1, -1)
        
        scaled = self.orthogonalizer.scaler.transform(factor_array)
        orthogonal = self.orthogonalizer.pca.transform(scaled)[0]
        
        # 加权求和
        score = np.dot(orthogonal, self.weights)
        
        # 映射到0-100
        score = (score + 3) * 15  # 假设分数范围约-3到3
        score = max(0, min(100, score))
        
        return score


if __name__ == '__main__':
    # 测试
    orth = FactorOrthogonalizer()
    report = orth.analyze_and_report(days=30)
    
    print("\n" + "="*60)
    print("建议:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
