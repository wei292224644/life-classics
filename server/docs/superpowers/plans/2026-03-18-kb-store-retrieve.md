# KB 存储与检索实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `store_to_kb(state)` 双写存储和 `search(query)` 混合检索，接入 parser_workflow 输出与 Agent 工具层。

**Architecture:** ChromaDB 存向量，SQLite FTS5 存 BM25 索引，写入时双写，查询时 RRF 融合两路结果后用已有本地 Reranker 重排。

**Tech Stack:** ChromaDB, SQLite FTS5, jieba, rank-bm25（不需要，FTS5 内置 BM25）, Qwen3-Reranker-0.6B（已有，`app/core/kb/vector_store/rerank.py`）

---

## 文件变更清单

### 修改现有文件
- `app/core/kb/writer/chroma_writer.py` — `content_type` 改 `semantic_type`，加 `raw_content` metadata
- `app/core/kb/writer/__init__.py` — 替换 `write_to_kb` → `store_to_kb`，删 Neo4j 代码
- `app/core/tools/knowledge_base.py` — 接入新 `search()`，删旧 `vector_store_manager`

### 新建文件
- `app/core/kb/writer/fts_writer.py` — SQLite FTS5 初始化、写入、删除
- `app/core/kb/retriever/__init__.py` — 公共 `search()` 入口
- `app/core/kb/retriever/vector_retriever.py` — ChromaDB 向量查询
- `app/core/kb/retriever/fts_retriever.py` — SQLite FTS5 BM25 查询
- `app/core/kb/retriever/rrf.py` — RRF 融合

### 删除文件
- `app/core/kb/writer/neo4j_writer.py`
- `app/core/kb/writer/models.py`（旧 `WriteResult`）
- `tests/core/kb/writer/test_neo4j_writer.py`

### 新建测试文件
- `tests/core/kb/writer/test_fts_writer.py`
- `tests/core/kb/writer/test_store_to_kb.py`（替换旧 `test_write_to_kb.py`）
- `tests/core/kb/retriever/test_vector_retriever.py`
- `tests/core/kb/retriever/test_fts_retriever.py`
- `tests/core/kb/retriever/test_rrf.py`
- `tests/core/kb/retriever/test_search.py`

---

## Task 1: 更新 `chroma_writer.py`

**修改：** `app/core/kb/writer/chroma_writer.py`
**测试：** `tests/core/kb/writer/test_chroma_writer.py`（已有，需更新）

**改什么：**
- `write()` 的 metadata 中 `content_type` → `semantic_type`（取 `chunk["semantic_type"]`）
- 加入 `raw_content`：`chunk["raw_content"][:1997] + "...（内容已截断）"` if 超 2000 字符，否则原样
- `delete_by_standard_no()` 不变

**潜在问题：**
- `chunk["raw_content"]` 可能为空字符串（transform 失败的 chunk），写空字符串进 metadata 没问题，不需要特殊处理
- ChromaDB metadata 不接受 `None`，确保所有值都是 str

**测试要验证：**
- metadata 中字段名是 `semantic_type` 不是 `content_type`
- `raw_content` 超 2000 字符时被截断且含截断标记
- `raw_content` 不足 2000 字符时原样写入

- [ ] 更新 `write()` 的 metadata 构造
- [ ] 运行已有测试确认不回归：`uv run pytest tests/core/kb/writer/test_chroma_writer.py -v`
- [ ] 更新测试断言（旧的断言会检查 `content_type` 字段，需改为 `semantic_type`）
- [ ] 确认测试通过
- [ ] commit

---

## Task 2: 新建 `fts_writer.py`

**新建：** `app/core/kb/writer/fts_writer.py`
**测试：** `tests/core/kb/writer/test_fts_writer.py`

**做什么：** 管理 SQLite FTS5 数据库，提供 `init_db()`、`write()`、`delete_by_standard_no()`。

**接口：**
```python
FTS_DB_PATH = "fts_db/kb_fts.db"  # 可通过 settings 覆盖

def init_db() -> None
    # 建 chunks 基础表 + chunks_fts 外部内容虚拟表（若已存在则跳过）
    # 建表后在 tokenized_content 上建 GIN 等价的 FTS5 索引

def write(chunks: List[DocumentChunk], doc_metadata: dict) -> None
    # 对每个 chunk：jieba.cut(chunk["content"]) → " ".join(words)
    # INSERT OR REPLACE INTO chunks (chunk_id, standard_no, semantic_type, section_path, tokenized_content)
    # 同步 INSERT INTO chunks_fts

def delete_by_standard_no(standard_no: str, errors: List[str]) -> bool
    # DELETE FROM chunks WHERE standard_no = ?
    # 同步 DELETE FROM chunks_fts WHERE chunk_id IN (...)
    # 文档不存在视为成功，返回 True；异常返回 False 并 append error
```

