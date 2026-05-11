#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建龙虎榜数据库表"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from database.db_config import get_database_url, get_engine_kwargs

Base = declarative_base()

class DragonTigerRecord(Base):
    """龙虎榜分析记录"""
    __tablename__ = 'dragon_tiger_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), nullable=False, unique=True, comment='交易日YYYYMMDD')
    total_buy = Column(Float, default=0, comment='总买入金额(亿元)')
    total_sell = Column(Float, default=0, comment='总卖出金额(亿元)')
    net_buy = Column(Float, default=0, comment='净流入金额(亿元)')
    hot_stocks = Column(Text, comment='热门股票JSON')
    seat_stats = Column(Text, comment='席位统计JSON')
    stock_stats = Column(Text, comment='股票统计JSON')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP', comment='创建时间')
    updated_at = Column(DateTime, server_default='CURRENT_TIMESTAMP', onupdate='CURRENT_TIMESTAMP', comment='更新时间')

class DragonTigerDetail(Base):
    """龙虎榜详情记录"""
    __tablename__ = 'dragon_tiger_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), nullable=False, comment='交易日YYYYMMDD')
    ts_code = Column(String(10), nullable=False, comment='股票代码')
    name = Column(String(20), comment='股票名称')
    close = Column(Float, comment='收盘价')
    pct_change = Column(Float, comment='涨跌幅(%)')
    turn_over_rate = Column(Float, comment='换手率(%)')
    amount = Column(Float, comment='总成交额(万元)')
    reason = Column(Text, comment='上榜原因')
    buy_amount = Column(Float, comment='买入金额(万元)')
    sell_amount = Column(Float, comment='卖出金额(万元)')
    net_buy = Column(Float, comment='净额(万元)')
    broker = Column(String(100), comment='营业部名称')
    seat_type = Column(String(10), comment='席位类型: 游资/机构/北向/普通')
    is_buy = Column(Integer, comment='是否买入: 1买入0卖出')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP', comment='创建时间')

def main():
    try:
        # 创建数据库引擎
        engine = create_engine(get_database_url(), **get_engine_kwargs())
        
        # 创建龙虎榜相关表
        DragonTigerRecord.__table__.create(bind=engine, checkfirst=True)
        DragonTigerDetail.__table__.create(bind=engine, checkfirst=True)
        
        print("✅ 龙虎榜数据库表创建成功")
        
        # 检查表是否存在
        inspector = engine.reflect()
        if 'dragon_tiger_records' in inspector.tables:
            print("✅ dragon_tiger_records 表已存在")
        if 'dragon_tiger_details' in inspector.tables:
            print("✅ dragon_tiger_details 表已存在")
            
        return True
    except Exception as e:
        print(f"❌ 创建龙虎榜数据库表失败: {e}")
        return False

if __name__ == '__main__':
    main()
