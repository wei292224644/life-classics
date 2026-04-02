# Workflow Parser 统一 Chunks 数据结构

## 背景与目标

当前 parser workflow 存在过度设计的数据结构：

```
raw_chunks → classified_chunks → final_chunks
RawChunk   → ClassifiedChunk    → ParserChunk
            → TypedSegment[] (嵌套)
```

`classify_node` 对每个 `RawChunk` 调用 LLM，将内容拆成多个 `TypedSegment`（例如 4KB 文档分出 12 个 segments），这些碎片穿过 `escalate → enrich → transform` 全套节点做大量重复计算，最后才在 `merge_node` 合并。

**目标：**

1. 全程只有一个 `chunks` 列表，所有节点读写同一个列表
2. `merge_node` 前置到 `escalate_node` 之后、`enrich_node` 之前，减少无效计算
3. 删除 `ClassifiedChunk`、`TypedSegment`、`final_chunks` 三种中间类型

---

## 统一 Chunk 数据模型

`Chunk` 是贯穿 parser workflow 全程的唯一数据结构，每个节点逐步填充其字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `chunk_id` | classify_node | 基于 doc_id + section_path + content 生成 |
| `doc_metadata` | parse_node | 文档元数据 |
| `section_path` | parse_node / slice_node | 章节路径 |
| `structure_type` | structure_node | paragraph / list / table / formula / header |
| `semantic_type` | classify_node | metadata / scope / limit / procedure / material / calculation / definition / amendment |
| `content` | 各节点逐步更新 | 当前内容（清洗后/转换后） |
| `raw_content` | parse_node | 同源 raw chunk 内容 |
| `confidence` | classify_node | LLM 分类置信度 |
| `escalated` | escalate_node | 是否经过二次判断 |
| `cross_refs` | enrich_node | 识别的引用标识符列表 |
| `ref_context` | enrich_node | 已解析的被引用表格内容 |
| `failed_table_refs` | enrich_node | 未能解析的表格引用 |
| `transform_params` | classify_node | 转换策略和提示词 |
| `meta` | 各节点按需填充 | 扩展字段 |

---

## WorkflowState 结构

```python
class WorkflowState:
    md_content: str
    doc_metadata: dict
    config: dict
    rules_dir: str
    chunks: List[Chunk]    # 全程唯一的 chunk 列表
    errors: List[str]
```

删除字段：`raw_chunks`（parse_node 之后不再保留）、`classified_chunks`、`final_chunks`

---

## Graph 节点连接

```
parse_node → clean_node → structure_node → slice_node → classify_node
→ escalate_node → merge_node → enrich_node → transform_node → END
```

### 各节点职责

| 节点 | 读取 | 写入/更新 |
|------|------|---------|
| parse_node | `md_content` | `chunks`（仅 content、section_path、raw_content） |
| clean_node | `chunks` | 更新 `chunks[].content` |
| structure_node | `chunks` | 填充 `chunks[].structure_type` |
| slice_node | `chunks` | 切分或合并 `chunks` 列表 |
| classify_node | `chunks` | 填充 `chunks[].semantic_type`、`confidence`、`transform_params`；**按 semantic_type 合并相邻 chunks** |
| escalate_node | `chunks` | 原地更新 `semantic_type == "unknown"` 的 chunks，标记 `escalated=True` |
| merge_node | `chunks` | 合并相邻且 `semantic_type` + `section_path` 相同的 chunks |
| enrich_node | `chunks` | 填充 `cross_refs`、`ref_context`、`failed_table_refs` |
| transform_node | `chunks` | 按 `transform_params` 转换 `content`，更新 `meta` |

### 条件边

`classify_node` 之后检查是否有 `semantic_type == "unknown"` 的 chunk：
- 有 → 走 `escalate_node`
- 无 → 直接走 `merge_node`（不再走 `escalate_node`）

---

## merge_node 合并规则

合并条件（同时满足）：
1. `section_path` 相同
2. `semantic_type` 相同
3. `raw_content` 相同（来自同一 raw chunk）

合并行为：
- `content` 用 `\n\n` 拼接
- `raw_content` 不重复拼接（相同，直接取其一）
- `cross_refs` 取并集
- `failed_table_refs` 取并集
- `confidence` 取较低值
- `chunk_id` 重新生成

---

## 删除的数据类型

| 类型 | 原因 |
|------|------|
| `ClassifiedChunk` | 其作用已被 `Chunk` 取代 |
| `TypedSegment` | classify_node 直接输出 `Chunk`，不再需要 segment 嵌套 |
| `final_chunks` | `chunks` 即为最终结果 |

---

## 完成标准

1. `WorkflowState` 类型定义中只有 `chunks` 字段，无 `classified_chunks` / `final_chunks`
2. `classify_node` 输出直接写入 `state["chunks"]`，不再有 `classified_chunks` 输出 key
3. `merge_node` 在 graph 中的位置在 `escalate_node` 之后、`enrich_node` 之前
4. `enrich_node` 和 `transform_node` 读取和写入 `state["chunks"]`
5. 所有 parser workflow 单元测试通过
6. 端到端真实 LLM 运行，碎分问题由 merge_node 消化（不再穿透 enrich/transform 造成浪费）
