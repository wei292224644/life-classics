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
- 独立调用：写入流程与 parser 流程解耦，由调用方串联

---

## 模块结构

```
app/core/kb_writer/
├── __init__.py       # 暴露 write_to_kb
├── models.py         # WriteResult
├── chroma_writer.py  # ChromaDB 写/删逻辑
└── neo4j_writer.py   # Neo4j 写/删逻辑
```

---

## 主函数

删除操作拆入各自 writer 中执行（`chroma_writer.delete_by_standard_no` 和 `neo4j_writer.delete_by_standard_no`），由 `write_to_kb` 先串行删除，再并行写入。

**前置条件**：`result["doc_metadata"]["standard_no"]` 必须存在（由 `parse_node` 的校验保证）。若缺失，`write_to_kb` 直接返回带 error 的 `WriteResult`，不抛异常。

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

**调用方式**（独立于 parser）：

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
1. 批量调用项目配置的 embedding 模型（通过 `app/core/llm` 工厂获取），将所有 chunk 的 `content` 并发向量化
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
(:Document {standard_no, title, doc_type, doc_type_source})
    -[:HAS_CHUNK]->
(:Chunk {chunk_id, content_type, section_path, content, raw_content})
```

`section_path` 存为数组（Neo4j 原生支持），方便按层级筛选。`DocumentChunk.meta` 字段不写入图库（仅用于调试）。

**写入 Cypher**：

```cypher
MERGE (d:Document {standard_no: $standard_no})
SET d.title = $title, d.doc_type = $doc_type, d.doc_type_source = $doc_type_source

CREATE (c:Chunk {chunk_id: $chunk_id, content_type: $content_type,
                  section_path: $section_path, content: $content,
                  raw_content: $raw_content})
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
- `write_to_kb` 集成测试 mock 两个 writer，覆盖：
  - 正常路径：验证调用顺序（先 delete，再并行 write）
  - 单侧删除失败：对应侧写入被跳过，另一侧正常，`errors` 包含错误信息
  - 单侧写入失败：`errors` 包含错误，另一侧不受影响
- 不写真实 DB 的集成测试，real-DB 测试单独标注并默认跳过
