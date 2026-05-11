"""
增量索引更新器
实现从 Markdown 记忆文件到 LanceDB 的实时同步
"""

import os
import re
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path

from memory_lancedb import LanceDBMemoryManager, VectorMemoryEntry


@dataclass
class MemoryIndexState:
    """记忆索引状态"""
    memory_id: str
    content_hash: str  # 内容哈希，用于检测变化
    indexed_at: datetime
    modified_at: datetime
    source_file: str


class IncrementalMemoryIndexer:
    """
    增量记忆索引器
    
    功能：
    1. 监听 Markdown 文件变化
    2. 检测新增/修改/删除的记忆
    3. 增量更新 LanceDB 索引
    4. 维护索引状态，避免重复处理
    """
    
    # 监听的文件
    WATCHED_FILES = [
        "SESSION-STATE.md",
        "LEARNINGS.md", 
        "ERRORS.md",
        "MEMORY.md"
    ]
    
    def __init__(
        self, 
        workspace_path: str = "/workspace/projects/workspace",
        lancedb_manager: LanceDBMemoryManager = None
    ):
        self.workspace = workspace_path
        self.lancedb = lancedb_manager or LanceDBMemoryManager(workspace_path)
        
        # 索引状态文件
        self.state_file = os.path.join(workspace_path, ".lancedb", "index_state.json")
        self.index_state: Dict[str, MemoryIndexState] = {}
        
        # 加载状态
        self._load_state()
    
    def _load_state(self):
        """加载索引状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.index_state[k] = MemoryIndexState(
                            memory_id=v['memory_id'],
                            content_hash=v['content_hash'],
                            indexed_at=datetime.fromisoformat(v['indexed_at']),
                            modified_at=datetime.fromisoformat(v['modified_at']),
                            source_file=v['source_file']
                        )
            except Exception as e:
                print(f"⚠️ 加载索引状态失败: {e}")
                self.index_state = {}
    
    def _save_state(self):
        """保存索引状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            data = {}
            for k, v in self.index_state.items():
                data[k] = {
                    'memory_id': v.memory_id,
                    'content_hash': v.content_hash,
                    'indexed_at': v.indexed_at.isoformat(),
                    'modified_at': v.modified_at.isoformat(),
                    'source_file': v.source_file
                }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ 保存索引状态失败: {e}")
    
    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def _parse_memory_entries(self, file_path: str) -> List[Dict]:
        """
        解析 Markdown 文件中的记忆条目
        
        Returns:
            记忆条目列表，每个条目包含 id, content, metadata
        """
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️ 读取文件失败 {file_path}: {e}")
            return entries
        
        # 匹配记忆条目格式
        # 格式: ## [MEM-YYYYMMDD-NNN] Level: X | Score: X.X
        pattern = r'##\s*\[(MEM-\d{8}-\d{3})\]\s*Level:\s*(\w+)\s*\|\s*Score:\s*([\d.]+).*?\n\*\*.*?\*\*\s*(.*?)\n\n### Content\n(.*?)(?=\n---|\Z)'
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            memory_id = match.group(1)
            level = match.group(2)
            score = float(match.group(3))
            header_info = match.group(4)
            memory_content = match.group(5).strip()
            
            # 解析 header 信息
            memory_type = "fact"
            timestamp = datetime.now().isoformat()
            keywords = []
            
            # 提取类型
            type_match = re.search(r'Type\s*:\s*(\w+)', header_info)
            if type_match:
                memory_type = type_match.group(1)
            
            # 提取时间
            time_match = re.search(r'Logged\s*:\s*([\d\-T:+]+)', header_info)
            if time_match:
                timestamp = time_match.group(1)
            
            # 提取关键词
            kw_match = re.search(r'Keywords\s*:\s*\[(.*?)\]', header_info)
            if kw_match:
                keywords = [k.strip() for k in kw_match.group(1).split(',') if k.strip()]
            
            entries.append({
                'id': memory_id,
                'content': memory_content,
                'metadata': {
                    'level': level,
                    'score': score,
                    'type': memory_type,
                    'timestamp': timestamp,
                    'keywords': keywords
                },
                'source': os.path.basename(file_path),
                'content_hash': self._compute_hash(memory_content)
            })
        
        return entries
    
    def scan_for_changes(self) -> Dict[str, List[Dict]]:
        """
        扫描文件变化
        
        Returns:
            {
                'new': [...],      # 新增的记忆
                'modified': [...], # 修改的记忆
                'deleted': [...]   # 删除的记忆ID
            }
        """
        new_entries = []
        modified_entries = []
        current_ids = set()
        
        for filename in self.WATCHED_FILES:
            file_path = os.path.join(self.workspace, filename)
            if not os.path.exists(file_path):
                continue
            
            entries = self._parse_memory_entries(file_path)
            
            for entry in entries:
                memory_id = entry['id']
                current_ids.add(memory_id)
                content_hash = entry['content_hash']
                
                if memory_id not in self.index_state:
                    # 新增
                    new_entries.append(entry)
                elif self.index_state[memory_id].content_hash != content_hash:
                    # 修改
                    modified_entries.append(entry)
        
        # 检测删除
        indexed_ids = set(self.index_state.keys())
        deleted_ids = list(indexed_ids - current_ids)
        
        return {
            'new': new_entries,
            'modified': modified_entries,
            'deleted': deleted_ids
        }
    
    def sync(self, verbose: bool = True) -> Dict:
        """
        执行增量同步
        
        Returns:
            同步统计
        """
        if not self.lancedb._initialized:
            if not self.lancedb.initialize():
                return {'error': 'LanceDB 初始化失败'}
        
        changes = self.scan_for_changes()
        
        stats = {
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'unchanged': len(self.index_state) - len(changes['deleted'])
        }
        
        # 处理新增
        for entry in changes['new']:
            vector_entry = VectorMemoryEntry(
                id=entry['id'],
                content=entry['content'],
                score=entry['metadata']['score'],
                source=entry['source'],
                metadata=entry['metadata']
            )
            
            if self.lancedb.add_memory(vector_entry):
                self.index_state[entry['id']] = MemoryIndexState(
                    memory_id=entry['id'],
                    content_hash=entry['content_hash'],
                    indexed_at=datetime.now(),
                    modified_at=datetime.now(),
                    source_file=entry['source']
                )
                stats['added'] += 1
                if verbose:
                    print(f"  + 新增: {entry['id']}")
        
        # 处理修改
        for entry in changes['modified']:
            # 删除旧版本
            self.lancedb.delete_memory(entry['id'])
            
            # 添加新版本
            vector_entry = VectorMemoryEntry(
                id=entry['id'],
                content=entry['content'],
                score=entry['metadata']['score'],
                source=entry['source'],
                metadata=entry['metadata']
            )
            
            if self.lancedb.add_memory(vector_entry):
                self.index_state[entry['id']].content_hash = entry['content_hash']
                self.index_state[entry['id']].modified_at = datetime.now()
                stats['updated'] += 1
                if verbose:
                    print(f"  ~ 更新: {entry['id']}")
        
        # 处理删除
        for memory_id in changes['deleted']:
            self.lancedb.delete_memory(memory_id)
            del self.index_state[memory_id]
            stats['deleted'] += 1
            if verbose:
                print(f"  - 删除: {memory_id}")
        
        # 保存状态
        self._save_state()
        
        return stats
    
    def full_reindex(self, verbose: bool = True) -> Dict:
        """
        完全重建索引
        
        用途：
        1. 首次部署
        2. 数据结构变更
        3. 修复索引损坏
        """
        if verbose:
            print("🔄 开始完全重建索引...")
        
        # 清空现有索引
        self.index_state = {}
        
        # 删除并重建表
        if self.lancedb._initialized:
            try:
                self.lancedb.db.drop_table(self.lancedb.table_name)
            except:
                pass
            self.lancedb.table = self.lancedb._create_table()
        
        # 执行同步
        stats = self.sync(verbose=verbose)
        
        if verbose:
            print(f"✅ 重建完成: 新增 {stats['added']}, 更新 {stats['updated']}, 删除 {stats['deleted']}")
        
        return stats
    
    def get_index_stats(self) -> Dict:
        """获取索引统计"""
        lancedb_stats = self.lancedb.get_stats()
        
        # 按文件统计
        file_stats = {}
        for state in self.index_state.values():
            file = state.source_file
            file_stats[file] = file_stats.get(file, 0) + 1
        
        return {
            **lancedb_stats,
            'tracked_memories': len(self.index_state),
            'by_file': file_stats,
            'last_sync': max(
                (s.modified_at for s in self.index_state.values()),
                default=None
            )
        }


