"""
T01 选股系统 - 主入口

提供命令行接口和定时调度
"""

import os
import sys

# 检查并安装依赖
sys.path.insert(0, os.path.dirname(__file__))
try:
    from install_deps import check_dependencies, install_dependencies
    missing = check_dependencies()
    if missing:
        print("⚠️ 检测到缺失依赖，正在自动安装...")
        install_dependencies(missing)
except Exception as e:
    print(f"⚠️ 依赖检查失败: {e}")

import argparse
import schedule
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional

# 初始化统一日志
from logging_config import init_logging, T01Logger, get_selection_logger
LOGS_DIR = init_logging()
logger = get_selection_logger()

from database.models import init_db, get_session
from selection_engine import TDaySelectionEngine, T1AuctionEngine, run_t_day_selection, run_t1_auction_selection
from messenger import get_messenger, FeishuMessenger, MockMessenger
from evolution import StrategyEvolutionEngine, run_weekly_evolution
from data_fetcher import create_fetcher
from date_calculator import get_previous_trading_day as local_get_previous_trading_day, is_trading_day as local_is_trading_day
from monitor import Monitor, monitored_task, init_monitor
from unifuncs_scheduler import run_unifuncs_warmup


def run_market_review_task(date: str = None):
    """
    执行 T01-Market-Review 市场复盘任务
    
    执行时间: 交易日 21:00
    分析当日热点板块，评估持续性，生成投资参考报告
    """
    task_logger = T01Logger.get_task_logger('market_review', date)
    monitor = Monitor()
    log_id = monitor.start_task('market_review', date)
    
    task_logger.info("="*60)
    task_logger.info(f"T01-Market-Review 市场复盘 - {datetime.now()}")
    task_logger.info("="*60)
    
    try:
        # 导入并执行市场复盘
        from market_review import analyze_market_review
        report = analyze_market_review()
        
        task_logger.info("✅ 市场复盘完成")
        monitor.end_task(log_id, 'success')
        return report
        
    except Exception as e:
        error_msg = str(e)
        task_logger.error(f"❌ 市场复盘失败: {error_msg}")
        task_logger.error(traceback.format_exc())
        monitor.end_task(log_id, 'failed', error_message=error_msg)
        raise


def run_deps_check_task(date: str = None):
    """
    执行T01依赖检查任务
    
    执行时间: 交易日 09:00
    检查所有必要依赖是否就绪，确保09:27竞价选股能正常运行
    """
    task_logger = T01Logger.get_task_logger('deps_check', date)
    monitor = Monitor()
    log_id = monitor.start_task('deps_check', date)
    
    task_logger.info("="*60)
    task_logger.info(f"T01-Deps-Check 依赖检查 - {datetime.now()}")
    task_logger.info("="*60)
    
    deps_ok = True
    issues = []
    
    # 1. 检查 Tushare API
    try:
        fetcher = create_fetcher()
        task_logger.info("✅ Tushare API 连接正常")
    except Exception as e:
        deps_ok = False
        issues.append(f"Tushare API: {e}")
        task_logger.error(f"❌ Tushare API 异常: {e}")
    
    # 2. 检查数据库连接
    try:
        from database.models import get_session
        from sqlalchemy import text
        session = get_session()
        session.execute(text("SELECT 1"))
        task_logger.info("✅ 数据库连接正常")
    except Exception as e:
        deps_ok = False
        issues.append(f"数据库: {e}")
        task_logger.error(f"❌ 数据库异常: {e}")
    
    # 3. 检查T日选股数据
    try:
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        from selection_engine import TDaySelectionEngine
        engine = TDaySelectionEngine()
        t_day = fetcher.get_previous_trading_day(date)
        from database.models import SelectionResult
        results = session.query(SelectionResult).filter(
            SelectionResult.trade_date == t_day,
            SelectionResult.selection_type == 't_day'
        ).count()
        task_logger.info(f"✅ T日({t_day})选股数据: {results} 只")
    except Exception as e:
        issues.append(f"T日数据: {e}")
        task_logger.warning(f"⚠️ T日数据检查: {e}")
    
    # 4. 检查市场情绪数据
    try:
        from database.models import MarketSentiment
        sentiment = session.query(MarketSentiment).filter(
            MarketSentiment.trade_date == date
        ).first()
        if sentiment:
            task_logger.info(f"✅ 市场情绪数据正常 (风险评分: {sentiment.risk_score})")
        else:
            task_logger.warning("⚠️ 今日市场情绪数据缺失")
    except Exception as e:
        issues.append(f"市场情绪: {e}")
        task_logger.warning(f"⚠️ 市场情绪检查: {e}")
    
    monitor.end_task(log_id, 'success' if deps_ok else 'failed')
    
    if deps_ok:
        task_logger.info("✅ T01-Deps-Check 依赖检查通过，09:27可执行竞价选股")
    else:
        task_logger.error(f"❌ T01-Deps-Check 依赖检查失败: {issues}")
        monitor.create_alert(
            alert_type='deps_check_failed',
            severity='warning',
            title='T01 依赖检查失败',
            message='; '.join(issues),
            trade_date=date
        )
    
    return deps_ok


