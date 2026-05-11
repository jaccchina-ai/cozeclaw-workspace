"""
T01 选股系统 - 双数据库管理器

支持 PostgreSQL 和 SQLite 双写，确保数据安全
集成时间旅行功能，支持历史数据查询和快照管理
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import traceback

# 导入时间旅行模块
from .time_travel import SQLiteTimeTravel

# PostgreSQL 配置（已禁用，优先使用SQLite）
POSTGRES_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'database': os.environ.get('PG_DATABASE', 't01_stocks'),
    'user': os.environ.get('PG_USER', 't01_user'),
    'password': os.environ.get('PG_PASSWORD', 't01_pass_2026')
}

POSTGRES_URL = (
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

# SQLite 配置
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 't01_stocks.db')
SQLITE_URL = f'sqlite:///{SQLITE_PATH}'


class DualDatabaseManager:
    """双数据库管理器 - 同时写入 PostgreSQL 和 SQLite，支持时间旅行"""
    
    def __init__(self):
        self.pg_engine = None
        self.sqlite_engine = None
        self.pg_session_factory = None
        self.sqlite_session_factory = None
        self.time_travel = None  # 时间旅行实例
        self._initialized = False
        
    def _ensure_initialized(self):
        """延迟初始化"""
        if self._initialized:
            return
            
        # 跳过PostgreSQL初始化，优先使用SQLite
        print("[双数据库] 🚀 优先使用SQLite数据库，跳过PostgreSQL初始化")
        self.pg_engine = None
        self.pg_session_factory = None
        
        # 初始化 SQLite
        try:
            self.sqlite_engine = create_engine(
                SQLITE_URL,
                connect_args={'check_same_thread': False},
                echo=False
            )
            self.sqlite_session_factory = sessionmaker(bind=self.sqlite_engine)
            print("[双数据库] ✅ SQLite 连接成功")
            
            # 初始化时间旅行系统
            self.time_travel = SQLiteTimeTravel(SQLITE_PATH)
            print("[双数据库] ✅ 时间旅行系统初始化成功")
        except Exception as e:
            print(f"[双数据库] ⚠️ SQLite 连接失败: {e}")
            self.sqlite_engine = None
            self.sqlite_session_factory = None
            self.time_travel = None
            
        self._initialized = True
    
    @contextmanager
    def get_pg_session(self):
        """获取 PostgreSQL 会话"""
        self._ensure_initialized()
        if self.pg_session_factory:
            session = self.pg_session_factory()
            try:
                yield session
            finally:
                session.close()
        else:
            yield None
    
    @contextmanager
    def get_sqlite_session(self):
        """获取 SQLite 会话"""
        self._ensure_initialized()
        if self.sqlite_session_factory:
            session = self.sqlite_session_factory()
            try:
                yield session
            finally:
                session.close()
        else:
            yield None
    
    def save_to_both(self, model_class, data: Dict[str, Any], 
                     unique_keys: List[str] = None) -> Dict[str, bool]:
        """
        同时保存到两个数据库
        
        Args:
            model_class: SQLAlchemy 模型类
            data: 数据字典
            unique_keys: 用于去重的键列表，如 ['trade_date', 'ts_code']
        
        Returns:
            {'postgres': bool, 'sqlite': bool}
        """
        self._ensure_initialized()
        results = {'postgres': False, 'sqlite': False}
        
        # 保存到 PostgreSQL
        if self.pg_session_factory:
            try:
                with self.get_pg_session() as session:
                    if session:
                        # 删除旧记录（去重）
                        if unique_keys:
                            filter_conditions = [
                                getattr(model_class, key) == data.get(key) 
                                for key in unique_keys
                            ]
                            session.query(model_class).filter(*filter_conditions).delete()
                        
                        # 创建新记录
                        record = model_class(**data)
                        session.add(record)
                        session.commit()
                        results['postgres'] = True
            except Exception as e:
                print(f"[双数据库] PostgreSQL 保存失败: {e}")
        
        # 保存到 SQLite
        if self.sqlite_session_factory:
            try:
                with self.get_sqlite_session() as session:
                    if session:
                        # 删除旧记录（去重）
                        if unique_keys:
                            filter_conditions = [
                                getattr(model_class, key) == data.get(key) 
                                for key in unique_keys
                            ]
                            session.query(model_class).filter(*filter_conditions).delete()
                        
                        # 创建新记录
                        record = model_class(**data)
                        session.add(record)
                        session.commit()
                        results['sqlite'] = True
            except Exception as e:
                print(f"[双数据库] SQLite 保存失败: {e}")
        
        return results
    
    def save_batch_to_both(self, model_class, data_list: List[Dict[str, Any]],
                           unique_keys: List[str] = None) -> Dict[str, int]:
        """
        批量保存到两个数据库
        
        Args:
            model_class: SQLAlchemy 模型类
            data_list: 数据字典列表
            unique_keys: 用于去重的键列表
        
        Returns:
            {'postgres': int, 'sqlite': int}
        """
        self._ensure_initialized()
        results = {'postgres': 0, 'sqlite': 0}
        
        if not data_list:
            return results
        
        # 批量保存到 PostgreSQL
        if self.pg_session_factory:
            try:
                with self.get_pg_session() as session:
                    if session:
                        for data in data_list:
                            try:
                                if unique_keys:
                                    filter_conditions = [
                                        getattr(model_class, key) == data.get(key) 
                                        for key in unique_keys
                                    ]
                                    session.query(model_class).filter(*filter_conditions).delete()
                                
                                record = model_class(**data)
                                session.add(record)
                                results['postgres'] += 1
                            except Exception:
                                continue
                        session.commit()
            except Exception as e:
                print(f"[双数据库] PostgreSQL 批量保存失败: {e}")
        
        # 批量保存到 SQLite
        if self.sqlite_session_factory:
            try:
                with self.get_sqlite_session() as session:
                    if session:
                        for data in data_list:
                            try:
                                if unique_keys:
                                    filter_conditions = [
                                        getattr(model_class, key) == data.get(key) 
                                        for key in unique_keys
                                    ]
                                    session.query(model_class).filter(*filter_conditions).delete()
                                
                                record = model_class(**data)
                                session.add(record)
                                results['sqlite'] += 1
                            except Exception:
                                continue
                        session.commit()
            except Exception as e:
                print(f"[双数据库] SQLite 批量保存失败: {e}")
        
        return results
    
    def query_with_fallback(self, model_class, filter_func=None, 
                            order_by=None, limit=None) -> List[Any]:
        """
        查询数据，PostgreSQL 优先，失败则回退到 SQLite
        
        Args:
            model_class: SQLAlchemy 模型类
            filter_func: 过滤函数
            order_by: 排序字段
            limit: 返回数量限制
        
        Returns:
            查询结果列表
        """
        self._ensure_initialized()
        
        # 优先从 PostgreSQL 查询
        if self.pg_session_factory:
            try:
                with self.get_pg_session() as session:
                    if session:
                        query = session.query(model_class)
                        if filter_func:
                            query = filter_func(query)
                        if order_by is not None:
                            query = query.order_by(order_by)
                        if limit:
                            query = query.limit(limit)
                        results = query.all()
                        if results:
                            return results
            except Exception as e:
                print(f"[双数据库] PostgreSQL 查询失败，尝试 SQLite: {e}")
        
        # 回退到 SQLite
        if self.sqlite_session_factory:
            try:
                with self.get_sqlite_session() as session:
                    if session:
                        query = session.query(model_class)
                        if filter_func:
                            query = filter_func(query)
                        if order_by is not None:
                            query = query.order_by(order_by)
                        if limit:
                            query = query.limit(limit)
                        return query.all()
            except Exception as e:
                print(f"[双数据库] SQLite 查询也失败: {e}")
        
        return []
    
    def is_pg_available(self) -> bool:
        """检查 PostgreSQL 是否可用"""
        self._ensure_initialized()
        return self.pg_engine is not None
    
    def is_sqlite_available(self) -> bool:
        """检查 SQLite 是否可用"""
        self._ensure_initialized()
        return self.sqlite_engine is not None
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        self._ensure_initialized()
        return {
            'postgresql': {
                'available': self.pg_engine is not None,
                'url': POSTGRES_URL.replace(POSTGRES_CONFIG['password'], '***')
            },
            'sqlite': {
                'available': self.sqlite_engine is not None,
                'path': SQLITE_PATH
            },
            'time_travel': {
                'available': self.time_travel is not None
            }
        }
    
    # ========== 时间旅行功能 ==========
    
    def query_at_date(self, table_name: str, target_date: str,
                      date_column: str = None) -> List[Dict]:
        """
        时间旅行：查询特定日期的数据
        
        Args:
            table_name: 表名
            target_date: 目标日期
            date_column: 日期字段名
            
        Returns:
            数据记录列表
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.query_at_date(table_name, target_date, date_column)
        
        print("[双数据库] 时间旅行系统不可用")
        return []
    
    def get_available_dates(self, table_name: str,
                            date_column: str = None) -> List[str]:
        """
        获取表中所有可用日期
        
        Args:
            table_name: 表名
            date_column: 日期字段名
            
        Returns:
            日期列表（降序）
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.get_available_dates(table_name, date_column)
        
        return []
    
    def get_latest_date(self, table_name: str,
                        date_column: str = None) -> Optional[str]:
        """
        获取表中最新日期
        
        Args:
            table_name: 表名
            date_column: 日期字段名
            
        Returns:
            最新日期字符串
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.get_latest_date(table_name, date_column)
        
        return None
    
    def compare_dates(self, table_name: str, date1: str, date2: str,
                      date_column: str = None) -> Dict:
        """
        对比两个日期的数据变化
        
        Args:
            table_name: 表名
            date1: 日期1
            date2: 日期2
            date_column: 日期字段名
            
        Returns:
            对比结果
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.compare_dates(table_name, date1, date2, date_column)
        
        return {'error': '时间旅行系统不可用'}
    
    def analyze_temporal_patterns(self, table_name: str,
                                   date_column: str = None) -> Dict:
        """
        分析时间模式
        
        Args:
            table_name: 表名
            date_column: 日期字段名
            
        Returns:
            时间模式分析结果
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.analyze_temporal_patterns(table_name, date_column)
        
        return {'error': '时间旅行系统不可用'}
    
    def get_timeline_report(self, table_name: str = None) -> Dict:
        """
        生成时间线报告
        
        Args:
            table_name: 表名，为空则生成所有表的报告
            
        Returns:
            时间线报告
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.get_timeline_report(table_name)
        
        return {'error': '时间旅行系统不可用'}
    
    # ========== 快照管理 ==========
    
    def create_snapshot(self, name: str = None, description: str = "") -> Optional[str]:
        """
        创建数据库快照
        
        Args:
            name: 快照名称
            description: 快照描述
            
        Returns:
            快照路径
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.create_snapshot(name, description)
        
        print("[双数据库] 时间旅行系统不可用，无法创建快照")
        return None
    
    def list_snapshots(self) -> List[Dict]:
        """列出所有快照"""
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.list_snapshots()
        
        return []
    
    def restore_from_snapshot(self, snapshot_name: str,
                              backup_current: bool = True) -> bool:
        """
        从快照恢复数据库
        
        Args:
            snapshot_name: 快照名称
            backup_current: 是否备份当前数据库
            
        Returns:
            是否成功
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.restore_from_snapshot(snapshot_name, backup_current)
        
        print("[双数据库] 时间旅行系统不可用，无法恢复快照")
        return False
    
    def cleanup_old_snapshots(self, keep_count: int = 10) -> int:
        """
        清理旧快照
        
        Args:
            keep_count: 保留的快照数量
            
        Returns:
            删除的快照数量
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.cleanup_old_snapshots(keep_count)
        
        return 0
    
    # ========== 机器学习数据查询 ==========
    
    def get_ml_training_data(self, t1_day: str = None) -> List[Dict]:
        """
        获取机器学习训练数据
        
        Args:
            t1_day: T+1日（竞价日），为空则获取最新
            
        Returns:
            训练数据列表
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.get_ml_training_data(t1_day)
        
        return []
    
    def get_historical_selections(self, ts_code: str = None,
                                  days: int = 30) -> List[Dict]:
        """
        获取历史选股记录
        
        Args:
            ts_code: 股票代码，为空则获取所有
            days: 最近天数
            
        Returns:
            选股记录列表
        """
        self._ensure_initialized()
        
        if self.time_travel:
            return self.time_travel.get_historical_selections(ts_code, days)
        
        return []
    
    def print_time_travel_status(self):
        """打印时间旅行系统状态"""
        self._ensure_initialized()
        
        if self.time_travel:
            self.time_travel.print_status()
        else:
            print("[双数据库] 时间旅行系统不可用")


# 全局单例
_dual_db_manager = None

def get_dual_db_manager() -> DualDatabaseManager:
    """获取双数据库管理器单例"""
    global _dual_db_manager
    if _dual_db_manager is None:
        _dual_db_manager = DualDatabaseManager()
    return _dual_db_manager


# 便捷函数
def save_to_both_databases(model_class, data: Dict[str, Any], 
                           unique_keys: List[str] = None) -> Dict[str, bool]:
    """同时保存到两个数据库"""
    manager = get_dual_db_manager()
    return manager.save_to_both(model_class, data, unique_keys)


def query_with_fallback(model_class, filter_func=None, 
                        order_by=None, limit=None) -> List[Any]:
    """查询数据，PostgreSQL 优先，失败回退到 SQLite"""
    manager = get_dual_db_manager()
    return manager.query_with_fallback(model_class, filter_func, order_by, limit)


def time_travel_query(table_name: str, target_date: str,
                      date_column: str = None) -> List[Dict]:
    """时间旅行查询：查询特定日期的数据"""
    manager = get_dual_db_manager()
    return manager.query_at_date(table_name, target_date, date_column)


def get_available_dates(table_name: str, date_column: str = None) -> List[str]:
    """获取表中所有可用日期"""
    manager = get_dual_db_manager()
    return manager.get_available_dates(table_name, date_column)


def create_database_snapshot(name: str = None, description: str = "") -> Optional[str]:
    """创建数据库快照"""
    manager = get_dual_db_manager()
    return manager.create_snapshot(name, description)


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("双数据库管理器测试")
    print("=" * 60)
    
    manager = get_dual_db_manager()
    status = manager.get_status()
    
    print(f"\nPostgreSQL: {'✅ 可用' if status['postgresql']['available'] else '❌ 不可用'}")
    print(f"SQLite: {'✅ 可用' if status['sqlite']['available'] else '❌ 不可用'}")
    print(f"时间旅行: {'✅ 可用' if status['time_travel']['available'] else '❌ 不可用'}")
    
    # 测试时间旅行功能
    print("\n" + "=" * 60)
    print("时间旅行功能测试")
    print("=" * 60)
    manager.print_time_travel_status()
