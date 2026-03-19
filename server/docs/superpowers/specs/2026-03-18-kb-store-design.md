# 知识库存储与检索设计

**日期**：2026-03-18
**状态**：已批准

---

## 背景

`parser_workflow` 已完成，能将 Markdown 文档转化为结构化的 `List[DocumentChunk]`。本设计覆盖两部分：
1. **存储**：`parser_workflow` 执行完后如何将结果写入知识库
2. **检索**：Agent 查询时如何从知识库召回相关 chunks

---

## 目标

- 提供 `store_to_kb(state)` 函数，在 `run_parser_workflow` 执行完后调用
- 双写：ChromaDB（向量） + SQLite FTS5（BM25 关键词）
- 提供 `search(query, filters?, top_k?)` 函数，支持混合检索 + 重排
- 支持幂等写入：先按 `standard_no` 删除旧数据，再写入新数据

---

## 决策记录

**不引入 Neo4j**：核心查询场景通过向量检索 + LLM 推理已足够覆盖。修改单和基础标准在向量检索时都会被召回，LLM 能推理出现行值。Neo4j 的图遍历价值目前是假设性的，等实际出现无法满足的查询需求时再引入。

**`raw_content` 存入 ChromaDB metadata**：检索结果返回给用户或 LLM 时需要展示原始可读文本。存入 metadata 保持单一存储，无额外依赖。`raw_content` 超过 2000 字符时截断并追加 `...（内容已截断）` 标记，避免 LLM 拿到无声明的残缺文本。

**BM25 使用 SQLite FTS5 + jieba**：项目规模约 1000+ 份标准、40k-100k chunks，纯内存 BM25 内存压力过大，重启需重建索引。SQLite FTS5 原生实现 BM25 评分，文件存储，零服务依赖，Python 标准库内置。PostgreSQL 专用于前端业务数据，不混入 KB chunks。

**全量重建 ChromaDB collection**：metadata schema 从 `content_type` 改为 `semantic_type`，所有文档重新走 `store_to_kb` 即可，无需迁移脚本。

**替换旧写入层**：`write_to_kb`、`WriteResult`（含 `chroma_ok`/`neo4j_ok`）、`neo4j_writer.py` 全部删除，由新的 `store_to_kb` + `StoreResult` 替代。不保留并行路径。

---

## 存储数据流

```
run_parser_workflow(md_content, doc_metadata) -> WorkflowState
    WorkflowState["final_chunks"]: List[DocumentChunk]
    WorkflowState["doc_metadata"]: dict

store_to_kb(state: WorkflowState) -> StoreResult
    ├── 前置校验：state["doc_metadata"]["standard_no"] 存在
    ├── delete_by_standard_no(standard_no)        # 双删：ChromaDB + SQLite
    ├── chroma_write(final_chunks, doc_metadata)  # 向量化 + upsert
    └── fts_write(final_chunks, doc_metadata)     # jieba 分词 + SQLite FTS5 insert
```

`run_parser_workflow` 返回 `WorkflowState`（`models.py` 中的 TypedDict），`store_to_kb` 直接读取 `state["final_chunks"]` 和 `state["doc_metadata"]`。

---

## 检索数据流

```
search(query, filters?, top_k=5) -> List[SearchResult]
    ├── 向量检索（ChromaDB，应用 filters 预过滤）  → Top-20 候选
    ├── BM25 检索（SQLite FTS5，应用 filters 后过滤） → Top-20 候选
    ├── RRF 融合（k=60）                            → 合并去重，Top-40
    └── 重排（DashScope Reranker）                  → 最终 top_k 条返回
```

`filters` 在向量侧通过 ChromaDB `where` 子句实现预过滤；在 FTS 侧通过子查询实现后过滤（FTS5 MATCH 结果中筛选 `standard_no` / `semantic_type` 匹配的行）。Reranker 最终输出数量等于 `top_k`。

---

## 存储接口设计

### 公共接口（`app/core/kb/writer/__init__.py`）

```python
class StoreResult(TypedDict):
    standard_no: str
    chunks_written: int
    ok: bool            # True 表示存储成功
    errors: List[str]   # 仅存储层错误，不传播 state["errors"]（parse 阶段警告）

async def store_to_kb(state: WorkflowState) -> StoreResult: ...
```

### ChromaDB 写入（修改现有 `app/core/kb/writer/chroma_writer.py`）

**Collection**：`gb_standards`

**Embedding 字段**：`chunk["content"]`（LLM 转写后规范化文本）

