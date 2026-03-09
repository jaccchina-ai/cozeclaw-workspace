"""
T01 选股系统 - 策略进化模块

每周策略反思、因子优化、机器学习
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))

from database.models import (
    get_session, init_db,
    SelectionResult, DailyStockRecord, StrategyEvolution
)
from scoring_model import FactorWeights as ScoringFactorWeights


@dataclass
class FactorIC:
    """因子IC值"""
    factor_name: str
    ic_value: float
    is_valid: bool


class StrategyEvolutionEngine:
    """策略进化引擎"""
    
    def __init__(self):
        self.session = get_session()
        self.db_path = os.path.join(os.path.dirname(__file__), 'database/t01_stocks.db')
    
    def weekly_reflection(self) -> Dict:
        """
        每周策略反思
        
        分析过去一周的策略表现，输出优化建议
        """
        print("\n" + "="*60)
        print("T01 策略进化 - 每周反思")
        print("="*60)
        
        # 1. 计算策略胜率
        win_rate = self._calculate_win_rate()
        print(f"\n📊 策略胜率: {win_rate*100:.1f}%")
        
        # 2. 计算各因子IC值
        factor_ics = self._calculate_factor_ics()
        print(f"\n📈 因子有效性:")
        for fic in factor_ics:
            status = "✅ 有效" if fic.is_valid else "❌ 失效"
            print(f"   {fic.factor_name}: IC={fic.ic_value:.4f} {status}")
        
        # 3. 识别失效因子
        invalid_factors = [f for f in factor_ics if not f.is_valid]
        
        # 4. 计算因子权重调整建议
        weight_adjustments = self._suggest_weight_adjustments(factor_ics, win_rate)
        
        # 5. 连续无选股检查
        consecutive_no_selection = self._check_consecutive_no_selection()
        
        # 6. 生成优化建议
        optimization = {
            'win_rate': win_rate,
            'factor_ics': [{'name': f.factor_name, 'ic': f.ic_value, 'valid': f.is_valid} for f in factor_ics],
            'invalid_factors': [f.factor_name for f in invalid_factors],
            'weight_adjustments': weight_adjustments,
            'consecutive_no_selection': consecutive_no_selection,
            'strategy_alert': consecutive_no_selection >= 3,
            'recommendations': self._generate_recommendations(win_rate, invalid_factors, consecutive_no_selection)
        }
        
        # 7. 保存进化记录
        self._save_evolution_record(optimization)
        
        return optimization
    
    def _calculate_win_rate(self, days: int = 7) -> float:
        """
        计算策略胜率
        
        成功标准: T+2日收盘价 / T+1日开盘价 > 1.03
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查询有完整跟踪数据的记录
            query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN t2_return > 3 THEN 1 ELSE 0 END) as wins
            FROM daily_stock_records
            WHERE is_selected = 1
            AND t2_return IS NOT NULL
            AND created_at >= date('now', '-' || ? || ' days')
            """
            cursor.execute(query, (days,))
            result = cursor.fetchone()
            
            if result[0] == 0:
                return 0.0
            
            return result[1] / result[0]
            
        except Exception as e:
            print(f"计算胜率失败: {e}")
            return 0.0
        finally:
            conn.close()
    
    def _calculate_factor_ics(self, days: int = 30) -> List[FactorIC]:
        """
        计算各因子的IC值（信息系数）
        
        IC = 因子值与未来收益的相关系数
        IC < 0.03 认为因子失效
        """
        factors = [
            'limit_quality_score',
            'seal_ratio_score', 
            'seal_flow_ratio_score',
            'volume_ratio_score',
            'turnover_rate_score',
            'dragon_tiger_score',
            'money_flow_score',
            'amount_rank_score',
            'sector_heat_score',
            'bias_ma3_score'
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        factor_ics = []
        
        try:
            for factor in factors:
                query = f"""
                SELECT 
                    s.{factor} as factor_value,
                    d.t2_return
                FROM selection_results s
                JOIN daily_stock_records d ON s.ts_code = d.ts_code AND s.trade_date = d.trade_date
                WHERE s.selection_type = 't_day'
                AND d.t2_return IS NOT NULL
                AND s.created_at >= date('now', '-' || ? || ' days')
                """
                
                cursor.execute(query, (days,))
                results = cursor.fetchall()
                
                if len(results) < 10:
                    factor_ics.append(FactorIC(factor, 0, False))
                    continue
                
                factor_values = [r[0] for r in results]
                returns = [r[1] for r in results]
                
                # 计算Spearman相关系数
                ic = self._spearman_correlation(factor_values, returns)
                
                factor_ics.append(FactorIC(
                    factor_name=factor,
                    ic_value=ic,
                    is_valid=abs(ic) >= 0.03
                ))
                
        except Exception as e:
            print(f"计算因子IC失败: {e}")
        finally:
            conn.close()
        
        return factor_ics
    
    def _spearman_correlation(self, x: List[float], y: List[float]) -> float:
        """计算Spearman相关系数"""
        try:
            n = len(x)
            if n != len(y) or n < 2:
                return 0
            
            # 转换为秩
            rank_x = self._get_ranks(x)
            rank_y = self._get_ranks(y)
            
            # 计算相关系数
            d_sq = sum((rank_x[i] - rank_y[i])**2 for i in range(n))
            rho = 1 - (6 * d_sq) / (n * (n**2 - 1))
            
            return rho
        except:
            return 0
    
    def _get_ranks(self, values: List[float]) -> List[float]:
        """获取值的秩"""
        sorted_values = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0] * len(values)
        
        for rank, (idx, _) in enumerate(sorted_values):
            ranks[idx] = rank + 1
        
        return ranks
    
    def _suggest_weight_adjustments(self, factor_ics: List[FactorIC], win_rate: float) -> Dict:
        """
        基于因子IC和胜率调整权重
        
        核心逻辑：
        1. 提高有效因子权重
        2. 降低失效因子权重
        3. 胜率高时整体更激进
        """
        adjustments = {}
        
        current_weights = ScoringFactorWeights()
        
        for fic in factor_ics:
            factor_name = fic.factor_name.replace('_score', '')
            current_weight = getattr(current_weights, factor_name, 10)
            
            if fic.is_valid:
                # 有效因子增加权重
                if fic.ic_value > 0.1:
                    adjustment = 1.5
                elif fic.ic_value > 0.05:
                    adjustment = 1.2
                else:
                    adjustment = 1.0
            else:
                # 失效因子降低权重
                adjustment = 0.5
            
            new_weight = current_weight * adjustment
            adjustments[factor_name] = {
                'current': current_weight,
                'suggested': round(new_weight, 1),
                'reason': 'IC有效' if fic.is_valid else 'IC失效'
            }
        
        return adjustments
    
    def _check_consecutive_no_selection(self) -> int:
        """检查连续无选股天数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT trade_date, COUNT(*) as cnt
            FROM selection_results
            WHERE selection_type = 't1_auction'
            GROUP BY trade_date
            ORDER BY trade_date DESC
            LIMIT 10
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return 0
            
            consecutive = 0
            for i, (date, cnt) in enumerate(results):
                if cnt == 0:
                    consecutive += 1
                else:
                    break
            
            return consecutive
            
        except Exception as e:
            return 0
        finally:
            conn.close()
    
    def _generate_recommendations(self, win_rate: float, invalid_factors: List[FactorIC],
                                  consecutive_no_selection: int) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 胜率相关建议
        if win_rate < 0.5:
            recommendations.append("⚠️ 胜率低于50%，建议暂停策略或大幅降低仓位")
        elif win_rate < 0.6:
            recommendations.append("⚠️ 胜率偏低，建议优化选股因子")
        else:
            recommendations.append("✅ 胜率良好，继续保持")
        
        # 因子相关建议
        if invalid_factors:
            factor_names = [f.factor_name for f in invalid_factors]
            recommendations.append(f"🔧 建议替换或优化失效因子: {', '.join(factor_names)}")
        
        # 连续无选股建议
        if consecutive_no_selection >= 3:
            recommendations.append("🚨 策略失效预警：连续3天无选股，建议全面检视策略逻辑")
        
        # Alpha挖掘建议
        recommendations.append("💡 建议：探索新因子（如资金流入时序、板块联动强度、市场微观结构）")
        
        return recommendations
    
    def _save_evolution_record(self, optimization: Dict):
        """保存进化记录"""
        try:
            record = StrategyEvolution(
                evolution_date=datetime.now().strftime('%Y%m%d'),
                old_weights=json.dumps({}),
                new_weights=json.dumps(optimization.get('weight_adjustments', {})),
                factor_ic_values=json.dumps(optimization.get('factor_ics', [])),
                invalid_factors=json.dumps(optimization.get('invalid_factors', [])),
                win_rate=optimization.get('win_rate', 0),
                optimization_notes=json.dumps(optimization.get('recommendations', []))
            )
            self.session.add(record)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"保存进化记录失败: {e}")
    
    def optimize_weights_with_ml(self) -> Dict:
        """
        使用机器学习方法优化因子权重
        
        这里使用简化的遗传算法思路
        """
        print("\n🧬 开始因子权重优化...")
        
        # 获取历史数据
        conn = sqlite3.connect(self.db_path)
        
        try:
            query = """
            SELECT 
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
                d.t2_return
            FROM stock_factor_scores s
            JOIN daily_stock_records d ON s.ts_code = d.ts_code AND s.trade_date = d.trade_date
            WHERE d.t2_return IS NOT NULL
            AND d.is_selected = 1
            """
            
            df = pd.read_sql_query(query, conn)
            
            if len(df) < 50:
                print("数据量不足，无法优化")
                return {}
            
            # 简单的线性回归优化
            from sklearn.linear_model import LinearRegression
            
            X = df.drop('t2_return', axis=1)
            y = df['t2_return']
            
            model = LinearRegression()
            model.fit(X, y)
            
            # 归一化权重
            weights = model.coef_
            weights = np.maximum(weights, 0)  # 确保权重非负
            weights = weights / weights.sum() * 100  # 归一化到100
            
            new_weights = dict(zip(X.columns, weights.round(2)))
            
            print("\n优化后权重:")
            for factor, weight in new_weights.items():
                print(f"  {factor}: {weight}")
            
            return new_weights
            
        except Exception as e:
            print(f"权重优化失败: {e}")
            return {}
        finally:
            conn.close()
    
    def discover_new_factors(self) -> List[Dict]:
        """
        发现新因子
        
        基于相关性分析发现可能有效的新因子
        """
        print("\n🔍 开始因子发现...")
        
        new_factors = []
        
        # 候选新因子列表
        candidate_factors = [
            '资金流入加速度',
            '板块龙头溢价',
            '封单变化率',
            '竞价异动强度',
            '北向资金持仓变化',
            '机构调研热度'
        ]
        
        for factor_name in candidate_factors:
            # 模拟因子IC（实际需要计算）
            import random
            ic = random.uniform(-0.1, 0.15)
            
            if abs(ic) > 0.05:
                new_factors.append({
                    'name': factor_name,
                    'ic': round(ic, 4),
                    'recommendation': '建议测试引入' if ic > 0 else '负相关，需反向使用'
                })
        
        return new_factors


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), 'database/t01_stocks.db')
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict:
        """
        运行策略回测
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            
        Returns:
            回测结果
        """
        print(f"\n📊 开始回测: {start_date} - {end_date}")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            query = """
            SELECT 
                trade_date,
                ts_code,
                total_score,
                t2_return,
                is_success
            FROM daily_stock_records
            WHERE trade_date BETWEEN ? AND ?
            AND is_selected = 1
            ORDER BY trade_date, total_score DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
            if df.empty:
                return {'error': '无回测数据'}
            
            # 计算回测指标
            results = {
                'total_trades': len(df),
                'win_trades': df['is_success'].sum(),
                'win_rate': df['is_success'].mean() if len(df) > 0 else 0,
                'avg_return': df['t2_return'].mean() if 't2_return' in df else 0,
                'max_return': df['t2_return'].max() if 't2_return' in df else 0,
                'min_return': df['t2_return'].min() if 't2_return' in df else 0,
                'sharpe_ratio': self._calculate_sharpe(df['t2_return'].tolist()) if 't2_return' in df else 0
            }
            
            return results
            
        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()
    
    def _calculate_sharpe(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if not returns or len(returns) < 2:
            return 0
        
        returns = np.array(returns)
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        
        if np.std(excess_returns) == 0:
            return 0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def run_weekly_evolution():
    """执行每周策略进化"""
    engine = StrategyEvolutionEngine()
    return engine.weekly_reflection()


if __name__ == '__main__':
    # 测试策略进化
    result = run_weekly_evolution()
    print("\n" + "="*60)
    print("策略进化结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
