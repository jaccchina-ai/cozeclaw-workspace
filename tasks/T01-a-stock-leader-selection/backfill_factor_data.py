#!/usr/bin/env python3
"""
T01 历史数据补录脚本

从历史消息文件中提取因子数据，补录到数据库
"""

import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.models import (
    init_db, get_session, StockFactorScore, AuctionData, SelectionResult
)

# 消息文件目录
MESSAGES_DIR = '/workspace/projects/workspace/logs/messages/sent'


def parse_t_day_message(content: str) -> Tuple[str, List[Dict]]:
    """
    解析T日选股消息，提取因子数据

    Returns:
        (date, stocks_data)
    """
    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    if date_match:
        date_str = date_match.group(1).replace('-', '')
    else:
        date_str = None

    stocks = []

    # 按股票分割内容
    stock_blocks = re.split(r'\n\d️⃣ \*\*', content)[1:]  # 分割后第一个为空

    for block in stock_blocks:
        try:
            # 提取股票代码和名称
            header_match = re.search(r'(\d{6}\.[A-Z]{2}) (.+?)\*\*', block)
            if not header_match:
                continue
            ts_code = header_match.group(1)
            stock_name = header_match.group(2).strip()

            # 提取总分
            total_match = re.search(r'总分:\s*([\d.]+)', block)
            total_score = float(total_match.group(1)) if total_match else 0

            # 提取原始指标
            raw_values = {}

            # 涨停质量
            limit_match = re.search(r'首次涨停=(\d{2}:\d{2}:\d{2}|[-]), 炸板=(\d+), 连板=(\d+)', block)
            if limit_match:
                raw_values['first_limit_time'] = limit_match.group(1) if limit_match.group(1) != '-' else ''
                raw_values['limit_times'] = int(limit_match.group(2))
                raw_values['consecutive_limit'] = int(limit_match.group(3))

            # 封成比
            seal_ratio_match = re.search(r'封成比:\s*([\d.]+)', block)
            if seal_ratio_match:
                raw_values['seal_ratio'] = float(seal_ratio_match.group(1))

            # 封流比
            seal_flow_match = re.search(r'封流比:\s*([\d.]+)', block)
            if seal_flow_match:
                raw_values['seal_flow_ratio'] = float(seal_flow_match.group(1))

            # 量比
            vol_match = re.search(r'量比:\s*([\d.]+)', block)
            if vol_match:
                raw_values['volume_ratio'] = float(vol_match.group(1))

            # 真实换手率
            turnover_match = re.search(r'真实换手率:\s*([\d.]+)%', block)
            if turnover_match:
                raw_values['real_turnover_rate'] = float(turnover_match.group(1))

            # 龙虎榜净买入
            net_buy_match = re.search(r'龙虎榜净买入:\s*([\d.]+)万', block)
            if net_buy_match:
                raw_values['net_buy'] = float(net_buy_match.group(1))

            # 主力净占比
            main_net_match = re.search(r'主力净占比:\s*([\d.-]+)%', block)
            if main_net_match:
                raw_values['main_net_ratio'] = float(main_net_match.group(1))

            # 成交额排名
            rank_match = re.search(r'成交额排名:\s*第(\d+)名', block)
            if rank_match:
                raw_values['amount_rank'] = int(rank_match.group(1))

            # 板块涨停数
            sector_zt_match = re.search(r'板块涨停:\s*([\d.]+)只', block)
            if sector_zt_match:
                raw_values['sector_zt_count'] = float(sector_zt_match.group(1))

            # Bias MA3
            bias_match = re.search(r'Bias MA3:\s*([\d.]+)%', block)
            if bias_match:
                raw_values['bias_ma3'] = float(bias_match.group(1))

            # 提取评分明细
            scores = {}
            score_line_match = re.search(r'【评分明细】\n(.+?)(?:\n\n|$)', block, re.DOTALL)
            if score_line_match:
                score_line = score_line_match.group(1)
                # 涨停
                limit_score = re.search(r'涨停:([\d.]+)', score_line)
                if limit_score:
                    scores['limit_quality_score'] = float(limit_score.group(1))
                # 封成比
                seal_score = re.search(r'封成比:([\d.]+)', score_line)
                if seal_score:
                    scores['seal_ratio_score'] = float(seal_score.group(1))
                # 封流比
                seal_flow_score = re.search(r'封流比:([\d.]+)', score_line)
                if seal_flow_score:
                    scores['seal_flow_ratio_score'] = float(seal_flow_score.group(1))
                # 量比
                vol_score = re.search(r'量比:([\d.]+)', score_line)
                if vol_score:
                    scores['volume_ratio_score'] = float(vol_score.group(1))
                # 换手
                turnover_score = re.search(r'换手:([\d.]+)', score_line)
                if turnover_score:
                    scores['turnover_rate_score'] = float(turnover_score.group(1))
                # 龙虎榜
                dragon_score = re.search(r'龙虎榜:([\d.]+)', score_line)
                if dragon_score:
                    scores['dragon_tiger_score'] = float(dragon_score.group(1))
                # 资金流
                money_score = re.search(r'资金流:([\d.]+)', score_line)
                if money_score:
                    scores['money_flow_score'] = float(money_score.group(1))
                # 成交额
                amount_score = re.search(r'成交额:([\d.]+)', score_line)
                if amount_score:
                    scores['amount_rank_score'] = float(amount_score.group(1))
                # 板块
                sector_score = re.search(r'板块:([\d.]+)', score_line)
                if sector_score:
                    scores['sector_heat_score'] = float(sector_score.group(1))
                # Bias
                bias_score = re.search(r'Bias:([\d.]+)', score_line)
                if bias_score:
                    scores['bias_ma3_score'] = float(bias_score.group(1))
                # 舆情
                sent_score = re.search(r'舆情:([\d.]+)', score_line)
                if sent_score:
                    scores['sentiment_score'] = float(sent_score.group(1))

            stocks.append({
                'ts_code': ts_code,
                'stock_name': stock_name,
                'total_score': total_score,
                'raw_values': raw_values,
                **scores
            })

        except Exception as e:
            print(f"   ⚠️ 解析股票数据失败: {e}")
            continue

    return date_str, stocks


