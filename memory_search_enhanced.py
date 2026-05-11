"""
增强型内存搜索工具 (降级方案)
在没有 LanceDB 的情况下提供改进的记忆搜索能力
"""

import os
import re
from typing import List, Dict, Optional
from datetime import datetime


class EnhancedMemorySearch:
    """
    增强型内存搜索
    
    功能：
    1. 多文件联合搜索
    2. 关键词加权匹配
    3. 重要性优先排序
    4. 上下文提取
    
    降级策略：当 LanceDB 不可用时使用
    """
    
    # 搜索的内存文件
    MEMORY_FILES = [
        "SESSION-STATE.md",
        "LEARNINGS.md",
        "ERRORS.md",
        "MEMORY.md"
    ]
    
    # 关键词权重
    KEYWORD_WEIGHTS = {
        "critical": 5,  # Critical 等级记忆
        "high": 3,      # High 等级记忆
        "记住": 2,      # 用户强调
        "重要": 2,
        "必须": 2,
        "密码": 4,      # 安全相关
        "密钥": 4,
        "邮箱": 2,
    }
    
    def __init__(self, workspace_path: str = "/workspace/projects/workspace"):
        self.workspace = workspace_path
        self.memory_cache = {}
        self._load_memories()
    
    def _load_memories(self):
        """加载所有记忆文件到缓存"""
        for filename in self.MEMORY_FILES:
            filepath = os.path.join(self.workspace, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.memory_cache[filename] = f.read()
                except Exception as e:
                    print(f"⚠️ 加载 {filename} 失败: {e}")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索记忆
        
        Args:
            query: 查询字符串
            top_k: 返回结果数
        
        Returns:
            记忆条目列表
        """
        results = []
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        for filename, content in self.memory_cache.items():
            # 解析记忆条目
            entries = self._parse_entries(content, filename)
            
            for entry in entries:
                # 计算相关性分数
                score = self._calculate_relevance(entry, query_keywords, query_lower)
                
                if score > 0:
                    results.append({
                        **entry,
                        'relevance_score': score,
                        'matched': True
                    })
        
        # 按分数排序
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return results[:top_k]
    
    def _parse_entries(self, content: str, source: str) -> List[Dict]:
        """解析记忆条目"""
        entries = []
        
        # 匹配记忆条目格式
        # ## [MEM-YYYYMMDD-NNN] Level: X | Score: X.X
        pattern = r'##\s*\[(MEM-\d{8}-\d{3})\]\s*Level:\s*(\w+)\s*\|\s*Score:\s*([\d.]+)'
        
        matches = list(re.finditer(pattern, content))
        
        for i, match in enumerate(matches):
            memory_id = match.group(1)
            level = match.group(2)
            score = float(match.group(3))
            
            # 提取内容
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(content)
            full_content = content[start:end]
            
            entries.append({
                'id': memory_id,
                'level': level,
                'score': score,
                'content': full_content,
                'source': source,
                'timestamp': self._extract_timestamp(full_content)
            })
        
        return entries
    
    def _extract_timestamp(self, content: str) -> Optional[str]:
        """提取时间戳"""
        match = re.search(r'Logged\s*:\s*([\d\-T:+]+)', content)
        return match.group(1) if match else None
    
    def _calculate_relevance(self, entry: Dict, query_keywords: set, query_lower: str) -> float:
        """计算相关性分数"""
        content_lower = entry['content'].lower()
        content_words = set(content_lower.split())
        
        # 1. 关键词匹配分数
        keyword_score = 0
        for keyword in query_keywords:
            if keyword in content_lower:
                # 基础匹配
                keyword_score += 1
                # 额外加权
                if keyword in self.KEYWORD_WEIGHTS:
                    keyword_score += self.KEYWORD_WEIGHTS[keyword]
        
        # 2. 短语匹配 (更高权重)
        if query_lower in content_lower:
            keyword_score += 5
        
        # 3. 重要性加权
        level_bonus = {
            'Critical': 5,
            'High': 3,
            'Medium': 1,
            'Low': 0,
            'Transient': -1
        }.get(entry['level'], 0)
        
        # 4. 分数加权 (原始重要性分数)
        score_bonus = entry['score'] * 0.2
        
        return keyword_score + level_bonus + score_bonus
    
    def get_recent_memories(self, days: int = 7, level: str = None) -> List[Dict]:
        """
        获取最近的记忆
        
        Args:
            days: 最近几天
            level: 过滤特定等级
        
        Returns:
            记忆列表
        """
        all_entries = []
        
        for filename, content in self.memory_cache.items():
            entries = self._parse_entries(content, filename)
            all_entries.extend(entries)
        
        # 过滤和排序
        results = []
        for entry in all_entries:
            if level and entry['level'] != level:
                continue
            results.append(entry)
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_entries = 0
        level_counts = {}
        source_counts = {}
        
        for filename, content in self.memory_cache.items():
            entries = self._parse_entries(content, filename)
            total_entries += len(entries)
            source_counts[filename] = len(entries)
            
            for entry in entries:
                level = entry['level']
                level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            'total_entries': total_entries,
            'by_level': level_counts,
            'by_source': source_counts,
            'files_indexed': len(self.memory_cache)
        }
    
    def refresh(self):
        """刷新缓存"""
        self.memory_cache = {}
        self._load_memories()


# 简化的记忆搜索接口 (兼容原有 memory_search 工具)
def enhanced_memory_search(query: str, max_results: int = 5) -> List[Dict]:
    """
    增强型记忆搜索接口
    
    用法与原有 memory_search 类似，但提供更多功能
    """
    searcher = EnhancedMemorySearch()
    return searcher.search(query, top_k=max_results)


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("增强型内存搜索测试 (降级方案)")
    print("=" * 60)
    
    searcher = EnhancedMemorySearch()
    
    # 测试搜索
    test_queries = [
        "用户邮箱",
        "选股系统",
        "重要决策",
    ]
    
    for query in test_queries:
        print(f"\n【查询: {query}】")
        results = searcher.search(query, top_k=3)
        
        if results:
            for r in results:
                print(f"  → {r['id']} [{r['level']}] 分数: {r['relevance_score']:.1f}")
                content_preview = r['content'].split('\n')[0][:60]
                print(f"    {content_preview}...")
        else:
            print("  (无结果)")
    
    # 测试统计
    print("\n【统计信息】")
    stats = searcher.get_stats()
    print(f"总条目: {stats['total_entries']}")
    print(f"按等级: {stats['by_level']}")
    print(f"按来源: {stats['by_source']}")
    
    print("\n✅ 测试完成")
