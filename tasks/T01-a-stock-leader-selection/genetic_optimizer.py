"""
T01 选股系统 - Phase 2: 遗传算法权重优化

使用DEAP实现遗传算法，自动优化因子权重
目标: 最大化胜率 + 夏普比率
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass

# DEAP遗传算法库
from deap import base, creator, tools, algorithms
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(__file__))


@dataclass
class BacktestResult:
    """回测结果"""
    win_rate: float
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    total_trades: int
    avg_return: float


class GeneticWeightOptimizer:
    """
    遗传算法权重优化器
    
    使用遗传算法自动搜索最优因子权重组合
    """
    
    # 因子列表
    FACTORS = [
        'limit_quality',
        'seal_ratio',
        'seal_flow_ratio',
        'volume_ratio',
        'turnover_rate',
        'dragon_tiger',
        'money_flow',
        'amount_rank',
        'sector_heat',
        'bias_ma3',
        'sentiment'
    ]
    
    def __init__(self, db_path: str = None):
        """
        初始化优化器
        
        Args:
            db_path: 数据库路径
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), 
                'database/t01_stocks.db'
            )
        self.db_path = db_path
        
        # 遗传算法参数
        self.population_size = 50      # 种群大小
        self.generations = 100         # 迭代代数
        self.cx_prob = 0.7             # 交叉概率
        self.mut_prob = 0.2            # 变异概率
        self.tournsize = 3             # 锦标赛选择大小
        
        # 权重约束
        self.weight_bounds = (0, 30)   # 单个权重范围
        
        # 初始化DEAP
        self._setup_deap()
    
    def _setup_deap(self):
        """设置DEAP遗传算法框架"""
        # 清除之前的定义（避免重复创建报错）
        if hasattr(creator, 'FitnessMax'):
            del creator.FitnessMax
        if hasattr(creator, 'Individual'):
            del creator.Individual
        
        # 创建适应度类（最大化）
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        
        # 创建个体类（列表）
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        # 工具箱
        self.toolbox = base.Toolbox()
        
        # 权重生成函数：随机生成0-30之间的权重
        self.toolbox.register("attr_weight", random.uniform, 0, 30)
        
        # 个体初始化：11个因子权重
        self.toolbox.register("individual", tools.initRepeat, 
                              creator.Individual, 
                              self.toolbox.attr_weight, 
                              n=len(self.FACTORS))
        
        # 种群初始化
        self.toolbox.register("population", tools.initRepeat, 
                              list, 
                              self.toolbox.individual)
        
        # 遗传算子
        self.toolbox.register("mate", tools.cxBlend, alpha=0.5)
        self.toolbox.register("mutate", tools.mutPolynomialBounded, 
                              low=self.weight_bounds[0], 
                              up=self.weight_bounds[1], 
                              eta=20.0, 
                              indpb=0.1)
        self.toolbox.register("select", tools.selTournament, 
                              tournsize=self.tournsize)
        
        # 评估函数（在optimize中设置，因为需要数据）
    
    def get_historical_data(self, days: int = 60) -> pd.DataFrame:
        """
        获取历史数据用于回测
        
        Args:
            days: 历史天数
            
        Returns:
            DataFrame: 历史因子和收益数据
        """
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT 
            s.trade_date,
            s.ts_code,
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
            d.t2_return,
            d.is_success
        FROM stock_factor_scores s
        JOIN daily_stock_records d ON s.ts_code = d.ts_code AND s.trade_date = d.trade_date
        WHERE s.created_at >= date('now', '-{days} days')
        AND d.t2_return IS NOT NULL
        ORDER BY s.trade_date, s.total_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def calculate_score(self, factor_values: np.ndarray, weights: np.ndarray) -> float:
        """
        计算加权总分
        
        Args:
            factor_values: 因子值数组
            weights: 权重数组
            
        Returns:
            float: 加权总分
        """
        # 归一化权重
        weights_norm = np.array(weights)
        if weights_norm.sum() > 0:
            weights_norm = weights_norm / weights_norm.sum()
        
        # 加权求和
        score = np.dot(factor_values, weights_norm)
        return score
    
    def backtest_weights(self, weights: List[float], df: pd.DataFrame, 
                         top_n: int = 3) -> BacktestResult:
        """
        回测权重组合
        
        Args:
            weights: 权重列表
            df: 历史数据
            top_n: 每日选股数量
            
        Returns:
            BacktestResult: 回测结果
        """
        if df.empty:
            return BacktestResult(0, 0, 0, 0, 0, 0)
        
        # 因子列名
        factor_cols = [f'{f}_score' for f in self.FACTORS]
        
        # 计算每日得分
        df = df.copy()
        weights_norm = np.array(weights)
        if weights_norm.sum() > 0:
            weights_norm = weights_norm / weights_norm.sum()
        
        # 计算加权得分
        df['calculated_score'] = df[factor_cols].fillna(0).dot(weights_norm)
        
        # 按日期分组，取每日top_n
        daily_returns = []
        daily_success = []
        
        for date, group in df.groupby('trade_date'):
            top_stocks = group.nlargest(top_n, 'calculated_score')
            if 't2_return' in top_stocks.columns:
                avg_return = top_stocks['t2_return'].mean()
                daily_returns.append(avg_return)
                daily_success.append((top_stocks['t2_return'] > 3).sum() / len(top_stocks))
        
        if not daily_returns:
            return BacktestResult(0, 0, 0, 0, 0, 0)
        
        # 计算指标
        returns_array = np.array(daily_returns)
        win_rate = np.mean(daily_success) if daily_success else 0
        total_return = returns_array.sum()
        
        # 夏普比率（日化）
        if len(returns_array) > 1 and np.std(returns_array) > 0:
            sharpe = np.mean(returns_array) / np.std(returns_array)
        else:
            sharpe = 0
        
        # 最大回撤
        cumulative = np.cumsum(returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-10)
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        return BacktestResult(
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            total_return=total_return,
            max_drawdown=max_drawdown,
            total_trades=len(daily_returns) * top_n,
            avg_return=np.mean(daily_returns)
        )
    
    def evaluate_individual(self, individual: List[float], df: pd.DataFrame) -> Tuple[float]:
        """
        评估个体的适应度
        
        Args:
            individual: 权重个体
            df: 历史数据
            
        Returns:
            Tuple: (适应度值,)
        """
        # 执行回测
        result = self.backtest_weights(individual, df)
        
        # 适应度函数：综合考虑胜率、夏普比率、总收益
        # 使用加权和，胜率权重最高
        fitness = (
            result.win_rate * 0.5 +          # 胜率权重50%
            min(result.sharpe_ratio, 2) * 0.3 +  # 夏普比率权重30%（上限2）
            min(result.total_return / 100, 1) * 0.2  # 总收益权重20%（上限100%）
        )
        
        # 惩罚项：最大回撤过大
        if result.max_drawdown < -0.2:  # 回撤超过20%
            fitness *= 0.5
        
        return (fitness,)
    
    def optimize(self, days: int = 60, top_n: int = 3, 
                 verbose: bool = True) -> Dict:
        """
        执行遗传算法优化
        
        Args:
            days: 历史数据天数
            top_n: 每日选股数量
            verbose: 是否打印日志
            
        Returns:
            Dict: 优化结果
        """
        print("\n" + "="*60)
        print("Phase 2: 遗传算法权重优化")
        print("="*60)
        
        # 1. 获取历史数据
        print(f"\n📊 加载历史数据 (最近{days}天)...")
        df = self.get_historical_data(days)
        
        if len(df) < 100:
            print(f"⚠️ 数据量不足 ({len(df)}条)，建议积累更多数据后再优化")
            return {
                'success': False,
                'error': 'Insufficient data',
                'data_count': len(df)
            }
        
        print(f"✅ 加载完成: {len(df)}条记录")
        
        # 2. 设置评估函数
        self.toolbox.register("evaluate", self.evaluate_individual, df=df)
        
        # 3. 创建初始种群
        print(f"\n🧬 初始化种群 (大小: {self.population_size})...")
        population = self.toolbox.population(n=self.population_size)
        
        # 4. 统计工具
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        # 5. 运行遗传算法
        print(f"🔄 开始进化 (代数: {self.generations})...")
        
        # 使用eaSimple算法
        population, log = algorithms.eaSimple(
            population,
            self.toolbox,
            cxpb=self.cx_prob,
            mutpb=self.mut_prob,
            ngen=self.generations,
            stats=stats,
            verbose=verbose
        )
        
        # 6. 获取最优个体
        best_individual = tools.selBest(population, k=1)[0]
        best_fitness = best_individual.fitness.values[0]
        
        print(f"\n🏆 最优个体适应度: {best_fitness:.4f}")
        
        # 7. 回测最优权重
        print("\n📈 回测最优权重...")
        best_result = self.backtest_weights(best_individual, df, top_n)
        
        # 8. 构建权重字典
        best_weights = {
            factor: round(weight, 2) 
            for factor, weight in zip(self.FACTORS, best_individual)
        }
        
        # 归一化后的权重
        weights_sum = sum(best_individual)
        if weights_sum > 0:
            best_weights_normalized = {
                factor: round(weight / weights_sum, 4) 
                for factor, weight in zip(self.FACTORS, best_individual)
            }
        else:
            best_weights_normalized = {f: 0 for f in self.FACTORS}
        
        # 9. 打印结果
        print("\n" + "="*60)
        print("优化结果:")
        print("="*60)
        print(f"\n📊 回测表现:")
        print(f"   胜率: {best_result.win_rate*100:.1f}%")
        print(f"   夏普比率: {best_result.sharpe_ratio:.2f}")
        print(f"   总收益: {best_result.total_return:.2f}%")
        print(f"   最大回撤: {best_result.max_drawdown*100:.1f}%")
        print(f"   交易次数: {best_result.total_trades}")
        print(f"   平均收益: {best_result.avg_return:.2f}%")
        
        print(f"\n⚖️ 最优权重 (归一化):")
        sorted_weights = sorted(best_weights_normalized.items(), 
                                key=lambda x: x[1], reverse=True)
        for factor, weight in sorted_weights:
            bar = "█" * int(weight * 50)
            print(f"   {factor:20s}: {weight:6.2%} {bar}")
        
        # 10. 返回结果
        result = {
            'success': True,
            'best_weights': best_weights,
            'best_weights_normalized': best_weights_normalized,
            'backtest_result': {
                'win_rate': best_result.win_rate,
                'sharpe_ratio': best_result.sharpe_ratio,
                'total_return': best_result.total_return,
                'max_drawdown': best_result.max_drawdown,
                'total_trades': best_result.total_trades,
                'avg_return': best_result.avg_return
            },
            'fitness': best_fitness,
            'generations': self.generations,
            'population_size': self.population_size,
            'data_count': len(df),
            'optimization_date': datetime.now().strftime('%Y%m%d')
        }
        
        # 11. 保存结果
        self._save_optimization_result(result)
        
        return result
    
    def _save_optimization_result(self, result: Dict):
        """保存优化结果"""
        result_path = os.path.join(
            os.path.dirname(__file__),
            f"optimization_results/ga_weights_{result['optimization_date']}.json"
        )
        
        # 确保目录存在
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存: {result_path}")
    
    def compare_with_current(self, optimized_weights: Dict, 
                              current_weights: Dict = None) -> Dict:
        """
        对比优化后的权重与当前权重
        
        Args:
            optimized_weights: 优化后的权重
            current_weights: 当前权重
            
        Returns:
            Dict: 对比结果
        """
        if current_weights is None:
            # 使用默认权重
            current_weights = {
                'limit_quality': 18,
                'seal_ratio': 20,
                'seal_flow_ratio': 20,
                'volume_ratio': 5,
                'turnover_rate': 5,
                'dragon_tiger': 10,
                'money_flow': 8,
                'amount_rank': 5,
                'sector_heat': 4,
                'bias_ma3': 3,
                'sentiment': 2
            }
        
        print("\n" + "="*60)
        print("权重对比分析")
        print("="*60)
        
        changes = []
        for factor in self.FACTORS:
            old_w = current_weights.get(factor, 10)
            new_w = optimized_weights.get(factor, 0) * 100  # 转换为百分比
            change = new_w - old_w
            change_pct = (change / old_w * 100) if old_w > 0 else 0
            
            changes.append({
                'factor': factor,
                'old_weight': old_w,
                'new_weight': new_w,
                'change': change,
                'change_pct': change_pct
            })
            
            direction = "↑" if change > 0 else "↓" if change < 0 else "→"
            print(f"   {factor:20s}: {old_w:5.1f} → {new_w:5.1f} "
                  f"({change:+5.1f}) {direction}")
        
        # 按变化幅度排序
        changes.sort(key=lambda x: abs(x['change']), reverse=True)
        
        print(f"\n📊 变化最大的因子:")
        for c in changes[:3]:
            print(f"   {c['factor']}: {c['change']:+.1f} ({c['change_pct']:+.1f}%)")
        
        return {
            'changes': changes,
            'max_increase': changes[0] if changes and changes[0]['change'] > 0 else None,
            'max_decrease': changes[-1] if changes and changes[-1]['change'] < 0 else None
        }


