#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unifuncs Deep Research API Client

用于调用 Unifuncs 深度研究 API，获取 A 股市场分析报告。

使用方法:
    from unifuncs_client import UnifuncsClient
    
    client = UnifuncsClient()
    result = client.get_report("今天A股热门板块哪几个？")
    print(result)
"""

import os
import time
import json
import requests
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass


@dataclass
class TaskResult:
    """任务结果数据类"""
    task_id: str
    status: str
    summary: Optional[str] = None
    answer: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class UnifuncsError(Exception):
    """Unifuncs API 错误"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class UnifuncsClient:
    """
    Unifuncs Deep Research API 客户端
    
    Attributes:
        api_key: API 密钥
        base_url: API 基础 URL
        default_model: 默认模型
        default_timeout: 默认超时时间（秒）
        default_poll_interval: 默认轮询间隔（秒）
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.unifuncs.com/deepresearch",
        default_model: str = "u2",
        default_timeout: int = 120,
        default_poll_interval: float = 3.0
    ):
        """
        初始化客户端
        
        Args:
            api_key: API 密钥，如不提供则使用默认值
            base_url: API 基础 URL
            default_model: 默认模型
            default_timeout: 默认超时时间
            default_poll_interval: 默认轮询间隔
        """
        self.api_key = api_key or "sk-gCxXKluzZeZEjUvvyc35efFBjOa6SUcR7gDDG9giUPG3Aetg"
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.default_timeout = default_timeout
        self.default_poll_interval = default_poll_interval
        
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_task(
        self,
        output_prompt: str,
        model: Optional[str] = None,
        output_type: Literal["summary", "full"] = "summary",
        reference_style: Literal["hidden", "visible"] = "hidden",
        messages: Optional[list] = None
    ) -> str:
        """
        创建研究任务
        
        Args:
            output_prompt: 研究问题/提示词
            model: 模型类型，默认使用 default_model
            output_type: 输出类型，summary 或 full
            reference_style: 引用风格，hidden 或 visible
            messages: 自定义消息数组，如不提供则自动构建
            
        Returns:
            task_id: 任务 ID
            
        Raises:
            UnifuncsError: API 调用失败
        """
        url = f"{self.base_url}/v1/create_task"
        
        if messages is None:
            messages = [{"role": "user", "content": "hi"}]
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "output_type": output_type,
            "output_prompt": output_prompt,
            "reference_style": reference_style
        }
        
        try:
            response = requests.post(url, headers=self._headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 处理嵌套的 data 字段
            if "data" in data:
                data = data["data"]
            
            if "task_id" not in data:
                raise UnifuncsError(
                    f"创建任务失败：响应中缺少 task_id，响应内容: {data}",
                    response=response.json()
                )
            
            return data["task_id"]
            
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            raise UnifuncsError(
                f"HTTP 错误: {e.response.status_code} - {error_data.get('message', str(e))}",
                status_code=e.response.status_code,
                response=error_data
            )
        except requests.exceptions.RequestException as e:
            raise UnifuncsError(f"网络请求失败: {str(e)}")
    
    def query_task(self, task_id: str) -> TaskResult:
        """
        查询任务状态和结果
        
        Args:
            task_id: 任务 ID
            
        Returns:
            TaskResult: 任务结果对象
            
        Raises:
            UnifuncsError: API 调用失败
        """
        url = f"{self.base_url}/v1/query_task"
        params = {"task_id": task_id}
        
        try:
            response = requests.get(url, headers=self._headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 处理嵌套的 data 字段
            if "data" in data:
                data = data["data"]
            
            status = data.get("status", "unknown")
            result = TaskResult(
                task_id=task_id,
                status=status,
                raw_response=data
            )
            
            if status == "completed":
                # 结果可能在 result 字段或直接在 data 中
                result_data = data.get("result", data)
                result.summary = result_data.get("summary")
                result.answer = result_data.get("answer") or result_data.get("output") or result_data.get("content")
            elif status == "failed":
                result.error = data.get("error") or data.get("message", "任务执行失败")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            raise UnifuncsError(
                f"HTTP 错误: {e.response.status_code} - {error_data.get('message', str(e))}",
                status_code=e.response.status_code,
                response=error_data
            )
        except requests.exceptions.RequestException as e:
            raise UnifuncsError(f"网络请求失败: {str(e)}")
    
    def get_report(
        self,
        output_prompt: str,
        timeout: Optional[int] = None,
        poll_interval: Optional[float] = None,
        **create_kwargs
    ) -> TaskResult:
        """
        一键获取研究报告（创建任务 + 轮询结果）
        
        Args:
            output_prompt: 研究问题/提示词
            timeout: 超时时间（秒），默认使用 default_timeout
            poll_interval: 轮询间隔（秒），默认使用 default_poll_interval
            **create_kwargs: 传递给 create_task 的其他参数
            
        Returns:
            TaskResult: 任务结果对象
            
        Raises:
            UnifuncsError: API 调用失败或超时
            TimeoutError: 任务超时
        """
        timeout = timeout or self.default_timeout
        poll_interval = poll_interval or self.default_poll_interval
        
        # 创建任务
        task_id = self.create_task(output_prompt, **create_kwargs)
        print(f"[Unifuncs] 任务已创建: {task_id}")
        
        # 轮询结果
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"任务超时（{timeout}秒）")
            
            result = self.query_task(task_id)
            print(f"[Unifuncs] 状态: {result.status} (已等待 {elapsed:.1f}秒)")
            
            if result.status == "completed":
                return result
            elif result.status == "failed":
                raise UnifuncsError(f"任务失败: {result.error}")
            
            time.sleep(poll_interval)


# 便捷函数
def get_hot_sectors() -> TaskResult:
    """
    获取今日热门板块分析
    
    Returns:
        TaskResult: 包含热门板块分析结果
    """
    client = UnifuncsClient()
    return client.get_report(
        "今天A股热门板块哪几个？请分析各板块的领涨股和资金流向。"
    )


def predict_limit_up_stocks() -> TaskResult:
    """
    预测涨停股连板概率
    
    Returns:
        TaskResult: 包含涨停股预测结果
    """
    client = UnifuncsClient()
    return client.get_report(
        "所有涨停股中，哪3个涨停股在下一个交易日继续涨停的概率最大？请给出具体理由。"
    )


def analyze_market_sentiment() -> TaskResult:
    """
    分析市场情绪
    
    Returns:
        TaskResult: 包含市场情绪分析结果
    """
    client = UnifuncsClient()
    return client.get_report(
        "请分析今日A股市场情绪，包括北向资金流向、主力资金动向、涨跌停比例，并预测明日市场走势。"
    )


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("Unifuncs Deep Research API 测试")
    print("=" * 50)
    
    try:
        # 创建客户端
        client = UnifuncsClient()
        
        # 测试创建任务
        print("\n[测试1] 创建任务...")
        task_id = client.create_task(
            "今天A股热门板块哪几个？所有涨停股中，哪3个涨停股在下一个交易日继续涨停的概率最大？"
        )
        print(f"任务ID: {task_id}")
        
        # 测试查询任务
        print("\n[测试2] 查询任务...")
        result = client.query_task(task_id)
        print(f"状态: {result.status}")
        
        # 如果需要等待完成
        if result.status not in ["completed", "failed"]:
            print("\n[测试3] 等待任务完成...")
            result = client.get_report(
                "分析今日市场热点",
                timeout=60,
                poll_interval=2
            )
        
        if result.status == "completed":
            print("\n[结果]")
            print(f"摘要: {result.summary}")
            print(f"详情: {result.answer}")
        else:
            print(f"\n任务状态: {result.status}")
            if result.error:
                print(f"错误: {result.error}")
                
    except Exception as e:
        print(f"\n错误: {e}")
