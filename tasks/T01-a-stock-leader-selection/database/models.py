"""
T01 选股系统 - 数据库模型

SQLite 数据库表结构定义
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 't01_stocks.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'


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
    open = Column(Float)                              # 开盘价
    high = Column(Float)                              # 最高价
    low = Column(Float)                               # 最低价
    close = Column(Float)                             # 收盘价
    pre_close = Column(Float)                         # 昨收价
    change = Column(Float)                            # 涨跌额
    pct_chg = Column(Float)                           # 涨跌幅%
    vol = Column(Float)                               # 成交量(手)
    amount = Column(Float)                            # 成交额(千元)
    
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


def init_db():
    """初始化数据库"""
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """获取数据库会话"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == '__main__':
    init_db()
    print(f"数据库初始化完成: {DB_PATH}")