**表结构：**
```sql
-- 基础表（结构化字段，用于 WHERE 过滤）
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    standard_no TEXT NOT NULL,
    semantic_type TEXT NOT NULL,
    section_path TEXT NOT NULL,
    tokenized_content TEXT NOT NULL
);

-- FTS5 外部内容表（BM25 索引）
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    tokenized_content,
    content=chunks,
    content_rowid=rowid,
    tokenize='ascii'
);
```

**潜在问题：**
- `fts_db/` 目录需在首次使用前创建，`init_db()` 里 `os.makedirs` 确保存在
- SQLite FTS5 外部内容表删除时需手动同步（删 chunks 表后 FTS5 索引不自动更新），需显式 `DELETE FROM chunks_fts WHERE chunk_id IN (?)`
- jieba 首次 `import jieba; jieba.cut(...)` 会触发词典加载（约 1 秒），属正常现象，不是 bug
- SQLite 连接不是线程安全的，每次操作用 `with sqlite3.connect(path) as conn` 新建连接，不要用全局连接对象

**测试要验证：**
- `write()` 后能用 FTS5 MATCH 查到对应 chunk_id
- `delete_by_standard_no()` 后对应 standard_no 的记录消失
- 同一 standard_no 写两次不产生重复（需先 delete 再 write）
- 空 chunks 列表不报错

- [ ] 创建 `fts_db/` 目录（在 `.gitignore` 中加入 `fts_db/`，类似 `chroma_db/`）
- [ ] 实现 `fts_writer.py`
- [ ] 写测试（用临时 db 文件，`tmp_path` fixture）
- [ ] 运行测试确认通过
- [ ] commit

---

## Task 3: 重写 `writer/__init__.py`

**修改：** `app/core/kb/writer/__init__.py`
**删除：** `neo4j_writer.py`，`models.py`
**测试：** `tests/core/kb/writer/test_store_to_kb.py`（替换旧 `test_write_to_kb.py`）

**做什么：** 暴露唯一公共接口 `store_to_kb(state)`。

**接口：**
```python
class StoreResult(TypedDict):
    standard_no: str
    chunks_written: int
    ok: bool
    errors: List[str]

async def store_to_kb(state: WorkflowState) -> StoreResult
    # 1. 取 state["doc_metadata"]["standard_no"]，缺失则返回 ok=False
    # 2. 双删（ChromaDB + SQLite），任一失败返回 ok=False，终止写入
    # 3. 双写（ChromaDB + SQLite），各自独立捕获错误
    # 4. 任一写入失败则 ok=False
    # 注意：不传播 state["errors"]（parse 阶段警告与存储无关）
```

**潜在问题：**
- `fts_writer.init_db()` 需在 `store_to_kb` 首次调用时确保已执行，或在模块 import 时调用
- 两个 delete 可并行（`asyncio.gather`）：先并行执行 ChromaDB delete 和 SQLite delete，两者都成功才继续写入；任一失败则终止，不写入
- 两个 write 同样可并行（`asyncio.gather`）：ChromaDB 是 async，SQLite 用 `asyncio.to_thread` 包装；两者独立捕获错误，任一失败标记 `ok=False`

**测试要验证：**
- `standard_no` 缺失时返回 `ok=False`
- 正常流程写入后 `chunks_written == len(final_chunks)`
- 模拟 ChromaDB 删除失败时不执行写入（mock `chroma_writer.delete_by_standard_no` 返回 False）
- `StoreResult.errors` 不包含 `state["errors"]` 内容

- [ ] 删除 `neo4j_writer.py`、`models.py`
- [ ] 删除 `test_neo4j_writer.py`、`test_write_to_kb.py`
- [ ] 重写 `writer/__init__.py`
- [ ] 写新测试
- [ ] `uv run pytest tests/core/kb/writer/ -v`
- [ ] commit

---

## Task 4: 新建 `vector_retriever.py`

**新建：** `app/core/kb/retriever/vector_retriever.py`
**测试：** `tests/core/kb/retriever/test_vector_retriever.py`

**做什么：** 封装 ChromaDB 查询，返回 `(chunk_id, distance, metadata)` 列表。

**接口：**
```python
async def query(
    query_text: str,
    top_k: int = 20,
    filters: dict | None = None,  # 传给 ChromaDB where 参数
) -> List[tuple[str, float, dict]]:
    # 返回 [(chunk_id, distance, metadata), ...]
    # 调用 embed_batch([query_text]) 获取向量，然后 collection.query()
    # filters 直接透传给 ChromaDB 的 where 参数
```

