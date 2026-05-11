"""
T01 龙头选股策略 - 配置文件模板
需要根据实际情况填写以下配置
"""

# ========== 数据源配置 ==========
# Tushare Pro API (推荐)
TUSHARE_TOKEN = "your_tushare_token_here"  # 请替换为您的token

# AKShare (备用数据源)
AKSHARE_ENABLE = True

# ========== 数据库配置 ==========
# SQLite (开发测试)
DB_SQLITE_PATH = "data/t01_stock.db"

# PostgreSQL (生产环境)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "t01_stock"
DB_USER = "your_username"
DB_PASSWORD = "your_password"

# ========== 选股参数配置 ==========
# 涨停板识别参数
ZT_THRESHOLD = 0.099  # 涨停阈值 (9.9%)

# 龙头股评分参数
LEADER_SCORE_FACTORS = {
    "volume_ratio": 0.25,      # 量比权重
    "turnover": 0.20,          # 换手率权重
    "limit_up_days": 0.30,     # 连板天数权重
    "sector_strength": 0.25,   # 板块强度权重
}

# 板块追踪参数
SECTOR_TRACK_DAYS = 5  # 追踪最近N天的板块表现

# ========== 回测配置 ==========
BACKTEST_START_DATE = "20240101"
BACKTEST_END_DATE = "20241231"
INITIAL_CAPITAL = 1000000  # 初始资金 (100万)

# ========== 风控配置 ==========
RISK_CONFIG = {
    "max_position_per_stock": 0.20,  # 单票最大仓位 20%
    "max_position_total": 0.80,       # 总最大仓位 80%
    "stop_loss_pct": -0.07,           # 止损线 -7%
    "stop_profit_pct": 0.15,          # 止盈线 +15%
}

# ========== 通知配置 ==========
# 飞书通知
FEISHU_WEBHOOK = "your_feishu_webhook_url"
FEISHU_SECRET = "your_feishu_secret"

# 邮件通知
EMAIL_ENABLE = True
EMAIL_TO = ["jarvis@jaccoffice.com"]

# ========== 定时任务配置 ==========
CRON_SCHEDULE = {
    "daily_scan": "0 15 * * 1-5",     # 交易日15:00执行
    "weekly_report": "0 18 * * 5",    # 周五18:00周报
}
