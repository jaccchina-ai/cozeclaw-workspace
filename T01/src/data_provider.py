"""
T01 龙头选股策略 - 数据获取模块
负责从各数据源获取股票数据
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, List

class DataProvider:
    """数据提供器基类"""
    
    def __init__(self):
        self.name = "BaseProvider"
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        raise NotImplementedError
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表"""
        raise NotImplementedError
    
    def get_limit_up_stocks(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取涨停股票列表"""
        raise NotImplementedError


class TushareProvider(DataProvider):
    """Tushare数据源"""
    
    def __init__(self, token: str):
        super().__init__()
        self.name = "Tushare"
        self.token = token
        self.pro = None
        self._init_connection()
    
    def _init_connection(self):
        """初始化Tushare连接"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            print(f"✅ Tushare连接成功")
        except ImportError:
            print("⚠️ 请先安装tushare: pip install tushare")
        except Exception as e:
            print(f"❌ Tushare连接失败: {e}")
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        if not self.pro:
            return None
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            print(f"获取数据失败 {ts_code}: {e}")
            return None
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表"""
        if not self.pro:
            return None
        try:
            df = self.pro.stock_basic(exchange='', list_status='L')
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return None
    
    def get_limit_up_stocks(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取涨停股票列表"""
        if not self.pro:
            return None
        try:
            df = self.pro.limit_list(trade_date=trade_date)
            return df
        except Exception as e:
            print(f"获取涨停列表失败: {e}")
            return None

    def get_money_flow(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取主力资金流向数据"""
        if not self.pro:
            return None
        try:
            df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            print(f"获取主力资金流向失败 {ts_code}: {e}")
            return None

    def get_top_list(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取龙虎榜数据"""
        if not self.pro:
            return None
        try:
            df = self.pro.top_list(trade_date=trade_date)
            return df
        except Exception as e:
            print(f"获取龙虎榜数据失败: {e}")
            return None


class AKShareProvider(DataProvider):
    """AKShare数据源 (备用)"""
    
    def __init__(self):
        super().__init__()
        self.name = "AKShare"
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        try:
            import akshare as ak
            # AKShare格式转换
            symbol = ts_code.split('.')[0]
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                    start_date=start_date, end_date=end_date)
            return df
        except ImportError:
            print("⚠️ 请先安装akshare: pip install akshare")
            return None
        except Exception as e:
            print(f"获取数据失败 {ts_code}: {e}")
            return None
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot()
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return None


class DataManager:
    """数据管理器 - 统一接口"""
    
    def __init__(self, primary_provider: DataProvider, backup_provider: Optional[DataProvider] = None):
        self.primary = primary_provider
        self.backup = backup_provider
    
    def get_data_with_fallback(self, method_name: str, *args, **kwargs):
        """带故障转移的数据获取"""
        result = None
        
        # 尝试主数据源
        try:
            method = getattr(self.primary, method_name)
            result = method(*args, **kwargs)
            if result is not None and not result.empty:
                return result
        except Exception as e:
            print(f"主数据源 {self.primary.name} 失败: {e}")
        
        # 尝试备用数据源
        if self.backup:
            try:
                print(f"切换到备用数据源: {self.backup.name}")
                method = getattr(self.backup, method_name)
                result = method(*args, **kwargs)
            except Exception as e:
                print(f"备用数据源 {self.backup.name} 也失败: {e}")
        
        return result
    
    def get_daily_data(self, ts_code: str, start_date: str, end_date: str):
        return self.get_data_with_fallback('get_daily_data', ts_code, start_date, end_date)
    
    def get_stock_list(self):
        return self.get_data_with_fallback('get_stock_list')
    
    def get_limit_up_stocks(self, trade_date: str):
        return self.get_data_with_fallback('get_limit_up_stocks', trade_date)


# ========== 便捷函数 ==========

def create_default_manager(token: str = None) -> DataManager:
    """创建默认数据管理器"""
    # 主数据源: Tushare
    tushare = TushareProvider(token or "your_token_here")
    
    # 备用数据源: AKShare
    akshare = AKShareProvider()
    
    return DataManager(tushare, akshare)


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("T01 数据获取模块测试")
    print("=" * 50)
    
    # 创建数据管理器
    dm = create_default_manager()
    
    # 测试获取股票列表
    print("\n📊 测试获取股票列表...")
    stocks = dm.get_stock_list()
    if stocks is not None:
        print(f"✅ 获取到 {len(stocks)} 只股票")
        print(stocks.head())
    else:
        print("❌ 获取股票列表失败")
    
    # 测试获取日线数据
    print("\n📈 测试获取日线数据...")
    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    df = dm.get_daily_data("000001.SZ", start, today)
    if df is not None:
        print(f"✅ 获取到 {len(df)} 条数据")
        print(df.head())
    else:
        print("❌ 获取日线数据失败")
