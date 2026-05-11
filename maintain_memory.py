import sys
sys.path.insert(0, '/workspace/projects/workspace')

# 尝试导入记忆系统工具
try:
    from memory_utils import calculate_importance, archive_low_score_memories, promote_high_score_memories, detect_duplicate_memories
    
    print("=== 记忆系统维护开始 ===")
    
    # 1. 重新评分
    print("\n1. 重新计算时间衰减后的分数...")
    recalculated = calculate_importance()
    print(f"   已重新评分 {recalculated} 条记忆")
    
    # 2. 归档候选
    print("\n2. 识别需要归档的低分记忆...")
    archive_candidates = archive_low_score_memories()
    print(f"   找到 {len(archive_candidates)} 条需要归档的记忆")
    
    # 3. 提升候选
    print("\n3. 识别需要提升的高分记忆...")
    promote_candidates = promote_high_score_memories()
    print(f"   找到 {len(promote_candidates)} 条需要提升的记忆")
    
    # 4. 重复检测
    print("\n4. 检测相似记忆...")
    duplicate_groups = detect_duplicate_memories()
    print(f"   找到 {len(duplicate_groups)} 组相似记忆")
    
    print("\n=== 记忆系统维护完成 ===")
    
except ImportError as e:
    print(f"记忆系统工具导入失败: {e}")
    print("请确保 memory_utils.py 文件存在且包含所需函数")
except Exception as e:
    print(f"记忆系统维护执行失败: {e}")