#!/usr/bin/env python3
"""
Unifuncs 数据同步模块
负责Unifuncs预热结果与选股任务的实时同步
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from logging_config import init_logging, T01Logger

# 初始化日志
LOGGER = T01Logger.get_task_logger('unifuncs_sync')

class UnifuncsSync:
    def __init__(self, config=None):
        self.config = config or {
            'timeout': 1800,  # 默认30分钟超时
            'check_interval': 300,  # 每5分钟检查一次
            'result_path': '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/unifuncs_result.json'
        }
    
    def _load_json_result(self, date):
        """从JSON文件加载Unifuncs结果"""
        try:
            with open(self.config['result_path'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(date, None)
        except FileNotFoundError:
            LOGGER.warning(f"Unifuncs结果文件未找到: {self.config['result_path']}")
            return None
        except json.JSONDecodeError:
            LOGGER.error(f"Unifuncs结果文件格式错误")
            return None
            
    def get_unifuncs_status(self, date):
        """获取Unifuncs预热任务状态"""
        result = self._load_json_result(date)
        if not result:
            return "not_started"
        return result.get('status', 'unknown')
        
    def wait_for_completion(self, date):
        """等待Unifuncs预热任务完成"""
        LOGGER.info(f"等待Unifuncs预热任务完成，日期: {date}")
        start_time = time.time()
        
        while time.time() - start_time < self.config['timeout']:
            status = self.get_unifuncs_status(date)
            
            if status == "completed":
                LOGGER.info("Unifuncs预热任务已完成")
                return True
            elif status == "failed":
                LOGGER.error("Unifuncs预热任务失败")
                return False
            elif status == "timeout":
                LOGGER.error("Unifuncs预热任务超时")
                return False
            elif status == "not_started":
                LOGGER.info("Unifuncs预热任务尚未开始")
            
            time.sleep(self.config['check_interval'])
            
        LOGGER.error("等待Unifuncs预热任务超时")
        return False
    
    def sync_results(self, date):
        """同步Unifuncs推荐结果"""
        result = self._load_json_result(date)
        if not result or result['status'] != 'completed':
            LOGGER.error("无法同步未完成的Unifuncs结果")
            return None
            
        # 提取推荐数据
        recommendations = result.get('recommendations', [])
        LOGGER.info(f"成功同步{len(recommendations)}条Unifuncs推荐结果")
        
        # 转换数据格式
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                'ts_code': self._format_code(rec['code']),
                'name': rec.get('name', ''),
                'consecutive_boards': rec.get('consecutive_boards', 0),
                'probability': rec.get('probability', ''),
                'reason': rec.get('reason', ''),
                'rank': rec.get('rank', 0)
            })
            
        return formatted_recommendations
    
    def _format_code(self, code):
        """格式化股票代码（如601606 -> 601606.SH）"""
        if isinstance(code, str):
            if code.startswith('6'):  # 沪市A股
                return f"{code}.SH"
            elif code.startswith('0'):  # 深市A股
                return f"{code}.SZ"
            elif code.startswith('3'):  # 创业板
                return f"{code}.SZ"
        return code
    
    def save_to_database(self, recommendations, date):
        """保存推荐结果到SQLite数据库"""
        try:
            from database.models import init_db, get_sqlite_manager
            
            manager = get_sqlite_manager()
            saved_count = 0
            
            for rec in recommendations:
                data = {
                    'ts_code': rec['ts_code'],
                    'stock_name': rec['name'],
                    'trade_date': date,
                    'unifuncs_rank': rec['rank'],
                    'unifuncs_probability': rec['probability'],
                    'unifuncs_reason': rec['reason']
                }
                success = manager.save_unifuncs_recommendation(data)
                if success:
                    saved_count += 1
                    
            LOGGER.info(f"成功保存{saved_count}条Unifuncs推荐结果到数据库")
            return True
        except Exception as e:
            LOGGER.error(f"保存Unifuncs推荐结果失败: {e}")
            return False


def main():
    """命令行测试"""
    sync = UnifuncsSync()
    today = datetime.now().strftime('%Y%m%d')
    
    print(f"=== Unifuncs同步测试: {today} ===")
    status = sync.get_unifuncs_status(today)
    print(f"当前状态: {status}")
    
    if status == "completed":
        results = sync.sync_results(today)
        if results:
            print(f"同步结果数量: {len(results)}")
            for rec in results[:3]:
                print(f"{rec['ts_code']} {rec['name']} - {rec['reason']}")
    elif status == "running":
        print("任务正在运行中...")
    else:
        print("任务尚未完成或未开始")


if __name__ == '__main__':
    main()