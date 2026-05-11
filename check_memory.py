import sys
sys.path.insert(0, '/workspace/projects/workspace')

try:
    from memory_utils import calculate_importance
    print('记忆维护工具已找到')
    # 这里可以添加记忆维护的具体逻辑
except ImportError:
    print('记忆维护工具未找到')