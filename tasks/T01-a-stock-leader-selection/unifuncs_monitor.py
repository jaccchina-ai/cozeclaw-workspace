#!/usr/bin/env python3
"""
Unifuncs集成监控模块
实时监控Unifuncs预热任务状态、API调用情况和匹配效果
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# 初始化日志
LOGGER = logging.getLogger('unifuncs_monitor')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class MonitorStats:
    """监控统计数据"""
    task_status: str = "unknown"
    api_calls: int = 0
    api_success_rate: float = 0.0
    match_rate: float = 0.0
    average_match_score: float = 0.0
    error_count: int = 0
    warnings_count: int = 0

class UnifuncsMonitor:
    def __init__(self, config=None):
        self.config = config or {
            'enabled': True,
            'alert_threshold': 0.5,  # 匹配度低于此值时告警
            'error_threshold': 3,  # 连续错误数超过此值时告警
            'check_interval': 3600,  # 每小时检查一次
            'alert_channel': 'feishu',
            'max_retries': 3
        }
        self.error_history = []
    
    def _get_task_status(self, date=None):
        """获取Unifuncs预热任务状态"""
        try:
            from unifuncs_sync import UnifuncsSync
            sync = UnifuncsSync()
            target_date = date or datetime.now().strftime('%Y%m%d')
            return sync.get_unifuncs_status(target_date)
        except Exception as e:
            LOGGER.error(f"获取任务状态失败: {e}")
            return "error"
    
    def _get_api_stats(self):
        """获取API调用统计"""
        try:
            # 从数据库或日志文件统计API调用情况
            # 这里仅做示例，实际需要根据实现调整
            return {
                'total_calls': 0,
                'success_calls': 0,
                'error_calls': 0
            }
        except Exception as e:
            LOGGER.error(f"获取API统计失败: {e}")
            return {'total_calls': 0, 'success_calls': 0, 'error_calls': 0}
    
    def _get_match_stats(self, date=None):
        """获取匹配效果统计"""
        try:
            from database.models import init_db, get_sqlite_manager
            manager = get_sqlite_manager()
            target_date = date or datetime.now().strftime('%Y%m%d')
            
            # 从数据库查询匹配统计
            stats = manager.get_unifuncs_match_stats(target_date)
            
            if stats:
                return {
                    'recommended_count': stats.get('recommended_count', 0),
                    'matched_count': stats.get('matched_count', 0),
                    'average_match_score': stats.get('average_match_score', 0.0)
                }
            else:
                # 未查询到数据，默认返回空
                return {
                    'recommended_count': 0,
                    'matched_count': 0,
                    'average_match_score': 0.0
                }
        except Exception as e:
            LOGGER.error(f"获取匹配统计失败: {e}")
            return {'recommended_count': 0, 'matched_count': 0, 'average_match_score': 0.0}
    
    def check_health(self, date=None) -> MonitorStats:
        """执行健康检查"""
        LOGGER.info("执行Unifuncs集成健康检查")
        
        stats = MonitorStats()
        
        # 任务状态检查
        stats.task_status = self._get_task_status(date)
        
        # API调用统计
        api_stats = self._get_api_stats()
        stats.api_calls = api_stats['total_calls']
        if api_stats['total_calls'] > 0:
            stats.api_success_rate = api_stats['success_calls'] / api_stats['total_calls'] * 100
        
        # 匹配效果统计
        match_stats = self._get_match_stats(date)
        if match_stats['recommended_count'] > 0:
            stats.match_rate = match_stats['matched_count'] / match_stats['recommended_count'] * 100
            stats.average_match_score = match_stats['average_match_score']
        
        # 错误历史
        if stats.task_status == 'failed' or stats.api_success_rate < 80:
            self.error_history.append(datetime.now())
        else:
            self.error_history.clear()
            
        return stats
    
    def generate_report(self, stats: MonitorStats) -> str:
        """生成健康检查报告"""
        report = ["Unifuncs集成健康检查报告", "="*40]
        report.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"任务状态: {stats.task_status}")
        report.append(f"API调用统计: {stats.api_calls}次，成功率: {stats.api_success_rate:.1f}%")
        report.append(f"匹配效果: 推荐{stats.match_rate:.1f}%命中，平均匹配度: {stats.average_match_score:.3f}")
        report.append(f"错误计数: {stats.error_count}")
        report.append(f"告警计数: {stats.warnings_count}")
        
        # 健康评估
        if stats.task_status == 'completed' and stats.match_rate >= self.config['alert_threshold']:
            report.append("\n✅ 健康状态: 良好")
        elif stats.task_status == 'completed' and stats.match_rate < self.config['alert_threshold']:
            report.append("\n⚠️ 健康状态: 匹配度较低")
        elif stats.task_status == 'failed' or stats.task_status == 'timeout':
            report.append("\n🚨 健康状态: 任务失败")
        else:
            report.append("\nℹ️ 健康状态: 任务未完成")
            
        return "\n".join(report)
    
    def send_alert(self, stats: MonitorStats):
        """发送告警通知"""
        try:
            from messenger import get_messenger
            messenger = get_messenger()
            
            if stats.task_status == 'failed':
                message = f"⚠️ Unifuncs预热任务失败\n日期: {datetime.now().strftime('%Y%m%d')}"
                messenger.send_text(message)
            elif stats.match_rate < self.config['alert_threshold'] and stats.match_rate > 0:
                message = f"⚠️ Unifuncs推荐匹配度过低\n当前匹配率: {stats.match_rate:.1f}%\n阈值: {self.config['alert_threshold']*100:.1f}%"
                messenger.send_text(message)
            elif stats.api_success_rate < 80 and stats.api_calls > 0:
                message = f"⚠️ Unifuncs API成功率过低\n当前成功率: {stats.api_success_rate:.1f}%\n阈值: 80%"
                messenger.send_text(message)
                
            # 连续错误告警
            if len(self.error_history) >= self.config['error_threshold']:
                message = f"🚨 Unifuncs连续{len(self.error_history)}次错误，建议检查"
                messenger.send_text(message)
                
        except Exception as e:
            LOGGER.error(f"发送告警失败: {e}")
    
    def run_monitoring(self, date=None):
        """运行完整监控流程"""
        if not self.config['enabled']:
            LOGGER.info("监控已禁用，跳过检查")
            return
            
        stats = self.check_health(date)
        report = self.generate_report(stats)
        LOGGER.info(report)
        
        # 检查是否需要告警
        if (stats.task_status in ['failed', 'timeout'] or 
            stats.match_rate < self.config['alert_threshold'] or
            stats.api_success_rate < 80):
            self.send_alert(stats)
            
        return stats
    
    def schedule_monitoring(self):
        """定时运行监控"""
        import schedule
        
        schedule.every(self.config['check_interval']).seconds.do(self.run_monitoring)
        LOGGER.info(f"定时监控已启动，每{self.config['check_interval']/3600:.1f}小时检查一次")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """测试监控功能"""
    monitor = UnifuncsMonitor()
    stats = monitor.run_monitoring()
    
    print("\n详细监控数据:")
    print(f"任务状态: {stats.task_status}")
    print(f"API调用: {stats.api_calls}次")
    print(f"API成功率: {stats.api_success_rate:.1f}%")
    print(f"匹配率: {stats.match_rate:.1f}%")
    print(f"平均匹配度: {stats.average_match_score:.3f}")


if __name__ == '__main__':
    main()