def run_unifuncs_warmup_task(date: str = None):
    """
    执行 Unifuncs 预热任务
    
    执行时间: 交易日 19:30
    提前调用 Unifuncs 获取舆情分析结果，供 20:00 选股使用
    """
    task_logger = T01Logger.get_task_logger('unifuncs', date)
    monitor = Monitor()
    log_id = monitor.start_task('unifuncs_warmup', date)
    
    try:
        task_logger.info("开始 Unifuncs 预热...")
        run_unifuncs_warmup(date)
        monitor.end_task(log_id, 'success')
        task_logger.info("✅ Unifuncs 预热完成")
    except Exception as e:
        monitor.end_task(log_id, 'failed', error_message=str(e))
        task_logger.error(f"❌ Unifuncs 预热失败: {e}")
        task_logger.error(traceback.format_exc())
        raise


def run_t_day_task(date: str = None, send_message: bool = True):
    """
    执行T日选股任务
    
    执行时间: 交易日 20:00
    """
    task_logger = T01Logger.get_task_logger('t_day', date)
    monitor = Monitor()
    log_id = monitor.start_task('t_day_selection', date)
    
    task_logger.info("="*60)
    task_logger.info(f"T01 T日选股任务启动 - {datetime.now()}")
    task_logger.info("="*60)
    
    try:
        # 执行选股
        stocks, sentiment = run_t_day_selection(date)
        
        if not stocks:
            task_logger.warning("⚠️ 无选股结果")
            monitor.end_task(log_id, 'success', result_count=0)
            return
        
        # 获取动态胜率
        try:
            evolution_engine = StrategyEvolutionEngine()
            win_rate = evolution_engine._calculate_win_rate(days=30)
        except:
            win_rate = 0.6
        
        # 获取 Unifuncs 热点板块信息
        hot_sectors = []
        try:
            from unifuncs_scheduler import load_result
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            unifuncs_result = load_result(date)
            if unifuncs_result and unifuncs_result.get('status') == 'completed':
                hot_sectors = unifuncs_result.get('hot_sectors', [])
                task_logger.info(f"📊 获取到热点板块: {hot_sectors}")
        except Exception as e:
            task_logger.warning(f"⚠️ 获取热点板块失败: {e}")
        
        # 发送消息
        if send_message:
            messenger = get_messenger()
            messenger.send_t_day_result(stocks, sentiment, date, win_rate, hot_sectors)
        
        task_logger.info(f"✅ T日选股完成，共选出 {len(stocks)} 只股票")
        monitor.end_task(log_id, 'success', result_count=len(stocks))
        return stocks, sentiment
        
    except Exception as e:
        error_msg = str(e)
        task_logger.error(f"❌ T日选股任务失败: {error_msg}")
        task_logger.error(traceback.format_exc())
        monitor.end_task(log_id, 'failed', error_message=error_msg)
        monitor.create_alert(
            alert_type='task_failed',
            severity='error',
            title='T日选股任务失败',
            message=error_msg,
            trade_date=date
        )
        raise


