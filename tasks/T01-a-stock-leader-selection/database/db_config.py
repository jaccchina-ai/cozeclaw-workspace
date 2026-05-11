"""
T01 选股系统 - 数据库配置

支持 PostgreSQL 和 SQLite 双模式
优先使用 PostgreSQL（外部持久化），SQLite 作为备用
"""

import os
from typing import Optional

# 数据库类型配置
# 优先使用 SQLite（用户选择）
DB_TYPE = 'sqlite'

# PostgreSQL 配置（优先使用环境变量）
POSTGRES_CONFIG = {
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': int(os.environ.get('PGPORT', 5432)),
    'database': os.environ.get('PGDATABASE', 't01_stocks'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'password': os.environ.get('PGPASSWORD', '')
}

# SQLite 配置（备用）
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 't01_stocks.db')


def get_database_url(db_type: Optional[str] = None) -> str:
    """
    获取数据库连接 URL
    
    Args:
        db_type: 数据库类型，'postgres' 或 'sqlite'，默认使用 DB_TYPE
    
    Returns:
        数据库连接 URL
    """
    db = db_type or DB_TYPE
    
    if db == 'postgres':
        # 使用标准 PostgreSQL URL 格式
        password = POSTGRES_CONFIG['password']
        host = POSTGRES_CONFIG['host']
        port = POSTGRES_CONFIG['port']
        database = POSTGRES_CONFIG['database']
        
        # 检查是否有 SSL 配置
        sslmode = os.environ.get('PGSSLMODE', 'require')
        
        return f"postgresql://{POSTGRES_CONFIG['user']}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
    else:
        return f'sqlite:///{SQLITE_DB_PATH}'


def get_engine_kwargs(db_type: Optional[str] = None) -> dict:
    """
    获取 SQLAlchemy Engine 创建参数
    
    Args:
        db_type: 数据库类型
    
    Returns:
        Engine 参数字典
    """
    db = db_type or DB_TYPE
    
    if db == 'postgres':
        return {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_pre_ping': True,
            'echo': False
        }
    else:
        return {
            'connect_args': {'check_same_thread': False},
            'echo': False
        }


# 导出配置
DATABASE_URL = get_database_url()

# 隐藏密码打印
display_url = DATABASE_URL.replace(POSTGRES_CONFIG.get('password', ''), '***') if DB_TYPE == 'postgres' else DATABASE_URL
print(f"[数据库配置] 使用 {DB_TYPE.upper()} 数据库")
print(f"[数据库配置] 连接地址: {display_url}")
