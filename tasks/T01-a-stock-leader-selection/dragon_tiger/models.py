#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜数据模型定义
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from database.models import Base

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
    
    def __repr__(self):
        return f"<DragonTigerRecord(trade_date={self.trade_date}, net_buy={self.net_buy})>"

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
    
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )
    
    def __repr__(self):
        return f"<DragonTigerDetail(ts_code={self.ts_code}, trade_date={self.trade_date})>"
