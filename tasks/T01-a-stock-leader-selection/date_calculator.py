#!/usr/bin/env python3
"""
T01 选股系统 - 日期计算模块

替代 Tushare API 的日期计算功能，避免 IP 限制问题
"""

import sys
from datetime import datetime, timedelta
from typing import Optional


def get_previous_trading_day(date: str = None) -> Optional[str]:
    """
    获取上一个交易日
    
    Args:
        date: 日期 YYYYMMDD 格式，默认今天
        
    Returns:
        上一个交易日日期，无则返回None
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')

    try:
        dt = datetime.strptime(date, '%Y%m%d')
        
        # 往回查找最多10天
        for i in range(1, 11):
            prev_dt = dt - timedelta(days=i)
            prev_date = prev_dt.strftime('%Y%m%d')
            
            # 使用简单的工作日判断（周一到周五
            if prev_dt.weekday() < 5:
                # 排除法定节假日（部分常见节假日）
                holiday_list = [
                    '20260101', '20260207', '20260208', '20260209', '20260210', '20260211', '20260212', '20260213',
                    '20260404', '20260405', '20260406', '20260501', '20260502', '20260503', '20260607', '20260608',
                    '20260928', '20260929', '20260930', '20261001', '20261002', '20261003', '20261004', '20261005',
                    '20261006', '20261007'
                ]
                if prev_date not in holiday_list:
                    return prev_date
        
        return None
    except Exception as e:
        print(f"日期计算失败: {e}")
        return None


def is_trading_day(date: str = None) -> bool:
    """
    判断是否为交易日
    
    Args:
        date: 日期 YYYYMMDD 格式，默认今天
        
    Returns:
        是否为交易日
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    try:
        dt = datetime.strptime(date, '%Y%m%d')
        
        # 判断是否为工作日
        if dt.weekday() >= 5:
            return False
        
        # 判断是否为法定节假日
        holiday_list = [
            '20260101', '20260207', '20260208', '20260209', '20260210', '20260211', '20260212', '20260213',
            '20260404', '20260405', '20260406', '20260501', '20260502', '20260503', '20260607', '20260608',
            '20260928', '20260929', '20260930', '20261001', '20261002', '20261003', '20261004', '20261005',
            '20261006', '20261007'
        ]
        
        return date not in holiday_list
        
    except Exception as e:
        print(f"判断交易日失败: {e}")
        return False


def get_trading_days_range(start_date: str, end_date: str) -> list:
    """
    获取日期范围内的交易日列表
    
    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        
    Returns:
        交易日列表
    """
    try:
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        trading_days = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            current_date = current_dt.strftime('%Y%m%d')
            if is_trading_day(current_date):
                trading_days.append(current_date)
            current_dt += timedelta(days=1)
        
        return trading_days
        
    except Exception as e:
        print(f"获取交易日范围失败: {e}")
        return []


if __name__ == '__main__':
    # 测试
    today = datetime.now().strftime('%Y%m%d')
    print(f"今天: {today}")
    print(f"是否交易日: {is_trading_day(today)}")
    
    prev_day = get_previous_trading_day(today)
    print(f"上一交易日: {prev_day}")
    
    # 测试日期范围
    start = '20260401'
    end = '20260410'
    print(f"{start} 到 {end} 的交易日: {get_trading_days_range(start, end)}")