def run_t1_auction_task(date: str = None, send_message: bool = True):
    """
    执行T01-T1-Auction任务 (T+1竞价选股)
    
    执行时间: 交易日 09:27
    注意: 竞价阶段不使用主力资金流向模块
    """
    task_logger = T01Logger.get_task_logger('t1_auction', date)
    monitor = Monitor()
    log_id = monitor.start_task('t1_auction_selection', date)
    
    task_logger.info("="*60)
    task_logger.info(f"T01 T+1竞价选股任务启动 - {datetime.now()}")
    task_logger.info("="*60)
    
    try:
        # 执行选股
        stocks = run_t1_auction_selection(date)
        
        if not stocks:
            task_logger.warning("⚠️ 无选股结果")
            monitor.end_task(log_id, 'success', result_count=0)
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
        
        task_logger.info(f"✅ 竞价选股完成，共选出 {len(stocks)} 只股票")
        monitor.end_task(log_id, 'success', result_count=len(stocks))
        return stocks
        
    except Exception as e:
        error_msg = str(e)
        task_logger.error(f"❌ T+1竞价选股任务失败: {error_msg}")
        task_logger.error(traceback.format_exc())
        monitor.end_task(log_id, 'failed', error_message=error_msg)
        monitor.create_alert(
            alert_type='task_failed',
            severity='error',
            title='T+1竞价选股任务失败',
            message=error_msg,
            trade_date=date
        )
        raise


def run_evolution_task():
    """
    执行策略进化任务
    
    执行时间: 每周日 20:00
    """
    task_logger = T01Logger.get_task_logger('evolution')
    monitor = Monitor()
    log_id = monitor.start_task('strategy_evolution')
    
    task_logger.info("="*60)
    task_logger.info(f"T01 策略进化任务启动 - {datetime.now()}")
    task_logger.info("="*60)
    
    try:
        result = run_weekly_evolution()
        task_logger.info("✅ 策略进化任务完成")
        monitor.end_task(log_id, 'success')
        return result
        
    except Exception as e:
        error_msg = str(e)
        task_logger.error(f"❌ 策略进化任务失败: {error_msg}")
        task_logger.error(traceback.format_exc())
        monitor.end_task(log_id, 'failed', error_message=error_msg)
        monitor.create_alert(
            alert_type='task_failed',
            severity='warning',
            title='策略进化任务失败',
            message=error_msg
        )
        raise


