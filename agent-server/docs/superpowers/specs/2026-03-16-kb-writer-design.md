# 知识库写入流程设计

**日期**：2026-03-16
**状态**：已确认

---

## 背景

`parser_workflow` 已能将 Markdown 文档处理为 `List[DocumentChunk]`。本设计描述如何将这批 chunk 持久化写入知识库（ChromaDB + Neo4j），供 RAG Agent 检索使用。

`DocumentChunk.content` 经 `transform_node` 处理后始终为字符串（LLM 转写的自然语言文本），可直接写入 ChromaDB。

---

## 目标

- 将 `ParserResult` 中的 `DocumentChunk` 写入 ChromaDB（向量检索）和 Neo4j（图关系查询）
- 支持幂等写入：同一文档重复写入时，先删除旧数据再写入新数据
- 独立调用：写入流程与 parser 流程解耦，由调用方（`POST /api/doc/upload`）串联

---

## 模块结构

`kb_writer` 和 `kb_reader` 共享客户端和 embedding 工具，统一放在 `app/core/kb/` 下：

```
app/core/kb/
├── clients.py          # ChromaDB + Neo4j 客户端初始化（单例）
├── embeddings.py       # embedding 调用（writer 批量向量化，reader 查询向量化）
├── writer/
│   ├── __init__.py     # 暴露 write_to_kb
│   ├── models.py       # WriteResult
│   ├── chroma_writer.py
│   └── neo4j_writer.py
└── reader/
    └── ...             # 后续实现
```

---

## 主函数

`write_to_kb` 先串行删除旧数据，再并行写入两侧。删除操作各自封装在对应 writer 中。

**前置条件**：`result["doc_metadata"]["standard_no"]` 必须存在（由 `parse_node` 的校验保证）。若缺失，直接返回带 error 的 `WriteResult`，不抛异常。

```python
async def write_to_kb(result: ParserResult) -> WriteResult:
    standard_no = result["doc_metadata"].get("standard_no")
    errors: List[str] = list(result["errors"])

    if not standard_no:
        errors.append("ERROR: standard_no missing, cannot write to KB")
        return WriteResult(standard_no="", chunks_written=0,
                           chroma_ok=False, neo4j_ok=False, errors=errors)

    # 串行删除旧数据（各自独立，失败则跳过对应侧写入）
    chroma_delete_ok = await chroma_writer.delete_by_standard_no(standard_no, errors)
    neo4j_delete_ok = await neo4j_writer.delete_by_standard_no(standard_no, errors)

    # 并行写入，各自捕获异常，ok 标志绑定到对应 writer
    async def do_chroma() -> bool:
        try:
            await chroma_writer.write(result["chunks"], result["doc_metadata"])
            return True
        except Exception as e:
            errors.append(f"chroma write error: {e}")
            return False

    async def do_neo4j() -> bool:
        try:
            await neo4j_writer.write(result["chunks"], result["doc_metadata"])
            return True
        except Exception as e:
            errors.append(f"neo4j write error: {e}")
            return False

    chroma_ok, neo4j_ok = await asyncio.gather(
        do_chroma() if chroma_delete_ok else asyncio.coroutine(lambda: False)(),
        do_neo4j() if neo4j_delete_ok else asyncio.coroutine(lambda: False)(),
    )

    return WriteResult(
        standard_no=standard_no,
        chunks_written=len(result["chunks"]),  # 写入尝试的 chunk 总数
        chroma_ok=chroma_ok,
        neo4j_ok=neo4j_ok,
        errors=errors,
    )
```

**语义说明**：
- `chunks_written` 表示写入尝试的 chunk 数量（即 `len(result["chunks"])`），而非实际成功数；调用方通过 `chroma_ok`/`neo4j_ok` 判断各侧是否写入成功
- 写入为"尽力而为"（best-effort）。删除成功但写入失败时，对应侧数据将丢失，调用方需通过 `WriteResult.errors` 检测并决定是否重试

**调用方式**（`parser_workflow` 完成后由上层串联）：

```python
parser_result = await run_parser_workflow(md_content, doc_metadata, rules_dir)
write_result = await write_to_kb(parser_result)
```

---

## WriteResult 模型

与 `parser_workflow` 保持一致，使用 `TypedDict`：

```python
class WriteResult(TypedDict):
    standard_no: str
    chunks_written: int
    chroma_ok: bool
    neo4j_ok: bool
    errors: List[str]
```

---

## ChromaDB 写入