def parse_t1_auction_message(content: str) -> Tuple[str, List[Dict]]:
    """
    解析T+1竞价消息，提取竞价数据

    Returns:
        (date, auction_data)
    """
    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    if date_match:
        date_str = date_match.group(1).replace('-', '')
    else:
        date_str = None

    auctions = []

    # 按股票分割内容
    stock_blocks = re.split(r'\n\d️⃣ \*\*', content)[1:]

    for block in stock_blocks:
        try:
            # 提取股票代码和名称
            header_match = re.search(r'(\d{6}\.[A-Z]{2}) (.+?)\*\*', block)
            if not header_match:
                continue
            ts_code = header_match.group(1)

            # 提取综合得分
            score_match = re.search(r'综合得分:\s*([\d.]+)', block)
            final_score = float(score_match.group(1)) if score_match else 0

            raw = {}

            # 竞价价格
            price_match = re.search(r'竞价价格:\s*([\d.]+)元', block)
            if price_match:
                raw['auction_price'] = float(price_match.group(1))

            # 竞价涨幅
            pct_match = re.search(r'竞价涨幅:\s*([\d.]+)%', block)
            if pct_match:
                raw['auction_pct_chg'] = float(pct_match.group(1))

            # 竞价成交量
            vol_match = re.search(r'竞价成交量:\s*([\d.]+)万手', block)
            if vol_match:
                raw['auction_vol'] = float(vol_match.group(1)) * 10000 * 100  # 万手转股

            # 竞价金额
            amount_match = re.search(r'竞价金额:\s*([\d.]+)万元', block)
            if amount_match:
                raw['auction_amount'] = float(amount_match.group(1))

            # 竞价换手率
            turnover_match = re.search(r'竞价换手率:\s*([\d.]+)%', block)
            if turnover_match:
                raw['auction_turnover'] = float(turnover_match.group(1))

            # 竞价量比
            vol_ratio_match = re.search(r'竞价量比:\s*([\d.]+)', block)
            if vol_ratio_match:
                raw['auction_volume_ratio'] = float(vol_ratio_match.group(1))

            # 竞价爆量比
            burst_match = re.search(r'竞价爆量比:\s*([\d.]+)', block)
            if burst_match:
                raw['auction_burst_ratio'] = float(burst_match.group(1))

            # 昨日收盘价
            pre_close_match = re.search(r'昨日收盘价:\s*([\d.]+)元', block)
            if pre_close_match:
                raw['pre_close'] = float(pre_close_match.group(1))

            # 是否弱转强
            is_wts = '【弱转强】' in block or '弱转强' in block

            auctions.append({
                'ts_code': ts_code,
                'final_score': final_score,
                'raw_values': raw,
                'is_weak_to_strong': is_wts
            })

        except Exception as e:
            print(f"   ⚠️ 解析竞价数据失败: {e}")
            continue

    return date_str, auctions


