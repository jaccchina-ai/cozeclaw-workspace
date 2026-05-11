"""
T01 选股系统 - Cron 任务处理器

被 OpenClaw Cron 调用执行定时选股任务
统一处理消息发送，避免双重发送
"""

import sys
import os
import subprocess
import traceback

sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

# 检查并安装依赖
try:
    from install_deps import check_dependencies, install_dependencies
    missing = check_dependencies()
    if missing:
        print("⚠️ 检测到缺失依赖，正在自动安装...")
        install_dependencies(missing)
except Exception as e:
    print(f"⚠️ 依赖检查失败: {e}")

# 初始化统一日志
from logging_config import init_logging, T01Logger
LOGS_DIR = init_logging()

from selection_engine import run_t_day_selection, run_t1_auction_selection
from evolution import run_weekly_evolution
from data_fetcher import create_fetcher
from messenger import get_messenger
from database.models import init_db

def run_t1_auction():
    """执行 T+1 竞价选股并发送结果"""
    # 获取任务专用logger
    logger = T01Logger.get_task_logger('t1_auction')
    logger.info("🚀 执行 T+1 竞价选股任务...")
    
    try:
        init_db()
        
        # 执行选股
        stocks = run_t1_auction_selection()
        
        if not stocks:
            logger.info("ℹ️ 今日无符合竞价选股条件的股票")
            return True
        
        # 获取市场情绪
        fetcher = create_fetcher()
        date = os.environ.get('TRADE_DATE') or __import__('datetime').datetime.now().strftime('%Y%m%d')
        sentiment = fetcher.get_market_sentiment(date)
        market_risk = sentiment.get('risk_score', 5)
        
        # 发送消息
        messenger = get_messenger()
        messenger.send_t1_auction_result(stocks, sentiment, date, market_risk)
        
        logger.info(f"✅ 竞价选股完成，共选出 {len(stocks)} 只股票")
        return True
        
    except Exception as e:
        error_msg = f"❌ 竞价选股失败: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False

def run_t_day():
    """执行 T日选股并发送结果"""
    logger = T01Logger.get_task_logger('t_day')
    logger.info("🚀 执行 T日选股任务...")
    
    try:
        init_db()
        
        # 等待Unifuncs预热任务完成
        try:
            from unifuncs_sync import UnifuncsSync
            sync = UnifuncsSync({'timeout': 60, 'check_interval': 10})
            date = __import__('datetime').datetime.now().strftime('%Y%m%d')
            
            logger.info("⏳ 等待Unifuncs预热任务完成...")
            if not sync.wait_for_completion(date):
                logger.warning("Unifuncs预热任务未完成，继续执行选股")
        except Exception as e:
            logger.error(f"等待Unifuncs预热任务失败: {e}")
        
        # 执行选股
        stocks, sentiment = run_t_day_selection()
        
        if not stocks:
            logger.info("ℹ️ 今日无符合T日选股条件的股票")
            return True
        
        # 获取动态胜率
        try:
            from evolution import StrategyEvolutionEngine
            evolution_engine = StrategyEvolutionEngine()
            win_rate = evolution_engine._calculate_win_rate(days=30)
        except:
            win_rate = 0.6
        
        # 发送消息
        date = __import__('datetime').datetime.now().strftime('%Y%m%d')
        messenger = get_messenger()
        messenger.send_t_day_result(stocks, sentiment, date, win_rate)
        
        logger.info(f"✅ T日选股完成，共选出 {len(stocks)} 只股票")
        return True
        
    except Exception as e:
        error_msg = f"❌ T日选股失败: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False

def run_track():
    """执行结果跟踪"""
    logger = T01Logger.get_task_logger('track')
    logger.info("🚀 执行结果跟踪任务...")
    
    result = subprocess.run(
        ['python3', 'main.py', 'track', '--no-message'],
        cwd='/workspace/projects/workspace/tasks/T01-a-stock-leader-selection',
        capture_output=True,
        text=True
    )
    
    logger.info(result.stdout)
    if result.stderr:
        logger.error(f"STDERR: {result.stderr}")
    
    success = result.returncode == 0
    if success:
        logger.info("✅ 结果跟踪任务完成")
    else:
        logger.error("❌ 结果跟踪任务失败")
    
    return success

def run_evolution():
    """执行策略进化"""
    logger = T01Logger.get_task_logger('evolution')
    logger.info("🚀 执行策略进化任务...")
    
    result = subprocess.run(
        ['python3', 'main.py', 'evolution', '--no-message'],
        cwd='/workspace/projects/workspace/tasks/T01-a-stock-leader-selection',
        capture_output=True,
        text=True
    )
    
    logger.info(result.stdout)
    if result.stderr:
        logger.error(f"STDERR: {result.stderr}")
    
    success = result.returncode == 0
    if success:
        logger.info("✅ 策略进化任务完成")
    else:
        logger.error("❌ 策略进化任务失败")
    
    return success

def run_unifuncs():
    """执行 Unifuncs 预热"""
    logger = T01Logger.get_task_logger('unifuncs')
    logger.info("🚀 执行 Unifuncs 预热任务...")
    
    result = subprocess.run(
        ['python3', 'main.py', 'unifuncs', '--no-message'],
        cwd='/workspace/projects/workspace/tasks/T01-a-stock-leader-selection',
        capture_output=True,
        text=True
    )
    
    logger.info(result.stdout)
    if result.stderr:
        logger.error(f"STDERR: {result.stderr}")
    
    success = result.returncode == 0
    if success:
        logger.info("✅ Unifuncs预热任务完成")
    else:
        logger.error("❌ Unifuncs预热任务失败")
    
    return success

def run_market_review():
    """执行市场复盘分析"""
    logger = T01Logger.get_task_logger('market_review')
    logger.info("🚀 执行市场复盘分析...")
    
    # 设置环境变量
    env = os.environ.copy()
    env['MX_APIKEY'] = 'mkt_sEL_RY2_Fh_NrwkOezNpa9nlc9wtoT5yHZE7W6A7J8s'
    
    result = subprocess.run(
        ['python3', 'market_review.py'],
        cwd='/workspace/projects/workspace/tasks/T01-a-stock-leader-selection',
        capture_output=True,
        text=True,
        env=env
    )
    
    logger.info(result.stdout)
    if result.stderr:
        logger.error(f"STDERR: {result.stderr}")
    
    success = result.returncode == 0
    if success:
        logger.info("✅ 市场复盘分析完成")
    else:
        logger.error("❌ 市场复盘分析失败")
    
    return success

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task', choices=['t1-auction', 't-day', 'track', 'evolution', 'unifuncs', 'market-review'])
    args = parser.parse_args()
    
    os.environ['TUSHARE_TOKEN'] = '870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab'
    
    # 记录启动信息到统一日志
    task_logger = T01Logger.get_task_logger(args.task.replace('-', '_'))
    task_logger.info(f"="*60)
    task_logger.info(f"Cron任务启动: {args.task}")
    task_logger.info(f"="*60)
    
    if args.task == 't1-auction':
        success = run_t1_auction()
    elif args.task == 't-day':
        success = run_t_day()
    elif args.task == 'track':
        success = run_track()
    elif args.task == 'evolution':
        success = run_evolution()
    elif args.task == 'unifuncs':
        success = run_unifuncs()
    elif args.task == 'market-review':
        success = run_market_review()
    
    task_logger.info(f"任务结束，状态: {'成功' if success else '失败'}")
    
    sys.exit(0 if success else 1)
