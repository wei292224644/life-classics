# 知识库写入流程设计

**日期**：2026-03-16
**状态**：已确认

---

## 背景

`parser_workflow` 已能将 Markdown 文档处理为 `List[DocumentChunk]`。本设计描述如何将这批 chunk 持久化写入知识库（ChromaDB + Neo4j），供 RAG Agent 检索使用。

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

```python
async def write_to_kb(result: ParserResult) -> WriteResult:
    standard_no = result["doc_metadata"]["standard_no"]
    await delete_existing(standard_no)
    await asyncio.gather(
        write_to_chroma(result["chunks"], result["doc_metadata"]),
        write_to_neo4j(result["chunks"], result["doc_metadata"]),
    )
    return WriteResult(
        standard_no=standard_no,
        chunks_written=len(result["chunks"]),
        chroma_ok=True,
        neo4j_ok=True,
        errors=result["errors"],
    )
```

**调用方式**（独立于 parser）：

```python
parser_result = await run_parser_workflow(md_content, doc_metadata, rules_dir)
write_result = await write_to_kb(parser_result)
```

---

## WriteResult 模型

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
| `id` | `chunk["chunk_id"]` | 唯一标识，用于幂等删除 |
| `document` | `chunk["content"]` | 向量化的自然语言文本 |
| `metadata.standard_no` | `doc_metadata["standard_no"]` | 用于按文档过滤删除 |
| `metadata.content_type` | `chunk["content_type"]` | 检索时可按类型过滤 |
| `metadata.section_path` | `"|".join(chunk["section_path"])` | 序列化为字符串（ChromaDB 不支持数组） |
| `metadata.doc_type` | `doc_metadata["doc_type"]` | 文档类型 |

**删除**：按 metadata 过滤删除：

```python
collection.delete(where={"standard_no": standard_no})
```

**写入**：批量 `upsert`，embedding 由 ChromaDB embedding function 自动生成。

---

## Neo4j 写入

**图模型**：

```
(:Document {standard_no, title, doc_type, doc_type_source})
    -[:HAS_CHUNK]->
(:Chunk {chunk_id, content_type, section_path, content, raw_content})
```

`section_path` 存为数组（Neo4j 原生支持），方便按层级筛选。

**写入 Cypher**：

```cypher
MERGE (d:Document {standard_no: $standard_no})
SET d.title = $title, d.doc_type = $doc_type, d.doc_type_source = $doc_type_source

CREATE (c:Chunk {chunk_id: $chunk_id, content_type: $content_type,
                  section_path: $section_path, content: $content,
                  raw_content: $raw_content})
CREATE (d)-[:HAS_CHUNK]->(c)
```

**删除 Cypher**：

```cypher
MATCH (d:Document {standard_no: $standard_no})-[:HAS_CHUNK]->(c:Chunk)
DETACH DELETE c
WITH d
DETACH DELETE d
```

---

## 错误处理

- ChromaDB 或 Neo4j 任一失败：捕获异常、记录到 `errors`，不中断另一路写入
- `write_to_kb` 不抛异常，调用方通过 `WriteResult.errors` 判断是否成功
- 删除时文档不存在：视为正常，不计入错误
- `chroma_ok` / `neo4j_ok` 字段反映各自写入是否成功

---

## 测试策略

- `chroma_writer` 和 `neo4j_writer` 各自独立单测，mock 客户端
- `write_to_kb` 集成测试 mock 两个 writer，验证调用顺序（先 delete，再并行 write）
- 不写真实 DB 的集成测试，real-DB 测试单独标注并默认跳过