**Collection**：单一 collection `gb_standards`，metadata 字段区分文档和类型。

**每条记录字段**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `id` | `chunk["chunk_id"]` | 唯一标识 |
| `document` | `chunk["content"]` | 向量化的自然语言文本（始终为字符串） |
| `metadata.standard_no` | `doc_metadata["standard_no"]` | 用于按文档过滤删除 |
| `metadata.content_type` | `chunk["content_type"]` | 检索时可按类型过滤 |
| `metadata.section_path` | `"|".join(chunk["section_path"])` | 序列化为字符串（ChromaDB 不支持数组）；仅用于过滤，结构查询走 Neo4j |
| `metadata.doc_type` | `doc_metadata["doc_type"]` | 文档类型 |

**删除**：使用 ChromaDB 的 `$eq` 过滤语法：

```python
collection.delete(where={"standard_no": {"$eq": standard_no}})
```

**写入**：
1. 通过 `embeddings.py` 批量并发向量化所有 chunk 的 `content`
2. 将向量通过 `embeddings` 参数显式传入 `collection.upsert()`，不依赖 ChromaDB 内置 embedding function

```python
# 伪代码
embeddings = await embed_batch([c["content"] for c in chunks])  # 并发
collection.upsert(
    ids=[c["chunk_id"] for c in chunks],
    documents=[c["content"] for c in chunks],
    embeddings=embeddings,
    metadatas=[{...} for c in chunks],
)
```

---

## Neo4j 写入

**图模型**：

```
(:Document {
    standard_no, title, doc_type, doc_type_source,
    publish_date, implement_date, status, issuing_authority
})
    -[:HAS_CHUNK]->
(:Chunk {chunk_id, content_type, section_path, content, raw_content})

(:Document)-[:REPLACES]->(:Document)    # 本标准替代的旧标准
(:Document)-[:REPLACED_BY]->(:Document) # 本标准被哪个新标准替代
```

- `section_path` 存为数组（Neo4j 原生支持），方便按层级筛选
- `DocumentChunk.meta` 字段不写入图库（仅用于调试）
- `REPLACES`/`REPLACED_BY` 关系通过 `doc_metadata` 中的对应字段写入，如字段不存在则跳过

**写入接口**：`neo4j_writer` 同时提供两个接口：
- `write_one(chunk, doc_metadata)` — 单条写入
- `write_batch(chunks, doc_metadata)` — 批量写入，使用 `UNWIND` 一次事务完成，性能更好；`write_to_kb` 使用此接口

**批量写入 Cypher**：

```cypher
MERGE (d:Document {standard_no: $standard_no})
SET d.title = $title, d.doc_type = $doc_type, d.doc_type_source = $doc_type_source,
    d.publish_date = $publish_date, d.implement_date = $implement_date,
    d.status = $status, d.issuing_authority = $issuing_authority

WITH d
UNWIND $chunks AS chunk
CREATE (c:Chunk {
    chunk_id: chunk.chunk_id,
    content_type: chunk.content_type,
    section_path: chunk.section_path,
    content: chunk.content,
    raw_content: chunk.raw_content
})
CREATE (d)-[:HAS_CHUNK]->(c)
```

**删除 Cypher**（使用 `OPTIONAL MATCH` 兼容无 chunk 的文档）：

```cypher
MATCH (d:Document {standard_no: $standard_no})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
DETACH DELETE c, d
```

---

## 错误处理

- 删除失败：`delete_by_standard_no` 返回 `False`，记录错误，跳过对应侧写入
- 写入失败：捕获异常，记录到 `errors`，不影响另一侧
- `write_to_kb` 不抛异常，调用方通过 `WriteResult.errors` 判断是否成功
- 删除时文档不存在：视为正常，返回 `True`，不计入错误
- 失败后数据可能处于部分删除状态，调用方需在 `errors` 非空时决定是否重试

---

## 测试策略

- `chroma_writer` 和 `neo4j_writer` 各自独立单测，mock 客户端
- `embeddings.py` 单测，mock embedding 模型
- `write_to_kb` 集成测试 mock 两个 writer，覆盖：
  - 正常路径：验证调用顺序（先 delete，再并行 write）
  - 单侧删除失败：对应侧写入被跳过，另一侧正常，`errors` 包含错误信息
  - 单侧写入失败：`errors` 包含错误，另一侧不受影响
  - `standard_no` 缺失：直接返回 error WriteResult
- 不写真实 DB 的集成测试，real-DB 测试单独标注并默认跳过
