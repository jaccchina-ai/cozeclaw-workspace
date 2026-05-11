#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价异动记录模型
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from database.models import Base
from datetime import datetime

class AuctionAnomalyRecord(Base):
    """竞价盘口异动记录"""
    __tablename__ = 'auction_anomaly_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(10), index=True, comment='股票代码')
    name = Column(String(20), comment='股票名称')
    trade_date = Column(String(8), index=True, comment='交易日')
    anomaly_type = Column(String(20), index=True, comment='异动类型')
    anomaly_reason = Column(Text, comment='异动原因')
    auction_price = Column(Float, comment='竞价价格')
    auction_pct_chg = Column(Float, comment='竞价涨跌幅')
    auction_vol = Column(Integer, comment='竞价成交量')
    anomaly_score = Column(Float, comment='异动分数')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def __repr__(self):
        return f"<AuctionAnomalyRecord(ts_code='{self.ts_code}', name='{self.name}', anomaly_type='{self.anomaly_type}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'ts_code': self.ts_code,
            'name': self.name,
            'trade_date': self.trade_date,
            'anomaly_type': self.anomaly_type,
            'anomaly_reason': self.anomaly_reason,
            'auction_price': self.auction_price,
            'auction_pct_chg': self.auction_pct_chg,
            'auction_vol': self.auction_vol,
            'anomaly_score': self.anomaly_score,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }