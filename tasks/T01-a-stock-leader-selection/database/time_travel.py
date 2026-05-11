#!/usr/bin/env python3
"""
T01 选股系统 - SQLite 时间旅行功能

模拟实现时间旅行查询功能，支持：
1. 查询特定时间点的数据
2. 对比不同日期的数据变化
3. 快照创建和恢复
4. 时间线分析

适用于 PostgreSQL 不可用时，从 SQLite 恢复历史数据分析
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd


class SQLiteTimeTravel:
    """SQLite 时间旅行系统"""
    
    def __init__(self, db_path: str = None):
        """
        初始化时间旅行系统
        
        Args:
            db_path: SQLite 数据库路径，默认为 T01 数据库
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 't01_stocks.db')
        
        self.db_path = db_path
        self.snapshot_dir = Path(db_path).parent / "snapshots"
        self.conn = None
        self._connect()
    
    def _connect(self):
        """连接数据库"""
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        else:
            print(f"⚠️ 数据库文件不存在: {self.db_path}")
    
    # ========== 时间字段检测 ==========
    
    def detect_time_columns(self, table_name: str) -> List[str]:
        """
        自动检测表中的时间字段
        
        Args:
            table_name: 表名
            
        Returns:
            时间字段列表
        """
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()
        
        time_columns = []
        time_patterns = [
            'date', 'time', 'created', 'updated', 'modified',
            'timestamp', 'dt_', '_at', 'trade_date', 't_day', 't1_day', 't2_day'
        ]
        
        for col in columns:
            col_name = col[1].lower()
            col_type = col[2].lower()
            
            # 匹配字段名模式
            if any(pattern in col_name for pattern in time_patterns):
                time_columns.append(col[1])
            # 匹配字段类型
            elif 'date' in col_type or 'time' in col_type:
                time_columns.append(col[1])
        
        return time_columns
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_time_info(self) -> Dict[str, Dict]:
        """
        获取所有表的时间字段信息
        
        Returns:
            {表名: {time_columns: [...], time_travel_supported: bool}}
        """
        tables = self.get_all_tables()
        result = {}
        
        for table in tables:
            time_cols = self.detect_time_columns(table)
            result[table] = {
                'time_columns': time_cols,
                'time_travel_supported': len(time_cols) > 0
            }
        
        return result
    
    # ========== 时间旅行查询 ==========
    
    def get_available_dates(self, table_name: str, date_column: str = None) -> List[str]:
        """
        获取表中所有可用日期
        
        Args:
            table_name: 表名
            date_column: 日期字段名，自动检测
            
        Returns:
            日期列表（降序）
        """
        if not self.conn:
            return []
        
        if not date_column:
            time_columns = self.detect_time_columns(table_name)
            if not time_columns:
                return []
            date_column = time_columns[0]
        
        try:
            query = f"""
            SELECT DISTINCT {date_column} as date
            FROM {table_name}
            WHERE {date_column} IS NOT NULL
            ORDER BY {date_column} DESC
            """
            
            cursor = self.conn.cursor()
            cursor.execute(query)
            return [row['date'] for row in cursor.fetchall() if row['date']]
        except Exception as e:
            print(f"查询日期失败: {e}")
            return []
    
    def query_at_date(self, table_name: str, target_date: str, 
                      date_column: str = None,
                      order_by: str = None) -> List[Dict]:
        """
        查询特定日期的数据
        
        Args:
            table_name: 表名
            target_date: 目标日期 (YYYYMMDD 或 YYYY-MM-DD)
            date_column: 日期字段名
            order_by: 排序字段（可选，默认自动检测）
            
        Returns:
            数据记录列表
        """
        if not self.conn:
            return []
        
        if not date_column:
            time_columns = self.detect_time_columns(table_name)
            if not time_columns:
                print(f"表 {table_name} 没有时间字段")
                return []
            date_column = time_columns[0]
        
        try:
            # 根据表名自动选择排序方式
            if order_by is None:
                if table_name in ['selection_results', 'stock_factor_scores']:
                    order_clause = "ORDER BY total_score DESC, final_rank ASC"
                elif table_name == 'ml_training_records':
                    order_clause = "ORDER BY t1_auction_rank ASC"
                elif table_name == 'auction_data':
                    order_clause = "ORDER BY t1_final_score DESC"
                else:
                    # 默认按创建时间倒序
                    order_clause = "ORDER BY created_at DESC"
            else:
                order_clause = f"ORDER BY {order_by}"
            
            query = f"""
            SELECT * FROM {table_name}
            WHERE {date_column} = ?
            {order_clause}
            """
            
            cursor = self.conn.cursor()
            cursor.execute(query, (target_date,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询失败: {e}")
            return []
    
    def query_date_range(self, table_name: str, start_date: str, end_date: str,
                         date_column: str = None) -> List[Dict]:
        """
        查询日期范围内的数据
        
        Args:
            table_name: 表名
            start_date: 开始日期
            end_date: 结束日期
            date_column: 日期字段名
            
        Returns:
            数据记录列表
        """
        if not self.conn:
            return []
        
        if not date_column:
            time_columns = self.detect_time_columns(table_name)
            date_column = time_columns[0] if time_columns else 'trade_date'
        
        try:
            query = f"""
            SELECT * FROM {table_name}
            WHERE {date_column} >= ? AND {date_column} <= ?
            ORDER BY {date_column} DESC
            """
            
            cursor = self.conn.cursor()
            cursor.execute(query, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询失败: {e}")
            return []
    
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
        data1 = self.query_at_date(table_name, date1, date_column)
        data2 = self.query_at_date(table_name, date2, date_column)
        
        # 提取股票代码集合
        codes1 = set(d.get('ts_code', d.get('id', str(i))) for i, d in enumerate(data1))
        codes2 = set(d.get('ts_code', d.get('id', str(i))) for i, d in enumerate(data2))
        
        return {
            'date1': date1,
            'date2': date2,
            'table': table_name,
            'date1_count': len(data1),
            'date2_count': len(data2),
            'added': list(codes2 - codes1),  # 新增
            'removed': list(codes1 - codes2),  # 移除
            'common': list(codes1 & codes2),  # 共有
            'change_count': abs(len(data1) - len(data2))
        }
    
    def get_latest_date(self, table_name: str, date_column: str = None) -> Optional[str]:
        """
        获取表中最新日期
        
        Args:
            table_name: 表名
            date_column: 日期字段名
            
        Returns:
            最新日期字符串
        """
        dates = self.get_available_dates(table_name, date_column)
        return dates[0] if dates else None
    
    # ========== 时间线分析 ==========
    
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
        if not date_column:
            time_columns = self.detect_time_columns(table_name)
            date_column = time_columns[0] if time_columns else None
        
        if not date_column:
            return {'error': 'No time column found'}
        
        try:
            query = f"""
            SELECT 
                {date_column} as date,
                COUNT(*) as record_count
            FROM {table_name}
            WHERE {date_column} IS NOT NULL
            GROUP BY {date_column}
            ORDER BY {date_column} DESC
            """
            
            cursor = self.conn.cursor()
            cursor.execute(query)
            patterns = [dict(row) for row in cursor.fetchall()]
            
            if not patterns:
                return {'error': 'No data found'}
            
            counts = [p['record_count'] for p in patterns]
            
            return {
                'table': table_name,
                'date_column': date_column,
                'patterns': patterns,
                'stats': {
                    'total_dates': len(patterns),
                    'total_records': sum(counts),
                    'avg_per_date': sum(counts) / len(counts),
                    'max_per_date': max(counts),
                    'min_per_date': min(counts),
                    'date_range': {
                        'start': patterns[-1]['date'],
                        'end': patterns[0]['date']
                    }
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_timeline_report(self, table_name: str = None) -> Dict:
        """
        生成时间线报告
        
        Args:
            table_name: 表名，为空则生成所有表的报告
            
        Returns:
            时间线报告
        """
        if table_name:
            tables = [table_name]
        else:
            # 只分析主要业务表
            tables = [
                'selection_results', 'stock_factor_scores', 'auction_data',
                'market_sentiment', 'tracked_results', 'ml_training_records'
            ]
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'tables': {}
        }
        
        for table in tables:
            time_cols = self.detect_time_columns(table)
            if not time_cols:
                continue
            
            dates = self.get_available_dates(table)
            if dates:
                report['tables'][table] = {
                    'time_columns': time_cols,
                    'date_count': len(dates),
                    'earliest_date': dates[-1],
                    'latest_date': dates[0],
                    'recent_dates': dates[:5]
                }
        
        return report
    
    # ========== 快照系统 ==========
    
    def create_snapshot(self, name: str = None, description: str = "") -> str:
        """
        创建数据库快照
        
        Args:
            name: 快照名称
            description: 快照描述
            
        Returns:
            快照路径
        """
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"snapshot_{timestamp}"
        
        # 确保快照目录存在
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_path = self.snapshot_dir / f"{name}.db"
        
        # 先获取表列表（连接还可用时）
        tables_list = self.get_all_tables()
        
        # 复制数据库
        if self.conn:
            self.conn.close()
            self.conn = None
        
        shutil.copy2(self.db_path, snapshot_path)
        
        # 保存元数据
        metadata = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'description': description,
            'original_db': self.db_path,
            'file_size': os.path.getsize(snapshot_path),
            'tables': tables_list
        }
        
        metadata_path = self.snapshot_dir / f"{name}_meta.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 重新连接
        self._connect()
        
        return str(snapshot_path)
    
    def list_snapshots(self) -> List[Dict]:
        """列出所有快照"""
        if not self.snapshot_dir.exists():
            return []
        
        snapshots = []
        for meta_file in self.snapshot_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    snapshots.append(metadata)
            except Exception:
                continue
        
        # 按创建时间排序
        snapshots.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return snapshots
    
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
        snapshot_path = self.snapshot_dir / f"{snapshot_name}.db"
        
        if not snapshot_path.exists():
            print(f"快照不存在: {snapshot_name}")
            return False
        
        # 备份当前数据库
        if backup_current and os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)
            print(f"当前数据库已备份: {backup_path}")
        
        # 关闭连接
        if self.conn:
            self.conn.close()
        
        # 恢复快照
        shutil.copy2(snapshot_path, self.db_path)
        
        # 重新连接
        self._connect()
        
        print(f"✅ 已从快照 {snapshot_name} 恢复数据库")
        return True
    
    def cleanup_old_snapshots(self, keep_count: int = 10) -> int:
        """
        清理旧快照
        
        Args:
            keep_count: 保留的快照数量
            
        Returns:
            删除的快照数量
        """
        snapshots = self.list_snapshots()
        
        if len(snapshots) <= keep_count:
            return 0
        
        # 删除超出数量的旧快照
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
                print(f"删除快照 {name} 失败: {e}")
        
        return deleted
    
    # ========== 机器学习数据查询 ==========
    
    def get_ml_training_data(self, t1_day: str = None) -> List[Dict]:
        """
        获取机器学习训练数据
        
        Args:
            t1_day: T+1日（竞价日），为空则获取最新
            
        Returns:
            训练数据列表
        """
        if not self.conn:
            return []
        
        if t1_day is None:
            t1_day = self.get_latest_date('ml_training_records', 't1_day')
        
        if not t1_day:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM ml_training_records
                WHERE t1_day = ?
                ORDER BY t1_auction_rank
            """, (t1_day,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询 ML 数据失败: {e}")
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
        if not self.conn:
            return []
        
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        try:
            cursor = self.conn.cursor()
            
            if ts_code:
                cursor.execute("""
                    SELECT * FROM selection_results
                    WHERE ts_code = ? 
                    AND trade_date >= ? 
                    AND trade_date <= ?
                    ORDER BY trade_date DESC
                """, (ts_code, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT * FROM selection_results
                    WHERE trade_date >= ? 
                    AND trade_date <= ?
                    ORDER BY trade_date DESC, final_rank
                """, (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询历史选股失败: {e}")
            return []
    
    # ========== 辅助方法 ==========
    
    def get_table_info(self, table_name: str) -> Dict:
        """获取表的详细信息"""
        if not self.conn:
            return {}
        
        cursor = self.conn.cursor()
        
        # 表结构
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = [dict(row) for row in cursor.fetchall()]
        
        # 统计
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = cursor.fetchone()['count']
        
        # 时间字段
        time_columns = self.detect_time_columns(table_name)
        
        return {
            'name': table_name,
            'columns': columns,
            'row_count': row_count,
            'time_columns': time_columns,
            'time_travel_supported': len(time_columns) > 0
        }
    
    def print_status(self):
        """打印时间旅行系统状态"""
        print("\n" + "=" * 60)
        print("📊 SQLite 时间旅行系统状态")
        print("=" * 60)
        
        print(f"数据库: {self.db_path}")
        print(f"快照目录: {self.snapshot_dir}")
        
        # 表的时间旅行支持
        tables = self.get_all_tables()
        print(f"\n共 {len(tables)} 个表:")
        
        for table in tables:
            info = self.get_table_info(table)
            support = "✅" if info.get('time_travel_supported') else "❌"
            print(f"  {support} {table} ({info.get('row_count', 0)} 行)")
            if info.get('time_columns'):
                print(f"      时间字段: {', '.join(info['time_columns'])}")
        
        # 快照信息
        snapshots = self.list_snapshots()
        print(f"\n快照: {len(snapshots)} 个")
        for snap in snapshots[:5]:
            print(f"  - {snap['name']} ({snap.get('created_at', 'unknown')})")
        
        print("=" * 60)
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ========== 命令行接口 ==========

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='T01 SQLite 时间旅行系统')
    parser.add_argument('--db', help='数据库文件路径')
    parser.add_argument('--status', action='store_true', help='显示系统状态')
    parser.add_argument('--table', help='表名')
    parser.add_argument('--timeline', action='store_true', help='显示时间线')
    parser.add_argument('--date', help='查询特定日期')
    parser.add_argument('--compare', nargs=2, metavar=('DATE1', 'DATE2'),
                        help='比较两个日期')
    parser.add_argument('--snapshot', metavar='NAME', help='创建快照')
    parser.add_argument('--list-snapshots', action='store_true', help='列出所有快照')
    parser.add_argument('--restore', metavar='NAME', help='从快照恢复')
    parser.add_argument('--cleanup', type=int, metavar='KEEP', 
                        help='清理旧快照，保留指定数量')
    
    args = parser.parse_args()
    
    traveler = SQLiteTimeTravel(args.db)
    
    try:
        if args.status:
            traveler.print_status()
        
        elif args.timeline and args.table:
            dates = traveler.get_available_dates(args.table)
            print(f"\n📅 表 {args.table} 的时间线:")
            for date in dates[:20]:
                print(f"  {date}")
        
        elif args.date and args.table:
            data = traveler.query_at_date(args.table, args.date)
            print(f"\n📊 {args.date} 的数据 ({len(data)} 条):")
            for record in data[:10]:
                code = record.get('ts_code', record.get('id', '?'))
                name = record.get('stock_name', '')
                score = record.get('total_score', 0)
                print(f"  {code} {name}: {score}")
        
        elif args.compare and args.table:
            result = traveler.compare_dates(args.table, args.compare[0], args.compare[1])
            print(f"\n🔍 对比结果:")
            print(f"  {result['date1']}: {result['date1_count']} 条")
            print(f"  {result['date2']}: {result['date2_count']} 条")
            print(f"  新增: {len(result['added'])} 个")
            print(f"  移除: {len(result['removed'])} 个")
        
        elif args.snapshot:
            path = traveler.create_snapshot(args.snapshot)
            print(f"✅ 快照已创建: {path}")
        
        elif args.list_snapshots:
            snapshots = traveler.list_snapshots()
            print(f"\n📚 所有快照 ({len(snapshots)} 个):")
            for snap in snapshots:
                print(f"  {snap['name']} - {snap.get('created_at', 'unknown')}")
        
        elif args.restore:
            success = traveler.restore_from_snapshot(args.restore)
            if success:
                print(f"✅ 已从快照 {args.restore} 恢复")
            else:
                print(f"❌ 恢复失败")
        
        elif args.cleanup is not None:
            deleted = traveler.cleanup_old_snapshots(args.cleanup)
            print(f"✅ 已删除 {deleted} 个旧快照")
        
        else:
            traveler.print_status()
    
    finally:
        traveler.close()


if __name__ == '__main__':
    main()
