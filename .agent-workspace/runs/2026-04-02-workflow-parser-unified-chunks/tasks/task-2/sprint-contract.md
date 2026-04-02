# Sprint Contract: Task 2 — classify_node 重构

## Workspace
`server/workflow_parser_kb/nodes/classify_node.py`

## 任务目标

重构 `classify_node`，使其直接输出 `List[Chunk]`，替代原有的 `ClassifiedChunk` 多级嵌套结构，并在 `classify_node` 内部实现"同 section_path + 同 semantic_type + 同 raw_content 相邻 Chunk 合并"逻辑。

## 完成标准

- [x] `classify_raw_chunk(raw_chunk: RawChunk, store: RulesStore, doc_metadata: dict)` 返回 `List[Chunk]` 而非 `ClassifiedChunk`
  - 每个 LLM `SegmentItem` 直接转为独立 `Chunk`（14 字段完整填充）
  - confidence < threshold 时，`semantic_type = "unknown"`，其他字段（transform_params 等）正常填充
  - `Chunk` 的 `chunk_id` 通过 `make_chunk_id(doc_id, section_path, content)` 生成（doc_id 取自 state["doc_metadata"]）
  - `cross_refs`、`ref_context`、`failed_table_refs` 初始为空列表/空字符串
  - `escalated = False`
- [x] 相邻合并逻辑：在 `classify_raw_chunk` 返回列表后，**按顺序**合并满足以下条件的相邻 Chunk：
  - `section_path` 相同
  - `semantic_type` 相同
  - `raw_content` 相同（来自同一 raw chunk，内容一致）
  - 合并行为：`content` 用 `\n\n` 拼接，`raw_content` 取其一，`cross_refs`/`failed_table_refs` 取并集，`confidence` 取较低值，`chunk_id` 重新生成
- [x] `classify_node(state: WorkflowState)` 输出 `{"chunks": List[Chunk], "errors": List[str]}` 而非 `{"classified_chunks": ...}`
  - 读取 `state["raw_chunks"]`（仍为 `List[RawChunk]`，待 Task 3/4 之后改为 `state["chunks"]`）
  - 并发逻辑不变（`asyncio.gather` + `Semaphore`）
- [x] 删除 `has_unknown` 逻辑（该判断由 graph 条件边通过检查 `semantic_type == "unknown"` 实现）
- [x] 删除 `POST_CLASSIFY_HOOKS` 调用（该 hook 机制待重新设计，不在本次 sprint 范围）
- [x] 不再引用 `TypedSegment`、`ClassifiedChunk` 作为结构类型（仅作类型别名 import 可保留）
- [ ] 测试文件 `server/tests/core/parser_workflow/test_classify_node_unified.py` 创建并通过

## 范围外

- 不修改 `slice_node`（仍输出 `raw_chunks`，由 Task 3 之后改为输出 `chunks`）
- 不修改 `graph.py` 节点连接（Task 4 负责）
- 不修改 `output.py`（`ClassifyOutput`/`SegmentItem` 结构不变，LLM prompt 仍返回分段结果）
- `enrich_node`、`escalate_node`、`transform_node`、`merge_node` 的适配（Task 3/5/6/7 负责）

## 实现方式

1. `classify_raw_chunk` 返回值类型改为 `List[Chunk]`
2. 每个 `SegmentItem` 构造为独立 `Chunk`（`chunk_id` 通过 `make_chunk_id` 生成，doc_id 来自 raw_chunk 的 meta）
3. 合并逻辑：在返回前，对 `List[Chunk]` 执行一次线性相邻合并
4. `classify_node` 遍历 `state["raw_chunks"]`，调用 `classify_raw_chunk`，将所有结果展平为 `List[Chunk]`
5. `POST_CLASSIFY_HOOKS` 调用暂时删除（待后续设计）

## 已知问题

- `classify_node` 仍读取 `state["raw_chunks"]`，因为 `slice_node` 仍输出 `raw_chunks`（Task 3 之后由 graph 连接调整解决）
- `classify_node` 不再调用 `POST_CLASSIFY_HOOKS`，原有的 hook 扩展机制需重新设计
- 由于 `TypedSegment = Chunk` 和 `ClassifiedChunk = Chunk` 是别名，类型注解不变但语义已变