def track_results_task():
    """
    执行结果跟踪任务

    执行时间: 交易日 16:10 (收盘后跟踪选股结果并计算胜率)
    跟踪 T+1 竞价阶段推荐的 3 只股票的多日收益情况

    新卖出策略:
    - T+2 日如果涨停: 卖出一半仓位，持有另一半
    - T+2 日如果不涨停: 收盘价全部卖出
    - T+3 日如果持有仓位且涨停: 继续持有
    - T+3 日如果持有仓位且不涨停: 收盘价卖出剩余一半
    - 以此类推，直到全部卖出

    统计逻辑:
    - 买入价: T+1 日开盘价
    - 卖出价: 各次卖出的收盘价
    - 统计: 最终总收益为正即算盈利

    数据存储:
    - tracked_results: 跟踪结果（支持分批次卖出记录）
    - ml_training_records: 机器学习训练数据
    """
    task_logger = T01Logger.get_task_logger('track')
    
    task_logger.info("="*60)
    task_logger.info(f"T01 结果跟踪任务启动 - {datetime.now()}")
    task_logger.info("="*60)

    fetcher = create_fetcher()
    session = get_session()

    # 今天是 T+2 日
    t2_day = datetime.now().strftime('%Y%m%d')

    # 计算 T+1 日和 T 日
    t1_day = fetcher.get_previous_trading_day(t2_day)
    if not t1_day:
        task_logger.warning("⚠️ Tushare API 获取 T+1 日失败，使用本地日期计算...")
        t1_day = local_get_previous_trading_day(t2_day)
    
    t_day = fetcher.get_previous_trading_day(t1_day) if t1_day else None
    if not t_day and t1_day:
        task_logger.warning("⚠️ Tushare API 获取 T 日失败，使用本地日期计算...")
        t_day = local_get_previous_trading_day(t1_day)
    
    if not t1_day or not t_day:
        task_logger.error("❌ 无法确定交易日")
        return

    task_logger.info(f"跟踪日期: T日={t_day}, T+1日={t1_day}, T+2日={t2_day}")

    # 从数据库获取 T+1 竞价选股结果
    from database.models import SelectionResult, StockFactorScore, AuctionData
    auction_results = session.query(SelectionResult).filter(
        SelectionResult.trade_date == t1_day,
        SelectionResult.selection_type == 't1_auction'
    ).order_by(SelectionResult.final_rank).limit(2).all()

    # 如果没有找到 T+1 竞价结果，尝试获取 T 日选股结果（替代方案）
    if not auction_results:
        task_logger.warning(f"⚠️ 未找到 {t1_day} 的 T+1 竞价选股结果，尝试获取 T 日选股结果")
        auction_results = session.query(SelectionResult).filter(
            SelectionResult.trade_date == t_day,
            SelectionResult.selection_type == 't_day'
        ).order_by(SelectionResult.final_rank).limit(2).all()
        
        if not auction_results:
            task_logger.error(f"❌ 未找到 {t1_day} 的 T+1 竞价选股结果，也未找到 {t_day} 的 T 日选股结果")
            return
        task_logger.info(f"📊 获取到 {len(auction_results)} 只 T 日推荐股票:")

    task_logger.info(f"📊 获取到 {len(auction_results)} 只 T+1 竞价推荐股票:")
    for r in auction_results:
        task_logger.info(f"   {r.final_rank}. {r.ts_code} {r.stock_name} - 得分: {r.total_score}")

    # 预获取 T日因子评分数据 (用于机器学习)
    t_factor_map = {}
    try:
        t_factors = session.query(StockFactorScore).filter(
            StockFactorScore.trade_date == t_day
        ).all()
        t_factor_map = {f.ts_code: f for f in t_factors}
        task_logger.info(f"📦 获取到 {len(t_factor_map)} 只股票的 T日因子评分")
    except Exception as e:
        task_logger.warning(f"⚠️ 获取 T日因子评分失败: {e}")

    # 预获取 T+1 竞价数据 (用于机器学习)
    t1_auction_map = {}
    try:
        t1_auctions = session.query(AuctionData).filter(
            AuctionData.trade_date == t1_day
        ).all()
        t1_auction_map = {a.ts_code: a for a in t1_auctions}
        task_logger.info(f"📦 获取到 {len(t1_auction_map)} 只股票的 T+1 竞价数据")
    except Exception as e:
        task_logger.warning(f"⚠️ 获取 T+1 竞价数据失败: {e}")

    # 获取 T+1 日开盘价
    t1_prices = {}
    try:
        for r in auction_results:
            t1_daily = fetcher.pro.daily(ts_code=r.ts_code, start_date=t1_day, end_date=t1_day)
            if not t1_daily.empty:
                t1_prices[r.ts_code] = float(t1_daily.iloc[0]['open'])
    except Exception as e:
        task_logger.warning(f"⚠️ 获取 T+1 日开盘价失败: {e}")

    # 跟踪每只股票的多日表现
    tracked_stocks = []
    ml_records = []  # 机器学习训练数据

    for stock in auction_results:
        ts_code = stock.ts_code
        stock_name = stock.stock_name
        t1_open = t1_prices.get(ts_code, 0)
        
        if t1_open <= 0:
            task_logger.warning(f"   ❌ {ts_code} {stock_name}: T+1 日开盘价无效 ({t1_open})")
            continue

        task_logger.info(f"\n📈 开始跟踪 {ts_code} {stock_name} (买入价: {t1_open:.2f})")

        # 初始化跟踪状态
        shares_held = 1.0  # 持有仓位比例（1.0表示满仓）
        sell_history = []
        total_profit = 0.0
        current_date = t2_day
        days_tracked = 0
        max_days = 10  # 最多跟踪10个交易日

        try:
            while shares_held > 0 and days_tracked < max_days:
                # 获取当前日期的行情数据
                daily_data = fetcher.pro.daily(ts_code=ts_code, start_date=current_date, end_date=current_date)
                if daily_data.empty:
                    task_logger.warning(f"   ⚠️ {current_date}: 无行情数据，结束跟踪")
                    break

                close_price = float(daily_data.iloc[0]['close'])
                # 判断是否涨停 (涨幅 >= 9.8%)
                pct_chg = float(daily_data.iloc[0]['pct_chg'])
                is_limit_up = pct_chg >= 9.8

                # 计算当日收益率
                daily_return = (close_price - t1_open) / t1_open * 100 if t1_open > 0 else 0

                # 决定卖出策略
                sell_ratio = 0.0
                if days_tracked == 0:
                    # T+2 日处理
                    if is_limit_up:
                        sell_ratio = 0.5  # 卖出一半
                        task_logger.info(f"   ✅ {current_date}: 涨停 ({pct_chg:.2f}%)，卖出50%仓位")
                    else:
                        sell_ratio = 1.0  # 全部卖出
                        task_logger.info(f"   ❌ {current_date}: 未涨停 ({pct_chg:.2f}%)，卖出全部仓位")
                else:
                    # T+3 日及以后处理
                    if is_limit_up:
                        sell_ratio = 0.0  # 继续持有
                        task_logger.info(f"   ✅ {current_date}: 涨停 ({pct_chg:.2f}%)，继续持有剩余仓位")
                    else:
                        sell_ratio = 1.0  # 卖出剩余全部仓位
                        task_logger.info(f"   ❌ {current_date}: 未涨停 ({pct_chg:.2f}%)，卖出剩余全部仓位")

                # 执行卖出
                if sell_ratio > 0 and shares_held > 0:
                    sell_amount = shares_held * sell_ratio
                    # 计算本次卖出的盈利
                    profit = (close_price - t1_open) * sell_amount
                    total_profit += profit
                    
                    # 记录卖出历史
                    sell_record = {
                        'date': current_date,
                        'price': close_price,
                        'ratio': sell_ratio,
                        'shares_sold': sell_amount,
                        'profit': profit,
                        'is_limit_up': is_limit_up
                    }
                    sell_history.append(sell_record)
                    
                    # 更新剩余仓位
                    shares_held -= sell_amount
                    shares_held = max(0.0, shares_held)
                    
                    task_logger.info(f"   💹 卖出 {sell_amount*100:.1f}% 仓位，价格 {close_price:.2f}，盈利 {profit:.2f} 元/股")

                task_logger.info(f"   📊 {current_date}: 收盘价 {close_price:.2f}，剩余仓位 {shares_held*100:.1f}%，累计盈利 {total_profit:.2f} 元/股")

                # 准备下一个交易日
                next_date = fetcher.get_next_trading_day(current_date)
                if not next_date or next_date == current_date:
                    task_logger.warning(f"   ⚠️ 无法获取下一个交易日，结束跟踪")
                    break
                
                current_date = next_date
                days_tracked += 1

            # 计算最终收益率
            final_return_pct = (total_profit / t1_open) * 100 if t1_open > 0 else 0
            is_win = final_return_pct > 3  # 盈利大于3%才判定为成功

            task_logger.info(f"\n🏁 {ts_code} {stock_name} 跟踪结束:")
            task_logger.info(f"   总盈利: {total_profit:.2f} 元/股 ({final_return_pct:.2f}%)")
            task_logger.info(f"   最终仓位: {shares_held*100:.1f}%")
            task_logger.info(f"   盈利状态: {'✅ 盈利' if is_win else '❌ 亏损'}")

            # 添加到跟踪列表
            tracked_stocks.append({
                'ts_code': ts_code,
                'stock_name': stock_name,
                't1_open': t1_open,
                'final_profit': total_profit,
                'return_pct': final_return_pct,
                'is_win': is_win,
                'rank': stock.final_rank,
                'shares_held': shares_held,
                'sell_history': sell_history,
                'days_tracked': days_tracked
            })

            # 构建机器学习训练数据（使用 T+2 日数据作为标签）
            t_factor = t_factor_map.get(ts_code)
            t1_auction = t1_auction_map.get(ts_code)
            
            if t_factor and t1_auction:
                # 获取 T+2 日行情数据
                t2_daily = fetcher.pro.daily(ts_code=ts_code, start_date=t2_day, end_date=t2_day)
                t2_close = float(t2_daily.iloc[0]['close']) if not t2_daily.empty else 0
                t2_return = (t2_close - t1_open) / t1_open * 100 if t1_open > 0 else 0
                
                from database.models import MLTrainingRecord
                ml_record = MLTrainingRecord(
                    # 日期标识
                    t_day=t_day,
                    t1_day=t1_day,
                    t2_day=t2_day,
                    ts_code=ts_code,
                    stock_name=stock_name,
                    
                    # T日因子评分
                    t_limit_quality_score=t_factor.limit_quality_score or 0,
                    t_seal_ratio_score=t_factor.seal_ratio_score or 0,
                    t_seal_flow_ratio_score=t_factor.seal_flow_ratio_score or 0,
                    t_volume_ratio_score=t_factor.volume_ratio_score or 0,
                    t_turnover_rate_score=t_factor.turnover_rate_score or 0,
                    t_dragon_tiger_score=t_factor.dragon_tiger_score or 0,
                    t_money_flow_score=t_factor.money_flow_score or 0,
                    t_amount_rank_score=t_factor.amount_rank_score or 0,
                    t_sector_heat_score=t_factor.sector_heat_score or 0,
                    t_bias_ma3_score=t_factor.bias_ma3_score or 0,
                    t_sentiment_score=t_factor.sentiment_score or 0,
                    t_sector_linkage_score=t_factor.sector_linkage_score or 0,
                    t_total_score=t_factor.total_score or 0,
                    
                    # T日原始值
                    t_first_limit_time=str(t_factor.first_limit_time_raw or ''),
                    t_limit_times=t_factor.limit_times_raw or 0,
                    t_seal_ratio=t_factor.seal_ratio_raw or 0,
                    t_seal_flow_ratio=t_factor.seal_flow_ratio_raw or 0,
                    t_volume_ratio=t_factor.volume_ratio_raw or 0,
                    t_turnover_rate=t_factor.turnover_rate_raw or 0,
                    t_net_buy_amount=t_factor.net_buy_amount_raw or 0,
                    t_main_net_inflow=t_factor.main_net_inflow_raw or 0,
                    t_amount_rank=t_factor.amount_rank_raw or 0,
                    t_sector_zt_count=t_factor.sector_zt_count_raw or 0,
                    t_bias_ma3=t_factor.bias_ma3_raw or 0,
                    
                    # T+1竞价因子
                    t1_auction_price=t1_auction.auction_price or 0,
                    t1_auction_pct_chg=t1_auction.auction_pct_chg or 0,
                    t1_auction_turnover=t1_auction.auction_turnover or 0,
                    t1_auction_volume_ratio=t1_auction.auction_volume_ratio or 0,
                    t1_auction_burst_ratio=t1_auction.auction_burst_ratio or 0,
                    t1_sector_resonance=t1_auction.sector_resonance or 0,
                    t1_auction_score=t1_auction.auction_score or 0,
                    t1_final_score=t1_auction.final_score or 0,
                    t1_is_weak_to_strong=t1_auction.is_weak_to_strong or False,
                    
                    # T+2收益标签
                    t1_open=t1_open,
                    t2_close=t2_close,
                    return_pct=round(t2_return, 2),
                    is_win=t2_return > 3,  # 保持原定义用于机器学习
                    
                    # 选股排名
                    t_day_rank=None,
                    t1_auction_rank=stock.final_rank,
                    
                    # 板块信息
                    sector=stock.sector,
                    sector_role_label=stock.sector_role_label
                )
                ml_records.append(ml_record)

        except Exception as e:
            task_logger.error(f"   ❌ 跟踪 {ts_code} 失败: {e}")
            continue

    if not tracked_stocks:
        task_logger.error("❌ 无有效跟踪数据")
        return

    # 统计整体胜率和平均收益率
    total = len(tracked_stocks)
    wins = sum(1 for s in tracked_stocks if s['is_win'])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = sum(s['return_pct'] for s in tracked_stocks) / total if total > 0 else 0

    task_logger.info("\n" + "="*60)
    task_logger.info(f"📊 多日跟踪收益统计 (T+1日={t1_day})")
    task_logger.info("="*60)
    task_logger.info(f"   跟踪股票数: {total}")
    task_logger.info(f"   盈利 (总收益为正): {wins} 只")
    task_logger.info(f"   胜率: {win_rate:.1f}%")
    task_logger.info(f"   平均收益率: {avg_return:.2f}%")
    task_logger.info("="*60)

    # 保存跟踪结果到数据库（自动去重）
    try:
        from database.models import TrackedResult
        import json
        
        # 先删除该日期的旧记录，避免重复
        for stock in tracked_stocks:
            session.query(TrackedResult).filter(
                TrackedResult.t1_day == t1_day,
                TrackedResult.ts_code == stock['ts_code']
            ).delete()
        
        # 插入新记录
        for stock in tracked_stocks:
            # 将卖出历史转换为JSON字符串
            sell_history_json = json.dumps(stock['sell_history'], ensure_ascii=False)
            
            record = TrackedResult(
                t_day=t_day,
                t1_day=t1_day,
                t2_day=t2_day,
                ts_code=stock['ts_code'],
                stock_name=stock['stock_name'],
                t1_open=stock['t1_open'],
                t2_close=0,  # 不再使用
                return_pct=stock['return_pct'],
                is_win=stock['is_win'],
                selection_rank=stock['rank'],
                shares_held=stock['shares_held'],
                sell_history=sell_history_json,
                final_profit=stock['final_profit']
            )
            session.add(record)
        session.commit()
        task_logger.info("✅ 跟踪结果已保存到数据库")
    except Exception as e:
        session.rollback()
        task_logger.error(f"⚠️ 保存跟踪结果失败: {e}")

    # 保存机器学习训练数据
    if ml_records:
        try:
            for record in ml_records:
                session.add(record)
            session.commit()
            task_logger.info(f"✅ 机器学习训练数据已保存 ({len(ml_records)} 条)")
        except Exception as e:
            session.rollback()
            task_logger.error(f"⚠️ 保存机器学习数据失败: {e}")

    # 发送消息通知
    try:
        messenger = get_messenger()
        messenger.send_track_result(tracked_stocks, win_rate, avg_return, t1_day, t2_day)
        task_logger.info("✅ 跟踪消息已发送")
    except Exception as e:
        task_logger.error(f"⚠️ 发送消息失败: {e}")

    task_logger.info("✅ 结果跟踪完成")