class WeightOptimizerRunner:
    """权重优化运行器"""
    
    @staticmethod
    def run_phase2_optimization(days: int = 60, force: bool = False) -> Dict:
        """
        运行Phase 2优化
        
        Args:
            days: 历史数据天数
            force: 是否强制执行（无视数据量要求）
            
        Returns:
            Dict: 优化结果
        """
        optimizer = GeneticWeightOptimizer()
        
        # 检查数据量
        df = optimizer.get_historical_data(days)
        
        if len(df) < 100 and not force:
            print(f"\n⚠️ 数据量不足: {len(df)}条")
            print("建议继续积累数据，或设置 force=True 强制执行")
            return {
                'success': False,
                'phase': 2,
                'error': 'Insufficient data',
                'data_count': len(df),
                'recommendation': '继续积累历史数据，建议至少100条记录'
            }
        
        # 执行优化
        result = optimizer.optimize(days=days)
        
        # 如果优化成功，进行权重对比
        if result.get('success'):
            optimizer.compare_with_current(result['best_weights_normalized'])
        
        return {
            'success': result.get('success', False),
            'phase': 2,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    # 测试Phase 2优化
    print("="*60)
    print("T01 Phase 2: 遗传算法权重优化测试")
    print("="*60)
    
    result = WeightOptimizerRunner.run_phase2_optimization(days=60)
    
    print("\n" + "="*60)
    print("Phase 2 完成")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
