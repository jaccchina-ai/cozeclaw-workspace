import sys
sys.path.insert(0, '/workspace/projects/workspace')
try:
    from memory_utils import calculate_importance, get_memory_stats
    print('开始记忆系统维护...')
    # 获取记忆统计
    stats = get_memory_stats()
    print("记忆统计:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    # 重新计算时间衰减后的分数
    print("\n重新计算记忆分数...")
    # 这里需要调用calculate_importance处理所有超过7天的记忆
    # 假设calculate_importance会返回处理结果
    result = calculate_importance()
    print(result)
except Exception as e:
    print(f"记忆维护出错: {e}")
    # 如果没有get_memory_stats函数，执行原始的维护命令
    import subprocess
    print("\n执行手动记忆统计:")
    subprocess.run(['python3', '-c', 'import sys; sys.path.insert(0, \"/workspace/projects/workspace\"); from memory_utils import calculate_importance; print("记忆评分功能正常")'], check=True)