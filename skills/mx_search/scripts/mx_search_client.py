#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
妙想资讯搜索 API Client

基于东方财富妙想搜索能力，用于获取涉及时效性信息或特定事件信息的任务。

使用方法:
    from mx_search_client import MxSearchClient
    
    client = MxSearchClient()
    result = client.search("格力电器最新研报")
    print(result)
    
    # 多Key Fallback 模式（自动切换）
    client = MxSearchClient(api_keys=["key1", "key2"])
"""

import os
import sys
import json
import time
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, date


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: str
    secu_list: list
    trunk: str
    raw_response: Optional[Dict[str, Any]] = None


class QuotaManager:
    """
    API 配额管理器 - 追踪每个 Key 的每日使用次数
    
    简单实现：内存存储，适合单进程使用
    如需持久化，可扩展为文件/数据库存储
    """
    
    def __init__(self, quota_per_key: int = 50):
        """
        初始化配额管理器
        
        Args:
            quota_per_key: 每个 Key 的每日配额上限（默认50）
        """
        self.quota_per_key = quota_per_key
        self._usage: Dict[str, Dict] = {}  # {api_key: {"count": int, "date": str}}
    
    def _get_today(self) -> str:
        """获取当前日期字符串"""
        return date.today().isoformat()
    
    def get_remaining(self, api_key: str) -> int:
        """
        获取指定 Key 的剩余配额
        
        Args:
            api_key: API Key
            
        Returns:
            剩余可调用次数
        """
        today = self._get_today()
        key_data = self._usage.get(api_key, {})
        
        # 如果是新的一天，重置计数
        if key_data.get("date") != today:
            return self.quota_per_key
        
        return max(0, self.quota_per_key - key_data.get("count", 0))
    
    def increment(self, api_key: str) -> int:
        """
        增加指定 Key 的使用计数
        
        Args:
            api_key: API Key
            
        Returns:
            当前已使用次数
        """
        today = self._get_today()
        
        if api_key not in self._usage or self._usage[api_key].get("date") != today:
            self._usage[api_key] = {"count": 0, "date": today}
        
        self._usage[api_key]["count"] += 1
        return self._usage[api_key]["count"]
    
    def is_available(self, api_key: str) -> bool:
        """
        检查指定 Key 是否还有剩余配额
        
        Args:
            api_key: API Key
            
        Returns:
            是否有剩余配额
        """
        return self.get_remaining(api_key) > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有 Key 的配额统计"""
        today = self._get_today()
        stats = {}
        for key, data in self._usage.items():
            # 脱敏显示 Key
            masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
            if data.get("date") == today:
                remaining = self.quota_per_key - data.get("count", 0)
                stats[masked_key] = {
                    "used": data.get("count", 0),
                    "remaining": max(0, remaining),
                    "total": self.quota_per_key
                }
        return stats


