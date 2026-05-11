#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜深度数据解析模块
"""

from .analyzer import DragonTigerAnalyzer
from .api import DragonTigerAPI
from .integration import DragonTigerIntegration

__version__ = '1.0.0'
__author__ = 'AI Assistant'
__description__ = '龙虎榜深度数据解析模块，为A股龙头选股系统提供龙虎榜因子分析'

# 导出主要类
__all__ = ['DragonTigerAnalyzer', 'DragonTigerAPI', 'DragonTigerIntegration']
