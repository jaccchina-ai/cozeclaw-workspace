#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时初始化脚本"""

from sqlalchemy import create_engine
from database.models import Base
from dragon_tiger.models import DragonTigerRecord, DragonTigerDetail
from database.db_config import get_database_url, get_engine_kwargs

def init_database():
    """初始化数据库表"""
    try:
        # 创建龙虎榜相关表
        engine = create_engine(get_database_url(), **get_engine_kwargs())
        DragonTigerRecord.__table__.create(bind=engine, checkfirst=True)
        DragonTigerDetail.__table__.create(bind=engine, checkfirst=True)
        print("✅ 龙虎榜数据库表创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建龙虎榜数据库表失败: {e}")
        return False

if __name__ == '__main__':
    init_database()
