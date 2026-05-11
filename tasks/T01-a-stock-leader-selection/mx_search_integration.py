#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 选股系统 - mx_search 集成模块

用于增强选股逻辑，提供：
1. 个股涨停原因查询
2. 板块热点原因查询
3. 风险事件预警

API 配额管理：每天最多50次调用
"""

import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/workspace/projects/workspace/skills/mx_search/scripts')

from mx_search_client import MxSearchClient, MxSearchError


class MxSearchIntegration:
    """mx_search 集成管理器（支持多Key Fallback）"""
    
    # API 配额配置（每Key每日配额）
    QUOTA_PER_KEY = 50
    
    # 多Key配置（支持Fallback）
    # 注意：生产环境应通过环境变量 MX_APIKEYS 配置，格式: "key1,key2"
    API_KEYS = [
        'mkt_sEL_RY2_Fh_NrwkOezNpa9nlc9wtoT5yHZE7W6A7J8s',  # 主Key
        'mkt_m3Bt4TsYCbk52ITqDSni_-fONv9L8lFqMstwmOaLmy8'   # 备用Key
    ]
    
    # 配额分配
    QUOTA_ALLOCATION = {
        'stock_reason': 15,      # 个股涨停原因
        'sector_hot': 10,        # 板块热点原因
        'risk_alert': 10,        # 风险预警
        'buffer': 15             # 预留缓冲
    }
    
    def __init__(self):
        """初始化 mx_search 客户端（多Key模式）"""
        # 过滤空Key
        valid_keys = [k for k in self.API_KEYS if k]
        
        # 优先使用环境变量 MX_APIKEYS（逗号分隔的多Key）
        env_keys = os.environ.get('MX_APIKEYS', '')
        if env_keys:
            import re
            valid_keys = [k.strip() for k in re.split(r'[,;\s]+', env_keys) if k.strip()]
        
        # 初始化多Key客户端
        self.client = MxSearchClient(api_keys=valid_keys, quota_per_key=self.QUOTA_PER_KEY)
        
        # 计算总配额
        self.DAILY_QUOTA = len(valid_keys) * self.QUOTA_PER_KEY if valid_keys else 0
        
        self.usage_log = []  # 记录API调用
        self._init_usage_tracking()
    
    def _init_usage_tracking(self):
        """初始化使用记录"""
        self.usage_file = '/workspace/projects/workspace/logs/mx_search_usage.json'
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, 'r') as f:
                    self.usage_log = json.load(f)
            except:
                self.usage_log = []
    
    def _record_usage(self, query_type: str, query: str, result_count: int):
        """记录API调用"""
        self.usage_log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': query_type,
            'query': query,
            'results': result_count
        })
        
        # 保存到文件
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_log[-100:], f, ensure_ascii=False, indent=2)  # 只保留最近100条
        except:
            pass
    
    def get_daily_usage(self) -> int:
        """获取今日已使用次数"""
        today = datetime.now().strftime('%Y-%m-%d')
        count = sum(1 for log in self.usage_log if log['timestamp'].startswith(today))
        return count
    
    def get_remaining_quota(self) -> int:
        """获取剩余配额（基于客户端配额管理器）"""
        # 使用客户端的配额统计
        stats = self.client.get_quota_stats()
        return stats.get('total_remaining', 0)
    
    def check_quota(self, required: int = 1) -> bool:
        """检查配额是否充足"""
        return self.get_remaining_quota() >= required
    
    def get_stock_limit_reason(self, stock_name: str, stock_code: str = '') -> Dict:
        """
        获取个股涨停原因
        
        Args:
            stock_name: 股票名称
            stock_code: 股票代码（可选）
            
        Returns:
            {
                'has_reason': bool,
                'reason': str,
                'source': str,
                'date': str,
                'institution': str
            }
        """
        if not self.check_quota(1):
            return {
                'has_reason': False,
                'reason': 'API配额不足',
                'source': '',
                'date': '',
                'institution': ''
            }
        
        try:
            # 构建查询
            query = f"{stock_name}涨停原因"
            result = self.client.search(query)
            items = result.get('results', [])
            
            self._record_usage('stock_reason', query, len(items))
            
            if not items:
                return {
                    'has_reason': False,
                    'reason': '未找到涨停原因',
                    'source': '',
                    'date': '',
                    'institution': ''
                }
            
            # 取第一条结果
            first = items[0]
            content = first.get('content', '')
            title = first.get('title', '')
            
            # 提取原因（取内容前200字符作为摘要）
            reason = content[:200] if content else title
            
            return {
                'has_reason': True,
                'reason': reason,
                'source': title,
                'date': first.get('date', ''),
                'institution': first.get('insName', '')
            }
            
        except MxSearchError as e:
            return {
                'has_reason': False,
                'reason': f'查询失败: {e.message}',
                'source': '',
                'date': '',
                'institution': ''
            }
        except Exception as e:
            return {
                'has_reason': False,
                'reason': f'查询异常: {str(e)}',
                'source': '',
                'date': '',
                'institution': ''
            }
    
    def get_sector_hot_reason(self, sector_name: str) -> Dict:
        """
        获取板块热点原因
        
        Args:
            sector_name: 板块名称
            
        Returns:
            {
                'has_reason': bool,
                'reason': str,
                'news_count': int,
                'latest_news': List[Dict]
            }
        """
        if not self.check_quota(1):
            return {
                'has_reason': False,
                'reason': 'API配额不足',
                'news_count': 0,
                'latest_news': []
            }
        
        try:
            # 构建查询
            query = f"{sector_name}板块近期新闻"
            result = self.client.search(query)
            items = result.get('results', [])
            
            self._record_usage('sector_hot', query, len(items))
            
            if not items:
                return {
                    'has_reason': False,
                    'reason': '未找到板块新闻',
                    'news_count': 0,
                    'latest_news': []
                }
            
            # 提取热点原因（取前3条新闻）
            latest_news = []
            for item in items[:3]:
                latest_news.append({
                    'title': item.get('title', ''),
                    'date': item.get('date', ''),
                    'content': item.get('content', '')[:150] + '...' if len(item.get('content', '')) > 150 else item.get('content', '')
                })
            
            # 综合热点原因（取第一条的完整内容）
            hot_reason = items[0].get('content', items[0].get('title', ''))[:300]
            
            return {
                'has_reason': True,
                'reason': hot_reason,
                'news_count': len(items),
                'latest_news': latest_news
            }
            
        except MxSearchError as e:
            return {
                'has_reason': False,
                'reason': f'查询失败: {e.message}',
                'news_count': 0,
                'latest_news': []
            }
        except Exception as e:
            return {
                'has_reason': False,
                'reason': f'查询异常: {str(e)}',
                'news_count': 0,
                'latest_news': []
            }
    
    def check_stock_risk(self, stock_name: str, stock_code: str = '') -> Dict:
        """
        检查个股风险事件
        
        Args:
            stock_name: 股票名称
            stock_code: 股票代码（可选）
            
        Returns:
            {
                'has_risk': bool,
                'risk_type': str,
                'risk_level': str,  # high/medium/low
                'details': str,
                'source': str
            }
        """
        if not self.check_quota(1):
            return {
                'has_risk': False,
                'risk_type': '未知',
                'risk_level': 'low',
                'details': 'API配额不足，无法检测风险',
                'source': ''
            }
        
        try:
            # 构建查询（检查减持、负面新闻等）
            query = f"{stock_name}减持 风险"
            result = self.client.search(query)
            items = result.get('results', [])
            
            self._record_usage('risk_alert', query, len(items))
            
            # 检查是否有风险相关新闻
            risk_keywords = ['减持', '预亏', '暴雷', '违规', '处罚', '立案调查']
            risk_items = []
            
            for item in items:
                title = item.get('title', '')
                content = item.get('content', '')
                text = title + ' ' + content
                
                for keyword in risk_keywords:
                    if keyword in text:
                        risk_items.append({
                            'title': title,
                            'date': item.get('date', ''),
                            'keyword': keyword,
                            'source': item.get('insName', '')
                        })
                        break
            
            if risk_items:
                # 有高风险
                first_risk = risk_items[0]
                return {
                    'has_risk': True,
                    'risk_type': f'发现{first_risk["keyword"]}相关新闻',
                    'risk_level': 'high' if first_risk['keyword'] in ['违规', '处罚', '立案调查'] else 'medium',
                    'details': first_risk['title'],
                    'source': first_risk['source']
                }
            else:
                return {
                    'has_risk': False,
                    'risk_type': '无',
                    'risk_level': 'low',
                    'details': '未发现明显风险事件',
                    'source': ''
                }
                
        except MxSearchError as e:
            return {
                'has_risk': False,
                'risk_type': '未知',
                'risk_level': 'low',
                'details': f'风险检测失败: {e.message}',
                'source': ''
            }
        except Exception as e:
            return {
                'has_risk': False,
                'risk_type': '未知',
                'risk_level': 'low',
                'details': f'风险检测异常: {str(e)}',
                'source': ''
            }
    
    def enhance_t_day_stocks(self, stocks: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        增强T日选股结果（添加涨停原因和风险信息）
        
        Args:
            stocks: 选股结果列表
            top_n: 只对前N只进行增强
            
        Returns:
            增强后的选股结果
        """
        enhanced_stocks = []
        
        for i, stock in enumerate(stocks):
            # 复制原数据
            enhanced = stock.copy()
            
            # 只对前N只查询涨停原因
            if i < top_n and self.check_quota(1):
                reason_info = self.get_stock_limit_reason(
                    stock.get('stock_name', ''),
                    stock.get('ts_code', '')
                )
                enhanced['limit_reason'] = reason_info.get('reason', '')
                enhanced['limit_reason_source'] = reason_info.get('source', '')
            else:
                enhanced['limit_reason'] = ''
                enhanced['limit_reason_source'] = ''
            
            # 检查风险（只对前5只）
            if i < 5 and self.check_quota(1):
                risk_info = self.check_stock_risk(
                    stock.get('stock_name', ''),
                    stock.get('ts_code', '')
                )
                enhanced['risk_alert'] = risk_info.get('has_risk', False)
                enhanced['risk_type'] = risk_info.get('risk_type', '')
                enhanced['risk_details'] = risk_info.get('details', '')
            else:
                enhanced['risk_alert'] = False
                enhanced['risk_type'] = ''
                enhanced['risk_details'] = ''
            
            enhanced_stocks.append(enhanced)
        
        return enhanced_stocks
    
    def enhance_sector_heat(self, sectors: List[Dict]) -> List[Dict]:
        """
        增强板块热度信息（添加热点原因）
        
        Args:
            sectors: 板块列表
            
        Returns:
            增强后的板块列表
        """
        enhanced_sectors = []
        
        for sector in sectors:
            enhanced = sector.copy()
            
            # 查询板块热点原因（只查询前3个板块）
            if len(enhanced_sectors) < 3 and self.check_quota(1):
                hot_info = self.get_sector_hot_reason(sector.get('sector_name', ''))
                enhanced['hot_reason'] = hot_info.get('reason', '')
                enhanced['hot_news_count'] = hot_info.get('news_count', 0)
                enhanced['hot_news'] = hot_info.get('latest_news', [])
            else:
                enhanced['hot_reason'] = ''
                enhanced['hot_news_count'] = 0
                enhanced['hot_news'] = []
            
            enhanced_sectors.append(enhanced)
        
        return enhanced_sectors
    
    def get_usage_report(self) -> Dict:
        """获取使用报告"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_usage = [log for log in self.usage_log if log['timestamp'].startswith(today)]
        
        type_count = {}
        for log in today_usage:
            t = log['type']
            type_count[t] = type_count.get(t, 0) + 1
        
        # 获取客户端配额统计
        quota_stats = self.client.get_quota_stats()
        
        return {
            'total_keys': quota_stats.get('total_keys', 0),
            'quota_per_key': quota_stats.get('quota_per_key', 50),
            'total_quota': quota_stats.get('total_keys', 0) * quota_stats.get('quota_per_key', 50),
            'used_today': len(today_usage),
            'remaining': quota_stats.get('total_remaining', 0),
            'by_type': type_count,
            'key_stats': quota_stats.get('key_stats', {}),
            'usage_rate': f"{len(today_usage)/self.DAILY_QUOTA*100:.1f}%" if self.DAILY_QUOTA > 0 else "N/A"
        }


# 便捷函数
def get_mx_search_client() -> MxSearchIntegration:
    """获取 mx_search 集成客户端"""
    return MxSearchIntegration()


if __name__ == '__main__':
    # 测试代码
    print("="*60)
    print("mx_search 集成模块测试（多Key Fallback模式）")
    print("="*60)
    
    mx = MxSearchIntegration()
    
    # 检查配额
    report = mx.get_usage_report()
    print(f"\n📊 API 配额报告:")
    print(f"  Key数量: {report['total_keys']}")
    print(f"  每Key配额: {report['quota_per_key']}")
    print(f"  总配额: {report['total_quota']}")
    print(f"  今日已用: {report['used_today']}")
    print(f"  剩余: {report['remaining']}")
    print(f"  使用率: {report['usage_rate']}")
    print(f"  Key详情: {report['key_stats']}")
    
    # 显示Fallback模式说明
    print(f"\n✅ 多Key Fallback已启用")
    print(f"   当主Key配额耗尽时将自动切换到备用Key")
    
    # 测试搜索（如果有配额）
    if mx.check_quota(1):
        print("\n可以正常使用mx_search功能")
    else:
        print("\n⚠️ 所有Key配额已耗尽")
        print("\n测试: 格力电器风险检测")
        result = mx.check_stock_risk('格力电器')
        print(f"  有风险: {result['has_risk']}")
        print(f"  风险类型: {result['risk_type']}")
        if result['has_risk']:
            print(f"  详情: {result['details']}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
