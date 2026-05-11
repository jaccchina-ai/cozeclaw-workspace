"""
T01 选股系统 - 监控模块

记录执行状态、API调用统计、异常告警
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

sys.path.insert(0, os.path.dirname(__file__))
from database.models import Base, get_session, init_db


# ==================== 监控数据模型 ====================

class TaskExecutionLog(Base):
    """任务执行日志表"""
    __tablename__ = 'task_execution_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(50), index=True)         # 任务名称: t_day_selection, t1_auction, evolution
    trade_date = Column(String(8), index=True)         # 交易日期
    start_time = Column(DateTime)                      # 开始时间
    end_time = Column(DateTime)                        # 结束时间
    duration_seconds = Column(Float)                   # 执行耗时(秒)
    status = Column(String(20))                        # 状态: running, success, failed
    result_count = Column(Integer, default=0)          # 结果数量
    error_message = Column(Text)                       # 错误信息
    details = Column(Text)                             # 详细信息(JSON)
    created_at = Column(DateTime, default=datetime.now)


class ApiCallLog(Base):
    """API调用日志表"""
    __tablename__ = 'api_call_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_name = Column(String(50), index=True)          # API名称: daily, limit_list, stk_auction等
    trade_date = Column(String(8), index=True)         # 交易日期
    call_time = Column(DateTime)                       # 调用时间
    success = Column(Boolean)                          # 是否成功
    response_time_ms = Column(Float)                   # 响应时间(毫秒)
    data_count = Column(Integer, default=0)            # 返回数据条数
    error_message = Column(Text)                       # 错误信息
    created_at = Column(DateTime, default=datetime.now)


class SystemAlert(Base):
    """系统告警表"""
    __tablename__ = 'system_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(30), index=True)        # 告警类型: api_error, task_failed, data_missing
    severity = Column(String(20))                      # 严重程度: info, warning, error, critical
    title = Column(String(200))                        # 告警标题
    message = Column(Text)                             # 告警内容
    trade_date = Column(String(8), index=True)         # 关联交易日期
    is_resolved = Column(Boolean, default=False)       # 是否已解决
    resolved_at = Column(DateTime)                     # 解决时间
    created_at = Column(DateTime, default=datetime.now)


# ==================== 监控管理器 ====================

class Monitor:
    """监控管理器"""
    
    def __init__(self):
        self.session = get_session()
        self._init_tables()
    
    def _init_tables(self):
        """初始化监控表"""
        Base.metadata.create_all(
            bind=self.session.get_bind(),
            tables=[TaskExecutionLog.__table__, ApiCallLog.__table__, SystemAlert.__table__]
        )
    
    # ==================== 任务执行日志 ====================
    
    def start_task(self, task_name: str, trade_date: str = None) -> int:
        """
        记录任务开始
        
        Returns:
            日志ID，用于后续更新
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        log = TaskExecutionLog(
            task_name=task_name,
            trade_date=trade_date,
            start_time=datetime.now(),
            status='running'
        )
        self.session.add(log)
        self.session.commit()
        return log.id
    
    def end_task(self, log_id: int, status: str = 'success', 
                 result_count: int = 0, error_message: str = None,
                 details: Dict = None):
        """记录任务结束"""
        log = self.session.query(TaskExecutionLog).filter_by(id=log_id).first()
        if log:
            log.end_time = datetime.now()
            log.duration_seconds = (log.end_time - log.start_time).total_seconds()
            log.status = status
            log.result_count = result_count
            log.error_message = error_message
            if details:
                log.details = json.dumps(details, ensure_ascii=False)
            self.session.commit()
    
    def get_task_history(self, task_name: str = None, days: int = 7) -> List[Dict]:
        """获取任务执行历史"""
        query = self.session.query(TaskExecutionLog)
        
        if task_name:
            query = query.filter(TaskExecutionLog.task_name == task_name)
        
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(TaskExecutionLog.created_at >= start_date)
        query = query.order_by(TaskExecutionLog.created_at.desc())
        
        return [
            {
                'id': log.id,
                'task_name': log.task_name,
                'trade_date': log.trade_date,
                'start_time': log.start_time.strftime('%Y-%m-%d %H:%M:%S') if log.start_time else None,
                'duration_seconds': log.duration_seconds,
                'status': log.status,
                'result_count': log.result_count,
                'error_message': log.error_message
            }
            for log in query.limit(50).all()
        ]
    
    # ==================== API调用日志 ====================
    
    def log_api_call(self, api_name: str, success: bool, 
                     response_time_ms: float = 0, data_count: int = 0,
                     error_message: str = None, trade_date: str = None):
        """记录API调用"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        log = ApiCallLog(
            api_name=api_name,
            trade_date=trade_date,
            call_time=datetime.now(),
            success=success,
            response_time_ms=response_time_ms,
            data_count=data_count,
            error_message=error_message
        )
        self.session.add(log)
        self.session.commit()
    
    def get_api_stats(self, days: int = 1) -> Dict:
        """获取API调用统计"""
        start_date = datetime.now() - timedelta(days=days)
        
        logs = self.session.query(ApiCallLog).filter(
            ApiCallLog.call_time >= start_date
        ).all()
        
        if not logs:
            return {'total_calls': 0, 'success_rate': 0, 'avg_response_time_ms': 0}
        
        total = len(logs)
        success = sum(1 for log in logs if log.success)
        avg_time = sum(log.response_time_ms or 0 for log in logs) / total
        
        # 按API分组统计
        api_stats = {}
        for log in logs:
            if log.api_name not in api_stats:
                api_stats[log.api_name] = {'total': 0, 'success': 0, 'avg_time': 0, 'times': []}
            api_stats[log.api_name]['total'] += 1
            if log.success:
                api_stats[log.api_name]['success'] += 1
            if log.response_time_ms:
                api_stats[log.api_name]['times'].append(log.response_time_ms)
        
        # 计算平均响应时间
        for api_name in api_stats:
            times = api_stats[api_name]['times']
            api_stats[api_name]['avg_time'] = sum(times) / len(times) if times else 0
            del api_stats[api_name]['times']
        
        return {
            'total_calls': total,
            'success_rate': success / total * 100 if total > 0 else 0,
            'avg_response_time_ms': avg_time,
            'api_breakdown': api_stats
        }
    
    # ==================== 系统告警 ====================
    
    def create_alert(self, alert_type: str, severity: str, 
                     title: str, message: str, trade_date: str = None):
        """创建告警"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        alert = SystemAlert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            trade_date=trade_date
        )
        self.session.add(alert)
        self.session.commit()
        
        # 打印告警信息
        severity_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        print(f"\n{severity_emoji.get(severity, '❗')} [{severity.upper()}] {title}")
        print(f"   {message}\n")
        
        return alert.id
    
    def resolve_alert(self, alert_id: int):
        """解决告警"""
        alert = self.session.query(SystemAlert).filter_by(id=alert_id).first()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now()
            self.session.commit()
    
    def get_active_alerts(self, severity: str = None) -> List[Dict]:
        """获取未解决的告警"""
        query = self.session.query(SystemAlert).filter_by(is_resolved=False)
        
        if severity:
            query = query.filter(SystemAlert.severity == severity)
        
        query = query.order_by(SystemAlert.created_at.desc())
        
        return [
            {
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'trade_date': alert.trade_date,
                'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for alert in query.limit(20).all()
        ]
    
    # ==================== 系统状态 ====================
    
    def get_system_status(self) -> Dict:
        """获取系统整体状态"""
        today = datetime.now().strftime('%Y%m%d')
        
        # 今日任务执行情况
        today_tasks = self.session.query(TaskExecutionLog).filter(
            TaskExecutionLog.trade_date == today
        ).all()
        
        tasks_summary = {}
        for task in today_tasks:
            if task.task_name not in tasks_summary:
                tasks_summary[task.task_name] = {
                    'total': 0, 'success': 0, 'failed': 0, 'running': 0
                }
            tasks_summary[task.task_name]['total'] += 1
            if task.status == 'success':
                tasks_summary[task.task_name]['success'] += 1
            elif task.status == 'failed':
                tasks_summary[task.task_name]['failed'] += 1
            elif task.status == 'running':
                tasks_summary[task.task_name]['running'] += 1
        
        # 今日API调用统计
        api_stats = self.get_api_stats(days=1)
        
        # 未解决告警
        active_alerts = self.get_active_alerts()
        
        return {
            'date': today,
            'tasks': tasks_summary,
            'api_stats': api_stats,
            'active_alerts': active_alerts,
            'system_healthy': len([a for a in active_alerts if a['severity'] in ['error', 'critical']]) == 0
        }
    
    def print_daily_report(self):
        """打印每日报告"""
        status = self.get_system_status()
        
        print("\n" + "="*60)
        print(f"📊 T01 系统状态报告 - {status['date']}")
        print("="*60)
        
        # 任务执行情况
        print("\n【今日任务执行】")
        if status['tasks']:
            for task_name, stats in status['tasks'].items():
                print(f"  {task_name}: 成功 {stats['success']}/{stats['total']}, "
                      f"失败 {stats['failed']}, 运行中 {stats['running']}")
        else:
            print("  暂无任务执行记录")
        
        # API统计
        print("\n【API调用统计】")
        api = status['api_stats']
        print(f"  总调用: {api['total_calls']} 次")
        print(f"  成功率: {api['success_rate']:.1f}%")
        print(f"  平均响应: {api['avg_response_time_ms']:.0f} ms")
        
        if api.get('api_breakdown'):
            print("  各接口详情:")
            for api_name, stats in api['api_breakdown'].items():
                rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                print(f"    {api_name}: {stats['total']}次, 成功率 {rate:.0f}%, 响应 {stats['avg_time']:.0f}ms")
        
        # 告警
        print("\n【未解决告警】")
        if status['active_alerts']:
            for alert in status['active_alerts']:
                print(f"  [{alert['severity'].upper()}] {alert['title']}")
        else:
            print("  ✅ 无未解决告警")
        
        # 系统健康
        print("\n【系统健康】")
        if status['system_healthy']:
            print("  ✅ 系统运行正常")
        else:
            print("  ⚠️ 系统存在异常，请检查告警")
        
        print("="*60 + "\n")


# ==================== 装饰器：自动记录任务执行 ====================

def monitored_task(task_name: str):
    """
    装饰器：自动记录任务执行状态
    
    Usage:
        @monitored_task('t_day_selection')
        def run_t_day_task():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = Monitor()
            log_id = monitor.start_task(task_name)
            
            try:
                result = func(*args, **kwargs)
                
                # 获取结果数量
                result_count = 0
                if isinstance(result, tuple) and len(result) > 0:
                    if isinstance(result[0], list):
                        result_count = len(result[0])
                elif isinstance(result, list):
                    result_count = len(result)
                
                monitor.end_task(log_id, 'success', result_count=result_count)
                return result
                
            except Exception as e:
                monitor.end_task(log_id, 'failed', error_message=str(e))
                monitor.create_alert(
                    alert_type='task_failed',
                    severity='error',
                    title=f'{task_name} 任务失败',
                    message=str(e)
                )
                raise
        
        return wrapper
    return decorator


# ==================== 初始化 ====================

def init_monitor():
    """初始化监控模块"""
    init_db()
    monitor = Monitor()
    print("✅ 监控模块初始化完成")
    return monitor


if __name__ == '__main__':
    # 测试监控模块
    monitor = init_monitor()
    
    # 测试任务记录
    import time
    log_id = monitor.start_task('test_task')
    time.sleep(1)
    monitor.end_task(log_id, 'success', result_count=5)
    
    # 测试API记录
    monitor.log_api_call('daily', True, 150.5, 100)
    monitor.log_api_call('limit_list', True, 89.3, 50)
    monitor.log_api_call('stk_auction', False, 500, 0, 'API限流')
    
    # 测试告警
    monitor.create_alert('api_error', 'warning', 'API调用限流', 'stk_auction 接口调用频率超限')
    
    # 打印报告
    monitor.print_daily_report()
