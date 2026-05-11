"""
LanceDB 本地向量记忆系统
基于 LANCEDB-PLAN.md 实现

功能：
1. 本地向量数据库存储
2. 嵌入向量生成
3. 向量相似度搜索
4. 混合检索 (向量 + 文本)
5. 增量索引更新
"""

import os
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# 尝试导入 LanceDB，如果失败则提供降级方案
try:
    import lancedb
    import pyarrow as pa
    import numpy as np
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("⚠️ LanceDB 未安装，运行降级模式")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("⚠️ sentence-transformers 未安装，运行降级模式")


@dataclass
class VectorMemoryEntry:
    """向量记忆条目"""
    id: str
    content: str
    vector: List[float] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    score: float = 0.0
    source: str = ""  # 来源文件: SESSION-STATE, LEARNINGS, ERRORS


class LanceDBMemoryManager:
    """LanceDB 记忆管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "db_path": ".lancedb/memory.lance",
        "table_name": "memories",
        "embedding_model": "all-MiniLM-L6-v2",
        "vector_dim": 384,
        "metric": "cosine"  # 或 "l2"
    }
    
    def __init__(self, workspace_path: str = "/workspace/projects/workspace", config: Dict = None):
        self.workspace = workspace_path
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.db_path = os.path.join(workspace_path, self.config["db_path"])
        self.table_name = self.config["table_name"]
        
        # 初始化状态
        self.db = None
        self.table = None
        self.model = None
        self._initialized = False
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def initialize(self) -> bool:
        """
        初始化 LanceDB 和嵌入模型
        
        Returns:
            是否成功初始化
        """
        if not LANCEDB_AVAILABLE:
            print("❌ LanceDB 不可用")
            return False
        
        try:
            # 1. 连接数据库
            self.db = lancedb.connect(self.db_path)
            print(f"✅ 连接到 LanceDB: {self.db_path}")
            
            # 2. 加载或创建表
            if self.table_name in self.db.table_names():
                self.table = self.db.open_table(self.table_name)
                print(f"✅ 加载现有表: {self.table_name}")
            else:
                self.table = self._create_table()
                print(f"✅ 创建新表: {self.table_name}")
            
            # 3. 加载嵌入模型
            if EMBEDDING_AVAILABLE:
                print(f"⏳ 加载嵌入模型: {self.config['embedding_model']}...")
                self.model = SentenceTransformer(self.config['embedding_model'])
                print(f"✅ 嵌入模型加载完成")
            else:
                print("⚠️ 嵌入模型不可用")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False
    
    def _create_table(self):
        """创建记忆表"""
        # 定义 schema
        schema = pa.schema([
            ("id", pa.string()),
            ("content", pa.string()),
            ("vector", pa.list_(pa.float32(), self.config["vector_dim"])),
            ("source", pa.string()),
            ("score", pa.float32()),
            ("level", pa.string()),
            ("memory_type", pa.string()),
            ("timestamp", pa.string()),
            ("keywords", pa.string()),  # JSON 字符串
        ])
        
        return self.db.create_table(self.table_name, schema=schema)
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        生成文本的嵌入向量
        
        Args:
            text: 输入文本
        
        Returns:
            嵌入向量，如果模型不可用则返回 None
        """
        if not self.model:
            return None
        
        try:
            vector = self.model.encode(text, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            print(f"⚠️ 嵌入生成失败: {e}")
            return None
    
    def add_memory(self, entry: VectorMemoryEntry) -> bool:
        """
        添加单条记忆
        
        Args:
            entry: 记忆条目
        
        Returns:
            是否成功
        """
        if not self._initialized or not self.table:
            print("❌ LanceDB 未初始化")
            return False
        
        try:
            # 生成嵌入
            if not entry.vector and self.model:
                entry.vector = self.generate_embedding(entry.content)
            
            if not entry.vector:
                print("⚠️ 无法生成嵌入，跳过添加")
                return False
            
            # 准备数据
            data = [{
                "id": entry.id,
                "content": entry.content,
                "vector": entry.vector,
                "source": entry.source,
                "score": entry.score,
                "level": entry.metadata.get("level", "Low"),
                "memory_type": entry.metadata.get("type", "fact"),
                "timestamp": entry.metadata.get("timestamp", datetime.now().isoformat()),
                "keywords": json.dumps(entry.metadata.get("keywords", []))
            }]
            
            # 添加到表
            self.table.add(data)
            return True
            
        except Exception as e:
            print(f"❌ 添加记忆失败: {e}")
            return False
    
    def add_memories_batch(self, entries: List[VectorMemoryEntry]) -> Tuple[int, int]:
        """
        批量添加记忆
        
        Args:
            entries: 记忆条目列表
        
        Returns:
            (成功数, 失败数)
        """
        success = 0
        failed = 0
        
        for entry in entries:
            if self.add_memory(entry):
                success += 1
            else:
                failed += 1
        
        return success, failed
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Dict = None
    ) -> List[Dict]:
        """
        向量相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            filter_dict: 过滤条件，如 {"level": "High"}
        
        Returns:
            搜索结果列表
        """
        if not self._initialized or not self.table:
            print("❌ LanceDB 未初始化")
            return []
        
        if not self.model:
            print("❌ 嵌入模型不可用")
            return []
        
        try:
            # 生成查询向量
            query_vector = self.generate_embedding(query)
            if not query_vector:
                return []
            
            # 构建搜索
            search = self.table.search(query_vector) \
                .metric(self.config["metric"]) \
                .limit(top_k)
            
            # 添加过滤
            if filter_dict:
                filter_str = " AND ".join([f"{k} = '{v}'" for k, v in filter_dict.items()])
                search = search.where(filter_str)
            
            # 执行搜索
            results = search.to_pandas()
            
            # 转换为字典列表
            records = results.to_dict('records')
            
            # 解析 keywords
            for record in records:
                if 'keywords' in record and record['keywords']:
                    try:
                        record['keywords'] = json.loads(record['keywords'])
                    except:
                        record['keywords'] = []
            
            return records
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
        
        Returns:
            是否成功
        """
        if not self._initialized or not self.table:
            return False
        
        try:
            self.table.delete(f"id = '{memory_id}'")
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        if not self._initialized or not self.table:
            return {"status": "not_initialized"}
        
        try:
            count = len(self.table)
            return {
                "status": "initialized",
                "total_memories": count,
                "table_name": self.table_name,
                "db_path": self.db_path,
                "embedding_model": self.config["embedding_model"],
                "vector_dim": self.config["vector_dim"]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """关闭连接"""
        self.db = None
        self.table = None
        self.model = None
        self._initialized = False


class HybridMemorySearcher:
    """混合记忆检索器 (向量 + 文本)"""
    
    def __init__(self, lancedb_manager: LanceDBMemoryManager):
        self.vector_db = lancedb_manager
        self.text_weight = 0.3
        self.vector_weight = 0.7
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        use_hybrid: bool = True
    ) -> List[Dict]:
        """
        混合搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            use_hybrid: 是否使用混合搜索
        
        Returns:
            搜索结果
        """
        if not use_hybrid:
            # 纯向量搜索
            return self.vector_db.search(query, top_k=top_k)
        
        # 1. 向量搜索 (召回更多候选)
        vector_results = self.vector_db.search(query, top_k=top_k * 3)
        
        # 2. 简单的文本匹配 (基于关键词)
        text_results = self._text_search(query, top_k * 2)
        
        # 3. 合并结果
        merged = self._merge_results(vector_results, text_results, query)
        
        # 4. 返回 Top K
        return merged[:top_k]
    
    def _text_search(self, query: str, top_k: int) -> List[Dict]:
        """简单的文本搜索 (基于关键词匹配)"""
        # 提取查询关键词
        query_words = set(query.lower().split())
        
        # 获取所有记忆 (简化版，实际应该使用全文索引)
        # 这里假设我们有一个简单的缓存
        results = []
        # TODO: 实现基于内存的文本搜索
        return results
    
    def _merge_results(
        self, 
        vector_results: List[Dict], 
        text_results: List[Dict],
        query: str
    ) -> List[Dict]:
        """合并向量搜索结果和文本搜索结果"""
        # 使用字典去重
        merged = {}
        
        # 添加向量结果
        for i, result in enumerate(vector_results):
            id = result['id']
            # 向量分数 (余弦相似度转为 0-1)
            vector_score = 1 - result.get('_distance', 0)
            merged[id] = {
                **result,
                '_score': vector_score * self.vector_weight,
                '_source': 'vector'
            }
        
        # 添加文本结果
        for result in text_results:
            id = result['id']
            text_score = result.get('text_score', 0)
            if id in merged:
                # 合并分数
                merged[id]['_score'] += text_score * self.text_weight
                merged[id]['_source'] = 'hybrid'
            else:
                merged[id] = {
                    **result,
                    '_score': text_score * self.text_weight,
                    '_source': 'text'
                }
        
        # 按分数排序
        sorted_results = sorted(merged.values(), key=lambda x: x['_score'], reverse=True)
        return sorted_results


# Markdown 记忆同步器
class MarkdownMemorySync:
    """从 Markdown 文件同步记忆到 LanceDB"""
    
    def __init__(self, workspace_path: str, lancedb_manager: LanceDBMemoryManager):
        self.workspace = workspace_path
        self.lancedb = lancedb_manager
    
    def parse_memory_entry(self, text: str) -> Optional[VectorMemoryEntry]:
        """解析 Markdown 中的记忆条目"""
        # 匹配格式: ## [MEM-YYYYMMDD-NNN] Level: X | Score: X.X
        pattern = r'##\s*\[(MEM-\d{8}-\d{3})\]\s*Level:\s*(\w+)\s*\|\s*Score:\s*([\d.]+)'
        match = re.search(pattern, text)
        
        if not match:
            return None
        
        memory_id = match.group(1)
        level = match.group(2)
        score = float(match.group(3))
        
        # 提取内容 (简化版)
        content = text[match.end():].strip()
        
        return VectorMemoryEntry(
            id=memory_id,
            content=content[:500],  # 限制长度
            score=score,
            metadata={"level": level}
        )
    
    def sync_all(self) -> Tuple[int, int]:
        """
        同步所有 Markdown 文件到 LanceDB
        
        Returns:
            (成功数, 失败数)
        """
        files = [
            "SESSION-STATE.md",
            "LEARNINGS.md",
            "ERRORS.md",
            "MEMORY.md"
        ]
        
        all_entries = []
        
        for filename in files:
            filepath = os.path.join(self.workspace, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析记忆条目
                entries = self._parse_file(content, filename)
                all_entries.extend(entries)
        
        # 批量添加到 LanceDB
        return self.lancedb.add_memories_batch(all_entries)
    
    def _parse_file(self, content: str, source: str) -> List[VectorMemoryEntry]:
        """解析单个文件"""
        entries = []
        # 按 ## 分割条目
        sections = re.split(r'\n##\s*', content)
        
        for section in sections:
            entry = self.parse_memory_entry("## " + section)
            if entry:
                entry.source = source
                entries.append(entry)
        
        return entries


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("LanceDB 记忆系统测试")
    print("=" * 60)
    
    # 初始化
    manager = LanceDBMemoryManager()
    
    if not LANCEDB_AVAILABLE:
        print("\n❌ LanceDB 未安装，跳过测试")
        print("请运行: pip install lancedb sentence-transformers")
        exit(1)
    
    success = manager.initialize()
    
    if success:
        print("\n✅ LanceDB 初始化成功")
        
        # 测试添加记忆
        test_entries = [
            VectorMemoryEntry(
                id="MEM-20260318-001",
                content="用户的工作邮箱是 jarvis@jaccoffice.com",
                score=5.0,
                source="SESSION-STATE.md",
                metadata={"level": "High", "type": "preference", "timestamp": datetime.now().isoformat()}
            ),
            VectorMemoryEntry(
                id="MEM-20260318-002",
                content="选股系统使用T01龙头战法策略",
                score=4.0,
                source="LEARNINGS.md",
                metadata={"level": "Medium", "type": "fact", "timestamp": datetime.now().isoformat()}
            ),
        ]
        
        print("\n【添加记忆测试】")
        success_count, fail_count = manager.add_memories_batch(test_entries)
        print(f"成功: {success_count}, 失败: {fail_count}")
        
        # 测试搜索
        if success_count > 0:
            print("\n【向量搜索测试】")
            results = manager.search("用户的邮箱是什么", top_k=3)
            print(f"查询 '用户的邮箱是什么' 返回 {len(results)} 条结果")
            for r in results:
                print(f"  - {r['id']}: {r['content'][:30]}... (距离: {r.get('_distance', 'N/A')})")
        
        # 统计信息
        print("\n【统计信息】")
        stats = manager.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        manager.close()
        print("\n✅ 测试完成")
    else:
        print("\n❌ 初始化失败")
