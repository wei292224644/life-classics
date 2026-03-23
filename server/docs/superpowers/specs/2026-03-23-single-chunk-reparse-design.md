# Single Chunk Re-parse Design

## 背景

当 `transform_node` 的 LLM 转写出错时（如表格转自然语言时理解错误），需要支持对该 chunk 单独重新执行 transform，而不是重跑整个文档。

**关键前提**：`classify_node` 只是拆分/合并 `raw_content`，不改变内容本身，因此 `ClassifiedChunk`（尤其是 `TypedSegment["content"]`）是可信的，只需要重跑 transform。

## 约束条件

- `slice_node` / `clean_node` / `classify_node` / `enrich_node` / `escalate_node` 不会重跑
- 可以接受富化引用（cross_refs）重新生成（可能与原结果略有差异）

## 详细流程

### Step 1 — 查询现有 chunk

从 ChromaDB 通过 `chunk_id` 获取：
- `raw_content` — chunk 原始 markdown（用于重解析）
- `section_path` — 章节路径（保留）
- `doc_metadata` — doc_id、standard_no、doc_type（保留）
- `chunk_id` — 旧 ID（用于删除）

### Step 2 — 构造 ClassifiedChunk

从 `DocumentChunk.metadata` 中取出 `segment_raw_content`（classify_node 输出的原始 segment 内容），重建 `TypedSegment`，再包装成 `ClassifiedChunk`：

```python
# segment_raw_content 来自 transform_node 的 meta字段，存储的是 classify_node 的原始输出
typed_segment = TypedSegment(
    content=metadata["segment_raw_content"],
    structure_type=chunk["structure_type"],
    semantic_type=chunk["semantic_type"],
    transform_params={
        "strategy": metadata.get("transform_strategy", "plain_embed"),
        "prompt_template": metadata.get("prompt_template", "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n"),
    },
    confidence=1.0,  # 不触发 escalate
    escalated=False,
    cross_refs=metadata.get("cross_refs", []),
    ref_context="",
    failed_table_refs=metadata.get("failed_table_refs", []),
)

classified = ClassifiedChunk(
    raw_chunk={
        "content": raw_content,
        "section_path": section_path,
        "char_count": len(raw_content),
    },
    segments=[typed_segment],
    has_unknown=False,
)
```

> `classify_node` 只拆分/合并 `raw_content`，不改变内容本身，所以 `segment_raw_content` 是可信的。

### Step 3 — 执行 transform_node

```python
state = WorkflowState(
    classified_chunks=[classified],
    doc_metadata=doc_metadata,
    errors=[],
)
transform_result = await transform_node(state)
# 输出: { "final_chunks": List[DocumentChunk], "errors": [...] }
```

`transform_node` 对每个 `TypedSegment` 执行 LLM 转写（table → 自然语言、formula 格式化等）。

### Step 4 — 执行 merge_node

```python
merge_result = merge_node({
    "final_chunks": transform_result["final_chunks"],
    "doc_metadata": doc_metadata,
})
# 输出: { "final_chunks": merged, "doc_metadata": doc_metadata }
```

合并同源、同类型的 chunk。

### Step 5 — 写回存储

1. 从 ChromaDB 删除旧 chunk（用旧 `chunk_id`）
2. 写入新 chunk（保留旧 `chunk_id`，保持向量检索连续性）
3. 同步更新 FTS

## 数据流

```
ChromaDB → 旧 DocumentChunk
                ↓
         提取 segment_raw_content + section_path + doc_metadata
                ↓
         重建 ClassifiedChunk
                ↓
         transform_node() → DocumentChunk
                ↓
         merge_node() → DocumentChunk (merged)
                ↓
         ChromaDB (delete old + insert new)
         FTS (update)
```

## 新增 API 端点

```
POST /api/chunks/{chunk_id}/reparse
```

Request: `{}`（chunk_id 在路径中，raw_content 等信息从存储中读取）

Response: 新的 `DocumentChunk`

## 缺失节点的影响

| 节点 | 影响 |
|---|---|
| classify_node | 不重跑，保留现有分类结果 |
| enrich_node | cross_refs 引用关系可能重建，与原结果可能有差异 |
| merge_node | 合并逻辑重跑，同源 chunk 会重新合并 |

## 实现工作量

低。只需新增薄薄一层编排：查询 → 重建 ClassifiedChunk → transform_node → merge_node → 写回。