**潜在问题：**
- ChromaDB `where` 参数格式：单字段 `{"standard_no": {"$eq": "GB 2762-2022"}}`，多字段用 `{"$and": [{"standard_no": {"$eq": "..."}}, {"semantic_type": {"$eq": "..."}}]}`。需在 `query()` 里把 `filters` dict 转换为 ChromaDB 格式：
  ```python
  def _to_chroma_where(filters: dict) -> dict:
      items = [{"k": {"$eq": v}} for k, v in filters.items()]  # 伪代码
      return items[0] if len(items) == 1 else {"$and": items}
  ```
- `collection.query()` 是同步，需 `asyncio.to_thread` 包装
- 返回的 `distances` 是 L2 距离（越小越相似），不是相似度分数

**测试要验证：**
- 正常查询返回 `top_k` 条（或更少）
- `filters` 能正确过滤（mock collection.query 验证 where 参数）
- 空 collection 不报错，返回空列表

- [ ] 创建 `tests/core/kb/retriever/` 目录和 `__init__.py`
- [ ] 实现 `vector_retriever.py`
- [ ] 写测试（mock ChromaDB collection）
- [ ] 运行测试
- [ ] commit

---

## Task 5: 新建 `fts_retriever.py`

**新建：** `app/core/kb/retriever/fts_retriever.py`
**测试：** `tests/core/kb/retriever/test_fts_retriever.py`

**做什么：** 封装 SQLite FTS5 BM25 查询，返回 `(chunk_id, bm25_score)` 列表。

**接口：**
```python
def query(
    query_text: str,
    top_k: int = 20,
    filters: dict | None = None,
) -> List[tuple[str, float]]:
    # 1. jieba.cut(query_text) → " ".join(words) → fts_query
    # 2. SELECT chunk_id, -rank FROM chunks_fts
    #    JOIN chunks ON chunks.rowid = chunks_fts.rowid
    #    WHERE chunks_fts MATCH ? [AND chunks.standard_no = ?]
    #    ORDER BY rank LIMIT top_k
    # 注意：FTS5 的 rank 是负数（越负越相关），取反后越大越好
    # filters 支持 standard_no、semantic_type 过滤（JOIN chunks 后 WHERE）
```

**潜在问题：**
- FTS5 `MATCH` 的查询词如果含 SQLite 特殊字符（`*`、`"`、`-`），会抛异常。需对 jieba 分词结果做简单清洗（过滤长度<1 的 token，过滤纯符号）
- `rank` 列是 FTS5 内置的 BM25 分数，是负数，查询时 `ORDER BY rank`（升序 = 最相关在前），取出后乘以 -1 转为正数
- 这是同步函数（SQLite 同步），调用方在 async 上下文中需用 `asyncio.to_thread` 包装（在 `retriever/__init__.py` 里处理）

**测试要验证：**
- 写入几条数据后能查到相关结果
- `filters` 正确过滤（只返回指定 standard_no 的结果）
- 查询词含特殊字符不崩溃

- [ ] 实现 `fts_retriever.py`
- [ ] 写测试（用临时 SQLite 文件）
- [ ] 运行测试
- [ ] commit

---

## Task 6: 新建 `rrf.py`

**新建：** `app/core/kb/retriever/rrf.py`
**测试：** `tests/core/kb/retriever/test_rrf.py`

**做什么：** 纯函数，合并两路检索结果，返回按 RRF 分排序的 chunk_id 列表。函数名统一为 `merge`（spec 中写的是 `rrf_merge`，以此计划为准）。

**接口：**
```python
def merge(
    vector_results: List[tuple[str, float]],  # (chunk_id, distance)，distance 越小越好
    bm25_results: List[tuple[str, float]],    # (chunk_id, bm25_score)，越大越好
    k: int = 60,
    max_results: int = 40,
) -> List[str]:
    # 对 vector_results 按 distance 升序排名（distance 越小 rank 越小）
    # 对 bm25_results 按 score 降序排名
    # RRF score = 1/(k + rank_vector) + 1/(k + rank_bm25)
    # 只在一路出现的 chunk：另一路 rank 视为 len(results) + 1（惩罚）
    # 返回按 RRF 分降序的 chunk_id 列表，最多 max_results 条
```

**潜在问题：**
- 两路都可能返回同一 chunk_id，需去重后合并
- 某路为空列表时，所有 chunk 的该路 rank = len(另一路) + 1，函数仍应正常工作（不能除以零）

**测试要验证：**
- 两路都有结果时正常合并
- 某路为空时另一路结果仍按排名返回
- 两路都为空时返回空列表
- 同一 chunk_id 在两路都出现时只在结果中出现一次

- [ ] 实现 `rrf.py`
- [ ] 写测试（纯单元测试，不依赖任何外部服务）
- [ ] 运行测试
- [ ] commit

---

## Task 7: 新建 `retriever/__init__.py`

