"""
T01 板块联动强度因子模块 (生产可用版 v2.0)

按照方案文档重新设计：
- 主体框架使用"板块热度 + 个股板块地位"
- 事件加分使用"涨停序位 / 最早上板 / 成交额占比"

核心公式：
sector_linkage_score
= 0.40 * sector_heat_score
+ 0.30 * stock_position_score
+ 0.20 * first_limit_timing_score
+ 0.10 * amount_share_score

特性：
1. 只用当日数据 + 本地股票到主板块映射
2. 不使用历史相关系数、Beta、lead_days
3. 输出0-100总分
4. 输出标签：板块核心龙头、板块前排跟随、板块后排跟风、独立强势股
"""

import os
import sys
import json
import sqlite3
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==================== 可配置参数 ====================

@dataclass
class SectorLinkageConfig:
    """板块联动因子配置"""
    # 权重配置
    sector_heat_weight: float = 0.40          # 板块热度权重
    stock_position_weight: float = 0.30       # 个股板块地位权重
    first_limit_timing_weight: float = 0.20   # 涨停序位权重
    amount_share_weight: float = 0.10         # 成交额占比权重
    
    # 子权重配置
    sector_heat_sub_weights: Dict = field(default_factory=lambda: {
        'limit_up_count': 0.50,    # 板块涨停家数分
        'avg_pct_change': 0.30,    # 板块平均涨幅分
        'up_ratio': 0.20           # 板块上涨家数占比分
    })
    
    stock_position_sub_weights: Dict = field(default_factory=lambda: {
        'pct_rank': 0.70,          # 个股涨幅板块内排名分
        'limit_time_rank': 0.30    # 个股涨停时间板块内排名分
    })
    
    # 标签分类阈值
    label_thresholds: Dict = field(default_factory=lambda: {
        'core_leader': {           # 板块核心龙头
            'fusion_score_min': 80,
            'sector_limitup_min': 3,
            'limitup_order_max': 2,
            'rank_pct_max': 0.20
        },
        'front_follower': {        # 板块前排跟随
            'fusion_score_min': 60,
            'fusion_score_max': 80,
            'sector_limitup_min': 2,
            'rank_pct_max': 0.50
        },
        'back_follower': {         # 板块后排跟风
            'fusion_score_max': 60
        },
        'independent_strong': {    # 独立强势股
            'position_score_ratio': 0.7,  # stock_position_score 占比高
            'heat_score_ratio': 0.3       # sector_heat_score 占比低
        }
    })
    
    # 数据库路径
    db_path: str = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db'


# ==================== 数据类 ====================

@dataclass
class SectorLinkageMetrics:
    """板块联动指标数据类"""
    # 股票和板块信息
    ts_code: str = ''
    trade_date: str = ''
    sector_code: str = ''          # 主行业板块代码
    sector_name: str = ''          # 主行业板块名称
    
    # 板块热度子指标
    sector_limit_up_count: int = 0      # 板块涨停家数
    sector_avg_pct_change: float = 0.0  # 板块平均涨幅 (%)
    sector_up_ratio: float = 0.0        # 板块上涨家数占比 (0-1)
    
    # 个股地位子指标
    stock_pct_rank_in_sector: float = 1.0  # 个股涨幅板块内排名百分位 (0-1, 越小越好)
    stock_limit_time_rank: int = 99        # 个股涨停时间板块内排名
    limitup_order_in_sector: int = 99      # 个股涨停序位
    
    # 成交额指标
    stock_amount: float = 0.0           # 个股成交额 (万元)
    sector_total_amount: float = 0.0    # 板块总成交额 (万元)
    amount_share_ratio: float = 0.0     # 成交额占比 (0-1)
    
    # 评分
    sector_heat_score: float = 0.0          # 板块热度分 (0-100)
    stock_position_score: float = 0.0       # 个股地位分 (0-100)
    first_limit_timing_score: float = 0.0   # 涨停序位分 (0-100)
    amount_share_score: float = 0.0         # 成交额占比分 (0-100)
    
    # 总分
    fusion_score: float = 0.0            # 综合评分 (0-100)
    sector_role_label: str = ''          # 板块角色标签
    
    # 降级原因
    degradation_reason: str = ''


# ==================== 板块映射管理 ====================

