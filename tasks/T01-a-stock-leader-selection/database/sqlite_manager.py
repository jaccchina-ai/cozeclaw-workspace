"""
T01 选股系统 - 数据库管理器

支持 PostgreSQL（优先）和 SQLite
提供数据存储、时间旅行查询、快照管理功能
"""

import os
import sqlite3
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

# 导入数据库配置
from database.db_config import DB_TYPE, POSTGRES_CONFIG, SQLITE_DB_PATH

# 路径配置
DB_PATH = SQLITE_DB_PATH
SNAPSHOT_DIR = Path(DB_PATH).parent / "snapshots"


class SQLiteManager:
    """数据库管理器 - 单例模式，优先使用 PostgreSQL"""
    
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
        self.db_path = DB_PATH
        self.snapshot_dir = SNAPSHOT_DIR
        self._pg_conn = None
        self._initialized = True
    
    def _get_placeholder(self):
        """获取当前数据库的占位符"""
        return '%s' if self.db_type == 'postgres' else '?'
    
    def _format_query(self, query: str, params: tuple = ()) -> tuple:
        """将 SQLite 占位符 ? 转换为 PostgreSQL 的 %s"""
        if self.db_type == 'postgres':
            # 将所有 ? 替换为 %s
            formatted_query = query.replace('?', '%s')
            return formatted_query, params
        return query, params
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        if self.db_type == 'postgres':
            # 使用 PostgreSQL
            import psycopg2
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
                conn.close()
        else:
            # 回退到 SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """执行查询并返回结果"""
        query, params = self._format_query(query, params)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 转换为字典列表
            if self.db_type == 'postgres':
                # PostgreSQL: 使用 column_name
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                # SQLite: row 已经是 Row 对象
                return [dict(row) for row in rows]
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """执行插入并返回 lastrowid"""
        query, params = self._format_query(query, params)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
            if self.db_type == 'postgres':
                cursor.execute("SELECT lastval()")
                return cursor.fetchone()[0]
            else:
                return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新并返回影响行数"""
        query, params = self._format_query(query, params)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_delete(self, query: str, params: tuple = ()) -> int:
        """执行删除并返回影响行数"""
        query, params = self._format_query(query, params)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    # ========== 数据保存方法 ==========
    
    def save_sentiment(self, data: Dict) -> bool:
        """保存市场情绪数据"""
        try:
            # 先删除旧记录
            self.execute_delete(
                "DELETE FROM market_sentiment WHERE trade_date = ?",
                (data.get('trade_date'),)
            )
            
            # 插入新记录
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO market_sentiment ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存市场情绪失败: {e}")
            return False
    
    def save_selection_result(self, data: Dict) -> bool:
        """保存选股结果"""
        try:
            # 先删除旧记录
            self.execute_delete(
                "DELETE FROM selection_results WHERE trade_date = ? AND selection_type = ? AND ts_code = ?",
                (data.get('trade_date'), data.get('selection_type'), data.get('ts_code'))
            )
            
            # 插入新记录
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO selection_results ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存选股结果失败: {e}")
            return False
    
    def save_factor_score(self, data: Dict) -> bool:
        """保存因子评分"""
        try:
            self.execute_delete(
                "DELETE FROM stock_factor_scores WHERE trade_date = ? AND ts_code = ?",
                (data.get('trade_date'), data.get('ts_code'))
            )
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO stock_factor_scores ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存因子评分失败: {e}")
            return False
    
    def save_auction_data(self, data: Dict) -> bool:
        """保存竞价数据"""
        try:
            self.execute_delete(
                "DELETE FROM auction_data WHERE trade_date = ? AND ts_code = ?",
                (data.get('trade_date'), data.get('ts_code'))
            )
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO auction_data ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存竞价数据失败: {e}")
            return False
    
    def save_unifuncs_result(self, data: Dict) -> bool:
        """保存 Unifuncs 结果"""
        try:
            self.execute_delete(
                "DELETE FROM unifuncs_results WHERE trade_date = ?",
                (data.get('trade_date'),)
            )
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO unifuncs_results ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存 Unifuncs 结果失败: {e}")
            return False
    
    def save_ml_training_record(self, data: Dict) -> bool:
        """保存 ML 训练记录"""
        try:
            self.execute_delete(
                "DELETE FROM ml_training_records WHERE t1_day = ? AND ts_code = ?",
                (data.get('t1_day'), data.get('ts_code'))
            )
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO ml_training_records ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存 ML 训练记录失败: {e}")
            return False
    
    def save_tracked_result(self, data: Dict) -> bool:
        """保存跟踪结果"""
        try:
            self.execute_delete(
                "DELETE FROM tracked_results WHERE t1_day = ? AND ts_code = ?",
                (data.get('t1_day'), data.get('ts_code'))
            )
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO tracked_results ({columns}) VALUES ({placeholders})"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"[SQLite] 保存跟踪结果失败: {e}")
            return False
    
    # ========== 数据查询方法 ==========
    
    def query_at_date(self, table_name: str, target_date: str,
                       date_column: str = 'trade_date') -> List[Dict]:
        """查询特定日期的数据"""
        try:
            return self.execute(
                f"SELECT * FROM {table_name} WHERE {date_column} = ?",
                (target_date,)
            )
        except Exception as e:
            print(f"[SQLite] 查询失败: {e}")
            return []
    
    def get_available_dates(self, table_name: str,
                            date_column: str = 'trade_date') -> List[str]:
        """获取表中所有可用日期"""
        try:
            results = self.execute(
                f"SELECT DISTINCT {date_column} as date FROM {table_name} "
                f"WHERE {date_column} IS NOT NULL ORDER BY {date_column} DESC"
            )
            return [r['date'] for r in results if r['date']]
        except Exception as e:
            print(f"[SQLite] 查询日期失败: {e}")
            return []
    
    def get_latest_date(self, table_name: str,
                        date_column: str = 'trade_date') -> Optional[str]:
        """获取表中最新日期"""
        dates = self.get_available_dates(table_name, date_column)
        return dates[0] if dates else None
    
    def get_ml_training_data(self, t1_day: str = None) -> List[Dict]:
        """获取 ML 训练数据"""
        if t1_day is None:
            t1_day = self.get_latest_date('ml_training_records', 't1_day')
        
        if not t1_day:
            return []
        
        return self.execute(
            "SELECT * FROM ml_training_records WHERE t1_day = ? ORDER BY t1_auction_rank",
            (t1_day,)
        )
    
    def get_historical_selections(self, ts_code: str = None,
                                   days: int = 30) -> List[Dict]:
        """获取历史选股记录"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        if ts_code:
            return self.execute(
                "SELECT * FROM selection_results WHERE ts_code = ? "
                "AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date DESC",
                (ts_code, start_date, end_date)
            )
        else:
            return self.execute(
                "SELECT * FROM selection_results WHERE trade_date >= ? "
                "AND trade_date <= ? ORDER BY trade_date DESC, final_rank",
                (start_date, end_date)
            )
    
    def get_unifuncs_result(self, date: str) -> Optional[Dict]:
        """获取 Unifuncs 结果"""
        results = self.execute(
            "SELECT * FROM unifuncs_results WHERE trade_date = ?",
            (date,)
        )
        return results[0] if results else None
    
    def get_selection_results(self, date: str, selection_type: str = None) -> List[Dict]:
        """获取选股结果"""
        if selection_type:
            return self.execute(
                "SELECT * FROM selection_results WHERE trade_date = ? AND selection_type = ? ORDER BY final_rank",
                (date, selection_type)
            )
        return self.execute(
            "SELECT * FROM selection_results WHERE trade_date = ? ORDER BY final_rank",
            (date,)
        )
    
    def get_factor_scores(self, date: str, ts_code: str = None) -> List[Dict]:
        """获取因子评分"""
        if ts_code:
            return self.execute(
                "SELECT * FROM stock_factor_scores WHERE trade_date = ? AND ts_code = ?",
                (date, ts_code)
            )
        return self.execute(
            "SELECT * FROM stock_factor_scores WHERE trade_date = ?",
            (date,)
        )
    
    def get_auction_data(self, date: str, ts_code: str = None) -> List[Dict]:
        """获取竞价数据"""
        if ts_code:
            return self.execute(
                "SELECT * FROM auction_data WHERE trade_date = ? AND ts_code = ?",
                (date, ts_code)
            )
        return self.execute(
            "SELECT * FROM auction_data WHERE trade_date = ? ORDER BY final_score DESC",
            (date,)
        )
    
    def get_sentiment(self, date: str) -> Optional[Dict]:
        """获取市场情绪"""
        results = self.execute(
            "SELECT * FROM market_sentiment WHERE trade_date = ?",
            (date,)
        )
        return results[0] if results else None
    
    # ========== 快照管理 ==========
    
    def create_snapshot(self, name: str = None, description: str = "") -> str:
        """创建数据库快照"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"snapshot_{timestamp}"
        
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshot_dir / f"{name}.db"
        
        shutil.copy2(self.db_path, snapshot_path)
        
        metadata = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'description': description,
            'original_db': self.db_path,
            'file_size': os.path.getsize(snapshot_path)
        }
        
        metadata_path = self.snapshot_dir / f"{name}_meta.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return str(snapshot_path)
    
    def list_snapshots(self) -> List[Dict]:
        """列出所有快照"""
        if not self.snapshot_dir.exists():
            return []
        
        snapshots = []
        for meta_file in self.snapshot_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    snapshots.append(json.load(f))
            except Exception:
                continue
        
        snapshots.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return snapshots
    
    def cleanup_old_snapshots(self, keep_count: int = 10) -> int:
        """清理旧快照"""
        snapshots = self.list_snapshots()
        
        if len(snapshots) <= keep_count:
            return 0
        
        deleted = 0
        for snapshot in snapshots[keep_count:]:
            name = snapshot['name']
            db_path = self.snapshot_dir / f"{name}.db"
            meta_path = self.snapshot_dir / f"{name}_meta.json"
            
            try:
                if db_path.exists():
                    os.remove(db_path)
                if meta_path.exists():
                    os.remove(meta_path)
                deleted += 1
            except Exception as e:
                print(f"[SQLite] 删除快照失败: {e}")
        
        return deleted
    
    # ========== 状态信息 ==========
    
    def get_status(self) -> Dict:
        """获取数据库状态"""
        if self.db_type == 'postgres':
            # PostgreSQL
            tables = self.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            table_names = [t['table_name'] for t in tables]
        else:
            # SQLite
            tables = self.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = [t['name'] for t in tables]
        
        table_stats = {}
        for table in table_names:
            try:
                result = self.execute(f"SELECT COUNT(*) as count FROM {table}")
                table_stats[table] = result[0]['count']
            except Exception:
                table_stats[table] = 0
        
        return {
            'db_type': self.db_type.upper(),
            'db_path': self.db_path if self.db_type != 'postgres' else f"postgresql://{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}",
            'file_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) and self.db_type != 'postgres' else 0,
            'tables': table_stats,
            'snapshots': len(self.list_snapshots()) if self.db_type != 'postgres' else 0
        }
    
    def print_status(self):
        """打印数据库状态"""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print(f"📊 {status['db_type']} 数据库状态")
        print("=" * 60)
        print(f"数据库: {status['db_path']}")
        if status['file_size'] > 0:
            print(f"文件大小: {status['file_size'] / 1024:.1f} KB")
        if status['snapshots'] > 0:
            print(f"快照数量: {status['snapshots']}")
        print(f"\n表统计:")
        for table, count in status['tables'].items():
            print(f"  {table}: {count} 条")


# 全局单例
_sqlite_manager = None

def get_sqlite_manager() -> SQLiteManager:
    """获取 SQLite 管理器单例"""
    global _sqlite_manager
    if _sqlite_manager is None:
        _sqlite_manager = SQLiteManager()
    return _sqlite_manager


# 便捷函数
def save_to_database(table: str, data: Dict, unique_keys: List[str] = None) -> bool:
    """保存数据到数据库"""
    manager = get_sqlite_manager()
    
    # 根据表名选择保存方法
    method_map = {
        'market_sentiment': manager.save_sentiment,
        'selection_results': manager.save_selection_result,
        'stock_factor_scores': manager.save_factor_score,
        'auction_data': manager.save_auction_data,
        'unifuncs_results': manager.save_unifuncs_result,
        'ml_training_records': manager.save_ml_training_record,
        'tracked_results': manager.save_tracked_result
    }
    
    save_method = method_map.get(table)
    if save_method:
        return save_method(data)
    
    # 通用保存方法
    try:
        if unique_keys:
            where_clause = ' AND '.join([f"{k} = ?" for k in unique_keys])
            where_values = tuple(data.get(k) for k in unique_keys)
            manager.execute_delete(f"DELETE FROM {table} WHERE {where_clause}", where_values)
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        manager.execute_insert(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(data.values()))
        return True
    except Exception as e:
        print(f"[SQLite] 保存失败: {e}")
        return False


if __name__ == '__main__':
    manager = get_sqlite_manager()
    manager.print_status()