**新建：** `app/core/kb/retriever/__init__.py`
**测试：** `tests/core/kb/retriever/test_search.py`

**做什么：** 组装完整检索管道，暴露 `search()` 公共接口。

**接口：**
```python
async def search(
    query: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> List[SearchResult]:
    # 1. 并行调用 vector_retriever.query() 和 asyncio.to_thread(fts_retriever.query)
    # 2. rrf.merge() 融合，得 chunk_id 列表（最多 40 条）
    # 3. 按 chunk_id 从 ChromaDB 批量取回 content + metadata（get() 接口）
    # 4. 组装成 List[Document]（LangChain Document，page_content=content）
    # 5. 调用已有 reranker.rerank(query, documents, top_k)
    # 6. 从 RerankedChunk 构造 SearchResult 返回

class SearchResult(TypedDict):
    chunk_id: str
    standard_no: str
    semantic_type: str
    section_path: str
    content: str       # LLM 转写文本
    raw_content: str   # 原始文本（来自 metadata）
    score: float       # reranker 相关性分数
```

**潜在问题：**
- ChromaDB `collection.get(ids=[...])` 是同步，需 `asyncio.to_thread` 包装
- **`raw_content` 只在 ChromaDB 里**：SQLite FTS 只存 `tokenized_content`，`raw_content` 必须通过 ChromaDB `get()` 获取，不能从 FTS 查询结果中取。RRF 后先拿 chunk_id 列表，再批量 `collection.get(ids=[...])` 取 content + metadata（含 raw_content），才能构造 SearchResult
- Reranker（`app/core/kb/vector_store/rerank.py`）第 210 行有模块级单例 `reranker = Reranker()`，在 import 时就加载 Qwen3-Reranker-0.6B 模型。**不要 `from app.core.kb.vector_store.rerank import reranker` 或 `import rerank_documents`**，这会在 import 时触发模型加载，导致测试极慢甚至 OOM。正确做法：只 `from app.core.kb.vector_store.rerank import Reranker`，在 `retriever/__init__.py` 内自己做懒初始化单例：
  ```python
  _reranker: Reranker | None = None
  def _get_reranker() -> Reranker:
      global _reranker
      if _reranker is None:
          _reranker = Reranker()
      return _reranker
  ```
- Reranker 是同步且 CPU/GPU 密集，需 `asyncio.to_thread` 包装

**测试要验证：**
- 正常流程端到端（mock vector_retriever、fts_retriever、reranker）
- `filters` 正确透传到两个 retriever
- `top_k` 控制最终返回数量
- 检索结果为空时返回空列表不报错

- [ ] 实现 `retriever/__init__.py`
- [ ] 写测试（mock 所有外部依赖）
- [ ] 运行测试
- [ ] commit

---

## Task 8: 更新 `knowledge_base.py` 工具

**修改：** `app/core/tools/knowledge_base.py`

**改什么：** 删除 `vector_store_manager` 依赖，改用 `search()`。

**注意：** `vector_store_manager` 在 `app/core/kb/vector_store/__init__.py` 中已被全部注释，当前 `knowledge_base.py` 在 import 时就会抛 `ImportError`，全量测试套件在 Task 8 之前就已经有失败。Task 8 完成后运行全量测试，预期失败数应归零（不是回归）。

**改后逻辑：**
```python
from app.core.kb.retriever import search

@tool
async def knowledge_base(query: str, top_k: int = 5) -> str:
    # results = await search(query, top_k=top_k)
    # 格式化 results（standard_no + raw_content + score）返回字符串
    # 异常捕获，返回 "知识库检索失败: {e}"
```

**潜在问题：**
- 旧工具是同步函数（`def`），改为 `async def` 后需确认 LangChain `@tool` 支持 async（支持，LangGraph 会正确 await）
- `SearchResult` 中的 `raw_content` 可能含截断标记，展示时原样透传给 LLM 即可

**测试要验证：**
- mock `search()` 验证工具正确格式化输出
- 空结果时返回"未检索到相关文档"
- 异常时返回错误信息字符串

- [ ] 更新 `knowledge_base.py`
- [ ] 写或更新测试
- [ ] 运行全量测试：`uv run pytest tests/ -v`
- [ ] commit

---

## 注意事项

**jieba 依赖：** 如果 `pyproject.toml` 中没有 `jieba`，需先 `uv add jieba`。

**fts_db 目录：** 检查根目录 `.gitignore`（不是 `agent-server/.gitignore`）是否已有 `fts_db/` 或 `agent-server/fts_db/`，参考 `chroma_db/` 的处理方式。

**旧 `vector_store` 目录：** `app/core/kb/vector_store/` 中的 `rerank.py` 继续保留（retriever 会复用），其他文件（如 `vector_store.py`、被注释的 `__init__.py`）可以保留不动，本次不清理。
