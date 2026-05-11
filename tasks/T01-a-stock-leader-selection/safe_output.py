"""
安全输出工具模块
解决 BrokenPipeError 问题

使用方法:
    from safe_output import safe_print, safe_stdout
    safe_print("消息")
"""

import sys
import os
import signal

# 忽略 SIGPIPE 信号
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# 检测是否在管道环境中
_IN_PIPE = not sys.stdout.isatty()

class SafeOutput:
    """安全输出类"""
    
    def __init__(self):
        self.stderr = sys.stderr
        self.stdout = sys.stdout
        self._closed = False
    
    def write(self, message: str, flush: bool = False):
        """安全写入"""
        if self._closed:
            return
        
        try:
            self.stdout.write(message)
            if flush:
                self.stdout.flush()
        except (BrokenPipeError, IOError):
            self._closed = True
            # 重定向到 stderr
            try:
                self.stderr.write(message)
            except:
                pass
    
    def print(self, *args, **kwargs):
        """安全打印"""
        try:
            print(*args, **kwargs)
        except (BrokenPipeError, IOError):
            # 尝试写入 stderr
            try:
                message = " ".join(str(arg) for arg in args)
                self.stderr.write(message + "\n")
            except:
                pass

# 全局实例
_safe_output = SafeOutput()

def safe_print(*args, **kwargs):
    """
    安全打印函数
    
    使用方法与 print() 相同，但会捕获 BrokenPipeError
    """
    _safe_output.print(*args, **kwargs)

def safe_stdout(message: str):
    """
    安全写入 stdout
    """
    _safe_output.write(message)

def is_pipe_environment() -> bool:
    """
    检查是否在管道环境中
    """
    return _IN_PIPE

# 如果需要在导入时替换 print
# import builtins
# builtins.print = safe_print
