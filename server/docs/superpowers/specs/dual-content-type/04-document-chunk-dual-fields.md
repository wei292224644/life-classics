# Spec 04：DocumentChunk（models.py）双字段替换

## 问题现象

流水线最终输出的 `DocumentChunk`（`models.py` 中的 TypedDict）仍只有单字段 `content_type`，导致写入向量库前丢失了 structure/semantic 双维度信息，下游 RAG 检索无法按维度过滤。

## 根因

`models.py` 中定义了两个同名但不同性质的 `DocumentChunk`：

```python
# models.py（parser_workflow 输出模型）
class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    content_type: str       ← 单字段，流水线最终产物
    content: str
    raw_content: str
    meta: dict
```

同时，`document_chunk.py`（kb 层）中有另一个同名 class，使用旧的 `ContentType` 枚举。两个 `DocumentChunk` 共存于不同模块，造成命名混乱，但 parser_workflow 内部只使用 `models.py` 中的 TypedDict。

`transform_node.py` 在最终输出时将 `seg["content_type"]` 写入该字段：

```python
# transform_node.py
results.append(
    DocumentChunk(
        ...
        content_type=seg["content_type"],   ← 单字段
        ...
    )
)
```

## 发现方式

查看 `models.py` 第 36 行 `DocumentChunk.content_type: str`，再追踪 transform_node.py 中构造 DocumentChunk 的代码（第 78 行），确认单字段写入。

搜索 `DocumentChunk` 的消费方：

```bash
grep -rn "DocumentChunk" app/core/parser_workflow/ --include="*.py"
```

确认只有 `transform_node.py` 和 `enrich_node.py` 构造它，`graph.py` 中通过 `final_chunks` 将结果传出流水线。

## 方案

将 `models.py` 中 `DocumentChunk` 的 `content_type` 替换为双字段：

```python
# 修改前
class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    content_type: str
    content: str
    raw_content: str
    meta: dict

# 修改后
class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    structure_type: str
    semantic_type: str
    content: str
    raw_content: str
    meta: dict
```

`transform_node.py` 和 `enrich_node.py` 中构造 `DocumentChunk` 的代码同步更新（见 Spec 08）。

**注意**：`document_chunk.py`（kb 层）中的同名 class 是独立模块，不在本次 parser_workflow 重构范围内，暂不变更。

## 依赖关系

- 前置：Spec 03（TypedSegment 双字段确定后，DocumentChunk 才能从中读取两个字段）
- 后置：Spec 08（transform_node、enrich_node 构造 DocumentChunk 时的字段赋值）

## 受影响文件

- `app/core/parser_workflow/models.py`（修改 `DocumentChunk`）
