#!/usr/bin/env python3
"""
T01 选股系统 - 主力资金流向多维度分析模块

增强版资金流向分析，包含:
1. 主力资金流入流出统计
2. 资金流向时序分析
3. 资金流向与股价联动分析
4. 板块资金流向对比
5. 异常资金流向检测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sqlite3
from sqlalchemy import text

class AdvancedMoneyFlowAnalyzer:
    """高级资金流向分析器"""
    
    def __init__(self):
        from database.models import get_session, DB_TYPE, POSTGRES_CONFIG
        self.session = get_session()
        self.db_type = DB_TYPE
        self.postgres_config = POSTGRES_CONFIG
        self.db_path = 'database/t01_stocks.db'
    
    def analyze_single_stock(self, ts_code: str, start_date: str = None, end_date: str = None) -> Dict:
        """
        单只股票资金流向多维度分析
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        result = {
            'ts_code': ts_code,
            'analysis_period': f'{start_date} to {end_date}',
            'fundamental_analysis': {},
            'flow_statistics': {},
            'time_series_analysis': {},
            'price_correlation': {},
            'sector_comparison': {},
            'anomaly_detection': {},
            'recommendations': []
        }
        
        # 1. 基础数据分析
        result['fundamental_analysis'] = self._analyze_fundamental(ts_code)
        
        # 2. 资金流向统计分析
        result['flow_statistics'] = self._analyze_flow_statistics(ts_code, start_date, end_date)
        
        # 3. 时序分析
        result['time_series_analysis'] = self._analyze_time_series(ts_code, start_date, end_date)
        
        # 4. 股价联动分析
        result['price_correlation'] = self._analyze_price_correlation(ts_code, start_date, end_date)
        
        # 5. 板块对比分析
        result['sector_comparison'] = self._analyze_sector_comparison(ts_code, start_date, end_date)
        
        # 6. 异常检测
        result['anomaly_detection'] = self._detect_anomalies(ts_code, start_date, end_date)
        
        # 7. 生成建议
        result['recommendations'] = self._generate_recommendations(result)
        
        return result
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db_type == 'postgres':
            import psycopg2
            return psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password']
            )
        else:
            return self._get_db_connection()
    
    def _analyze_fundamental(self, ts_code: str) -> Dict:
        """基本面数据分析"""
        try:
            # 获取最新日K数据
            query = """
            SELECT name, industry, free_share, free_mv, turnover_rate
            FROM daily_stock_data
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT 1
            """ % ('%s' if self.db_type == 'postgres' else '?')
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query.replace("?", "%s"), (ts_code,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'stock_name': row[0],
                    'industry': row[1],
                    'free_share': f'{row[2]:.2f}万',
                    'free_mv': f'{row[3]:.2f}亿',
                    'latest_turnover': f'{row[4]:.2f}%'
                }
            return {}
        except Exception as e:
            print(f"基本面分析失败: {e}")
            return {}
    
    def _analyze_flow_statistics(self, ts_code: str, start_date: str, end_date: str) -> Dict:
        """资金流向统计分析"""
        try:
            query = """
            SELECT 
                SUM(main_net_inflow) as total_main_inflow,
                SUM(medium_net) as total_medium_inflow,
                SUM(small_net) as total_small_inflow,
                AVG(main_net_ratio) as avg_main_ratio,
                MAX(main_net_inflow) as max_single_day_inflow,
                MIN(main_net_inflow) as min_single_day_inflow,
                COUNT(*) as trading_days
            FROM daily_stock_data
            WHERE ts_code = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            """
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query.replace("?", "%s"), (ts_code, start_date, end_date))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                total_inflow = row[0] + row[1] + row[2] if all(row[:3]) else None
                return {
                    'total_main_inflow': f'{row[0]:,.2f}万元' if row[0] is not None else '无数据',
                    'total_medium_inflow': f'{row[1]:,.2f}万元' if row[1] is not None else '无数据',
                    'total_small_inflow': f'{row[2]:,.2f}万元' if row[2] is not None else '无数据',
                    'total_net_inflow': f'{total_inflow:,.2f}万元' if total_inflow is not None else '无数据',
                    'avg_main_ratio': f'{row[3]:.2f}%' if row[3] is not None else '无数据',
                    'max_single_day_inflow': f'{row[4]:,.2f}万元' if row[4] is not None else '无数据',
                    'max_single_day_outflow': f'{row[5]:,.2f}万元' if row[5] is not None else '无数据',
                    'trading_days_analyzed': row[6],
                    'dominant_force': self._determine_dominant_force(row[0], row[1], row[2])
                }
            return {}
        except Exception as e:
            print(f"资金流向统计失败: {e}")
            return {}
    
    def _determine_dominant_force(self, main_inflow: float, medium_inflow: float, small_inflow: float) -> str:
        """判断主导资金力量"""
        if not all([main_inflow, medium_inflow, small_inflow]):
            return '无法判断'
        
        total = abs(main_inflow) + abs(medium_inflow) + abs(small_inflow)
        main_ratio = abs(main_inflow) / total * 100
        medium_ratio = abs(medium_inflow) / total * 100
        small_ratio = abs(small_inflow) / total * 100
        
        if main_ratio > 50:
            return '主力主导'
        elif small_ratio > 50:
            return '散户主导'
        elif medium_ratio > 40:
            return '中户主导'
        else:
            return '多力量平衡'
    
    def _analyze_time_series(self, ts_code: str, start_date: str, end_date: str) -> Dict:
        """资金流向时序分析"""
        try:
            query = """
            SELECT trade_date, main_net_inflow, main_net_ratio, close, pct_chg
            FROM daily_stock_data
            WHERE ts_code = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            ORDER BY trade_date
            """
            
            conn = self._get_db_connection()
            df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
            conn.close()
            
            if df.empty:
                return {'message': '无足够数据进行时序分析'}
            
            # 计算5日和10日移动平均
            df['main_inflow_ma5'] = df['main_net_inflow'].rolling(5).mean()
            df['main_inflow_ma10'] = df['main_net_inflow'].rolling(10).mean()
            
            # 计算资金流入强度指数
            df['flow_strength'] = df['main_net_inflow'] / df['main_net_inflow'].abs().mean()
            
            # 统计连续流入流出天数
            df['is_inflow'] = df['main_net_inflow'] > 0
            df['consecutive_days'] = df['is_inflow'].groupby(
                (df['is_inflow'] != df['is_inflow'].shift()).cumsum()
            ).cumcount() + 1
            
            return {
                'has_consecutive_flow': any(df['consecutive_days'] >= 3),
                'max_consecutive_inflow': int(df[df['is_inflow']]['consecutive_days'].max() if any(df['is_inflow']) else 0),
                'max_consecutive_outflow': int(df[~df['is_inflow']]['consecutive_days'].max() if any(~df['is_inflow']) else 0),
                'avg_flow_strength': float(df['flow_strength'].mean()),
                'strong_inflow_days': int((df['flow_strength'] > 2).sum()),
                'strong_outflow_days': int((df['flow_strength'] < -2).sum()),
                'ma5_trend': self._analyze_ma_trend(df['main_inflow_ma5'])
            }
        except Exception as e:
            print(f"时序分析失败: {e}")
            return {}
    
    def _analyze_ma_trend(self, ma_series: pd.Series) -> str:
        """分析移动平均线趋势"""
        if ma_series.isna().all():
            return '无数据'
        
        # 去掉NaN值
        ma_clean = ma_series.dropna()
        if len(ma_clean) < 3:
            return '趋势不明显'
        
        # 计算斜率
        x = np.arange(len(ma_clean))
        y = ma_clean.values
        slope, _ = np.polyfit(x, y, 1)
        
        if slope > 0.1:
            return '持续流入趋势'
        elif slope < -0.1:
            return '持续流出趋势'
        else:
            return '趋势平稳'
    
    def _analyze_price_correlation(self, ts_code: str, start_date: str, end_date: str) -> Dict:
        """资金流向与股价联动分析"""
        try:
            query = """
            SELECT main_net_inflow, main_net_ratio, close, pct_chg, turnover_rate
            FROM daily_stock_data
            WHERE ts_code = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            """
            
            conn = self._get_db_connection()
            df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
            conn.close()
            
            if len(df) < 10:
                return {'message': '数据不足，无法进行相关性分析'}
            
            # 计算相关性
            corr_main_price = df['main_net_inflow'].corr(df['pct_chg'])
            corr_main_turnover = df['main_net_inflow'].corr(df['turnover_rate'])
            
            # 分位数分析
            df['flow_quantile'] = pd.qcut(df['main_net_inflow'], q=5, labels=['Q1(最低)', 'Q2', 'Q3', 'Q4', 'Q5(最高)'])
            quantile_stats = df.groupby('flow_quantile')['pct_chg'].agg(['mean', 'std', 'count'])
            
            return {
                'correlation_with_price_change': f'{corr_main_price:.3f}',
                'correlation_with_turnover': f'{corr_main_turnover:.3f}',
                'correlation_strength': self._interpret_correlation(corr_main_price),
                'quantile_analysis': quantile_stats.to_dict('index'),
                'best_flow_quantile': quantile_stats['mean'].idxmax(),
                'best_flow_avg_return': f'{quantile_stats["mean"].max():.2f}%'
            }
        except Exception as e:
            print(f"股价联动分析失败: {e}")
            return {}
    
    def _interpret_correlation(self, corr_value: float) -> str:
        """解释相关系数强度"""
        corr_abs = abs(corr_value)
        
        if corr_abs >= 0.7:
            return '高度相关'
        elif corr_abs >= 0.4:
            return '中度相关'
        elif corr_abs >= 0.2:
            return '低度相关'
        else:
            return '几乎无关'
    
    def _analyze_sector_comparison(self, ts_code: str, start_date: str, end_date: str) -> Dict:
        """板块资金流向对比分析"""
        try:
            # 获取股票所属行业
            query = """
            SELECT industry
            FROM daily_stock_data
            WHERE ts_code = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query.replace("?", "%s"), (ts_code,))
            result = cursor.fetchone()
            
            if not result:
                return {'message': '无法获取行业信息'}
            
            industry = result[0]
            
            # 获取行业平均资金流向
            query = """
            SELECT 
                AVG(main_net_inflow) as avg_main_inflow,
                AVG(main_net_ratio) as avg_main_ratio,
                COUNT(DISTINCT ts_code) as stock_count
            FROM daily_stock_data
            WHERE industry = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            """
            
            cursor.execute(query.replace("?", "%s"), (industry, start_date, end_date))
            sector_stats = cursor.fetchone()
            
            # 获取个股数据
            query = """
            SELECT 
                AVG(main_net_inflow) as stock_avg_inflow,
                AVG(main_net_ratio) as stock_avg_ratio
            FROM daily_stock_data
            WHERE ts_code = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            """
            
            cursor.execute(query.replace("?", "%s"), (ts_code, start_date, end_date))
            stock_stats = cursor.fetchone()
            
            conn.close()
            
            if sector_stats and stock_stats:
                return {
                    'industry': industry,
                    'sector_stock_count': sector_stats[2],
                    'sector_avg_main_inflow': f'{sector_stats[0]:,.2f}万元',
                    'sector_avg_main_ratio': f'{sector_stats[1]:.2f}%',
                    'stock_avg_main_inflow': f'{stock_stats[0]:,.2f}万元',
                    'stock_avg_main_ratio': f'{stock_stats[1]:.2f}%',
                    'vs_sector_inflow': f'{(stock_stats[0] - sector_stats[0]):,.2f}万元',
                    'vs_sector_ratio': f'{(stock_stats[1] - sector_stats[1]):.2f}个百分点',
                    'sector_rank': self._calculate_sector_rank(ts_code, industry, start_date, end_date)
                }
            
            return {}
        except Exception as e:
            print(f"板块对比分析失败: {e}")
            return {}
    
    def _calculate_sector_rank(self, ts_code: str, industry: str, start_date: str, end_date: str) -> str:
        """计算个股在行业中的资金流向排名"""
        try:
            query = """
            SELECT ts_code, AVG(main_net_inflow) as avg_inflow
            FROM daily_stock_data
            WHERE industry = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            GROUP BY ts_code
            ORDER BY avg_inflow DESC
            """
            
            conn = self._get_db_connection()
            df = pd.read_sql_query(query, conn, params=(industry, start_date, end_date))
            conn.close()
            
            if df.empty:
                return 'N/A'
            
            # 找到当前股票的排名
            stock_idx = df[df['ts_code'] == ts_code].index[0]
            total_stocks = len(df)
            percentile = ((total_stocks - stock_idx) / total_stocks) * 100
            
            return f'行业前{int(percentile + 0.5)}%'
        except Exception as e:
            print(f"计算行业排名失败: {e}")
            return 'N/A'
    
    def _detect_anomalies(self, ts_code: str, start_date: str, end_date: str) -> Dict:
        """异常资金流向检测"""
        try:
            query = """
            SELECT trade_date, main_net_inflow, turnover_rate, pct_chg, close
            FROM daily_stock_data
            WHERE ts_code = ?
              AND trade_date BETWEEN ? AND ?
              AND main_net_inflow IS NOT NULL
            """
            
            conn = self._get_db_connection()
            df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
            conn.close()
            
            if len(df) < 20:
                return {'message': '数据不足，无法进行异常检测'}
            
            anomalies = {
                'large_flow_events': [],
                'price_divergence': [],
                'turnover_spikes': []
            }
            
            # 检测大额资金流动
            mean_inflow = df['main_net_inflow'].mean()
            std_inflow = df['main_net_inflow'].std()
            threshold = mean_inflow + 3 * std_inflow
            
            large_flow = df[abs(df['main_net_inflow']) > threshold]
            for _, row in large_flow.iterrows():
                anomalies['large_flow_events'].append({
                    'date': row['trade_date'],
                    'flow_amount': f'{row["main_net_inflow"]:,.2f}万元',
                    'price_change': f'{row["pct_chg"]:.2f}%',
                    'type': '大额流入' if row['main_net_inflow'] > 0 else '大额流出'
                })
            
            # 检测资金流向与股价背离
            df['flow_direction'] = df['main_net_inflow'] > 0
            df['price_direction'] = df['pct_chg'] > 0
            
            divergence = df[df['flow_direction'] != df['price_direction']]
            for _, row in divergence.iterrows():
                anomalies['price_divergence'].append({
                    'date': row['trade_date'],
                    'flow_amount': f'{row["main_net_inflow"]:,.2f}万元',
                    'price_change': f'{row["pct_chg"]:.2f}%',
                    'type': '资金流入股价下跌' if row['main_net_inflow'] > 0 else '资金流出股价上涨'
                })
            
            # 检测换手率异常 spike
            mean_turnover = df['turnover_rate'].mean()
            std_turnover = df['turnover_rate'].std()
            turnover_threshold = mean_turnover + 2 * std_turnover
            
            turnover_spikes = df[df['turnover_rate'] > turnover_threshold]
            for _, row in turnover_spikes.iterrows():
                anomalies['turnover_spikes'].append({
                    'date': row['trade_date'],
                    'turnover': f'{row["turnover_rate"]:.2f}%',
                    'flow_amount': f'{row["main_net_inflow"]:,.2f}万元',
                    'price_change': f'{row["pct_chg"]:.2f}%'
                })
            
            return {
                'total_anomalies': len(anomalies['large_flow_events']) + len(anomalies['price_divergence']) + len(anomalies['turnover_spikes']),
                'large_flow_events': anomalies['large_flow_events'],
                'price_divergence': anomalies['price_divergence'],
                'turnover_spikes': anomalies['turnover_spikes']
            }
        except Exception as e:
            print(f"异常检测失败: {e}")
            return {}
    
    def _generate_recommendations(self, analysis_result: Dict) -> List[str]:
        """基于分析结果生成投资建议"""
        recommendations = []
        
        # 基于资金流向统计
        flow_stats = analysis_result.get('flow_statistics', {})
        if flow_stats.get('dominant_force') == '主力主导':
            recommendations.append('主力资金主导，关注后续走势')
            
        # 基于时序分析
        ts_analysis = analysis_result.get('time_series_analysis', {})
        if ts_analysis.get('ma5_trend') == '持续流入趋势':
            recommendations.append('资金持续流入，趋势向好')
        elif ts_analysis.get('ma5_trend') == '持续流出趋势':
            recommendations.append('资金持续流出，需警惕')
            
        # 基于股价联动
        price_corr = analysis_result.get('price_correlation', {})
        if price_corr.get('correlation_strength') == '高度相关':
            recommendations.append('资金流向与股价高度相关，可作为买卖参考')
            
        # 基于板块对比
        sector_comp = analysis_result.get('sector_comparison', {})
        if 'sector_rank' in sector_comp and '前' in sector_comp['sector_rank']:
            recommendations.append(f'{sector_comp["sector_rank"]}，行业资金关注度较高')
            
        # 基于异常检测
        anomaly_detect = analysis_result.get('anomaly_detection', {})
        if anomaly_detect.get('total_anomalies', 0) > 5:
            recommendations.append('近期资金异动频繁，需密切关注')
            
        if not recommendations:
            recommendations.append('暂无明确建议，建议结合其他指标综合判断')
            
        return recommendations
    
    def analyze_portfolio(self, ts_codes: List[str], start_date: str = None, end_date: str = None) -> Dict:
        """
        投资组合资金流向分析
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        portfolio_analysis = {
            'portfolio_summary': {},
            'stock_analysis': {},
            'sector_distribution': {},
            'recommendations': []
        }
        
        # 1. 组合汇总分析
        portfolio_analysis['portfolio_summary'] = self._analyze_portfolio_summary(ts_codes, start_date, end_date)
        
        # 2. 个股分析
        for ts_code in ts_codes:
            portfolio_analysis['stock_analysis'][ts_code] = self.analyze_single_stock(ts_code, start_date, end_date)
        
        # 3. 行业分布分析
        portfolio_analysis['sector_distribution'] = self._analyze_sector_distribution(ts_codes, start_date, end_date)
        
        # 4. 生成建议
        portfolio_analysis['recommendations'] = self._generate_portfolio_recommendations(portfolio_analysis)
        
        return portfolio_analysis
    
    def _analyze_portfolio_summary(self, ts_codes: List[str], start_date: str, end_date: str) -> Dict:
        """投资组合汇总分析"""
        try:
            all_data = []
            
            for ts_code in ts_codes:
                query = """
                SELECT ts_code, main_net_inflow, pct_chg, turnover_rate
                FROM daily_stock_data
                WHERE ts_code = ?
                  AND trade_date BETWEEN ? AND ?
                  AND main_net_inflow IS NOT NULL
                """
                
                conn = self._get_db_connection()
                df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
                conn.close()
                
                if not df.empty:
                    all_data.append(df)
            
            if not all_data:
                return {'message': '无足够数据进行组合分析'}
            
            portfolio_df = pd.concat(all_data)
            
            # 计算组合整体指标
            portfolio_summary = {
                'total_stocks_analyzed': len(ts_codes),
                'avg_daily_main_inflow': f'{portfolio_df["main_net_inflow"].mean():,.2f}万元',
                'avg_price_correlation': portfolio_df.groupby('ts_code').apply(
                    lambda x: x['main_net_inflow'].corr(x['pct_chg'])
                ).mean().round(3),
                'positive_flow_stocks': int((portfolio_df.groupby('ts_code')['main_net_inflow'].mean() > 0).sum()),
                'negative_flow_stocks': int((portfolio_df.groupby('ts_code')['main_net_inflow'].mean() <= 0).sum())
            }
            
            return portfolio_summary
        except Exception as e:
            print(f"组合汇总分析失败: {e}")
            return {}
    
    def _analyze_sector_distribution(self, ts_codes: List[str], start_date: str, end_date: str) -> Dict:
        """投资组合行业分布分析"""
        try:
            sector_data = {}
            
            for ts_code in ts_codes:
                query = """
                SELECT industry
                FROM daily_stock_data
                WHERE ts_code = ?
                ORDER BY trade_date DESC
                LIMIT 1
                """
                
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute(query.replace("?", "%s"), (ts_code,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    industry = result[0]
                    if industry not in sector_data:
                        sector_data[industry] = 0
                    sector_data[industry] += 1
            
            total_stocks = len(ts_codes)
            sector_dist = {
                industry: {
                    'count': count,
                    'percentage': f'{(count / total_stocks) * 100:.1f}%'
                }
                for industry, count in sector_data.items()
            }
            
            return sector_dist
        except Exception as e:
            print(f"行业分布分析失败: {e}")
            return {}
    
    def _generate_portfolio_recommendations(self, portfolio_analysis: Dict) -> List[str]:
        """生成投资组合建议"""
        recommendations = []
        
        # 基于组合汇总
        summary = portfolio_analysis.get('portfolio_summary', {})
        if summary.get('positive_flow_stocks', 0) > summary.get('negative_flow_stocks', 0):
            recommendations.append('组合整体资金流入占优，趋势向好')
        else:
            recommendations.append('组合整体资金流出占优，需评估风险')
            
        # 基于行业分布
        sector_dist = portfolio_analysis.get('sector_distribution', {})
        if len(sector_dist) <= 2:
            recommendations.append('行业集中度较高，建议适当分散')
        elif len(sector_dist) >= 5:
            recommendations.append('行业分布分散，有助于降低单一行业风险')
            
        return recommendations

def main():
    """测试模块功能"""
    analyzer = AdvancedMoneyFlowAnalyzer()
    
    # 测试单只股票分析
    test_ts_code = '000001.SZ'  # 平安银行
    print(f"开始分析 {test_ts_code}...")
    result = analyzer.analyze_single_stock(test_ts_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 保存分析结果
    output_file = f'money_flow_analysis_{test_ts_code}_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析结果已保存到 {output_file}")

if __name__ == '__main__':
    main()