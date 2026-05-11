# LanceDB 本地向量库实施计划

> 从 OpenAI Embedding API 迁移到本地 LanceDB 向量数据库

---

## 🎯 迁移目标

| 指标 | 现状 (OpenAI API) | 目标 (LanceDB) | 提升 |
|------|------------------|----------------|------|
| **查询延迟** | ~500ms | ~10ms | **50x** |
| **离线能力** | ❌ 需网络 | ✅ 完全离线 | **关键** |
| **存储成本** | API 调用费 | 一次性 | **长期省钱** |
| **数据隐私** | 数据外传 | 本地处理 | **更安全** |
| **容量限制** | 50K 缓存 | 无限 | **可扩展** |

---

## 📦 LanceDB 简介

### 什么是 LanceDB？

LanceDB 是一个**无服务器**的向量数据库，基于 Apache Arrow 和 Lance 列式格式构建：

- ✅ **无服务器**: 无需单独部署服务，直接嵌入应用
- ✅ **高性能**: 基于向量化的查询，比传统方案快10-100倍
- ✅ **持久化**: 数据存储在本地文件，支持 TB 级别
- ✅ **多模态**: 支持文本、图像、向量等多种数据类型
- ✅ **开源**: Apache 2.0 协议，免费使用

### 为什么选 LanceDB？

对比其他向量数据库：

| 数据库 | 部署复杂度 | 性能 | 持久化 | 嵌入支持 |
|--------|-----------|------|--------|---------|
| **LanceDB** | ⭐ 无服务器 | ⭐⭐⭐ 极高 | ✅ 原生 | ✅ 支持 |
| Chroma | ⭐ 简单 | ⭐⭐ 中等 | ✅ 支持 | ✅ 支持 |
| Pinecone | ⭐⭐⭐ 云服务 | ⭐⭐⭐ 高 | ☁️ 托管 | ❌ 外部 |
| Milvus | ⭐⭐⭐ 复杂 | ⭐⭐⭐ 高 | ✅ 支持 | ❌ 外部 |
| Weaviate | ⭐⭐ 中等 | ⭐⭐⭐ 高 | ✅ 支持 | ✅ 支持 |

**选择 LanceDB 的原因**:
1. **零运维**: 不需要 Docker，不需要独立服务
2. **Python 原生**: 完美集成 OpenClaw 的 Python 环境
3. **文件存储**: 与现有 Markdown 记忆系统兼容
4. **增量更新**: 支持实时插入和更新

---

## 🔧 技术架构

### 新架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    新记忆检索架构 (LanceDB)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  记忆文件层 (Markdown)                                            │
│  ├── SESSION-STATE.md                                           │
│  ├── LEARNINGS.md                                               │
│  ├── ERRORS.md                                                  │
│  └── MEMORY.md                                                  │
│         │                                                       │
│         ▼ (同步/索引)                                            │
│  ┌─────────────────────────────────────┐                       │
│  │      LanceDB 向量数据库              │                       │
│  │  ┌─────────────────────────────┐    │                       │
│  │  │ Table: memory_embeddings    │    │                       │
│  │  │ - id: string                │    │                       │
│  │  │ - content: string           │    │                       │
│  │  │ - vector: vector(384)       │    │  <-- 嵌入向量          │
│  │  │ - metadata: struct          │    │                       │
│  │  │   - level, score, type      │    │                       │
│  │  │   - keywords, timestamp     │    │                       │
│  │  └─────────────────────────────┘    │                       │
│  │                                    │                       │
│  │  存储: .lancedb/memory.lance       │                       │
│  └─────────────────────────────────────┘                       │
│         │                                                       │
│         ▼ (查询)                                                 │
│  ┌─────────────────────────────────────┐                       │
│  │        混合检索引擎                 │                       │
│  │  ├── 向量搜索 (LanceDB ANN)         │                       │
│  │  ├── 文本搜索 (BM25/TF-IDF)        │                       │
│  │  └── 重排序 (交叉编码器)            │                       │
│  └─────────────────────────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 嵌入模型选择

**方案1: all-MiniLM-L6-v2 (推荐)**
- 维度: 384
- 大小: ~80MB
- 速度: 极快
- 质量: 适合一般语义搜索
- 语言: 多语言（含中文）

**方案2: BGE-large-zh**
- 维度: 1024
- 大小: ~1GB
- 速度: 中等
- 质量: 中文优化，质量更高
- 语言: 中文专用

**方案3: OpenAI text-embedding-3-small (备选)**
- 维度: 1536
- 大小: API 调用
- 速度: 依赖网络
- 质量: 最高
- 语言: 多语言

**推荐**: 方案1 (all-MiniLM-L6-v2) - 平衡性能和资源占用

---

## 📋 实施步骤

### Phase 1: 环境准备 (Day 1)

```bash
# 1. 安装依赖
pip install lancedb sentence-transformers

# 2. 下载嵌入模型
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 3. 创建存储目录
mkdir -p /workspace/projects/workspace/.lancedb
```

### Phase 2: 核心模块开发 (Day 2-3)

