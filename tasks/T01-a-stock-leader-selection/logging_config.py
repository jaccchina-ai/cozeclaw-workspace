"""
T01 选股系统 - 统一日志配置

统一收集所有日志到 /workspace/projects/workspace/logs/ 目录
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

# 日志根目录
LOGS_DIR = Path('/workspace/projects/workspace/logs')
T01_LOGS_DIR = LOGS_DIR / 't01'

# 确保日志目录存在
T01_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class T01Logger:
    """T01 统一日志管理器"""
    
    # 日志格式
    FORMATTER = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 简单格式（用于控制台）
    SIMPLE_FORMATTER = logging.Formatter(
        '%(message)s'
    )
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_to_file: bool = True, log_to_console: bool = True, level=logging.INFO):
        """
        获取或创建logger
        
        Args:
            name: logger名称，如 'selection', 'data_fetcher', 'messenger'
            log_to_file: 是否写入文件
            log_to_console: 是否输出到控制台
            level: 日志级别
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(f't01.{name}')
        logger.setLevel(level)
        logger.handlers = []  # 清除已有handler
        
        # 文件日志
        if log_to_file:
            today = datetime.now().strftime('%Y%m%d')
            log_file = T01_LOGS_DIR / f'{name}_{today}.log'
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setFormatter(cls.FORMATTER)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)
        
        # 控制台日志
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(cls.SIMPLE_FORMATTER)
            console_handler.setLevel(level)
            logger.addHandler(console_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def get_task_logger(cls, task_name: str, date: str = None):
        """
        获取任务专用logger
        
        Args:
            task_name: 任务名称，如 't1_auction', 't_day', 'track'
            date: 日期，默认今天
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        log_file = T01_LOGS_DIR / f'task_{task_name}_{date}.log'
        
        logger = logging.getLogger(f't01.task.{task_name}')
        logger.setLevel(logging.INFO)
        logger.handlers = []
        
        # 任务日志文件
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(cls.FORMATTER)
        logger.addHandler(file_handler)
        
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(cls.SIMPLE_FORMATTER)
        logger.addHandler(console_handler)
        
        return logger


def init_logging():
    """初始化日志系统，在应用启动时调用"""
    # 创建日志目录
    T01_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 设置根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    
    # 清除默认handler
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加错误日志文件（收集所有ERROR级别日志）
    error_log = T01_LOGS_DIR / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_log, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(T01Logger.FORMATTER)
    root_logger.addHandler(error_handler)
    
    print(f"✅ 日志系统初始化完成")
    print(f"   日志目录: {T01_LOGS_DIR}")
    
    return T01_LOGS_DIR


def get_logs_summary(days: int = 7) -> dict:
    """
    获取最近日志摘要
    
    Args:
        days: 查询天数
        
    Returns:
        日志统计信息
    """
    summary = {
        'log_dir': str(T01_LOGS_DIR),
        'recent_files': [],
        'error_count': 0,
        'task_runs': {}
    }
    
    if not T01_LOGS_DIR.exists():
        return summary
    
    # 获取最近的日志文件
    log_files = sorted(T01_LOGS_DIR.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
    
    for f in log_files[:20]:
        stat = f.stat()
        summary['recent_files'].append({
            'name': f.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 统计错误日志
    error_log = T01_LOGS_DIR / 'errors.log'
    if error_log.exists():
        with open(error_log, 'r', encoding='utf-8') as f:
            content = f.read()
            summary['error_count'] = content.count('[ERROR]')
    
    return summary


# 便捷函数
def get_selection_logger():
    """获取选股模块logger"""
    return T01Logger.get_logger('selection')


def get_data_logger():
    """获取数据获取模块logger"""
    return T01Logger.get_logger('data_fetcher')


def get_messenger_logger():
    """获取消息发送模块logger"""
    return T01Logger.get_logger('messenger')


def get_monitor_logger():
    """获取监控模块logger"""
    return T01Logger.get_logger('monitor')