**Metadata schema**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `standard_no` | `doc_metadata["standard_no"]` | 必填，过滤和删除 |
| `doc_type` | `doc_metadata.get("doc_type", "")` | 跨文档过滤 |
| `semantic_type` | `chunk["semantic_type"]` | 替换旧 `content_type` 字段 |
| `section_path` | `"\|".join(chunk["section_path"])` | 章节路径 |
| `raw_content` | `chunk["raw_content"][:2000]` 或截断后加 `...（内容已截断）` | 原始文本 |

**异步**：`collection.upsert()` 通过 `asyncio.to_thread` 包装。

### SQLite FTS5 写入（新建 `app/core/kb/writer/fts_writer.py`）

**数据库文件**：`fts_db/kb_fts.db`（与 `chroma_db/` 同级）

**表结构**：

```sql
-- 普通表，存储结构化字段，支持 WHERE 过滤
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    standard_no TEXT NOT NULL,
    semantic_type TEXT NOT NULL,
    section_path TEXT NOT NULL,
    tokenized_content TEXT NOT NULL
);

-- FTS5 虚拟表，索引 tokenized_content，BM25 评分
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    tokenized_content,
    content=chunks,
    content_rowid=rowid,
    tokenize='ascii'
);
```

`chunks` 是基础表，`chunks_fts` 是外部内容表（content table），两者通过 `rowid` 关联。`filters` 查询通过 `chunks_fts JOIN chunks` 实现。

写入时：`jieba.cut(chunk["content"])` → 空格连接 → 存入 `tokenized_content`。
查询时：`jieba.cut(query)` → 空格连接 → `chunks_fts MATCH` + `JOIN chunks WHERE` 过滤。

---

## 检索接口设计

### 公共接口（`app/core/kb/retriever/__init__.py`）

```python
class SearchResult(TypedDict):
    chunk_id: str
    standard_no: str
    semantic_type: str
    section_path: str
    content: str        # LLM 转写文本（向量化用）
    raw_content: str    # 原始文本（展示用，可能含截断标记）
    score: float        # 重排后得分

async def search(
    query: str,
    filters: dict | None = None,   # 如 {"standard_no": "GB 2762-2022", "semantic_type": "limit"}
    top_k: int = 5,
) -> List[SearchResult]: ...
```

### RRF 融合（`app/core/kb/retriever/rrf.py`）

```python
def rrf_merge(
    vector_results: List[tuple[str, float]],   # (chunk_id, distance)
    bm25_results: List[tuple[str, float]],     # (chunk_id, bm25_score)
    k: int = 60,
) -> List[str]:
    # RRF score = 1/(k + rank_vector) + 1/(k + rank_bm25)
    # 返回 chunk_id 列表，按 RRF 分降序，最多 40 条
```

---

## 文件变更清单

### 新建文件

```
app/core/kb/writer/fts_writer.py
app/core/kb/retriever/__init__.py
app/core/kb/retriever/vector_retriever.py
app/core/kb/retriever/fts_retriever.py
app/core/kb/retriever/reranker.py
app/core/kb/retriever/rrf.py
```

### 修改现有文件

```
app/core/kb/writer/__init__.py      # 替换 write_to_kb → store_to_kb，删除 Neo4j 代码
app/core/kb/writer/chroma_writer.py # content_type → semantic_type，加 raw_content
app/core/tools/knowledge_base.py    # 过滤字段从 content_type 改为 semantic_type（如有引用）
```

### 删除文件

```
app/core/kb/writer/neo4j_writer.py  # 删除
app/core/kb/writer/models.py        # 删除旧 WriteResult（如存在）
```

---

## 存储错误处理

| 情形 | 行为 |
|------|------|
| `standard_no` 缺失 | 立即返回 `ok=False`，`chunks_written=0` |
| delete 失败（任一侧） | 写入 `errors`，终止写入，`ok=False` |
| `embed_batch` 失败 | 写入 `errors`，`chunks_written=0`，`ok=False` |
| ChromaDB upsert 失败 | 写入 `errors`，`ok=False` |
| SQLite insert 失败 | 写入 `errors`，`ok=False` |
| `final_chunks` 为空 | 正常返回，`chunks_written=0`，`ok=True` |
| delete 时文档不存在 | 视为成功，继续写入 |

ChromaDB 和 SQLite 独立捕获错误，任一失败均标记 `ok=False`，但两者不互相阻断（尽量都写）。

---

## 调用示例

```python
# 存储
state = await run_parser_workflow(md_content, doc_metadata)
result = await store_to_kb(state)
if not result["ok"]:
    logger.warning(f"store failed for {result['standard_no']}: {result['errors']}")

# 检索
results = await search(
    "婴儿食品中铅的限量",
    filters={"semantic_type": "limit"},
    top_k=5,
)
for r in results:
    print(r["standard_no"], r["raw_content"])
```
