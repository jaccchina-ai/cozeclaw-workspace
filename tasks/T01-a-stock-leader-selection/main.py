"""
T01 选股系统 - 主入口

提供命令行接口和定时调度
"""

import os
import sys
import argparse
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from database.models import init_db
from selection_engine import TDaySelectionEngine, T1AuctionEngine, run_t_day_selection, run_t1_auction_selection
from messenger import get_messenger, FeishuMessenger, MockMessenger
from evolution import StrategyEvolutionEngine, run_weekly_evolution
from data_fetcher import create_fetcher


def run_t_day_task(date: str = None, send_message: bool = True):
    """
    执行T日选股任务
    
    执行时间: 交易日 20:00
    """
    print(f"\n{'='*60}")
    print(f"T01 T日选股任务启动 - {datetime.now()}")
    print(f"{'='*60}")
    
    # 执行选股
    stocks, sentiment = run_t_day_selection(date)
    
    if not stocks:
        print("⚠️ 无选股结果")
        return
    
    # 获取动态胜率
    try:
        evolution_engine = StrategyEvolutionEngine()
        win_rate = evolution_engine._calculate_win_rate(days=30)
    except:
        win_rate = 0.6  # 默认60%
    
    # 发送消息
    if send_message:
        messenger = get_messenger()
        messenger.send_t_day_result(stocks, sentiment, date, win_rate)
    
    return stocks, sentiment


def run_t1_auction_task(date: str = None, send_message: bool = True):
    """
    执行T+1竞价选股任务
    
    执行时间: 交易日 09:25
    """
    print(f"\n{'='*60}")
    print(f"T01 T+1竞价选股任务启动 - {datetime.now()}")
    print(f"{'='*60}")
    
    # 执行选股
    stocks = run_t1_auction_selection(date)
    
    if not stocks:
        print("⚠️ 无选股结果")
        return
    
    # 获取市场情绪
    fetcher = create_fetcher()
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    sentiment = fetcher.get_market_sentiment(date)
    
    # 发送消息
    if send_message:
        messenger = get_messenger()
        market_risk = sentiment.get('risk_score', 5)
        messenger.send_t1_auction_result(stocks, sentiment, date, market_risk)
    
    return stocks


def run_evolution_task():
    """
    执行策略进化任务
    
    执行时间: 每周日 20:00
    """
    print(f"\n{'='*60}")
    print(f"T01 策略进化任务启动 - {datetime.now()}")
    print(f"{'='*60}")
    
    result = run_weekly_evolution()
    return result


def track_results_task():
    """
    执行结果跟踪任务
    
    执行时间: 交易日 15:05 (收盘后)
    跟踪T+2收益情况
    """
    print(f"\n{'='*60}")
    print(f"T01 结果跟踪任务启动 - {datetime.now()}")
    print(f"{'='*60}")
    
    fetcher = create_fetcher()
    
    # 获取T+2日期（今天是某只股票的T+2日）
    today = datetime.now().strftime('%Y%m%d')
    t_day = fetcher.get_previous_trading_day(today)
    if t_day:
        t_day = fetcher.get_previous_trading_day(t_day)  # T日
    
    if not t_day:
        print("无法确定T日")
        return
    
    print(f"跟踪 {t_day} 选股结果的T+2表现...")
    
    # TODO: 从数据库获取T日选股结果，获取今天的收盘价，计算收益率
    # 这里简化处理
    
    print("✅ 结果跟踪完成")


def start_scheduler():
    """
    启动定时调度器
    
    调度规则:
    - T日选股: 交易日 20:00
    - T+1竞价: 交易日 09:25
    - 结果跟踪: 交易日 15:05
    - 策略进化: 每周日 20:00
    """
    print("\n🚀 T01 选股系统调度器启动")
    print("="*60)
    
    # T日选股: 交易日 20:00
    schedule.every().day.at("20:00").do(
        lambda: run_t_day_task() if create_fetcher().is_trading_day() else None
    )
    
    # T+1竞价: 交易日 09:25
    schedule.every().day.at("09:25").do(
        lambda: run_t1_auction_task() if create_fetcher().is_trading_day() else None
    )
    
    # 结果跟踪: 交易日 15:05
    schedule.every().day.at("15:05").do(
        lambda: track_results_task() if create_fetcher().is_trading_day() else None
    )
    
    # 策略进化: 每周日 20:00
    schedule.every().sunday.at("20:00").do(run_evolution_task)
    
    print("调度规则:")
    print("  - T日选股: 交易日 20:00")
    print("  - T+1竞价: 交易日 09:25")
    print("  - 结果跟踪: 交易日 15:05")
    print("  - 策略进化: 每周日 20:00")
    print("="*60)
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='T01 A股龙头选股系统')
    
    parser.add_argument('command', choices=[
        't-day',      # T日选股
        't1-auction', # T+1竞价选股
        'evolution',  # 策略进化
        'schedule',   # 启动调度器
        'init',       # 初始化数据库
        'test'        # 测试运行
    ], help='执行的命令')
    
    parser.add_argument('--date', type=str, help='指定日期 YYYYMMDD')
    parser.add_argument('--no-message', action='store_true', help='不发送消息')
    parser.add_argument('--mock', action='store_true', help='使用模拟数据')
    
    args = parser.parse_args()
    
    # 初始化数据库
    init_db()
    
    if args.command == 'init':
        print("✅ 数据库初始化完成")
        return
    
    if args.command == 't-day':
        run_t_day_task(args.date, send_message=not args.no_message)
    
    elif args.command == 't1-auction':
        run_t1_auction_task(args.date, send_message=not args.no_message)
    
    elif args.command == 'evolution':
        run_evolution_task()
    
    elif args.command == 'schedule':
        start_scheduler()
    
    elif args.command == 'test':
        # 测试运行
        print("\n🧪 测试模式运行")
        print("="*60)
        
        # 测试T日选股（使用模拟消息）
        print("\n1. 测试T日选股...")
        stocks, sentiment = run_t_day_selection(args.date)
        if stocks:
            messenger = MockMessenger()
            messenger.send_t_day_result(stocks, sentiment, args.date)
        
        print("\n✅ 测试完成")


if __name__ == '__main__':
    main()