def start_scheduler():
    """
    启动定时调度器

    调度规则:
    - Unifuncs预热: 交易日 19:30
    - T日选股: 交易日 20:00
    - T01-Market-Review: 交易日 21:00
    - T01-Deps-Check: 交易日 09:00
    - T01-T1-Auction: 交易日 09:27
    - T01-Track: 交易日 16:10
    - 策略进化: 每周日 20:00
    """
    logger.info("🚀 T01 选股系统调度器启动")
    logger.info("="*60)
    
    # Unifuncs预热: 交易日 19:30
    schedule.every().day.at("19:30").do(
        lambda: run_unifuncs_warmup_task() if local_is_trading_day() else None
    )
    
    # T日选股: 交易日 20:00
    schedule.every().day.at("20:00").do(
        lambda: run_t_day_task() if local_is_trading_day() else None
    )
    
    # T01-Market-Review: 交易日 21:00 (市场复盘)
    schedule.every().day.at("21:00").do(
        lambda: run_market_review_task() if local_is_trading_day() else None
    )
    
    # T01-Deps-Check: 交易日 09:00 (依赖检查)
    schedule.every().day.at("09:00").do(
        lambda: run_deps_check_task() if local_is_trading_day() else None
    )
    
    # T01-T1-Auction: 交易日 09:27 (竞价选股)
    schedule.every().day.at("09:27").do(
        lambda: run_t1_auction_task() if local_is_trading_day() else None
    )
    
    # T01-Track: 交易日 16:10 (跟踪选股结果并计算胜率)
    schedule.every().day.at("16:10").do(
        lambda: track_results_task() if local_is_trading_day() else None
    )
    
    # 策略进化: 每周日 20:00
    schedule.every().sunday.at("20:00").do(run_evolution_task)
    
    logger.info("调度规则:")
    logger.info("  - Unifuncs预热: 交易日 19:30")
    logger.info("  - T日选股: 交易日 20:00")
    logger.info("  - T01-Market-Review: 交易日 21:00")
    logger.info("  - T01-Deps-Check: 交易日 09:00")
    logger.info("  - T01-T1-Auction: 交易日 09:27")
    logger.info("  - 结果跟踪: 交易日 15:45")
    logger.info("  - 策略进化: 每周日 20:00")
    logger.info("="*60)
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='T01 A股龙头选股系统')
    
    parser.add_argument('command', choices=[
        'deps-check',    # 依赖检查
        't-day',         # T日选股
        't1-auction',    # T+1竞价选股
        'market-review', # 市场复盘
        'unifuncs',      # Unifuncs预热
        'evolution',     # 策略进化
        'track',         # 结果跟踪
        'schedule',      # 启动调度器
        'init',          # 初始化数据库
        'status',        # 查看系统状态
        'test'           # 测试运行
    ], help='执行的命令')
    
    parser.add_argument('--date', type=str, help='指定日期 YYYYMMDD')
    parser.add_argument('--no-message', action='store_true', help='不发送消息')
    parser.add_argument('--mock', action='store_true', help='使用模拟数据')
    
    args = parser.parse_args()
    
    # 初始化数据库和监控
    init_db()
    monitor = init_monitor()
    
    if args.command == 'init':
        logger.info("✅ 数据库和监控初始化完成")
        return
    
    if args.command == 'status':
        monitor.print_daily_report()
        return
    
    if args.command == 'unifuncs':
        # 直接执行预热，不检查交易日
        run_unifuncs_warmup(args.date) if args.date else run_unifuncs_warmup_task()
    
    elif args.command == 'market-review':
        run_market_review_task(args.date)
    
    elif args.command == 'deps-check':
        run_deps_check_task(args.date)
    
    if args.command == 't-day':
        run_t_day_task(args.date, send_message=not args.no_message)
    
    elif args.command == 't1-auction':
        run_t1_auction_task(args.date, send_message=not args.no_message)
    
    elif args.command == 'evolution':
        run_evolution_task()
    
    elif args.command == 'track':
        track_results_task()
    
    elif args.command == 'schedule':
        start_scheduler()
    
    elif args.command == 'test':
        # 测试运行
        logger.info("🧪 测试模式运行")
        logger.info("="*60)
        
        # 测试T日选股（使用模拟消息）
        logger.info("1. 测试T日选股...")
        stocks, sentiment = run_t_day_selection(args.date)
        if stocks:
            # 获取热点板块
            hot_sectors = []
            try:
                from unifuncs_scheduler import load_result
                test_date = args.date if args.date else datetime.now().strftime('%Y%m%d')
                unifuncs_result = load_result(test_date)
                if unifuncs_result and unifuncs_result.get('status') == 'completed':
                    hot_sectors = unifuncs_result.get('hot_sectors', [])
            except:
                pass
            
            messenger = MockMessenger()
            messenger.send_t_day_result(stocks, sentiment, args.date, hot_sectors=hot_sectors)
        
        logger.info("✅ 测试完成")


if __name__ == '__main__':
    main()
