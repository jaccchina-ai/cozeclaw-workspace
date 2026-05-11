"""
T01 选股系统 - 双写数据库管理器

确保数据同时写入 PostgreSQL 和 SQLite，确保数据安全和完整
读取时优先 PostgreSQL，失败时回退 SQLite
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

# 导入数据库配置
from database.db_config import DB_TYPE, POSTGRES_CONFIG, SQLITE_DB_PATH

# 路径配置
SQLITE_PATH = SQLITE_DB_PATH


class DualWriteManager:
    """
    双写数据库管理器 - 单例模式

    写入：同时写入 PostgreSQL 和 SQLite
    读取：优先 PostgreSQL，失败时回退 SQLite
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.db_type = DB_TYPE
        self.sqlite_path = SQLITE_PATH
        self._pg_conn = None
        self._sqlite_conn = None
        self._initialized = True

    # ==================== 连接管理 ====================

    @contextmanager
    def get_pg_connection(self):
        """获取 PostgreSQL 连接"""
        import psycopg2
        conn = None
        try:
            conn = psycopg2.connect(
                host=POSTGRES_CONFIG['host'],
                port=POSTGRES_CONFIG['port'],
                database=POSTGRES_CONFIG['database'],
                user=POSTGRES_CONFIG['user'],
                password=POSTGRES_CONFIG['password'],
                sslmode=os.environ.get('PGSSLMODE', 'require')
            )
            yield conn
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_sqlite_connection(self):
        """获取 SQLite 连接"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ==================== 双写操作 ====================

    def save_selection_result(self, data: Dict) -> Dict[str, bool]:
        """
        双写保存选股结果

        Returns:
            {'postgres': bool, 'sqlite': bool}
        """
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                # 先删除旧记录
                cursor.execute("""
                    DELETE FROM selection_results
                    WHERE trade_date = %s AND selection_type = %s AND ts_code = %s
                """, (data.get('trade_date'), data.get('selection_type'), data.get('ts_code')))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                # 使用 INSERT INTO ... ON CONFLICT (id) DO UPDATE SET 或者直接使用 INSERT OR REPLACE
                # 由于我们已经删除了旧记录，这里应该不会有冲突
                # 但为了保险，还是使用 ON CONFLICT DO NOTHING
                cursor.execute(
                    f"INSERT INTO selection_results ({columns}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {', '.join([f'{col} = EXCLUDED.{col}' for col in data_copy.keys()])}",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存选股结果失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM selection_results
                    WHERE trade_date = ? AND selection_type = ? AND ts_code = ?
                """, (data.get('trade_date'), data.get('selection_type'), data.get('ts_code')))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO selection_results ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存选股结果失败: {e}")
            results['sqlite'] = False

        return results

    def save_factor_score(self, data: Dict) -> Dict[str, bool]:
        """双写保存因子评分"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM stock_factor_scores
                    WHERE trade_date = %s AND ts_code = %s
                """, (data.get('trade_date'), data.get('ts_code')))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO stock_factor_scores ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存因子评分失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM stock_factor_scores
                    WHERE trade_date = ? AND ts_code = ?
                """, (data.get('trade_date'), data.get('ts_code')))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO stock_factor_scores ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存因子评分失败: {e}")
            results['sqlite'] = False

        return results

    def save_auction_data(self, data: Dict) -> Dict[str, bool]:
        """双写保存竞价数据"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM auction_data
                    WHERE trade_date = %s AND ts_code = %s
                """, (data.get('trade_date'), data.get('ts_code')))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO auction_data ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存竞价数据失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM auction_data
                    WHERE trade_date = ? AND ts_code = ?
                """, (data.get('trade_date'), data.get('ts_code')))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO auction_data ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存竞价数据失败: {e}")
            results['sqlite'] = False

        return results

    def save_sentiment(self, data: Dict) -> Dict[str, bool]:
        """双写保存市场情绪"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM market_sentiment WHERE trade_date = %s
                """, (data.get('trade_date'),))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO market_sentiment ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存市场情绪失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM market_sentiment WHERE trade_date = ?
                """, (data.get('trade_date'),))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO market_sentiment ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存市场情绪失败: {e}")
            results['sqlite'] = False

        return results

    def save_unifuncs_result(self, data: Dict) -> Dict[str, bool]:
        """双写保存 Unifuncs 结果"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM unifuncs_results WHERE trade_date = %s
                """, (data.get('trade_date'),))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO unifuncs_results ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存 Unifuncs 结果失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM unifuncs_results WHERE trade_date = ?
                """, (data.get('trade_date'),))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO unifuncs_results ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存 Unifuncs 结果失败: {e}")
            results['sqlite'] = False

        return results

    def save_ml_training_record(self, data: Dict) -> Dict[str, bool]:
        """双写保存 ML 训练记录"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM ml_training_records
                    WHERE t1_day = %s AND ts_code = %s
                """, (data.get('t1_day'), data.get('ts_code')))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO ml_training_records ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存 ML 训练记录失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM ml_training_records
                    WHERE t1_day = ? AND ts_code = ?
                """, (data.get('t1_day'), data.get('ts_code')))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO ml_training_records ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存 ML 训练记录失败: {e}")
            results['sqlite'] = False

        return results

    def save_tracked_result(self, data: Dict) -> Dict[str, bool]:
        """双写保存跟踪结果"""
        results = {}

        # PostgreSQL
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM tracked_results
                    WHERE t1_day = %s AND ts_code = %s
                """, (data.get('t1_day'), data.get('ts_code')))
                conn.commit()
                
                # 插入新记录 - 排除id字段，让数据库自动生成
                data_copy = data.copy()
                if 'id' in data_copy:
                    del data_copy['id']
                
                columns = ', '.join(data_copy.keys())
                placeholders = ', '.join(['%s'] * len(data_copy))
                cursor.execute(
                    f"INSERT INTO tracked_results ({columns}) VALUES ({placeholders})",
                    tuple(data_copy.values())
                )
                conn.commit()
                results['postgres'] = True
        except Exception as e:
            print(f"[双写] PostgreSQL 保存跟踪结果失败: {e}")
            results['postgres'] = False

        # SQLite
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM tracked_results
                    WHERE t1_day = ? AND ts_code = ?
                """, (data.get('t1_day'), data.get('ts_code')))

                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                cursor.execute(
                    f"INSERT INTO tracked_results ({columns}) VALUES ({placeholders})",
                    tuple(data.values())
                )
                conn.commit()
                results['sqlite'] = True
        except Exception as e:
            print(f"[双写] SQLite 保存跟踪结果失败: {e}")
            results['sqlite'] = False

        return results

    # ==================== 读取操作（优先 PostgreSQL，回退 SQLite） ====================

    def query(self, query: str, params: tuple = (), use_pg: bool = True) -> List[Dict]:
        """
        查询数据，优先 PostgreSQL，失败时回退 SQLite

        Args:
            query: SQL 查询语句（PostgreSQL 格式，%s 占位符）
            params: 查询参数
            use_pg: 是否优先使用 PostgreSQL

        Returns:
            查询结果列表
        """
        # 尝试 PostgreSQL
        if use_pg:
            try:
                with self.get_pg_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"[读取] PostgreSQL 查询失败，回退到 SQLite: {e}")

        # 回退到 SQLite
        try:
            # 将 %s 转换为 ?
            sqlite_query = query.replace('%s', '?')
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sqlite_query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[读取] SQLite 查询也失败: {e}")
            return []

    def get_selection_results(self, date: str, selection_type: str = None) -> List[Dict]:
        """获取选股结果"""
        if selection_type:
            return self.query(
                "SELECT * FROM selection_results WHERE trade_date = %s AND selection_type = %s ORDER BY final_rank",
                (date, selection_type)
            )
        return self.query(
            "SELECT * FROM selection_results WHERE trade_date = %s ORDER BY final_rank",
            (date,)
        )

    def get_factor_scores(self, date: str, ts_code: str = None) -> List[Dict]:
        """获取因子评分"""
        if ts_code:
            return self.query(
                "SELECT * FROM stock_factor_scores WHERE trade_date = %s AND ts_code = %s",
                (date, ts_code)
            )
        return self.query(
            "SELECT * FROM stock_factor_scores WHERE trade_date = %s",
            (date,)
        )

    def get_auction_data(self, date: str, ts_code: str = None) -> List[Dict]:
        """获取竞价数据"""
        if ts_code:
            return self.query(
                "SELECT * FROM auction_data WHERE trade_date = %s AND ts_code = %s",
                (date, ts_code)
            )
        return self.query(
            "SELECT * FROM auction_data WHERE trade_date = %s ORDER BY final_score DESC",
            (date,)
        )

    def get_sentiment(self, date: str) -> Optional[Dict]:
        """获取市场情绪"""
        results = self.query(
            "SELECT * FROM market_sentiment WHERE trade_date = %s",
            (date,)
        )
        return results[0] if results else None

    def get_unifuncs_result(self, date: str) -> Optional[Dict]:
        """获取 Unifuncs 结果"""
        results = self.query(
            "SELECT * FROM unifuncs_results WHERE trade_date = %s",
            (date,)
        )
        return results[0] if results else None

    def get_ml_training_data(self, t1_day: str = None) -> List[Dict]:
        """获取 ML 训练数据"""
        if t1_day is None:
            dates = self.query(
                "SELECT DISTINCT t1_day FROM ml_training_records WHERE t1_day IS NOT NULL ORDER BY t1_day DESC LIMIT 1"
            )
            if dates:
                t1_day = dates[0].get('t1_day')
            else:
                return []

        if not t1_day:
            return []

        return self.query(
            "SELECT * FROM ml_training_records WHERE t1_day = %s ORDER BY t1_auction_rank",
            (t1_day,)
        )

    def get_latest_date(self, table_name: str, date_column: str = 'trade_date') -> Optional[str]:
        """获取最新日期"""
        results = self.query(
            f"SELECT DISTINCT {date_column} as date FROM {table_name} WHERE {date_column} IS NOT NULL ORDER BY {date_column} DESC LIMIT 1"
        )
        return results[0]['date'] if results else None

    def get_available_dates(self, table_name: str, date_column: str = 'trade_date') -> List[str]:
        """获取所有可用日期"""
        results = self.query(
            f"SELECT DISTINCT {date_column} as date FROM {table_name} WHERE {date_column} IS NOT NULL ORDER BY {date_column} DESC"
        )
        return [r['date'] for r in results if r['date']]

    def query_at_date(self, table_name: str, target_date: str, date_column: str = 'trade_date') -> List[Dict]:
        """查询特定日期的数据"""
        return self.query(
            f"SELECT * FROM {table_name} WHERE {date_column} = %s",
            (target_date,)
        )

    # ==================== 状态信息 ====================

    def get_status(self) -> Dict:
        """获取双写数据库状态"""
        status = {
            'postgres': {'connected': False, 'tables': {}},
            'sqlite': {'connected': False, 'tables': {}, 'file_size': 0}
        }

        # PostgreSQL 状态
        try:
            with self.get_pg_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                status['postgres']['connected'] = True
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    status['postgres']['tables'][table] = cursor.fetchone()[0]
        except Exception as e:
            print(f"[状态] PostgreSQL 连接失败: {e}")

        # SQLite 状态
        try:
            with self.get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cursor.fetchall()]
                status['sqlite']['connected'] = True
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    status['sqlite']['tables'][table] = cursor.fetchone()[0]
                status['sqlite']['file_size'] = os.path.getsize(self.sqlite_path) if os.path.exists(self.sqlite_path) else 0
        except Exception as e:
            print(f"[状态] SQLite 连接失败: {e}")

        return status

    def print_status(self):
        """打印双写数据库状态"""
        status = self.get_status()

        print("\n" + "=" * 70)
        print("📊 双写数据库状态")
        print("=" * 70)

        # PostgreSQL
        pg = status['postgres']
        print(f"\n🗄️  PostgreSQL: {'✅ 已连接' if pg['connected'] else '❌ 未连接'}")
        if pg['connected']:
            print("   表统计:")
            for table, count in list(pg['tables'].items())[:10]:
                print(f"     {table}: {count} 条")

        # SQLite
        sq = status['sqlite']
        print(f"\n💾  SQLite: {'✅ 已连接' if sq['connected'] else '❌ 未连接'}")
        if sq['connected'] and sq['file_size'] > 0:
            print(f"   文件大小: {sq['file_size'] / 1024:.1f} KB")
            print("   表统计:")
            for table, count in list(sq['tables'].items())[:10]:
                print(f"     {table}: {count} 条")

        print("=" * 70)


# 全局单例
_dual_write_manager = None


def get_dual_write_manager() -> DualWriteManager:
    """获取双写管理器单例"""
    global _dual_write_manager
    if _dual_write_manager is None:
        _dual_write_manager = DualWriteManager()
    return _dual_write_manager


if __name__ == '__main__':
    manager = get_dual_write_manager()
    manager.print_status()
