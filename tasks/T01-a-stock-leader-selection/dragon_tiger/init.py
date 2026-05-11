#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜模块初始化脚本
功能：创建数据库表，初始化游资席位数据等
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base
from database.models import create_engine, get_database_url, get_engine_kwargs
from dragon_tiger.models import DragonTigerRecord, DragonTigerDetail
import logging

logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库表"""
    try:
        # 创建龙虎榜相关表
        engine = create_engine(get_database_url(), **get_engine_kwargs())
        DragonTigerRecord.__table__.create(bind=engine, checkfirst=True)
        DragonTigerDetail.__table__.create(bind=engine, checkfirst=True)
        logger.info("龙虎榜数据库表创建成功")
        return True
    except Exception as e:
        logger.error(f"创建龙虎榜数据库表失败: {e}")
        return False

def init_hot_money_seats():
    """初始化游资席位数组"""
    # 这部分数据已经集成在DragonTigerAnalyzer类中
    # 这里可以添加从数据库或配置文件加载游资席位的逻辑
    logger.info("游资席位数组初始化完成")
    return True

def main():
    """主初始化函数"""
    logger.info("开始初始化龙虎榜模块...")
    
    # 初始化数据库
    if not init_database():
        logger.error("数据库初始化失败")
        return False
    
    # 初始化游资席位
    if not init_hot_money_seats():
        logger.error("游资席位初始化失败")
        return False
    
    logger.info("龙虎榜模块初始化成功")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
