"""
T01 选股系统 - 数据库模型

支持 PostgreSQL 和 SQLite 双模式
默认使用 PostgreSQL
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from datetime import datetime
import os

# 导入数据库配置
from database.db_config import get_database_url, get_engine_kwargs, DB_TYPE, POSTGRES_CONFIG

Base = declarative_base()

# 涨跌停数据模型
class LimitStockData(Base):
    """涨跌停股票数据"""
    __tablename__ = 'limit_stock_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment='股票代码')
    name = Column(String(50), comment='股票名称')
    close = Column(Float, comment='收盘价')
    pct_chg = Column(Float, comment='涨跌幅')
    limit_price = Column(Float, comment='涨跌停价格')
    open_times = Column(Integer, comment='打开次数')
    up_stat = Column(Float, comment='封板时长(秒)')
    trade_date = Column(String(10), nullable=False, comment='交易日期')
    exchange = Column(String(10), comment='交易所')
    limit_type = Column(String(1), comment='涨跌停类型 U-涨停 D-跌停')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    __table_args__ = (
        Index('idx_limit_ts_code_date', 'ts_code', 'trade_date'),
        Index('idx_limit_type', 'limit_type'),
    )

# 涨跌停分时数据模型
class LimitStepData(Base):
    """涨跌停分时数据"""
    __tablename__ = 'limit_step_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(String(10), nullable=False, comment='交易日期')
    time = Column(String(10), comment='时间')
    price = Column(Float, comment='价格')
    pct_chg = Column(Float, comment='涨跌幅')
    vol = Column(Integer, comment='成交量(手)')
    amount = Column(Float, comment='成交额(元)')
    type = Column(String(10), comment='类型')
    status = Column(String(10), comment='状态')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    __table_args__ = (
        Index('idx_step_ts_code_date', 'ts_code', 'trade_date'),
        Index('idx_step_time', 'time'),
    )

# 使用配置中的数据库 URL
DATABASE_URL = get_database_url()

# 保留 SQLite 路径用于迁移
DB_PATH = os.path.join(os.path.dirname(__file__), 't01_stocks.db')


class TradingCalendar(Base):
    """交易日历表"""
    __tablename__ = 'trading_calendar'
    
    exchange = Column(String(10), primary_key=True)  # 交易所 SSE/SZSE
    cal_date = Column(String(8), primary_key=True)   # 日期 YYYYMMDD
    is_open = Column(Boolean)                         # 是否交易日
    pretrade_date = Column(String(8))                 # 上一交易日


class DailyStockData(Base):
    """每日股票数据表"""
    __tablename__ = 'daily_stock_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), index=True)          # 股票代码
    trade_date = Column(String(8), index=True)        # 交易日期
    name = Column(String(20))                         # 股票名称
    industry = Column(String(50))                     # 所属行业
    open = Column(Float)                              # 开盘价
    high = Column(Float)                              # 最高价
    low = Column(Float)                               # 最低价
    close = Column(Float)                             # 收盘价
    pre_close = Column(Float)                         # 昨收价
    change = Column(Float)                            # 涨跌额
    pct_chg = Column(Float)                           # 涨跌幅%
    vol = Column(Float)                               # 成交量(手)
    amount = Column(Float)                            # 成交额(千元)
    
    # 资金流向字段
    main_net_inflow = Column(Float)                   # 主力净流入(万元)
    main_net_ratio = Column(Float)                    # 主力净占比(%)
    medium_net = Column(Float)                        # 中单净额(万元)
    small_net = Column(Float)                         # 散户净额(万元)
    
    # 扩展字段
    turnover_rate = Column(Float)                     # 换手率
    volume_ratio = Column(Float)                      # 量比
    free_share = Column(Float)                        # 自由流通股本
    free_mv = Column(Float)                           # 自由流通市值
    real_turnover_rate = Column(Float)                # 真实换手率
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_ts_trade', 'ts_code', 'trade_date'),
    )


class LimitUpStock(Base):
    """涨停股票表"""
    __tablename__ = 'limit_up_stocks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), index=True)          # 股票代码
    trade_date = Column(String(8), index=True)        # 交易日期
    
    # 涨停详情
    first_limit_time = Column(String(8))              # 首次涨停时间
    last_limit_time = Column(String(8))               # 最后涨停时间
    limit_times = Column(Integer, default=0)          # 炸板次数
    up_stat = Column(String(20))                      # 涨停统计 如"2/3"表示2连板3日涨停
    limit_amount = Column(Float)                      # 封单金额(万元)
    
    # 计算字段
    seal_ratio = Column(Float)                        # 封成比 = 封单金额/成交金额
    seal_flow_ratio = Column(Float)                   # 封流比 = 封单金额/自由流通市值
    consecutive_limit = Column(Integer, default=1)    # 连板数
    
    # 基础数据
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    pct_chg = Column(Float)
    vol = Column(Float)                               # 成交量(手)
    amount = Column(Float)                            # 成交额(千元)
    
    # 评分相关
    total_score = Column(Float, default=0)            # 总分
    score_rank = Column(Integer)                      # 排名
    unifuncs_recommended = Column(Boolean, default=False)  # unifuncs推荐
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_limit_ts_trade', 'ts_code', 'trade_date'),
    )


class StockFactorScore(Base):
    """股票因子评分表"""
    __tablename__ = 'stock_factor_scores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), index=True)
    trade_date = Column(String(8), index=True)
    
    # 十一个因子评分 (每项10分，满分110分，归一化到100分)
    limit_quality_score = Column(Float, default=0)    # 涨停质量
    seal_ratio_score = Column(Float, default=0)       # 封成比
    seal_flow_ratio_score = Column(Float, default=0)  # 封流比
    volume_ratio_score = Column(Float, default=0)     # 量比
    turnover_rate_score = Column(Float, default=0)    # 真实换手率
    dragon_tiger_score = Column(Float, default=0)     # 龙虎榜+北向资金
    money_flow_score = Column(Float, default=0)       # 个股资金结构
    amount_rank_score = Column(Float, default=0)      # 成交金额排名
    sector_heat_score = Column(Float, default=0)      # 热点板块
    bias_ma3_score = Column(Float, default=0)         # MA3乖离率
    sentiment_score = Column(Float, default=0)        # 舆情分析(附加)
    sector_linkage_score = Column(Float, default=0)   # 板块联动强度
    
    total_score = Column(Float, default=0)
    
    # 因子原始值
    first_limit_time_raw = Column(String(8))          # 首次涨停时间原始值
    limit_times_raw = Column(Integer)
    seal_ratio_raw = Column(Float)
    seal_flow_ratio_raw = Column(Float)
    volume_ratio_raw = Column(Float)
    turnover_rate_raw = Column(Float)
    net_buy_amount_raw = Column(Float)                # 龙虎榜净买入
    main_net_inflow_raw = Column(Float)               # 主力净流入
    amount_rank_raw = Column(Integer)
    sector_zt_count_raw = Column(Integer)
    bias_ma3_raw = Column(Float)
    sector_linkage_raw = Column(Text)                 # 板块联动原始值(JSON)
    
    created_at = Column(DateTime, default=datetime.now)


class AuctionData(Base):
    """竞价数据表"""
    __tablename__ = 'auction_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), index=True)
    trade_date = Column(String(8), index=True)
    
    # 竞价数据
    auction_price = Column(Float)                     # 竞价价格
    auction_vol = Column(Float)                       # 竞价成交量
    auction_amount = Column(Float)                    # 竞价金额
    auction_pct_chg = Column(Float)                   # 竞价涨跌幅
    auction_turnover = Column(Float)                  # 竞价换手率
    auction_volume_ratio = Column(Float)              # 竞价量比
    auction_burst_ratio = Column(Float)               # 竞价爆量比
    
    # 板块相关
    sector_auction_pct = Column(Float)                # 板块竞价涨幅
    sector_resonance = Column(Float)                  # 板块共振度
    
    # 评分
    auction_score = Column(Float, default=0)
    final_score = Column(Float, default=0)            # 最终综合评分
    
    # 特殊情况
    is_weak_to_strong = Column(Boolean, default=False)  # 竞价爆量弱转强
    
    # ML 训练用字段
    is_selected = Column(Boolean, default=False)        # 是否被选中（进入前N）
    is_filtered = Column(Boolean, default=False)        # 是否被过滤排除
    filter_reason = Column(String(50))                  # 过滤原因
    market_risk = Column(Float, default=0)              # T+1日市场风险评分
    t_day_score = Column(Float, default=0)              # T日基础得分
    
    # 各因子评分和原始值（用于ML训练）
    auction_turnover_score = Column(Float, default=0)   # 竞价换手率评分
    auction_turnover_raw = Column(Float, default=0)     # 竞价换手率原始值
    auction_amount_score = Column(Float, default=0)     # 竞价金额评分
    auction_amount_raw = Column(Float, default=0)       # 竞价金额原始值
    auction_pct_chg_score = Column(Float, default=0)    # 竞价涨幅评分
    auction_pct_chg_raw = Column(Float, default=0)      # 竞价涨幅原始值
    auction_volume_ratio_score = Column(Float, default=0)  # 竞价量比评分
    auction_volume_ratio_raw = Column(Float, default=0)    # 竞价量比原始值
    auction_burst_ratio_score = Column(Float, default=0)   # 竞价爆量比评分
    auction_burst_ratio_raw = Column(Float, default=0)     # 竞价爆量比原始值
    sector_auction_pct_score = Column(Float, default=0)    # 板块竞价涨幅评分
    sector_auction_pct_raw = Column(Float, default=0)      # 板块竞价涨幅原始值
    sector_resonance_score = Column(Float, default=0)      # 板块共振度评分
    sector_resonance_raw = Column(Float, default=0)        # 板块共振度原始值
    t_day_score_score = Column(Float, default=0)           # T日评分得分
    t_day_score_raw = Column(Float, default=0)             # T日评分原始值
    
    created_at = Column(DateTime, default=datetime.now)


class MarketSentiment(Base):
    """市场情绪表"""
    __tablename__ = 'market_sentiment'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), unique=True, index=True)
    
    # 涨跌停统计
    zt_num = Column(Integer, default=0)               # 涨停家数
    dt_num = Column(Integer, default=0)               # 跌停家数
    fb_ratio = Column(Float, default=0)               # 炸板率
    yzt_num = Column(Integer, default=0)              # 一字涨停数
    
    # 情绪阶段
    sentiment_stage = Column(String(20))              # 冰点/混沌/主升/高潮
    
    # 大盘数据
    sh_close = Column(Float)                          # 上证收盘
    sh_ma5 = Column(Float)                            # 上证5日均线
    sh_bias = Column(Float)                           # 上证偏离度
    
    # 融资融券
    rz_ye = Column(Float)                             # 融资余额(亿)
    rz_ye_change = Column(Float)                      # 融资余额变化率
    rq_ye = Column(Float)                             # 融券余额(亿)
    rq_ye_change = Column(Float)                      # 融券余额变化率
    rz_buy_repay_ratio = Column(Float)                # 融资买入/偿还比
    
    # 北向资金
    north_net_inflow = Column(Float)                  # 北向净流入(亿)
    
    # 风险评分
    risk_score = Column(Float, default=0)             # 风险评分(越高越危险)
    suggested_position = Column(Float, default=0.5)   # 建议仓位
    
    created_at = Column(DateTime, default=datetime.now)


class SelectionResult(Base):
    """选股结果表"""
    __tablename__ = 'selection_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), index=True)
    selection_type = Column(String(20))               # 't_day' / 't1_auction'
    
    ts_code = Column(String(12), index=True)
    stock_name = Column(String(20))
    
    # 评分
    total_score = Column(Float)
    final_rank = Column(Integer)
    sector_linkage_score = Column(Float, default=0)   # 板块联动强度得分
    sector_role_label = Column(String(20))            # 板块角色标签
    
    # 推荐信息
    sector = Column(String(50))                       # 所属板块
    reason = Column(Text)                             # 推荐理由
    unifuncs_recommended = Column(Boolean, default=False)
    
    # T+1竞价特有
    auction_price = Column(Float)
    auction_pct_chg = Column(Float)
    suggested_position = Column(Float)                # 建议仓位
    stop_loss = Column(Float)                         # 止损价
    target_price = Column(Float)                      # 目标价
    
    # 后续跟踪
    t2_open = Column(Float)                           # T+2开盘价
    t2_close = Column(Float)                          # T+2收盘价
    t2_return = Column(Float)                         # T+2收益率
    is_success = Column(Boolean)                      # 是否成功(>3%)
    
    created_at = Column(DateTime, default=datetime.now)


class StrategyEvolution(Base):
    """策略进化记录表"""
    __tablename__ = 'strategy_evolution'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    evolution_date = Column(String(8), index=True)
    
    # 因子权重调整
    old_weights = Column(Text)                        # JSON格式旧权重
    new_weights = Column(Text)                        # JSON格式新权重
    
    # 因子有效性
    factor_ic_values = Column(Text)                   # JSON格式因子IC值
    invalid_factors = Column(Text)                    # JSON格式失效因子列表
    
    # 策略表现
    win_rate = Column(Float)                          # 胜率
    avg_return = Column(Float)                        # 平均收益
    
    # 调优建议
    optimization_notes = Column(Text)
    
    # MoA多模型分析结果（Phase 3新增）
    moa_analysis = Column(Text)                       # JSON格式MoA分析结果
    final_recommendation = Column(Text)               # 最终优化建议
    execution_plan = Column(Text)                     # JSON格式执行计划
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    created_at = Column(DateTime, default=datetime.now)


class DailyStockRecord(Base):
    """每日股票记录表(用于策略反思)"""
    __tablename__ = 'daily_stock_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(12), index=True)
    trade_date = Column(String(8), index=True)
    
    # T日数据
    t_close = Column(Float)                           # T日收盘
    t_score = Column(Float)                           # T日评分
    t_rank = Column(Integer)                          # T日排名
    
    # T+1数据
    t1_open = Column(Float)                           # T+1开盘
    t1_auction_price = Column(Float)                  # T+1竞价
    t1_auction_score = Column(Float)                  # T+1竞价评分
    t1_close = Column(Float)                          # T+1收盘
    t1_high = Column(Float)                           # T+1最高
    
    # T+2数据
    t2_open = Column(Float)
    t2_close = Column(Float)
    t2_return = Column(Float)                         # 实际收益
    
    # 判断结果
    is_selected = Column(Boolean, default=False)      # 是否被选中
    is_success = Column(Boolean)                      # 是否成功
    
    created_at = Column(DateTime, default=datetime.now)


class TrackedResult(Base):
    """T+1 竞价选股结果跟踪表"""
    __tablename__ = 'tracked_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 日期
    t_day = Column(String(8), index=True)             # T日
    t1_day = Column(String(8), index=True)            # T+1日
    t2_day = Column(String(8), index=True)            # T+2日
    
    # 股票信息
    ts_code = Column(String(12), index=True)
    stock_name = Column(String(20))
    
    # 买卖点
    t1_open = Column(Float)                           # T+1开盘价 (买入价)
    t2_close = Column(Float)                          # T+2收盘价 (兼容旧数据)
    
    # 收益统计（新规则）
    return_pct = Column(Float)                        # 总收益率 (%)
    is_win = Column(Boolean, default=False)           # 是否盈利 (总收益为正)
    final_profit = Column(Float)                       # 最终总盈利（元/股）
    
    # 仓位跟踪
    shares_held = Column(Float, default=1.0)           # 剩余仓位比例
    sell_history = Column(Text, default='[]')          # 卖出历史（JSON格式）
    
    # 选股排名
    selection_rank = Column(Integer)                  # T+1竞价排名
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_tracked_t1', 't1_day', 'ts_code'),
    )


class MLTrainingRecord(Base):
    """机器学习训练数据表 - 存储完整的因子特征和收益标签
    
    数据来源:
    - T日因子: 从 stock_factor_scores 表获取
    - T+1竞价因子: 从 auction_data 表获取
    - T+2收益: 从 tracked_results 表获取
    
    用途:
    - 机器学习模型训练
    - 因子有效性分析
    - 策略优化
    """
    __tablename__ = 'ml_training_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # ========== 日期标识 ==========
    t_day = Column(String(8), index=True)             # T日 (选股日)
    t1_day = Column(String(8), index=True)            # T+1日 (竞价日)
    t2_day = Column(String(8), index=True)            # T+2日 (卖出日)
    
    # ========== 股票信息 ==========
    ts_code = Column(String(12), index=True)
    stock_name = Column(String(20))
    
    # ========== T日因子评分 (12个) ==========
    # 来自 stock_factor_scores 表
    t_limit_quality_score = Column(Float, default=0)      # 涨停质量评分
    t_seal_ratio_score = Column(Float, default=0)         # 封成比评分
    t_seal_flow_ratio_score = Column(Float, default=0)    # 封流比评分
    t_volume_ratio_score = Column(Float, default=0)       # 量比评分
    t_turnover_rate_score = Column(Float, default=0)      # 换手率评分
    t_dragon_tiger_score = Column(Float, default=0)       # 龙虎榜评分
    t_money_flow_score = Column(Float, default=0)         # 资金流向评分
    t_amount_rank_score = Column(Float, default=0)        # 成交额排名评分
    t_sector_heat_score = Column(Float, default=0)        # 板块热度评分
    t_bias_ma3_score = Column(Float, default=0)           # MA3乖离率评分
    t_sentiment_score = Column(Float, default=0)          # 舆情评分
    t_sector_linkage_score = Column(Float, default=0)     # 板块联动评分
    t_total_score = Column(Float, default=0)              # T日总评分
    
    # ========== T日原始值 (11个) ==========
    t_first_limit_time = Column(String(8))                 # 首次涨停时间
    t_limit_times = Column(Integer, default=0)             # 炸板次数
    t_seal_ratio = Column(Float, default=0)                # 封成比原始值
    t_seal_flow_ratio = Column(Float, default=0)           # 封流比原始值
    t_volume_ratio = Column(Float, default=0)              # 量比原始值
    t_turnover_rate = Column(Float, default=0)             # 换手率原始值
    t_net_buy_amount = Column(Float, default=0)            # 龙虎榜净买入
    t_main_net_inflow = Column(Float, default=0)           # 主力净流入
    t_amount_rank = Column(Integer, default=0)             # 成交额排名
    t_sector_zt_count = Column(Integer, default=0)         # 板块涨停股数
    t_bias_ma3 = Column(Float, default=0)                  # MA3乖离率原始值
    
    # ========== T+1竞价因子 (6个) ==========
    # 来自 auction_data 表
    t1_auction_price = Column(Float, default=0)            # 竞价价格
    t1_auction_pct_chg = Column(Float, default=0)          # 竞价涨跌幅
    t1_auction_turnover = Column(Float, default=0)         # 竞价换手率
    t1_auction_volume_ratio = Column(Float, default=0)     # 竞价量比
    t1_auction_burst_ratio = Column(Float, default=0)      # 竞价爆量比
    t1_sector_resonance = Column(Float, default=0)         # 板块共振度
    t1_auction_score = Column(Float, default=0)            # 竞价评分
    t1_final_score = Column(Float, default=0)              # 最终评分
    t1_is_weak_to_strong = Column(Boolean, default=False)  # 是否弱转强
    
    # ========== T+2收益标签 (目标变量) ==========
    # 来自 tracked_results 表
    t1_open = Column(Float)                                # T+1开盘价 (买入价)
    t2_close = Column(Float)                               # T+2收盘价 (卖出价)
    return_pct = Column(Float)                             # 收益率 (%)
    is_win = Column(Boolean, default=False)                # 是否盈利 (>3%)
    
    # ========== 选股排名 ==========
    t_day_rank = Column(Integer)                           # T日选股排名
    t1_auction_rank = Column(Integer)                      # T+1竞价排名
    
    # ========== 元数据 ==========
    sector = Column(String(50))                            # 所属板块
    sector_role_label = Column(String(20))                 # 板块角色标签
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_ml_t1', 't1_day', 'ts_code'),
        Index('idx_ml_training', 't_day', 'ts_code'),
    )


# ==================== 游资画像数据库 ====================

class HotMoneyProfile(Base):
    """游资画像表 - 存储游资基本信息和风格特征"""
    __tablename__ = 'hot_money_profile'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 游资标识
    hot_money_id = Column(String(50), unique=True, index=True)  # 游资唯一标识（如：zhangmengzhu）
    hot_money_name = Column(String(50))                          # 游资名称（如：章盟主）
    
    # 风格特征（多选，JSON数组）
    style_tags = Column(Text)              # 风格标签：打板/低吸/半路板/首板/连板/趋势
    position_style = Column(String(20))    # 持仓风格：短线/中线/波段
    
    # 操作偏好
    preferred_mv = Column(String(50))      # 偏好市值：小盘(<50亿)/中盘(50-200亿)/大盘
    preferred_sector = Column(Text)        # 偏好板块（JSON数组）
    avoid_sector = Column(Text)            # 规避板块（JSON数组）
    
    # 统计指标
    total_trades = Column(Integer, default=0)       # 总操作次数
    win_count = Column(Integer, default=0)          # 盈利次数
    loss_count = Column(Integer, default=0)         # 亏损次数
    win_rate = Column(Float, default=0)             # 胜率 (%)
    avg_return = Column(Float, default=0)           # 平均收益率 (%)
    avg_holding_days = Column(Float, default=0)     # 平均持仓天数
    max_profit = Column(Float, default=0)           # 单笔最大盈利 (%)
    max_loss = Column(Float, default=0)             # 单笔最大亏损 (%)
    
    # 影响力评分
    influence_score = Column(Float, default=5)      # 影响力评分 (1-10)
    follow_value = Column(Float, default=5)         # 跟随价值 (1-10)
    
    # 备注
    description = Column(Text)              # 游资描述
    typical_stocks = Column(Text)           # 代表作（JSON数组）
    
    # 状态
    is_active = Column(Boolean, default=True)      # 是否活跃
    last_trade_date = Column(String(8))            # 最近操作日期
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class HotMoneySeat(Base):
    """游资席位表 - 存储游资席位及其马甲关系"""
    __tablename__ = 'hot_money_seat'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 席位信息
    seat_name = Column(String(100), unique=True, index=True)  # 席位完整名称
    seat_code = Column(String(20))                            # 席位代码（如有）
    broker = Column(String(50))                               # 所属券商
    
    # 关联游资
    hot_money_id = Column(String(50), index=True)             # 关联的游资ID
    is_primary = Column(Boolean, default=False)               # 是否主席位
    
    # 席位类型
    seat_type = Column(String(20))    # 知名游资/机构/北向/量化/普通游资
    
    # 统计（该席位）
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    
    # 备注
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)


class HotMoneyTrade(Base):
    """游资操作记录表 - 存储游资历史操作"""
    __tablename__ = 'hot_money_trade'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 操作信息
    trade_date = Column(String(8), index=True)      # 操作日期
    ts_code = Column(String(12), index=True)        # 股票代码
    stock_name = Column(String(20))                 # 股票名称
    
    # 游资信息
    hot_money_id = Column(String(50), index=True)   # 游资ID
    seat_name = Column(String(100), index=True)     # 操作席位
    
    # 操作详情
    trade_type = Column(String(10))          # 买入/卖出
    buy_amount = Column(Float)               # 买入金额(万元)
    sell_amount = Column(Float)              # 卖出金额(万元)
    net_buy = Column(Float)                  # 净买入(万元)
    buy_ratio = Column(Float)                # 买入占比(%)
    
    # 股票状态
    stock_status = Column(String(20))        # 首板/2板/3板/高位
    is_limit_up = Column(Boolean)            # 是否涨停
    
    # 后续跟踪
    t1_return = Column(Float)                # T+1收益(%)
    t2_return = Column(Float)                # T+2收益(%)
    t3_return = Column(Float)                # T+3收益(%)
    max_return = Column(Float)               # 最大收益(%)
    is_win = Column(Boolean)                 # 是否盈利
    
    # 数据来源
    source = Column(String(20))              # 数据来源：龙虎榜/人工录入
    raw_data = Column(Text)                  # 原始数据(JSON)
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_hm_trade', 'trade_date', 'hot_money_id', 'ts_code'),
    )


class HotMoneyStats(Base):
    """游资统计表 - 存储游资周期性统计数据"""
    __tablename__ = 'hot_money_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 统计周期
    hot_money_id = Column(String(50), index=True)
    stat_date = Column(String(8), index=True)       # 统计截止日期
    stat_period = Column(String(10))                # 统计周期：7d/30d/90d/all
    
    # 操作统计
    total_trades = Column(Integer, default=0)       # 总操作次数
    limit_up_trades = Column(Integer, default=0)    # 涨停股操作次数
    consecutive_trades = Column(Integer, default=0) # 连板股操作次数
    
    # 收益统计
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0)             # 胜率
    avg_return = Column(Float, default=0)           # 平均收益
    profit_loss_ratio = Column(Float, default=0)    # 盈亏比
    
    # 持仓统计
    avg_holding_days = Column(Float, default=0)
    max_continuous_win = Column(Integer, default=0) # 最大连赢次数
    max_continuous_loss = Column(Integer, default=0)# 最大连亏次数
    
    # 板块偏好
    top_sectors = Column(Text)              # 最爱板块(JSON数组)
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_hm_stats', 'hot_money_id', 'stat_period'),
    )


class UnifuncsResult(Base):
    """Unifuncs 舆情分析结果表"""
    __tablename__ = 'unifuncs_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 日期标识
    trade_date = Column(String(8), unique=True, index=True)  # 交易日期 YYYYMMDD
    
    # 任务信息
    task_id = Column(String(100))                     # Unifuncs 任务ID
    status = Column(String(20))                       # 任务状态: completed/failed/timeout
    
    # 结构化结果
    hot_sectors = Column(Text)                        # 热点板块 (JSON数组)
    recommendations = Column(Text)                    # 推荐股票列表 (JSON数组)
    
    # 原始数据
    answer = Column(Text)                             # Unifuncs 完整回答
    summary = Column(Text)                            # 摘要
    
    # 元数据
    extraction_method = Column(String(20))            # 提取方式: llm/regex
    llm_model = Column(String(50))                    # 使用的LLM模型
    raw_response = Column(Text)                       # 原始响应 (JSON)
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_unifuncs_date', 'trade_date'),
    )


def init_db():
    """初始化数据库"""
    engine_kwargs = get_engine_kwargs()
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    try:
        Base.metadata.create_all(engine)
    except ProgrammingError as e:
        # 忽略索引已存在的错误
        if "already exists" in str(e) and "relation " in str(e):
            print(f"忽略已存在的数据库对象: {e}")
        else:
            raise
    return engine


def get_session():
    """获取数据库会话"""
    engine_kwargs = get_engine_kwargs()
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == '__main__':
    init_db()
    if DB_TYPE == 'postgres':
        print(f"PostgreSQL 数据库初始化完成: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
    else:
        print(f"SQLite 数据库初始化完成: {DB_PATH}")