# 文件监听器 (简化版)
class MemoryFileWatcher:
    """
    Markdown 记忆文件监听器
    
    注意：完整实现需要使用 watchdog 库
    这里提供简化版，基于轮询
    """
    
    def __init__(self, workspace_path: str, indexer: IncrementalMemoryIndexer):
        self.workspace = workspace_path
        self.indexer = indexer
        self.file_mtimes = {}
    
    def check_changes(self) -> bool:
        """
        检查文件变化
        
        Returns:
            是否有变化
        """
        changed = False
        
        for filename in self.indexer.WATCHED_FILES:
            file_path = os.path.join(self.workspace, filename)
            if not os.path.exists(file_path):
                continue
            
            mtime = os.path.getmtime(file_path)
            
            if filename not in self.file_mtimes:
                self.file_mtimes[filename] = mtime
                changed = True
            elif self.file_mtimes[filename] != mtime:
                self.file_mtimes[filename] = mtime
                changed = True
        
        return changed
    
    def sync_if_changed(self) -> Optional[Dict]:
        """如果有变化则同步"""
        if self.check_changes():
            print("📁 检测到文件变化，执行增量同步...")
            return self.indexer.sync()
        return None


# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("增量索引更新器测试")
    print("=" * 60)
    
    # 初始化
    lancedb = LanceDBMemoryManager()
    if not lancedb.initialize():
        print("❌ LanceDB 初始化失败，跳过测试")
        exit(1)
    
    indexer = IncrementalMemoryIndexer(lancedb_manager=lancedb)
    
    print("\n【扫描变化】")
    changes = indexer.scan_for_changes()
    print(f"新增: {len(changes['new'])}, 修改: {len(changes['modified'])}, 删除: {len(changes['deleted'])}")
    
    if changes['new'] or changes['modified']:
        print("\n【执行同步】")
        stats = indexer.sync()
        print(f"结果: 新增 {stats.get('added', 0)}, 更新 {stats.get('updated', 0)}, 删除 {stats.get('deleted', 0)}")
    
    print("\n【索引统计】")
    stats = indexer.get_index_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成")