class MxSearchError(Exception):
    """妙想搜索 API 错误"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class MxSearchClient:
    """
    妙想资讯搜索 API 客户端（支持多 Key Fallback）
    
    Attributes:
        api_keys: API 密钥列表
        base_url: API 基础 URL
        timeout: 默认超时时间（秒）
        quota_manager: 配额管理器
        current_key_index: 当前使用的 Key 索引
        min_request_interval: 最小请求间隔（秒）
        last_request_time: 上次请求时间戳
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        base_url: str = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search",
        timeout: int = 30,
        quota_per_key: int = 50,
        min_request_interval: float = 1.2  # 默认1.2秒间隔，避免频率限制
    ):
        """
        初始化客户端
        
        Args:
            api_key: 单个 API 密钥（兼容旧版，优先级低于 api_keys）
            api_keys: API 密钥列表（支持多 Key 轮询）
            base_url: API 基础 URL
            timeout: 默认超时时间
            quota_per_key: 每个 Key 的每日配额上限
            min_request_interval: 最小请求间隔（秒），避免触发频率限制
        """
        self.base_url = base_url
        self.timeout = timeout
        self.quota_manager = QuotaManager(quota_per_key)
        self.current_key_index = 0
        self.min_request_interval = min_request_interval
        self.last_request_time = 0
        
        # 构建 api_keys 列表
        keys = []
        
        # 1. 优先使用传入的 api_keys 列表
        if api_keys:
            keys.extend(api_keys)
        
        # 2. 兼容旧版：从 api_key 参数获取
        if api_key:
            keys.append(api_key)
        
        # 3. 从环境变量获取（支持 MX_APIKEYS 逗号分隔，或 MX_APIKEY 单个）
        env_keys = os.environ.get('MX_APIKEYS', '')
        if env_keys:
            # 支持逗号、分号、空格分隔
            import re
            keys.extend([k.strip() for k in re.split(r'[,;\s]+', env_keys) if k.strip()])
        else:
            env_key = os.environ.get('MX_APIKEY', '')
            if env_key:
                keys.append(env_key)
        
        # 去重并保持顺序
        seen = set()
        self.api_keys = []
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                self.api_keys.append(k)
        
        if not self.api_keys:
            print("⚠️ 警告: 未配置 API Key，搜索功能将不可用")
        else:
            masked = [f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "***" for k in self.api_keys]
            print(f"✅ 已加载 {len(self.api_keys)} 个 API Key: {', '.join(masked)}")
    
    def _get_available_key(self) -> Optional[str]:
        """
        获取一个可用的 API Key（按顺序轮询）
        
        Returns:
            可用的 API Key，如果没有则返回 None
        """
        if not self.api_keys:
            return None
        
        # 从当前索引开始轮询
        for i in range(len(self.api_keys)):
            idx = (self.current_key_index + i) % len(self.api_keys)
            key = self.api_keys[idx]
            
            if self.quota_manager.is_available(key):
                self.current_key_index = idx
                return key
        
        return None
    
    def _is_rate_limit_error(self, error: MxSearchError) -> bool:
        """
        检查错误是否由频率限制导致
        
        Args:
            error: 搜索错误
            
        Returns:
            是否是频率限制错误
        """
        error_msg = error.message.lower()
        
        # 检查常见的频率限制指示
        rate_limit_indicators = [
            'rate',
            'frequency',
            '429',
            'too many',
            'throttle',
            '频率',
            '请求过快',
            '请求过于频繁',
            '稍后再试',
            'rate limit',
            'quota exceeded'
        ]
        
        # 检查 HTTP 429 状态码
        if error.status_code == 429:
            return True
        
        # 检查错误消息
        return any(indicator in error_msg for indicator in rate_limit_indicators)

    def _is_quota_exceeded(self, error: MxSearchError) -> bool:
        """
        检查错误是否由配额超限导致

        Args:
            error: 搜索错误

        Returns:
            是否是配额超限错误
        """
        error_msg = error.message.lower()

        # 检查常见的配额超限指示
        quota_indicators = [
            'quota',
            'limit',
            '429',
            'exceed',
            '配额',
            '超限',
            '限制',
            '次数已达',
            '调用次数'
        ]

        # 检查 HTTP 429 状态码
        if error.status_code == 429:
            return True

        # 检查错误消息
        return any(indicator in error_msg for indicator in quota_indicators)
    
    def search(self, query: str, timeout: Optional[int] = None, retry_on_quota: bool = True, retry_on_rate_limit: bool = True) -> Dict[str, Any]:
        """
        搜索金融资讯（支持自动 Fallback 和频率限制保护）
        
        Args:
            query: 搜索问句
            timeout: 超时时间（秒），默认使用初始化时的设置
            retry_on_quota: 配额超限时是否自动切换 Key 重试
            retry_on_rate_limit: 频率限制时是否自动重试
            
        Returns:
            搜索结果字典
            
        Raises:
            MxSearchError: API 调用失败且所有 Key 都不可用
        """
        if not self.api_keys:
            raise MxSearchError("未配置 API Key，请设置环境变量 MX_APIKEY 或 MX_APIKEYS")
        
        # 频率控制：确保请求间隔不小于最小间隔
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        # 记录已尝试的 Key，避免无限循环
        attempted_keys = set()
        rate_limit_retries = 0
        max_rate_limit_retries = 3  # 频率限制最大重试次数
        
        while True:
            # 获取一个可用 Key
            api_key = self._get_available_key()
            
            if api_key is None:
                # 所有 Key 都已耗尽配额
                raise MxSearchError(
                    f"所有 API Key 配额已耗尽（每Key每日{self.quota_manager.quota_per_key}次）。"
                    f"配额统计: {json.dumps(self.quota_manager.get_stats(), ensure_ascii=False)}"
                )
            
            if api_key in attempted_keys:
                # 已经尝试过这个 Key，说明其他 Key 都失败了
                break
            
            attempted_keys.add(api_key)
            
            try:
                # 执行搜索
                result = self._do_search(api_key, query, timeout)
                
                # 成功，增加配额计数
                self.quota_manager.increment(api_key)
                self.last_request_time = time.time()
                
                # 添加配额信息到结果
                remaining = self.quota_manager.get_remaining(api_key)
                result['_meta'] = {
                    'api_key_masked': f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***",
                    'quota_remaining': remaining,
                    'quota_total': self.quota_manager.quota_per_key
                }
                
                return result
                
            except MxSearchError as e:
                # 检查是否是频率限制错误
                if retry_on_rate_limit and self._is_rate_limit_error(e):
                    rate_limit_retries += 1
                    if rate_limit_retries <= max_rate_limit_retries:
                        sleep_time = 2 ** rate_limit_retries  # 指数退避：2, 4, 8秒
                        print(f"⚠️ 频率限制，等待 {sleep_time} 秒后重试 ({rate_limit_retries}/{max_rate_limit_retries})...")
                        time.sleep(sleep_time)
                        # 重置尝试记录，允许重试当前Key
                        attempted_keys.discard(api_key)
                        continue
                
                # 检查是否是配额超限错误
                if retry_on_quota and self._is_quota_exceeded(e):
                    # 标记此 Key 配额已耗尽（强制设为最大值）
                    self.quota_manager._usage[api_key] = {
                        "count": self.quota_manager.quota_per_key,
                        "date": self.quota_manager._get_today()
                    }
                    print(f"⚠️ Key {api_key[:6]}... 配额超限，尝试切换...")
                    continue  # 尝试下一个 Key
                else:
                    # 其他错误，直接抛出
                    raise
        
        # 所有 Key 都尝试过了
        raise MxSearchError("所有 API Key 调用失败")
    
    def get_quota_stats(self) -> Dict[str, Any]:
        """
        获取当前配额使用统计
        
        Returns:
            配额统计信息，包括每个 Key 的使用情况
        """
        return {
            'total_keys': len(self.api_keys),
            'quota_per_key': self.quota_manager.quota_per_key,
            'key_stats': self.quota_manager.get_stats(),
            'total_remaining': sum(
                self.quota_manager.get_remaining(k) for k in self.api_keys
            )
        }
    
    def _do_search(self, api_key: str, query: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        实际执行搜索请求（内部方法）
        
        Args:
            api_key: API Key
            query: 搜索问句
            timeout: 超时时间
            
        Returns:
            搜索结果
            
        Raises:
            MxSearchError: API 调用失败
        """
        headers = {
            'Content-Type': 'application/json',
            'apikey': api_key
        }
        
        payload = {
            'query': query
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=timeout or self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # 检查外层状态
            if data.get('status') != 0:
                raise MxSearchError(
                    f"API 错误: {data.get('message', '未知错误')}",
                    response=data
                )
            
            # 解析嵌套数据结构
            inner_data = data.get('data', {})
            if inner_data.get('code') != 0:
                raise MxSearchError(
                    f"搜索失败: {inner_data.get('message', '未知错误')}",
                    response=inner_data
                )
            
            # 获取搜索结果数据 (在 llmSearchResponse.data 中)
            llm_response = inner_data.get('data', {})
            search_results = llm_response.get('llmSearchResponse', {}).get('data', [])
            
            return {
                'results': search_results,
                'request_id': inner_data.get('requestId'),
                'trace_id': llm_response.get('traceId'),
                'raw': llm_response
            }
            
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            raise MxSearchError(
                f"HTTP 错误: {e.response.status_code} - {error_data.get('message', str(e))}",
                status_code=e.response.status_code,
                response=error_data
            )
        except requests.exceptions.Timeout:
            raise MxSearchError(f"请求超时（{timeout or self.timeout}秒）")
        except requests.exceptions.RequestException as e:
            raise MxSearchError(f"网络请求失败: {str(e)}")
    
    def search_stock(self, stock_name: str, info_type: str = "最新研报") -> Dict[str, Any]:
        """
        搜索个股资讯
        
        Args:
            stock_name: 股票名称
            info_type: 资讯类型（如：最新研报、机构观点、新闻等）
            
        Returns:
            搜索结果
        """
        query = f"{stock_name}{info_type}"
        return self.search(query)
    
    def search_sector(self, sector_name: str, info_type: str = "近期新闻") -> Dict[str, Any]:
        """
        搜索板块资讯
        
        Args:
            sector_name: 板块名称
            info_type: 资讯类型（如：近期新闻、政策解读等）
            
        Returns:
            搜索结果
        """
        query = f"{sector_name}{info_type}"
        return self.search(query)
    
    def search_macro(self, topic: str) -> Dict[str, Any]:
        """
        搜索宏观资讯
        
        Args:
            topic: 宏观主题（如：美联储加息对A股影响）
            
        Returns:
            搜索结果
        """
        return self.search(topic)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='妙想资讯搜索')
    parser.add_argument('--query', '-q', type=str, required=True, help='搜索问句')
    parser.add_argument('--api-key', type=str, default=None, help='API Key（可选，默认从环境变量读取）')
    parser.add_argument('--timeout', type=int, default=30, help='超时时间（秒）')
    parser.add_argument('--output', '-o', type=str, default=None, help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    try:
        client = MxSearchClient(api_key=args.api_key, timeout=args.timeout)
        result = client.search(args.query)
        
        # 格式化输出
        output = json.dumps(result, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✅ 结果已保存到: {args.output}")
        else:
            print(output)
            
    except MxSearchError as e:
        print(f"❌ 错误: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
