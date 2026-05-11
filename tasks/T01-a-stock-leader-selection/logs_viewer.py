#!/usr/bin/env python3
"""
T01 日志查看工具

用法:
    python3 logs_viewer.py                    # 查看今日所有日志摘要
    python3 logs_viewer.py --today            # 查看今日日志
    python3 logs_viewer.py --date 20260316    # 查看指定日期日志
    python3 logs_viewer.py --errors           # 查看错误日志
    python3 logs_viewer.py --task t1_auction  # 查看指定任务日志
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from logging_config import T01_LOGS_DIR, get_logs_summary


def list_log_files(date_str: str = None):
    """列出日志文件"""
    if date_str:
        pattern = f'*_{date_str}.log'
    else:
        pattern = '*.log'
    
    files = sorted(T01_LOGS_DIR.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
    return files


def view_log_file(filepath: Path, tail: int = 50):
    """查看日志文件内容"""
    if not filepath.exists():
        print(f"❌ 日志文件不存在: {filepath}")
        return
    
    print(f"\n{'='*60}")
    print(f"📄 {filepath.name}")
    print(f"{'='*60}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 显示最后N行
        if tail and len(lines) > tail:
            print(f"... (共 {len(lines)} 行，显示最后 {tail} 行) ...\n")
            lines = lines[-tail:]
        
        for line in lines:
            print(line.rstrip())
            
    except Exception as e:
        print(f"❌ 读取失败: {e}")


def view_errors():
    """查看错误日志"""
    error_log = T01_LOGS_DIR / 'errors.log'
    if error_log.exists():
        view_log_file(error_log, tail=100)
    else:
        print("ℹ️ 暂无错误日志")


def show_summary():
    """显示日志摘要"""
    summary = get_logs_summary(days=7)
    
    print("=" * 60)
    print("📊 T01 选股系统日志摘要")
    print("=" * 60)
    print(f"\n日志目录: {summary['log_dir']}")
    
    if summary['recent_files']:
        print(f"\n最近日志文件:")
        print("-" * 60)
        for f in summary['recent_files'][:10]:
            size_kb = f['size'] / 1024
            print(f"  {f['name']:40s} {size_kb:>8.1f}KB  {f['modified']}")
    
    if summary['error_count'] > 0:
        print(f"\n⚠️ 错误日志中共有 {summary['error_count']} 条错误记录")
        print(f"   查看: python3 logs_viewer.py --errors")


def main():
    parser = argparse.ArgumentParser(description='T01 日志查看工具')
    parser.add_argument('--today', action='store_true', help='查看今日日志')
    parser.add_argument('--date', type=str, help='查看指定日期日志 (YYYYMMDD)')
    parser.add_argument('--errors', action='store_true', help='查看错误日志')
    parser.add_argument('--task', type=str, help='查看指定任务日志 (t1_auction/t_day/track)')
    parser.add_argument('--summary', action='store_true', help='显示日志摘要')
    parser.add_argument('--tail', type=int, default=50, help='显示最后N行 (默认50)')
    
    args = parser.parse_args()
    
    if not T01_LOGS_DIR.exists():
        print(f"❌ 日志目录不存在: {T01_LOGS_DIR}")
        return
    
    if args.errors:
        view_errors()
        return
    
    if args.summary:
        show_summary()
        return
    
    if args.today:
        date_str = datetime.now().strftime('%Y%m%d')
    elif args.date:
        date_str = args.date
    else:
        # 默认显示摘要
        show_summary()
        return
    
    if args.task:
        # 查看指定任务的日志
        log_file = T01_LOGS_DIR / f'task_{args.task}_{date_str}.log'
        if log_file.exists():
            view_log_file(log_file, tail=args.tail)
        else:
            print(f"❌ 未找到任务日志: {log_file.name}")
            # 列出可用的任务日志
            task_logs = list(T01_LOGS_DIR.glob(f'task_*_{date_str}.log'))
            if task_logs:
                print(f"\n可用的任务日志:")
                for f in task_logs:
                    print(f"  - {f.name}")
    else:
        # 显示该日期所有日志
        files = list_log_files(date_str)
        if files:
            for f in files:
                view_log_file(f, tail=min(args.tail, 20))
                print()
        else:
            print(f"ℹ️ {date_str} 暂无日志文件")


if __name__ == '__main__':
    main()
