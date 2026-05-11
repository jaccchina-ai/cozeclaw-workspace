#!/usr/bin/env python3
"""
T01 选股系统 - PostgreSQL 表结构创建脚本
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# PostgreSQL 连接配置
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 't01_stocks',
    'user': 't01_user',
    'password': 't01_pass_2026'
}

# SQL 创建表语句
CREATE_TABLES_SQL = """
-- 交易日历表
CREATE TABLE IF NOT EXISTS trading_calendar (
    exchange VARCHAR(10) NOT NULL,
    cal_date VARCHAR(8) NOT NULL,
    is_open BOOLEAN,
    pretrade_date VARCHAR(8),
    PRIMARY KEY (exchange, cal_date)
);

-- 每日股票数据表
CREATE TABLE IF NOT EXISTS daily_stock_data (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    pre_close FLOAT,
    change FLOAT,
    pct_chg FLOAT,
    vol FLOAT,
    amount FLOAT,
    turnover_rate FLOAT,
    volume_ratio FLOAT,
    free_share FLOAT,
    free_mv FLOAT,
    real_turnover_rate FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_ts_code ON daily_stock_data(ts_code);
CREATE INDEX IF NOT EXISTS idx_daily_trade_date ON daily_stock_data(trade_date);
CREATE INDEX IF NOT EXISTS idx_daily_ts_trade ON daily_stock_data(ts_code, trade_date);

-- 涨停股票表
CREATE TABLE IF NOT EXISTS limit_up_stocks (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    first_limit_time VARCHAR(8),
    last_limit_time VARCHAR(8),
    limit_times INTEGER DEFAULT 0,
    up_stat VARCHAR(20),
    limit_amount FLOAT,
    seal_ratio FLOAT,
    seal_flow_ratio FLOAT,
    consecutive_limit INTEGER DEFAULT 1,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    pct_chg FLOAT,
    vol FLOAT,
    amount FLOAT,
    total_score FLOAT DEFAULT 0,
    score_rank INTEGER,
    unifuncs_recommended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_limit_ts_code ON limit_up_stocks(ts_code);
CREATE INDEX IF NOT EXISTS idx_limit_trade_date ON limit_up_stocks(trade_date);
CREATE INDEX IF NOT EXISTS idx_limit_ts_trade ON limit_up_stocks(ts_code, trade_date);

-- 股票因子评分表
CREATE TABLE IF NOT EXISTS stock_factor_scores (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    limit_quality_score FLOAT DEFAULT 0,
    seal_ratio_score FLOAT DEFAULT 0,
    seal_flow_ratio_score FLOAT DEFAULT 0,
    volume_ratio_score FLOAT DEFAULT 0,
    turnover_rate_score FLOAT DEFAULT 0,
    dragon_tiger_score FLOAT DEFAULT 0,
    money_flow_score FLOAT DEFAULT 0,
    amount_rank_score FLOAT DEFAULT 0,
    sector_heat_score FLOAT DEFAULT 0,
    bias_ma3_score FLOAT DEFAULT 0,
    sentiment_score FLOAT DEFAULT 0,
    sector_linkage_score FLOAT DEFAULT 0,
    total_score FLOAT DEFAULT 0,
    first_limit_time_raw VARCHAR(8),
    limit_times_raw INTEGER,
    seal_ratio_raw FLOAT,
    seal_flow_ratio_raw FLOAT,
    volume_ratio_raw FLOAT,
    turnover_rate_raw FLOAT,
    net_buy_amount_raw FLOAT,
    main_net_inflow_raw FLOAT,
    amount_rank_raw INTEGER,
    sector_zt_count_raw INTEGER,
    bias_ma3_raw FLOAT,
    sector_linkage_raw TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_factor_ts_code ON stock_factor_scores(ts_code);
CREATE INDEX IF NOT EXISTS idx_factor_trade_date ON stock_factor_scores(trade_date);

-- 竞价数据表
CREATE TABLE IF NOT EXISTS auction_data (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    auction_price FLOAT,
    auction_vol FLOAT,
    auction_amount FLOAT,
    auction_pct_chg FLOAT,
    auction_turnover FLOAT,
    auction_volume_ratio FLOAT,
    auction_burst_ratio FLOAT,
    sector_auction_pct FLOAT,
    sector_resonance FLOAT,
    auction_score FLOAT DEFAULT 0,
    final_score FLOAT DEFAULT 0,
    is_weak_to_strong BOOLEAN DEFAULT FALSE,
    is_selected BOOLEAN DEFAULT FALSE,
    is_filtered BOOLEAN DEFAULT FALSE,
    filter_reason VARCHAR(50),
    market_risk FLOAT DEFAULT 0,
    t_day_score FLOAT DEFAULT 0,
    auction_turnover_score FLOAT DEFAULT 0,
    auction_turnover_raw FLOAT DEFAULT 0,
    auction_amount_score FLOAT DEFAULT 0,
    auction_amount_raw FLOAT DEFAULT 0,
    auction_pct_chg_score FLOAT DEFAULT 0,
    auction_pct_chg_raw FLOAT DEFAULT 0,
    auction_volume_ratio_score FLOAT DEFAULT 0,
    auction_volume_ratio_raw FLOAT DEFAULT 0,
    auction_burst_ratio_score FLOAT DEFAULT 0,
    auction_burst_ratio_raw FLOAT DEFAULT 0,
    sector_auction_pct_score FLOAT DEFAULT 0,
    sector_auction_pct_raw FLOAT DEFAULT 0,
    sector_resonance_score FLOAT DEFAULT 0,
    sector_resonance_raw FLOAT DEFAULT 0,
    t_day_score_score FLOAT DEFAULT 0,
    t_day_score_raw FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auction_ts_code ON auction_data(ts_code);
CREATE INDEX IF NOT EXISTS idx_auction_trade_date ON auction_data(trade_date);

-- 市场情绪表
CREATE TABLE IF NOT EXISTS market_sentiment (
    id SERIAL PRIMARY KEY,
    trade_date VARCHAR(8) UNIQUE NOT NULL,
    zt_num INTEGER DEFAULT 0,
    dt_num INTEGER DEFAULT 0,
    fb_ratio FLOAT DEFAULT 0,
    yzt_num INTEGER DEFAULT 0,
    sentiment_stage VARCHAR(20),
    sh_close FLOAT,
    sh_ma5 FLOAT,
    sh_bias FLOAT,
    rz_ye FLOAT,
    rz_ye_change FLOAT,
    rq_ye FLOAT,
    rq_ye_change FLOAT,
    rz_buy_repay_ratio FLOAT,
    north_net_inflow FLOAT,
    risk_score FLOAT DEFAULT 0,
    suggested_position FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sentiment_trade_date ON market_sentiment(trade_date);

-- 选股结果表
CREATE TABLE IF NOT EXISTS selection_results (
    id SERIAL PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    selection_type VARCHAR(20),
    ts_code VARCHAR(12) NOT NULL,
    stock_name VARCHAR(20),
    total_score FLOAT,
    final_rank INTEGER,
    sector_linkage_score FLOAT DEFAULT 0,
    sector_role_label VARCHAR(20),
    sector VARCHAR(50),
    reason TEXT,
    unifuncs_recommended BOOLEAN DEFAULT FALSE,
    auction_price FLOAT,
    auction_pct_chg FLOAT,
    suggested_position FLOAT,
    stop_loss FLOAT,
    target_price FLOAT,
    t2_open FLOAT,
    t2_close FLOAT,
    t2_return FLOAT,
    is_success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_selection_trade_date ON selection_results(trade_date);
CREATE INDEX IF NOT EXISTS idx_selection_ts_code ON selection_results(ts_code);

-- 策略进化记录表
CREATE TABLE IF NOT EXISTS strategy_evolution (
    id SERIAL PRIMARY KEY,
    evolution_date VARCHAR(8) NOT NULL,
    old_weights TEXT,
    new_weights TEXT,
    factor_ic_values TEXT,
    invalid_factors TEXT,
    win_rate FLOAT,
    avg_return FLOAT,
    optimization_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evolution_date ON strategy_evolution(evolution_date);

-- 每日股票记录表
CREATE TABLE IF NOT EXISTS daily_stock_records (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    t_close FLOAT,
    t_score FLOAT,
    t_rank INTEGER,
    t1_open FLOAT,
    t1_auction_price FLOAT,
    t1_auction_score FLOAT,
    t1_close FLOAT,
    t1_high FLOAT,
    t2_open FLOAT,
    t2_close FLOAT,
    t2_return FLOAT,
    is_selected BOOLEAN DEFAULT FALSE,
    is_success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_record_ts_code ON daily_stock_records(ts_code);
CREATE INDEX IF NOT EXISTS idx_record_trade_date ON daily_stock_records(trade_date);

-- T+1 竞价选股结果跟踪表
CREATE TABLE IF NOT EXISTS tracked_results (
    id SERIAL PRIMARY KEY,
    t_day VARCHAR(8) NOT NULL,
    t1_day VARCHAR(8) NOT NULL,
    t2_day VARCHAR(8) NOT NULL,
    ts_code VARCHAR(12) NOT NULL,
    stock_name VARCHAR(20),
    t1_open FLOAT,
    t2_close FLOAT,
    return_pct FLOAT,
    is_win BOOLEAN DEFAULT FALSE,
    selection_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracked_t1 ON tracked_results(t1_day, ts_code);
CREATE INDEX IF NOT EXISTS idx_tracked_t_day ON tracked_results(t_day);

-- 机器学习训练数据表
CREATE TABLE IF NOT EXISTS ml_training_records (
    id SERIAL PRIMARY KEY,
    t_day VARCHAR(8) NOT NULL,
    t1_day VARCHAR(8) NOT NULL,
    t2_day VARCHAR(8) NOT NULL,
    ts_code VARCHAR(12) NOT NULL,
    stock_name VARCHAR(20),
    t_limit_quality_score FLOAT DEFAULT 0,
    t_seal_ratio_score FLOAT DEFAULT 0,
    t_seal_flow_ratio_score FLOAT DEFAULT 0,
    t_volume_ratio_score FLOAT DEFAULT 0,
    t_turnover_rate_score FLOAT DEFAULT 0,
    t_dragon_tiger_score FLOAT DEFAULT 0,
    t_money_flow_score FLOAT DEFAULT 0,
    t_amount_rank_score FLOAT DEFAULT 0,
    t_sector_heat_score FLOAT DEFAULT 0,
    t_bias_ma3_score FLOAT DEFAULT 0,
    t_sentiment_score FLOAT DEFAULT 0,
    t_sector_linkage_score FLOAT DEFAULT 0,
    t_total_score FLOAT DEFAULT 0,
    t_first_limit_time VARCHAR(8),
    t_limit_times INTEGER DEFAULT 0,
    t_seal_ratio FLOAT DEFAULT 0,
    t_seal_flow_ratio FLOAT DEFAULT 0,
    t_volume_ratio FLOAT DEFAULT 0,
    t_turnover_rate FLOAT DEFAULT 0,
    t_net_buy_amount FLOAT DEFAULT 0,
    t_main_net_inflow FLOAT DEFAULT 0,
    t_amount_rank INTEGER DEFAULT 0,
    t_sector_zt_count INTEGER DEFAULT 0,
    t_bias_ma3 FLOAT DEFAULT 0,
    t1_auction_price FLOAT DEFAULT 0,
    t1_auction_pct_chg FLOAT DEFAULT 0,
    t1_auction_turnover FLOAT DEFAULT 0,
    t1_auction_volume_ratio FLOAT DEFAULT 0,
    t1_auction_burst_ratio FLOAT DEFAULT 0,
    t1_sector_resonance FLOAT DEFAULT 0,
    t1_auction_score FLOAT DEFAULT 0,
    t1_final_score FLOAT DEFAULT 0,
    t1_is_weak_to_strong BOOLEAN DEFAULT FALSE,
    t1_open FLOAT,
    t2_close FLOAT,
    return_pct FLOAT,
    is_win BOOLEAN DEFAULT FALSE,
    t_day_rank INTEGER,
    t1_auction_rank INTEGER,
    sector VARCHAR(50),
    sector_role_label VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_t1 ON ml_training_records(t1_day, ts_code);
CREATE INDEX IF NOT EXISTS idx_ml_training ON ml_training_records(t_day, ts_code);

-- 游资画像表
CREATE TABLE IF NOT EXISTS hot_money_profile (
    id SERIAL PRIMARY KEY,
    hot_money_id VARCHAR(50) UNIQUE NOT NULL,
    hot_money_name VARCHAR(50),
    style_tags TEXT,
    position_style VARCHAR(20),
    preferred_mv VARCHAR(50),
    preferred_sector TEXT,
    avoid_sector TEXT,
    total_trades INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0,
    avg_return FLOAT DEFAULT 0,
    avg_holding_days FLOAT DEFAULT 0,
    max_profit FLOAT DEFAULT 0,
    max_loss FLOAT DEFAULT 0,
    influence_score FLOAT DEFAULT 5,
    follow_value FLOAT DEFAULT 5,
    description TEXT,
    typical_stocks TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_trade_date VARCHAR(8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hot_money_id ON hot_money_profile(hot_money_id);

-- 游资席位表
CREATE TABLE IF NOT EXISTS hot_money_seat (
    id SERIAL PRIMARY KEY,
    seat_name VARCHAR(100) UNIQUE NOT NULL,
    seat_code VARCHAR(20),
    broker VARCHAR(50),
    hot_money_id VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE,
    seat_type VARCHAR(20),
    total_trades INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seat_hot_money_id ON hot_money_seat(hot_money_id);

-- 游资操作记录表
CREATE TABLE IF NOT EXISTS hot_money_trade (
    id SERIAL PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(12) NOT NULL,
    stock_name VARCHAR(20),
    hot_money_id VARCHAR(50) NOT NULL,
    seat_name VARCHAR(100) NOT NULL,
    trade_type VARCHAR(10),
    buy_amount FLOAT,
    sell_amount FLOAT,
    net_buy FLOAT,
    buy_ratio FLOAT,
    stock_status VARCHAR(20),
    is_limit_up BOOLEAN,
    t1_return FLOAT,
    t2_return FLOAT,
    t3_return FLOAT,
    max_return FLOAT,
    is_win BOOLEAN,
    source VARCHAR(20),
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hm_trade_date ON hot_money_trade(trade_date);
CREATE INDEX IF NOT EXISTS idx_hm_trade_ts_code ON hot_money_trade(ts_code);
CREATE INDEX IF NOT EXISTS idx_hm_trade_hot_money_id ON hot_money_trade(hot_money_id);

-- 游资统计表
CREATE TABLE IF NOT EXISTS hot_money_stats (
    id SERIAL PRIMARY KEY,
    hot_money_id VARCHAR(50) NOT NULL,
    stat_date VARCHAR(8) NOT NULL,
    stat_period VARCHAR(10),
    total_trades INTEGER DEFAULT 0,
    limit_up_trades INTEGER DEFAULT 0,
    consecutive_trades INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0,
    avg_return FLOAT DEFAULT 0,
    profit_loss_ratio FLOAT DEFAULT 0,
    avg_holding_days FLOAT DEFAULT 0,
    max_continuous_win INTEGER DEFAULT 0,
    max_continuous_loss INTEGER DEFAULT 0,
    top_sectors TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hm_stats_hot_money_id ON hot_money_stats(hot_money_id);
"""


def create_tables():
    """创建所有表"""
    print("=" * 60)
    print("T01 PostgreSQL 表结构创建")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 执行创建表语句
        cursor.execute(CREATE_TABLES_SQL)
        
        print("✅ 所有表创建成功")
        
        # 验证表
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"\n已创建 {len(tables)} 个表:")
        for t in tables:
            print(f"  - {t[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        raise


if __name__ == '__main__':
    create_tables()