```python
# memory_lancedb.py - LanceDB 管理器

import lancedb
from sentence_transformers import SentenceTransformer

class LanceDBMemory:
    def __init__(self, db_path: str = ".lancedb/memory.lance"):
        self.db = lancedb.connect(db_path)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def init_table(self):
        """初始化记忆表"""
        schema = pa.schema([
            ("id", pa.string()),
            ("content", pa.string()),
            ("vector", pa.list_(pa.float32(), 384)),
            ("metadata", pa.struct([
                ("level", pa.string()),
                ("score", pa.float32()),
                ("type", pa.string()),
                ("timestamp", pa.string()),
            ]))
        ])
        self.table = self.db.create_table("memories", schema=schema)
    
    def add_memory(self, memory: MemoryEntry):
        """添加记忆"""
        vector = self.model.encode(memory.content)
        self.table.add([{
            "id": memory.id,
            "content": memory.content,
            "vector": vector.tolist(),
            "metadata": {
                "level": memory.level,
                "score": memory.score,
                "type": memory.memory_type,
                "timestamp": memory.logged_at.isoformat()
            }
        }])
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """向量搜索"""
        query_vector = self.model.encode(query)
        results = self.table.search(query_vector.tolist()) \
            .metric("cosine") \
            .limit(top_k) \
            .to_pandas()
        return results.to_dict('records')
```

### Phase 3: 混合检索优化 (Day 4)

```python
class HybridSearcher:
    """混合检索：向量 + 文本 + 重排序"""
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        # 1. 向量搜索 (召回候选)
        vector_results = self.vector_search(query, top_k * 4)
        
        # 2. 文本搜索 (补充召回)
        text_results = self.text_search(query, top_k * 2)
        
        # 3. 合并去重
        candidates = self.merge_results(vector_results, text_results)
        
        # 4. 重排序
        reranked = self.rerank(query, candidates)
        
        # 5. 返回 Top K
        return reranked[:top_k]
```

### Phase 4: 增量索引 (Day 5)

```python
class IncrementalIndexer:
    """增量索引更新"""
    
    def sync_from_markdown(self):
        """从 Markdown 文件同步到 LanceDB"""
        # 1. 读取所有记忆文件
        memories = self.parse_markdown_files()
        
        # 2. 获取已索引的 ID
        indexed_ids = set(self.get_indexed_ids())
        
        # 3. 找出新增和更新的
        new_memories = [m for m in memories if m.id not in indexed_ids]
        updated_memories = [m for m in memories 
                          if m.id in indexed_ids and m.modified]
        
        # 4. 批量更新
        if new_memories:
            self.lancedb.add_batch(new_memories)
        if updated_memories:
            self.lancedb.update_batch(updated_memories)
        
        return len(new_memories), len(updated_memories)
```

---

## 🔄 迁移策略

### 数据迁移计划

```python
def migrate_to_lancedb():
    """
    从现有系统迁移到 LanceDB
    """
    # 1. 读取所有现有记忆
    memories = []
    memories.extend(parse_session_state())
    memories.extend(parse_learnings())
    memories.extend(parse_errors())
    
    # 2. 生成嵌入
    print(f"正在生成 {len(memories)} 条记忆的嵌入向量...")
    
    # 3. 批量插入 LanceDB
    lancedb = LanceDBMemory()
    lancedb.init_table()
    
    batch_size = 100
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i+batch_size]
        lancedb.add_batch(batch)
        print(f"已处理 {i+len(batch)}/{len(memories)}")
    
    print("迁移完成!")
```

### 回滚方案

保留 OpenAI API 作为备选：

```python
class MemorySearchFallback:
    """记忆搜索带降级策略"""
    
    def search(self, query: str):
        try:
            # 优先使用 LanceDB
            return self.lancedb.search(query)
        except Exception as e:
            # 降级到 OpenAI API
            print(f"LanceDB 失败，降级到 API: {e}")
            return self.openai_search(query)
```

---

## 📊 性能基准测试

### 测试计划

```python
# benchmark.py

def benchmark_search():
    """搜索性能基准测试"""
    queries = [
        "用户邮箱是什么",
        "选股系统配置",
        "之前犯的错误",
    ]
    
    # LanceDB
    lancedb_times = []
    for query in queries:
        start = time.time()
        results = lancedb.search(query)
        lancedb_times.append(time.time() - start)
    
    # OpenAI API
    api_times = []
    for query in queries:
        start = time.time()
        results = openai_search(query)
        api_times.append(time.time() - start)
    
    print(f"LanceDB 平均延迟: {sum(lancedb_times)/len(lancedb_times)*1000:.1f}ms")
    print(f"OpenAI API 平均延迟: {sum(api_times)/len(api_times)*1000:.1f}ms")
```

---

## ⚠️ 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 嵌入模型质量不足 | 检索质量下降 | 用中文优化模型 BGE |
| LanceDB 不稳定 | 系统不可用 | 保留 OpenAI API 降级 |
| 模型下载失败 | 无法初始化 | 预下载模型到 workspace |
| 内存占用过高 | OOM | 使用轻量级模型，限制并发 |

---

## ✅ 检查清单

### 实施前
- [ ] 确认 Python 版本 >= 3.8
- [ ] 测试 LanceDB 安装
- [ ] 测试嵌入模型下载
- [ ] 备份现有记忆文件

### 实施中
- [ ] 开发 LanceDB 管理器
- [ ] 实现混合检索
- [ ] 实现增量索引
- [ ] 性能基准测试

### 实施后
- [ ] 数据完整性验证
- [ ] 检索质量对比测试
- [ ] 监控和告警配置
- [ ] 文档更新

---

## 🚀 下一步行动

1. **安装依赖**: `pip install lancedb sentence-transformers`
2. **测试嵌入模型**: 下载并测试 all-MiniLM-L6-v2
3. **开发核心模块**: 实现 LanceDBMemory 类
4. **数据迁移**: 将现有记忆迁移到 LanceDB
5. **集成测试**: 验证检索质量和性能

是否需要我开始安装依赖并开发核心模块？
