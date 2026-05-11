"""
T01 选股系统 - 正交化评分模型

集成因子正交化到评分流程
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from scoring_model import ScoringModel, FactorWeights, StockScore


class OrthogonalScoringModel(ScoringModel):
    """
    正交化评分模型
    
    在标准评分模型基础上，增加因子正交化处理
    解决封成比/封流比等因子的高度共线性问题
    """
    
    def __init__(self, weights: FactorWeights = None, use_orthogonalization: bool = True):
        """
        初始化正交化评分模型
        
        Args:
            weights: 因子权重
            use_orthogonalization: 是否使用正交化
        """
        super().__init__(weights)
        self.use_orthogonalization = use_orthogonalization
        self.scaler = StandardScaler()
        self.pca = None
        self.orthogonal_weights = None
        self.is_fitted = False
        
        # 因子名称映射
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
    
    def fit(self, historical_scores: List[Dict], returns: List[float] = None):
        """
        拟合正交化模型
        
        Args:
            historical_scores: 历史因子分数列表
            returns: 对应的历史收益率（可选）
        """
        if not historical_scores:
            print("⚠️ 无历史数据，跳过正交化拟合")
            return
        
        # 转换为DataFrame
        df = pd.DataFrame(historical_scores)
        
        # 提取因子列
        factor_cols = [f for f in self.factor_names if f in df.columns]
        if len(factor_cols) < 5:
            print(f"⚠️ 因子数据不足 ({len(factor_cols)} < 5)，跳过正交化")
            return
        
        factor_data = df[factor_cols].fillna(0)
        
        print(f"\n📊 拟合正交化模型...")
        print(f"   样本数: {len(factor_data)}")
        print(f"   因子数: {len(factor_cols)}")
        
        # 计算原始相关性
        corr = factor_data.corr()
        high_corr = self._find_high_correlations(corr, threshold=0.7)
        
        if high_corr:
            print(f"   发现 {len(high_corr)} 对高相关因子:")
            for f1, f2, r in high_corr[:3]:
                print(f"     {f1} ↔ {f2}: {r:.3f}")
        
        # 标准化
        scaled = self.scaler.fit_transform(factor_data)
        
        # PCA正交化
        self.pca = PCA(n_components=0.90)  # 保留90%方差
        orthogonal = self.pca.fit_transform(scaled)
        
        n_components = orthogonal.shape[1]
        
        print(f"   正交化后维度: {n_components}")
        print(f"   保留方差: {sum(self.pca.explained_variance_ratio_)*100:.1f}%")
        
        # 计算正交化后的权重
        if returns and len(returns) == len(orthogonal):
            # 使用收益率优化权重
            self.orthogonal_weights = self._optimize_weights(orthogonal, returns)
        else:
            # 使用等权或方差解释比例加权
            self.orthogonal_weights = self.pca.explained_variance_ratio_
        
        self.is_fitted = True
        print(f"   ✅ 正交化模型拟合完成")
    
    def _find_high_correlations(self, corr_matrix: pd.DataFrame, 
                               threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """找出高相关因子对"""
        high_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                r = abs(corr_matrix.iloc[i, j])
                if r > threshold:
                    high_corr.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr_matrix.iloc[i, j]
                    ))
        return sorted(high_corr, key=lambda x: abs(x[2]), reverse=True)
    
    def _optimize_weights(self, orthogonal: np.ndarray, 
                         returns: List[float]) -> np.ndarray:
        """
        优化正交化因子权重
        
        简单版本：使用相关系数作为权重
        """
        returns = np.array(returns)
        weights = []
        
        for i in range(orthogonal.shape[1]):
            corr = np.corrcoef(orthogonal[:, i], returns)[0, 1]
            weights.append(abs(corr))
        
        weights = np.array(weights)
        return weights / weights.sum() if weights.sum() > 0 else np.ones(len(weights)) / len(weights)
    
    def calculate_total_score(self, scores: Dict[str, float]) -> float:
        """
        计算正交化后的总分
        
        Args:
            scores: 各因子原始分数
            
        Returns:
            float: 正交化后的总分
        """
        if not self.use_orthogonalization or not self.is_fitted:
            # 使用原始加权方法
            return super().calculate_total_score(scores)
        
        # 提取因子值
        factor_values = [scores.get(f, 0) for f in self.factor_names]
        factor_array = np.array(factor_values).reshape(1, -1)
        
        # 标准化
        scaled = self.scaler.transform(factor_array)
        
        # 正交化
        orthogonal = self.pca.transform(scaled)[0]
        
        # 加权求和
        weighted_score = np.dot(orthogonal, self.orthogonal_weights)
        
        # 映射到0-100（根据经验调整）
        # 假设正交化分数范围约 -2 到 3
        final_score = (weighted_score + 2) * 20
        final_score = max(0, min(100, final_score))
        
        return final_score
    
    def get_orthogonal_info(self) -> Dict:
        """获取正交化信息"""
        if not self.is_fitted:
            return {"status": "not_fitted"}
        
        return {
            "status": "fitted",
            "original_dims": len(self.factor_names),
            "orthogonal_dims": len(self.orthogonal_weights),
            "variance_explained": sum(self.pca.explained_variance_ratio_),
            "explained_variance_ratio": self.pca.explained_variance_ratio_.tolist()
        }


class FactorAnalyzer:
    """
    因子分析器
    
    分析因子有效性和相关性
    """
    
    def __init__(self):
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
    
    def analyze_factor_correlation(self, historical_data: List[Dict]) -> Dict:
        """
        分析因子相关性
        
        Args:
            historical_data: 历史因子数据
            
        Returns:
            Dict: 分析报告
        """
        df = pd.DataFrame(historical_data)
        factor_cols = [f for f in self.factor_names if f in df.columns]
        
        if len(factor_cols) < 2:
            return {"error": "Insufficient factor data"}
        
        factor_data = df[factor_cols].fillna(0)
        
        # 相关性矩阵
        corr_matrix = factor_data.corr()
        
        # 找出高相关对
        high_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.5:
                    high_corr.append({
                        "factor1": corr_matrix.columns[i],
                        "factor2": corr_matrix.columns[j],
                        "correlation": round(r, 3)
                    })
        
        # 排序
        high_corr.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        return {
            "correlation_matrix": corr_matrix.round(3).to_dict(),
            "high_correlations": high_corr,
            "recommendation": "建议对高相关因子进行正交化处理" if high_corr else "因子相关性良好"
        }
    
    def suggest_orthogonalization(self, threshold: float = 0.7) -> List[str]:
        """
        建议需要正交化的因子
        
        基于经验规则，返回建议优先处理的因子
        """
        # 基于业务逻辑，以下因子可能存在共线性
        suggestions = []
        
        # 封单相关因子高度相关
        suggestions.append("seal_ratio_score ↔ seal_flow_ratio_score: 封单相关，建议正交化")
        
        # 资金流向相关
        suggestions.append("money_flow_score ↔ turnover_rate_score: 资金流向相关，可能相关")
        
        return suggestions


def demo_orthogonalization():
    """
    演示因子正交化效果
    """
    print("="*60)
    print("因子正交化演示")
    print("="*60)
    
    # 创建模拟数据（模拟真实场景中的相关性）
    np.random.seed(42)
    n_samples = 100
    
    # 基础因子
    base_factor = np.random.randn(n_samples)
    
    # 创建相关因子（模拟封成比和封流比的高度相关）
    seal_ratio = base_factor * 0.8 + np.random.randn(n_samples) * 0.6
    seal_flow = seal_ratio * 0.85 + np.random.randn(n_samples) * 0.5
    
    # 其他独立因子
    other_factors = np.random.randn(n_samples, 9)
    
    # 构建数据
    data = []
    for i in range(n_samples):
        data.append({
            'limit_quality_score': base_factor[i] * 0.5 + np.random.randn() * 0.8,
            'seal_ratio_score': seal_ratio[i],
            'seal_flow_ratio_score': seal_flow[i],
            'volume_ratio_score': other_factors[i, 0],
            'turnover_rate_score': other_factors[i, 1],
            'dragon_tiger_score': other_factors[i, 2],
            'money_flow_score': seal_flow[i] * 0.3 + other_factors[i, 3] * 0.9,
            'amount_rank_score': other_factors[i, 4],
            'sector_heat_score': other_factors[i, 5],
            'bias_ma3_score': other_factors[i, 6],
            'sentiment_score': other_factors[i, 7]
        })
    
    # 分析相关性
    analyzer = FactorAnalyzer()
    report = analyzer.analyze_factor_correlation(data)
    
    print("\n📊 原始因子相关性分析")
    print(f"   发现 {len(report['high_correlations'])} 对高相关因子:")
    for hc in report['high_correlations'][:3]:
        print(f"     {hc['factor1']} ↔ {hc['factor2']}: {hc['correlation']}")
    
    # 拟合正交化模型
    model = OrthogonalScoringModel(use_orthogonalization=True)
    model.fit(data)
    
    info = model.get_orthogonal_info()
    print(f"\n✅ 正交化模型信息:")
    print(f"   原始维度: {info['original_dims']}")
    print(f"   正交维度: {info['orthogonal_dims']}")
    print(f"   保留方差: {info['variance_explained']*100:.1f}%")
    
    # 测试评分
    test_scores = data[0]
    
    # 创建 StockScore 对象用于原始评分
    test_stock = StockScore(ts_code='test', stock_name='test')
    for key, value in test_scores.items():
        setattr(test_stock, key, value)
    
    original_score = ScoringModel().calculate_total_score(test_stock)
    orthogonal_score = model.calculate_total_score(test_scores)
    
    print(f"\n📝 评分对比:")
    print(f"   原始评分: {original_score:.2f}")
    print(f"   正交评分: {orthogonal_score:.2f}")
    
    print("\n" + "="*60)
    print("结论: 正交化消除了因子共线性，评分更加独立可靠")
    print("="*60)


if __name__ == '__main__':
    demo_orthogonalization()