class SectorMappingManager:
    """
    股票-主板块映射管理器
    
    使用 SQLite 本地存储，每周检查更新
    """
    
    def __init__(self, db_path: str, data_fetcher=None):
        """
        初始化
        
        Args:
            db_path: 数据库路径
            data_fetcher: DataFetcher 实例
        """
        self.db_path = db_path
        self.fetcher = data_fetcher
        self._ensure_table()
    
    def _ensure_table(self):
        """确保映射表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_sector_mapping (
                ts_code TEXT PRIMARY KEY,
                sector_code TEXT NOT NULL,
                sector_name TEXT,
                last_updated TEXT,
                UNIQUE(ts_code)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sector_code 
            ON stock_sector_mapping(sector_code)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_sector(self, ts_code: str) -> Optional[Tuple[str, str]]:
        """
        获取股票的主板块
        
        Args:
            ts_code: 股票代码
            
        Returns:
            (sector_code, sector_name) 或 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sector_code, sector_name 
            FROM stock_sector_mapping 
            WHERE ts_code = ?
        ''', (ts_code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return (result[0], result[1])
        return None
    
    def set_sector(self, ts_code: str, sector_code: str, sector_name: str):
        """
        设置股票的主板块
        
        Args:
            ts_code: 股票代码
            sector_code: 板块代码
            sector_name: 板块名称
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO stock_sector_mapping 
            (ts_code, sector_code, sector_name, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (ts_code, sector_code, sector_name, datetime.now().strftime('%Y%m%d')))
        
        conn.commit()
        conn.close()
    
    def batch_set_sectors(self, mappings: List[Tuple[str, str, str]]):
        """
        批量设置股票-板块映射
        
        Args:
            mappings: [(ts_code, sector_code, sector_name), ...]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y%m%d')
        data = [(m[0], m[1], m[2], now) for m in mappings]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO stock_sector_mapping 
            (ts_code, sector_code, sector_name, last_updated)
            VALUES (?, ?, ?, ?)
        ''', data)
        
        conn.commit()
        conn.close()
    
    def needs_update(self) -> bool:
        """
        检查是否需要更新映射表（每周检查一次）
        
        Returns:
            是否需要更新
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查最后更新时间
        cursor.execute('''
            SELECT MAX(last_updated) FROM stock_sector_mapping
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return True
        
        last_updated = result[0]
        if isinstance(last_updated, str):
            last_date = datetime.strptime(last_updated, '%Y%m%d')
            return (datetime.now() - last_date).days >= 7
        
        return True
    
    def update_all_mappings(self, date: str = None):
        """
        更新所有股票的板块映射
        
        Args:
            date: 日期 YYYYMMDD
        """
        if not self.fetcher:
            logger.warning("DataFetcher 未设置，无法更新映射")
            return
        
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        logger.info(f"开始更新股票-板块映射，日期: {date}")
        
        try:
            # 获取所有行业板块
            industry_sectors = self.fetcher.get_tdx_industry_sectors(date)
            if industry_sectors.empty:
                logger.warning("未获取到行业板块数据")
                return
            
            mappings = []
            total = len(industry_sectors)
            
            for idx, (_, sector) in enumerate(industry_sectors.iterrows()):
                sector_code = sector['ts_code']
                sector_name = sector['name']
                
                if idx % 10 == 0:
                    logger.info(f"处理进度: {idx}/{total} - {sector_name}")
                
                # 获取板块成分股
                members = self.fetcher.get_tdx_sector_members(sector_code, date)
                if members.empty:
                    continue
                
                for _, member in members.iterrows():
                    ts_code = member['con_code']
                    mappings.append((ts_code, sector_code, sector_name))
            
            # 批量写入
            self.batch_set_sectors(mappings)
            logger.info(f"更新完成，共 {len(mappings)} 条映射")
            
        except Exception as e:
            logger.error(f"更新映射失败: {e}")


# ==================== 板块联动因子计算器 ====================

class SectorLinkageFactor:
    """板块联动强度因子计算器（生产可用版）"""
    
    def __init__(self, data_fetcher, config: SectorLinkageConfig = None):
        """
        初始化
        
        Args:
            data_fetcher: DataFetcher 实例
            config: 配置对象
        """
        self.fetcher = data_fetcher
        self.config = config or SectorLinkageConfig()
        self.mapping_manager = SectorMappingManager(
            self.config.db_path, 
            data_fetcher
        )
        
        # 缓存当日板块数据
        self._sector_data_cache: Dict[str, Dict] = {}
        self._cache_date: str = ''
    
    def calculate(self, ts_code: str, trade_date: str, 
                  stock_data: Dict = None) -> SectorLinkageMetrics:
        """
        计算板块联动强度指标
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
            stock_data: 个股数据（可选，包含 pct_chg, amount 等）
            
        Returns:
            SectorLinkageMetrics 指标对象
        """
        metrics = SectorLinkageMetrics(
            ts_code=ts_code,
            trade_date=trade_date
        )
        
        try:
            # 1. 获取或确定主行业板块（传递 stock_data 以避免额外API调用）
            sector_info = self._get_or_determine_sector(ts_code, trade_date, stock_data)
            if not sector_info:
                metrics.degradation_reason = "无法确定主行业板块"
                metrics.sector_role_label = "独立强势股"
                return metrics
            
            metrics.sector_code = sector_info['sector_code']
            metrics.sector_name = sector_info['sector_name']
            
            # 2. 获取板块数据
            sector_data = self._get_sector_data(metrics.sector_code, trade_date)
            if not sector_data:
                metrics.degradation_reason = "无法获取板块数据"
                # 降级处理：使用默认值
                metrics.sector_linkage_score = 50
                metrics.sector_role_label = "独立强势股"
                return metrics
            
            # 3. 获取板块内所有股票数据
            sector_stocks = self._get_sector_stocks_data(
                metrics.sector_code, trade_date
            )
            
            # 4. 计算各子指标
            if sector_stocks:
                # 正常计算
                self._calc_sector_heat(sector_data, sector_stocks, metrics)
                self._calc_stock_position(ts_code, sector_stocks, metrics)
                self._calc_first_limit_timing(ts_code, sector_stocks, metrics)
                self._calc_amount_share(ts_code, sector_stocks, metrics)
            else:
                # 降级计算：仅使用板块数据
                self._calc_sector_heat_from_sector_data(sector_data, metrics)
                # 其他指标使用默认值
                metrics.stock_position_score = 50
                metrics.first_limit_timing_score = 50
                metrics.amount_share_score = 50
                metrics.degradation_reason = "使用板块数据降级计算"
            
            # 5. 计算综合评分
            self._calc_fusion_score(metrics)
            
            # 6. 确定角色标签
            self._determine_role_label(metrics)
            
        except Exception as e:
            logger.error(f"计算板块联动因子失败 {ts_code}: {e}")
            metrics.degradation_reason = str(e)
        
        return metrics
    
    def _get_or_determine_sector(self, ts_code: str, trade_date: str, 
                                   stock_data: Dict = None) -> Optional[Dict]:
        """
        获取或确定股票的主行业板块
        
        优先级：
        1. stock_data 中的 industry 字段（申万行业分类）
        2. 本地映射表
        3. 动态确定（避免大量API调用，使用简化逻辑）
        """
        # 1. 优先使用 stock_data 中的 industry 字段
        if stock_data and 'industry' in stock_data:
            industry_name = stock_data['industry']
            if industry_name:
                # 在通达信行业板块中查找匹配
                matched = self._match_industry_to_tdx(industry_name, trade_date)
                if matched:
                    # 更新本地映射
                    self.mapping_manager.set_sector(ts_code, matched['sector_code'], matched['sector_name'])
                    return {**matched, 'source': 'industry_field'}
        
        # 2. 查本地映射
        cached = self.mapping_manager.get_sector(ts_code)
        if cached:
            return {
                'sector_code': cached[0],
                'sector_name': cached[1],
                'source': 'cached'
            }
        
        # 3. 动态确定（简化版，避免大量API调用）
        return self._determine_primary_sector_simple(ts_code, trade_date)
    
    def _match_industry_to_tdx(self, industry_name: str, trade_date: str) -> Optional[Dict]:
        """
        将申万行业名称匹配到通达信行业板块
        
        Args:
            industry_name: 申万行业名称（如"光学光电"、"电力"等）
            trade_date: 交易日期
            
        Returns:
            匹配的通达信板块信息，或 None
        """
        try:
            # 获取通达信行业板块列表
            tdx_sectors = self.fetcher.get_tdx_industry_sectors(trade_date)
            if tdx_sectors.empty:
                return None
            
            # 直接匹配
            matched = tdx_sectors[tdx_sectors['name'] == industry_name]
            if not matched.empty:
                row = matched.iloc[0]
                return {
                    'sector_code': row['ts_code'],
                    'sector_name': row['name']
                }
            
            # 模糊匹配（行业名称包含关系）
            for _, row in tdx_sectors.iterrows():
                tdx_name = row['name']
                # 双向包含匹配
                if industry_name in tdx_name or tdx_name in industry_name:
                    return {
                        'sector_code': row['ts_code'],
                        'sector_name': row['name']
                    }
            
            # 尝试关键词匹配
            keywords_map = {
                '光学光电': ['光学', '光电', '电子'],
                '电力': ['电力', '电气'],
                '养殖业': ['养殖', '农业', '畜牧'],
                '房地产': ['房地产', '房产'],
                '银行': ['银行', '金融'],
                '证券': ['证券', '券商'],
                '保险': ['保险'],
                '白酒': ['白酒', '酒'],
                '医药': ['医药', '医疗', '生物'],
                '汽车': ['汽车', '整车', '新能源车'],
                '通信': ['通信', '通信设备', '通信工程'],
                '计算机': ['计算机', '软件', 'IT'],
                '传媒': ['传媒', '影视', '广告'],
                '化工': ['化工', '化学'],
                '机械': ['机械', '设备'],
                '建材': ['建材', '水泥', '玻璃'],
                '钢铁': ['钢铁', '钢'],
                '煤炭': ['煤炭', '煤'],
                '石油': ['石油', '油', '油气'],
                '有色金属': ['有色', '金属'],
                '军工': ['军工', '国防'],
            }
            
            if industry_name in keywords_map:
                keywords = keywords_map[industry_name]
                for _, row in tdx_sectors.iterrows():
                    tdx_name = row['name']
                    if any(kw in tdx_name for kw in keywords):
                        return {
                            'sector_code': row['ts_code'],
                            'sector_name': row['name']
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def _determine_primary_sector_simple(self, ts_code: str, trade_date: str) -> Optional[Dict]:
        """
        简化版的板块确定（避免大量API调用）
        
        使用 get_stock_tdx_sectors 方法（已有速率限制）
        """
        try:
            # 使用 data_fetcher 的 get_stock_tdx_sectors 方法
            # 该方法已内置速率限制
            sectors = self.fetcher.get_stock_tdx_sectors(ts_code, trade_date)
            
            if not sectors:
                return None
            
            # 返回第一个行业板块
            for sector in sectors:
                if sector.get('idx_type') == '行业板块':
                    return {
                        'sector_code': sector['ts_code'],
                        'sector_name': sector['name'],
                        'source': 'dynamic'
                    }
            
            # 如果没有行业板块，返回第一个
            if sectors:
                sector = sectors[0]
                return {
                    'sector_code': sector['ts_code'],
                    'sector_name': sector['name'],
                    'source': 'dynamic'
                }
            
            return None
            
        except Exception as e:
            return None
    
    def _determine_primary_sector(self, ts_code: str, trade_date: str) -> Optional[Dict]:
        """
        动态确定股票的主行业板块
        
        当股票属于多个行业板块时的选择逻辑：
        1. 当日行业板块涨停家数更多
        2. 当日行业板块总成交额更大
        3. 个股在该行业板块中的涨幅排名更高
        """
        try:
            # 获取所有行业板块
            industry_sectors = self.fetcher.get_tdx_industry_sectors(trade_date)
            if industry_sectors.empty:
                return None
            
            # 查找包含该股票的行业板块
            candidate_sectors = []
            
            for _, sector in industry_sectors.iterrows():
                sector_code = sector['ts_code']
                sector_name = sector['name']
                
                # 获取板块成分股
                members = self.fetcher.get_tdx_sector_members(sector_code, trade_date)
                if members.empty:
                    continue
                
                member_codes = members['con_code'].tolist()
                if ts_code not in member_codes:
                    continue
                
                # 获取板块行情
                sector_daily = self.fetcher.get_tdx_sector_daily(
                    ts_code=sector_code, date=trade_date
                )
                if sector_daily.empty:
                    continue
                
                row = sector_daily.iloc[0]
                candidate_sectors.append({
                    'sector_code': sector_code,
                    'sector_name': sector_name,
                    'limit_up_num': int(row.get('limit_up_num', 0) or 0),
                    'amount': float(row.get('amount', 0) or 0),
                    'pct_change': float(row.get('pct_change', 0) or 0)
                })
            
            if not candidate_sectors:
                return None
            
            # 按优先级排序
            # 1. 涨停家数多的优先
            # 2. 成交额大的优先
            # 3. 涨幅大的优先
            candidate_sectors.sort(
                key=lambda x: (
                    x['limit_up_num'], 
                    x['amount'], 
                    x['pct_change']
                ),
                reverse=True
            )
            
            best = candidate_sectors[0]
            
            # 更新本地映射
            self.mapping_manager.set_sector(
                ts_code, 
                best['sector_code'], 
                best['sector_name']
            )
            
            return {
                'sector_code': best['sector_code'],
                'sector_name': best['sector_name'],
                'source': 'dynamic'
            }
            
        except Exception as e:
            logger.error(f"确定主行业板块失败 {ts_code}: {e}")
            return None
    
    def _get_sector_data(self, sector_code: str, trade_date: str) -> Optional[Dict]:
        """获取板块数据（带缓存）"""
        cache_key = f"{sector_code}_{trade_date}"
        
        if self._cache_date == trade_date and cache_key in self._sector_data_cache:
            return self._sector_data_cache[cache_key]
        
        try:
            sector_daily = self.fetcher.get_tdx_sector_daily(
                ts_code=sector_code, date=trade_date
            )
            
            if sector_daily.empty:
                return None
            
            row = sector_daily.iloc[0]
            data = {
                'ts_code': sector_code,
                'pct_change': float(row.get('pct_change', 0) or 0),
                'limit_up_num': int(row.get('limit_up_num', 0) or 0),
                'up_num': int(row.get('up_num', 0) or 0),
                'down_num': int(row.get('down_num', 0) or 0),
                'amount': float(row.get('amount', 0) or 0),
                'total_count': int(row.get('total_count', 0) or 0)
            }
            
            # 更新缓存
            self._sector_data_cache[cache_key] = data
            self._cache_date = trade_date
            
            return data
            
        except Exception as e:
            logger.error(f"获取板块数据失败 {sector_code}: {e}")
            return None
    
    def _get_sector_stocks_data(self, sector_code: str, trade_date: str) -> List[Dict]:
        """
        获取板块内所有股票的当日数据（优化版，减少API调用）
        
        Returns:
            [{
                'ts_code': str,
                'pct_change': float,
                'amount': float,
                'is_limit_up': bool,
                'limit_up_time': str  # 涨停时间
            }, ...]
        """
        try:
            # 获取板块成分股（添加延迟避免限速）
            members = self.fetcher.get_tdx_sector_members(sector_code, trade_date)
            if members.empty:
                return []
            
            member_codes = members['con_code'].tolist()
            
            # 使用批量接口获取行情（减少API调用次数）
            try:
                batch_df = self.fetcher.get_stocks_daily_batch(member_codes, trade_date)
                if batch_df.empty:
                    return []
                
                stocks_data = []
                for _, row in batch_df.iterrows():
                    pct_change = float(row.get('pct_chg', 0) or 0)
                    amount = float(row.get('amount', 0) or 0)
                    
                    # 判断是否涨停（考虑四舍五入）
                    is_limit_up = pct_change >= 9.8
                    
                    stocks_data.append({
                        'ts_code': row['ts_code'],
                        'pct_change': pct_change,
                        'amount': amount,
                        'is_limit_up': is_limit_up,
                        'limit_up_time': ''  # 需要从分时数据获取，暂时留空
                    })
                
                return stocks_data
                
            except Exception as batch_error:
                logger.warning(f"批量获取行情失败，使用简化计算: {batch_error}")
                # 降级：返回空列表，使用板块数据计算
                return []
            
        except Exception as e:
            logger.error(f"获取板块成分股数据失败 {sector_code}: {e}")
            return []
    
    def _calc_sector_heat_from_sector_data(self, sector_data: Dict, 
                                            metrics: SectorLinkageMetrics):
        """仅使用板块数据计算热度分（降级模式）"""
        try:
            # 板块涨停家数分
            limit_up_count = sector_data.get('limit_up_num', 0)
            limit_up_score = 100 * (1 - np.exp(-limit_up_count / 5))
            limit_up_score = min(100, max(0, limit_up_score))
            
            # 板块涨幅分
            avg_pct = sector_data.get('pct_change', 0)
            avg_pct_score = (avg_pct + 5) / 15 * 100
            avg_pct_score = min(100, max(0, avg_pct_score))
            
            # 综合热度分
            metrics.sector_heat_score = limit_up_score * 0.7 + avg_pct_score * 0.3
            metrics.sector_limit_up_count = limit_up_count
            
        except Exception as e:
            logger.error(f"降级计算板块热度失败: {e}")
            metrics.sector_heat_score = 50
    
    def _calc_sector_heat(self, sector_data: Dict, sector_stocks: List[Dict], 
                          metrics: SectorLinkageMetrics):
        """计算板块热度分"""
        try:
            weights = self.config.sector_heat_sub_weights
            
            # 1. 板块涨停家数分 (0-100)
            # 使用 sigmoid 函数平滑映射
            limit_up_count = sector_data.get('limit_up_num', 0)
            # 10个涨停以上为高分
            limit_up_score = 100 * (1 - np.exp(-limit_up_count / 5))
            limit_up_score = min(100, max(0, limit_up_score))
            
            # 2. 板块平均涨幅分 (0-100)
            # 使用 min-max 归一化
            avg_pct = sector_data.get('pct_change', 0)
            # 假设板块涨幅范围 -5% 到 +10%
            avg_pct_score = (avg_pct + 5) / 15 * 100
            avg_pct_score = min(100, max(0, avg_pct_score))
            
            # 3. 板块上涨家数占比分 (0-100)
            up_num = sector_data.get('up_num', 0)
            down_num = sector_data.get('down_num', 0)
            total = up_num + down_num
            if total > 0:
                up_ratio = up_num / total
            else:
                up_ratio = 0.5
            up_ratio_score = up_ratio * 100
            
            # 加权计算
            sector_heat_score = (
                weights['limit_up_count'] * limit_up_score +
                weights['avg_pct_change'] * avg_pct_score +
                weights['up_ratio'] * up_ratio_score
            )
            
            metrics.sector_limit_up_count = limit_up_count
            metrics.sector_avg_pct_change = avg_pct
            metrics.sector_up_ratio = up_ratio
            metrics.sector_heat_score = round(sector_heat_score, 2)
            
        except Exception as e:
            logger.error(f"计算板块热度分失败: {e}")
    
    def _calc_stock_position(self, ts_code: str, sector_stocks: List[Dict], 
                             metrics: SectorLinkageMetrics):
        """计算个股板块地位分"""
        try:
            if not sector_stocks:
                return
            
            weights = self.config.stock_position_sub_weights
            
            # 按涨幅排序
            sorted_by_pct = sorted(
                sector_stocks, 
                key=lambda x: x['pct_change'], 
                reverse=True
            )
            total_count = len(sorted_by_pct)
            
            # 1. 个股涨幅板块内排名分 (0-100)
            pct_rank = 1.0  # 默认最后
            for rank, stock in enumerate(sorted_by_pct, 1):
                if stock['ts_code'] == ts_code:
                    pct_rank = rank / total_count
                    break
            
            # 排名越靠前分数越高
            pct_rank_score = (1 - pct_rank) * 100
            
            # 2. 个股涨停时间板块内排名分 (0-100)
            # 由于没有分时数据，使用涨幅排序作为替代
            # 涨停股排在前面
            limit_up_stocks = [s for s in sector_stocks if s['is_limit_up']]
            limit_time_rank = len(limit_up_stocks) + 1  # 默认靠后
            
            for rank, stock in enumerate(limit_up_stocks, 1):
                if stock['ts_code'] == ts_code:
                    limit_time_rank = rank
                    break
            
            limit_time_rank_score = (1 - limit_time_rank / max(len(limit_up_stocks), 1)) * 100
            
            # 加权计算
            stock_position_score = (
                weights['pct_rank'] * pct_rank_score +
                weights['limit_time_rank'] * limit_time_rank_score
            )
            
            metrics.stock_pct_rank_in_sector = round(pct_rank, 4)
            metrics.stock_limit_time_rank = limit_time_rank
            metrics.stock_position_score = round(stock_position_score, 2)
            
        except Exception as e:
            logger.error(f"计算个股板块地位分失败: {e}")
    
    def _calc_first_limit_timing(self, ts_code: str, sector_stocks: List[Dict], 
                                  metrics: SectorLinkageMetrics):
        """计算涨停序位分"""
        try:
            # 获取板块内涨停股
            limit_up_stocks = [s for s in sector_stocks if s['is_limit_up']]
            
            if not limit_up_stocks:
                metrics.first_limit_timing_score = 0
                metrics.limitup_order_in_sector = 99
                return
            
            # 按涨幅排序（涨幅越高，越可能早涨停）
            limit_up_stocks.sort(key=lambda x: x['pct_change'], reverse=True)
            
            # 查找目标股票的涨停序位
            limitup_order = len(limit_up_stocks) + 1
            for rank, stock in enumerate(limit_up_stocks, 1):
                if stock['ts_code'] == ts_code:
                    limitup_order = rank
                    break
            
            metrics.limitup_order_in_sector = limitup_order
            
            # 计算得分：序位越靠前分数越高
            # 使用 1 / order 或百分位
            if limitup_order <= len(limit_up_stocks):
                timing_score = (1 - limitup_order / len(limit_up_stocks)) * 100
            else:
                timing_score = 0
            
            metrics.first_limit_timing_score = round(max(0, timing_score), 2)
            
        except Exception as e:
            logger.error(f"计算涨停序位分失败: {e}")
    
    def _calc_amount_share(self, ts_code: str, sector_stocks: List[Dict], 
                           metrics: SectorLinkageMetrics):
        """计算成交额占比分"""
        try:
            if not sector_stocks:
                metrics.amount_share_score = 0
                return
            
            total_amount = sum(s['amount'] for s in sector_stocks)
            
            if total_amount <= 0:
                metrics.amount_share_score = 0
                return
            
            # 查找目标股票成交额
            stock_amount = 0
            for stock in sector_stocks:
                if stock['ts_code'] == ts_code:
                    stock_amount = stock['amount']
                    break
            
            amount_share = stock_amount / total_amount
            
            # 成交额占比分：使用 sigmoid 平滑映射
            # 占比越高分数越高，但有边际递减
            amount_score = 100 * (1 - np.exp(-amount_share * 10))
            
            metrics.stock_amount = stock_amount
            metrics.sector_total_amount = total_amount
            metrics.amount_share_ratio = round(amount_share, 4)
            metrics.amount_share_score = round(min(100, amount_score), 2)
            
        except Exception as e:
            logger.error(f"计算成交额占比分失败: {e}")
    
    def _calc_fusion_score(self, metrics: SectorLinkageMetrics):
        """计算综合评分"""
        try:
            cfg = self.config
            
            fusion_score = (
                cfg.sector_heat_weight * metrics.sector_heat_score +
                cfg.stock_position_weight * metrics.stock_position_score +
                cfg.first_limit_timing_weight * metrics.first_limit_timing_score +
                cfg.amount_share_weight * metrics.amount_share_score
            )
            
            metrics.fusion_score = round(min(100, max(0, fusion_score)), 2)
            
        except Exception as e:
            logger.error(f"计算综合评分失败: {e}")
    
    def _determine_role_label(self, metrics: SectorLinkageMetrics):
        """确定板块角色标签"""
        try:
            cfg = self.config.label_thresholds
            
            # 获取各评分占比
            total_score = (
                metrics.sector_heat_score + 
                metrics.stock_position_score + 
                metrics.first_limit_timing_score + 
                metrics.amount_share_score
            )
            
            if total_score > 0:
                heat_ratio = metrics.sector_heat_score / total_score
                position_ratio = metrics.stock_position_score / total_score
            else:
                heat_ratio = position_ratio = 0
            
            # 判断规则
            # 1. 板块核心龙头
            core = cfg['core_leader']
            if (metrics.fusion_score >= core['fusion_score_min'] and
                metrics.sector_limit_up_count >= core['sector_limitup_min'] and
                metrics.limitup_order_in_sector <= core['limitup_order_max'] and
                metrics.stock_pct_rank_in_sector <= core['rank_pct_max']):
                metrics.sector_role_label = "板块核心龙头"
                return
            
            # 2. 板块前排跟随
            front = cfg['front_follower']
            if (front['fusion_score_min'] <= metrics.fusion_score < front['fusion_score_max'] and
                metrics.sector_limit_up_count >= front['sector_limitup_min'] and
                metrics.stock_pct_rank_in_sector <= front['rank_pct_max']):
                metrics.sector_role_label = "板块前排跟随"
                return
            
            # 3. 独立强势股
            indep = cfg['independent_strong']
            if (position_ratio >= indep['position_score_ratio'] and
                heat_ratio <= indep['heat_score_ratio']):
                metrics.sector_role_label = "独立强势股"
                return
            
            # 4. 板块后排跟风
            back = cfg['back_follower']
            if metrics.fusion_score < back['fusion_score_max']:
                metrics.sector_role_label = "板块后排跟风"
                return
            
            # 默认
            metrics.sector_role_label = "板块前排跟随"
            
        except Exception as e:
            logger.error(f"确定角色标签失败: {e}")
            metrics.sector_role_label = "未知"


# ==================== 便捷函数 ====================

def calculate_sector_linkage_score(ts_code: str, trade_date: str, 
                                    data_fetcher, stock_data: Dict = None) -> Dict:
    """
    便捷函数：计算板块联动强度评分
    
    Args:
        ts_code: 股票代码
        trade_date: 交易日期
        data_fetcher: DataFetcher 实例
        stock_data: 个股数据（可选）
        
    Returns:
        包含评分和原始值的字典
    """
    calculator = SectorLinkageFactor(data_fetcher)
    metrics = calculator.calculate(ts_code, trade_date, stock_data)
    
    return {
        'sector_linkage_score': metrics.fusion_score,
        'sector_role_label': metrics.sector_role_label,
        'sector_code': metrics.sector_code,
        'sector_name': metrics.sector_name,
        'sector_linkage_raw': {
            'sector_heat_score': metrics.sector_heat_score,
            'stock_position_score': metrics.stock_position_score,
            'first_limit_timing_score': metrics.first_limit_timing_score,
            'amount_share_score': metrics.amount_share_score,
            'sector_limit_up_count': metrics.sector_limit_up_count,
            'stock_pct_rank_in_sector': metrics.stock_pct_rank_in_sector,
            'limitup_order_in_sector': metrics.limitup_order_in_sector,
            'amount_share_ratio': metrics.amount_share_ratio,
        },
        'degradation_reason': metrics.degradation_reason
    }


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=== 板块联动强度因子测试 (v2.0 生产可用版) ===\n")
    
    import sys
    sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
    from data_fetcher import DataFetcher
    
    fetcher = DataFetcher()
    calculator = SectorLinkageFactor(fetcher)
    
    # 测试股票
    test_stocks = [
        '600396.SH',  # 华电辽能
        '603387.SH',  # 基蛋生物
        '000020.SZ',  # 深华发A
    ]
    test_date = '20260318'
    
    for test_stock in test_stocks:
        print(f"\n{'='*60}")
        print(f"测试股票: {test_stock}")
        print(f"测试日期: {test_date}")
        print(f"{'='*60}")
        
        metrics = calculator.calculate(test_stock, test_date)
        
        print(f"\n【板块信息】")
        print(f"  主行业板块: {metrics.sector_name} ({metrics.sector_code})")
        
        print(f"\n【板块热度】")
        print(f"  板块涨停家数: {metrics.sector_limit_up_count}")
        print(f"  板块平均涨幅: {metrics.sector_avg_pct_change:.2f}%")
        print(f"  板块上涨占比: {metrics.sector_up_ratio:.2%}")
        print(f"  板块热度分: {metrics.sector_heat_score:.1f}")
        
        print(f"\n【个股地位】")
        print(f"  板块内涨幅排名: {metrics.stock_pct_rank_in_sector:.2%}")
        print(f"  涨停序位: {metrics.limitup_order_in_sector}")
        print(f"  个股地位分: {metrics.stock_position_score:.1f}")
        
        print(f"\n【涨停序位】")
        print(f"  涨停序位: {metrics.limitup_order_in_sector}")
        print(f"  涨停序位分: {metrics.first_limit_timing_score:.1f}")
        
        print(f"\n【成交额】")
        print(f"  个股成交额: {metrics.stock_amount:.2f}万元")
        print(f"  板块总成交额: {metrics.sector_total_amount:.2f}万元")
        print(f"  成交额占比: {metrics.amount_share_ratio:.2%}")
        print(f"  成交额占比分: {metrics.amount_share_score:.1f}")
        
        print(f"\n【综合评分】")
        print(f"  总分: {metrics.fusion_score:.1f}")
        print(f"  角色标签: {metrics.sector_role_label}")
        
        if metrics.degradation_reason:
            print(f"  降级原因: {metrics.degradation_reason}")
    
    print("\n\n✅ 测试完成!")
