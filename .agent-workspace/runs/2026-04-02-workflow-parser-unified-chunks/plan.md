# Workflow Parser 统一 Chunks 数据结构 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 parser workflow 数据结构，从多级中间状态统一为全程单一 chunks 列表，merge_node 前置到 enrich_node 之前。

**Architecture:** WorkflowState 只保留 `chunks: List[Chunk]` 字段，所有节点读写同一列表。classify_node 直接输出 Chunk 而非 ClassifiedChunk/TypedSegment。graph 顺序调整为 classify → escalate → merge → enrich → transform。

**Tech Stack:** Python TypedDict, LangGraph StateGraph

---

## 任务依赖关系

```
Task 1 (models)  ──→  所有后续任务
Task 2 (classify_node)  ──→  Task 4 (graph)
Task 3 (merge_node)     ──→  Task 4 (graph)
Task 5 (escalate_node)  ──→  Task 4 (graph)
Task 6 (enrich_node)    ──→  Task 4 (graph)
Task 7 (transform_node) ──→  Task 4 (graph)
Task 4 (graph)         ──→  Task 9 (tests)
```

---

## Task 1: 重构 models.py — 定义统一 Chunk 类型

**Files:**
- Modify: `server/workflow_parser_kb/models.py`

**验收标准:**
- `Chunk` TypedDict 包含 spec 中定义的所有字段（chunk_id, doc_metadata, section_path, structure_type, semantic_type, content, raw_content, confidence, escalated, cross_refs, ref_context, failed_table_refs, transform_params, meta）
- `WorkflowState` 只有 md_content, doc_metadata, config, rules_dir, chunks, errors 六个字段
- 删除 `ClassifiedChunk`、`TypedSegment`、`ParserChunk` 类型定义
- 删除 `final_chunks` 字段
- `ParserResult` 使用 `Chunk` 而非 `ParserChunk`

---

## Task 2: 重构 classify_node — 直接输出 Chunk 列表

**Files:**
- Modify: `server/workflow_parser_kb/nodes/classify_node.py`
- Create: `server/tests/core/parser_workflow/test_classify_node_unified.py`

**验收标准:**
- 函数 `classify_raw_chunk` 返回 `List[Chunk]` 而非 `ClassifiedChunk`
- 每个 LLM SegmentItem 直接转为独立 Chunk
- 包含相邻合并逻辑：同 section_path + 同 semantic_type + 同 raw_content 的 Chunk 合并为一个
- `classify_node` 函数输出 `{"chunks": List[Chunk], "errors": List[str]}` 而非 `{"classified_chunks": ...}`
- 不再引用 `ClassifiedChunk` 或 `TypedSegment`

---

## Task 3: 重构 merge_node — 读写 state["chunks"]

**Files:**
- Modify: `server/workflow_parser_kb/nodes/merge_node.py`

**验收标准:**
- 输入从 `state["final_chunks"]` 改为 `state["chunks"]`
- 输出从 `{"final_chunks": merged}` 改为 `{"chunks": merged}`
- 合并规则不变（section_path 相同 + semantic_type 相同 + raw_content 相同）
- 合并行为不变（content 拼接、raw_content 不重复、cross_refs 并集等）

---

## Task 4: 更新 graph.py — 调整节点连接和 WorkflowState

**Files:**
- Modify: `server/workflow_parser_kb/graph.py`

**验收标准:**
- `WorkflowState` 初始化时使用 `chunks=[]` 而非 `raw_chunks=[], classified_chunks=[], final_chunks=[]`
- graph 边顺序：classify_node → (条件边) → escalate_node / merge_node → enrich_node → transform_node → merge_node → END
- 条件边判断：检查 `state["chunks"]` 中是否存在 `semantic_type == "unknown"` 的 chunk
- 不再引用 `classified_chunks`、`final_chunks`
- `run_parser_workflow` 和 `run_parser_workflow_stream` 的输出使用统一的 `chunks`

---

## Task 5: 重构 escalate_node — 读写 state["chunks"]

**Files:**
- Modify: `server/workflow_parser_kb/nodes/escalate_node.py`

**验收标准:**
- 遍历 `state["chunks"]` 而非 `state["classified_chunks"]`
- 原地更新 `semantic_type == "unknown"` 的 chunk，更新 `semantic_type`、`transform_params`、`escalated` 字段
- 输出 `{"chunks": updated_list}` 而非 `{"classified_chunks": ...}`

---

## Task 6: 重构 enrich_node — 读写 state["chunks"]

**Files:**
- Modify: `server/workflow_parser_kb/nodes/enrich_node.py`

**验收标准:**
- 遍历 `state["chunks"]` 而非 `state["classified_chunks"]`
- 对每个 chunk 填充 `cross_refs`、`ref_context`、`failed_table_refs`
- 输出 `{"chunks": updated_list}` 而非 `{"classified_chunks": ...}`

---

## Task 7: 重构 transform_node — 读写 state["chunks"]

**Files:**
- Modify: `server/workflow_parser_kb/nodes/transform_node.py`

**验收标准:**
- `apply_strategy` 函数接收 `List[Chunk]` 而非 `List[TypedSegment]`
- 遍历 `state["chunks"]` 而非 `state["classified_chunks"]`
- 输出 `{"chunks": transformed_list}` 而非 `{"final_chunks": ...}`

---

## Task 8: 更新 output.py — 保持 ClassifyOutput 结构不变

**Files:**
- Modify: `server/workflow_parser_kb/nodes/output.py`

**验收标准:**
- `ClassifyOutput` 和 `SegmentItem` 保持不变（classify_node 的 LLM prompt 仍需返回分段结果）
- 仅在 classify_node 内部将 `ClassifyOutput.segments` 展开为 flat `List[Chunk]`

---

## Task 9: 更新所有受影响的测试文件

**Files:**
- Modify: `server/tests/core/parser_workflow/test_merge_node.py`
- Modify: `server/tests/core/parser_workflow/test_enrich_node.py`
- Modify: `server/tests/core/parser_workflow/test_transform_node.py`
- Modify: `server/tests/core/parser_workflow/test_workflow.py`
- Modify: `server/tests/core/parser_workflow/test_classify_node.py`
- Modify: `server/tests/core/parser_workflow/test_classify_node_unit.py`

**验收标准:**
- 所有 `WorkflowState` 构造改用 `chunks` 字段
- 移除所有 `classified_chunks`、`final_chunks` 引用
- `DocumentChunk` / `ParserChunk` 替换为 `Chunk` 类型
- parser_workflow 目录下所有测试用例通过

---

## 端到端验证

**验收标准:**
- 运行完整 parser workflow，验证 chunks 从 classify_node 输出后经 merge 合并，再经 enrich 和 transform 处理
- 真实 LLM 输入一个 4KB 左右文档，classify 后出现 N 个细碎 chunks，merge 后合并为 M 个（M < N），enrich/transform 不再处理那些注定被合并的碎片
