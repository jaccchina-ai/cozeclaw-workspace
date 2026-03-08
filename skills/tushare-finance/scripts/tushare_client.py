#!/usr/bin/env python3
"""
Tushare Finance Client for OpenClaw
"""

import os
import json
import sys
from pathlib import Path

try:
    import tushare as ts
    import pandas as pd
except ImportError:
    print("Installing required packages...")
    os.system("pip install tushare pandas -q")
    import tushare as ts
    import pandas as pd

# Load configuration
PROJECT_ROOT = Path("/workspace/projects")
TOKEN_FILE = PROJECT_ROOT / ".tushare-token"
CONFIG_FILE = PROJECT_ROOT / ".tushare-config.json"

# Read token
if TOKEN_FILE.exists():
    with open(TOKEN_FILE, 'r') as f:
        TOKEN = f.read().strip()
else:
    print("Error: Tushare token file not found")
    sys.exit(1)

# Initialize Tushare
ts.set_token(TOKEN)
pro = ts.pro_api()

def get_stock_basic(ts_code=None):
    """Get basic stock information"""
    return pro.stock_basic(ts_code=ts_code)

def get_daily(ts_code, start_date=None, end_date=None):
    """Get daily stock data"""
    return pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

def get_realtime_quotes(ts_code):
    """Get real-time quotes"""
    return pro.daily(ts_code=ts_code)

def get_index_basic(market="SSE"):
    """Get index basic information"""
    return pro.index_basic(market=market)

def get_fund_basic(market="E"):
    """Get fund basic information"""
    return pro.fund_basic(market=market)

def get_fund_nav(ts_code):
    """Get fund net value"""
    return pro.fund_nav(ts_code=ts_code)

def get_fina_indicator(ts_code, period=None):
    """Get financial indicators"""
    return pro.fina_indicator(ts_code=ts_code, period=period)

def get_income(ts_code, period=None):
    """Get income statement"""
    return pro.income(ts_code=ts_code, period=period)

if __name__ == "__main__":
    # Test connection
    print("Testing Tushare connection...")
    try:
        basic = get_stock_basic()
        print(f"✓ Connection successful!")
        print(f"  Total stocks: {len(basic)}")
        print(f"  Sample stocks:")
        print(basic.head(10).to_string())
    except Exception as e:
        print(f"✗ Connection failed: {e}")
