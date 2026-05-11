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
    ).order_by(SelectionResult.final_rank).limit(3).all()

    # 如果没有找到 T+1 竞价结果，尝试获取 T 日选股结果（替代方案）
    if not auction_results:
        task_logger.warning(f"⚠️ 未找到 {t1_day} 的 T+1 竞价选股结果，尝试获取 T 日选股结果")
        auction_results = session.query(SelectionResult).filter(
            SelectionResult.trade_date == t_day,
            SelectionResult.selection_type == 't_day'
        ).order_by(SelectionResult.final_rank).limit(3).all()
        
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
            is_win = total_profit > 0  # 总收益为正即算盈利

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