# Parser Node 并发 LLM 调用实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `classify_node` 和 `transform_node` 从顺序同步改为 `asyncio.gather` 全并发执行。

**Architecture:** 两个 node 函数从 `def` 改为 `async def`，内部对所有 chunk 的 LLM 调用通过 `asyncio.gather` + `asyncio.to_thread` 并发执行，错误通过 `return_exceptions=True` 捕获，汇总到 `state["errors"]`。

**Tech Stack:** Python asyncio, LangGraph async invoke

---

## 文件变更概览

| 文件 | 改动 |
|------|------|
| `server/parser/nodes/classify_node.py` | `def` → `async def`，顺序循环 → `asyncio.gather` |
| `server/parser/nodes/transform_node.py` | `def` → `async def`，顺序循环 → `asyncio.gather` |
| `server/tests/core/parser_workflow/test_classify_node_unit.py` | 添加并发行为测试 |
| `server/tests/core/parser_workflow/test_transform_node_unit.py` | 添加并发行为测试 |

---

## Task 1: classify_node 改为 async def 并发执行

**Files:**
- Modify: `server/parser/nodes/classify_node.py`

**Changes:**
- 添加 `import asyncio`
- `def classify_node` → `async def classify_node`
- 移除 `_tracer.start_as_current_span`（并发下 span 边界不好对齐，简单处理：去掉 span 或保持同步逻辑不变）
- 顺序循环 → `results = await asyncio.gather(*[asyncio.to_thread(classify_raw_chunk, chunk, store) for chunk in state["raw_chunks"]], return_exceptions=True)`
- 分离成功/异常：`for i, result in enumerate(results)` → `isinstance(result, Exception)` 判断
- `errors.append(f"classify_node[{i}]: {result}")` → 到 `state.get("errors", []) + errors`
- metrics: `parser_chunks_processed_total.inc(len(classified))`（只用成功数）

---

## Task 2: classify_node 并发行为单元测试

**Files:**
- Modify: `server/tests/core/parser_workflow/test_classify_node_unit.py`

**Test:** `test_classify_node_concurrent_execution_with_exceptions`
- `@pytest.mark.asyncio` 装饰器（async 测试）
- `async def test_...`
- mock `parser.nodes.classify_node.asyncio.to_thread`：
  - 4 个 chunk 的 side_effect：3 个返回成功的 `ClassifyOutput`，1 个直接返回 `Exception("timeout")`（模拟 LLM 超时）
  - `to_thread` 被 mock 后不会真正调 LLM，所以不需要额外 mock `classify_raw_chunk`
- 调用 `await classify_node(state)`
- 验证 `classified_chunks` 长度 = 3（成功数）
- 验证 `errors` 长度 = 1，格式为 `"classify_node[1]: timeout"`

---

## Task 3: transform_node 改为 async def 并发执行

**Files:**
- Modify: `server/parser/nodes/transform_node.py`

**Changes:**
- 添加 `import asyncio`
- `def transform_node` → `async def transform_node`
- 移除 `_tracer.start_as_current_span`（同上）
- 顺序循环 → `results = await asyncio.gather(*[asyncio.to_thread(apply_strategy, ...) for classified in state["classified_chunks"]], return_exceptions=True)`
- 分离成功/异常，errors 追加到 `state.get("errors", [])`
- metrics: `parser_chunks_processed_total.inc(chunk_count)`（输入数，不变）

---

## Task 4: transform_node 并发行为单元测试

**Files:**
- Modify: `server/tests/core/parser_workflow/test_transform_node_unit.py`

**Test:** `test_transform_node_concurrent_execution_with_exceptions`
- `@pytest.mark.asyncio` 装饰器（async 测试）
- `async def test_...`
- mock `parser.nodes.transform_node.asyncio.to_thread`：
  - 3 个 classified chunks 的 side_effect：2 个返回 `List[DocumentChunk]`，1 个直接 `Exception("timeout")`
- 调用 `await transform_node(state)`
- 验证 `final_chunks` 长度 = 2（成功数）
- 验证 `errors` 长度 = 1，格式为 `"transform_node[1]: timeout"`

---

## Task 5: 回归测试

```bash
cd server && uv run pytest tests/core/parser_workflow/ -v --ignore="*real_llm*" --ignore="*real*"
```

**Expected:** 171+/173+ 通过。2 个预先存在的失败（`test_merge_node_with_real_artifact` 路径错误，`test_calculation_prompt_preserves_latex_block` 断言过时）可忽略。

---

## Task 6: 提交

```bash
git add server/parser/nodes/classify_node.py server/parser/nodes/transform_node.py
git add server/tests/core/parser_workflow/test_classify_node_unit.py server/tests/core/parser_workflow/test_transform_node_unit.py
git commit -m "feat(parser): parallelize LLM calls in classify_node and transform_node via asyncio.gather"
```