def save_factor_scores_to_db(session, date: str, stocks: List[Dict]):
    """保存因子评分到数据库"""
    try:
        # 先删除旧记录
        session.query(StockFactorScore).filter(
            StockFactorScore.trade_date == date
        ).delete()

        for stock in stocks:
            raw = stock.get('raw_values', {})
            record = StockFactorScore(
                ts_code=stock['ts_code'],
                trade_date=date,
                limit_quality_score=stock.get('limit_quality_score', 0),
                seal_ratio_score=stock.get('seal_ratio_score', 0),
                seal_flow_ratio_score=stock.get('seal_flow_ratio_score', 0),
                volume_ratio_score=stock.get('volume_ratio_score', 0),
                turnover_rate_score=stock.get('turnover_rate_score', 0),
                dragon_tiger_score=stock.get('dragon_tiger_score', 0),
                money_flow_score=stock.get('money_flow_score', 0),
                amount_rank_score=stock.get('amount_rank_score', 0),
                sector_heat_score=stock.get('sector_heat_score', 0),
                bias_ma3_score=stock.get('bias_ma3_score', 0),
                sentiment_score=stock.get('sentiment_score', 0),
                total_score=stock.get('total_score', 0),
                first_limit_time_raw=raw.get('first_limit_time', ''),
                limit_times_raw=raw.get('limit_times', 0),
                seal_ratio_raw=raw.get('seal_ratio', 0),
                seal_flow_ratio_raw=raw.get('seal_flow_ratio', 0),
                volume_ratio_raw=raw.get('volume_ratio', 0),
                turnover_rate_raw=raw.get('real_turnover_rate', 0),
                net_buy_amount_raw=raw.get('net_buy', 0),
                main_net_inflow_raw=raw.get('main_net_ratio', 0),
                amount_rank_raw=raw.get('amount_rank', 0),
                sector_zt_count_raw=raw.get('sector_zt_count', 0),
                bias_ma3_raw=raw.get('bias_ma3', 0)
            )
            session.add(record)

        session.commit()
        return len(stocks)
    except Exception as e:
        session.rollback()
        raise e


def save_auction_data_to_db(session, date: str, auctions: List[Dict]):
    """保存竞价数据到数据库"""
    from database.models import AuctionData
    try:
        # 先删除旧记录
        session.query(AuctionData).filter(
            AuctionData.trade_date == date
        ).delete()

        for stock in auctions:
            raw = stock.get('raw_values', {})
            record = AuctionData(
                ts_code=stock['ts_code'],
                trade_date=date,
                auction_price=raw.get('auction_price', 0),
                auction_vol=raw.get('auction_vol', 0),
                auction_amount=raw.get('auction_amount', 0),
                auction_pct_chg=raw.get('auction_pct_chg', 0),
                auction_turnover=raw.get('auction_turnover', 0),
                auction_volume_ratio=raw.get('auction_volume_ratio', 0),
                auction_burst_ratio=raw.get('auction_burst_ratio', 0),
                sector_auction_pct=raw.get('sector_auction_pct', 0),
                sector_resonance=raw.get('sector_resonance', 0),
                final_score=stock.get('final_score', 0),
                is_weak_to_strong=stock.get('is_weak_to_strong', False)
            )
            session.add(record)

        session.commit()
        return len(auctions)
    except Exception as e:
        session.rollback()
        raise e


def main():
    """主函数"""
    print("=" * 60)
    print("T01 历史数据补录脚本")
    print("=" * 60)

    # 初始化数据库
    init_db()
    session = get_session()

    # 获取所有消息文件
    if not os.path.exists(MESSAGES_DIR):
        print(f"❌ 消息目录不存在: {MESSAGES_DIR}")
        return

    files = os.listdir(MESSAGES_DIR)
    t_day_files = [f for f in files if 't_day' in f.lower()]
    t1_files = [f for f in files if 't1_auction' in f.lower()]

    print(f"\n发现 {len(t_day_files)} 个 T日选股消息文件")
    print(f"发现 {len(t1_files)} 个 T+1竞价消息文件")

    # 处理T日选股消息
    print("\n" + "-" * 60)
    print("【处理 T日选股消息】")
    print("-" * 60)

    t_day_total = 0
    for filename in sorted(t_day_files):
        filepath = os.path.join(MESSAGES_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            date, stocks = parse_t_day_message(content)
            if date and stocks:
                count = save_factor_scores_to_db(session, date, stocks)
                print(f"✅ {filename}: 补录 {count} 只股票 (日期: {date})")
                t_day_total += count
            else:
                print(f"⚠️ {filename}: 无有效数据")
        except Exception as e:
            print(f"❌ {filename}: 处理失败 - {e}")

    # 处理T+1竞价消息
    print("\n" + "-" * 60)
    print("【处理 T+1竞价消息】")
    print("-" * 60)

    t1_total = 0
    for filename in sorted(t1_files):
        filepath = os.path.join(MESSAGES_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            date, auctions = parse_t1_auction_message(content)
            if date and auctions:
                count = save_auction_data_to_db(session, date, auctions)
                print(f"✅ {filename}: 补录 {count} 只股票 (日期: {date})")
                t1_total += count
            else:
                print(f"⚠️ {filename}: 无有效数据")
        except Exception as e:
            print(f"❌ {filename}: 处理失败 - {e}")

    # 统计结果
    print("\n" + "=" * 60)
    print("【补录完成】")
    print("=" * 60)
    print(f"T日因子数据: {t_day_total} 条")
    print(f"T+1竞价数据: {t1_total} 条")

    # 验证数据库
    factor_count = session.query(StockFactorScore).count()
    auction_count = session.query(AuctionData).count()
    print(f"\n数据库验证:")
    print(f"  StockFactorScore 表: {factor_count} 条")
    print(f"  AuctionData 表: {auction_count} 条")

    print("\n✅ 补录完成!")


if __name__ == '__main__':
    main()
