# Parser Node 并发 LLM 调用设计

## 背景

`classify_node` 和 `transform_node` 当前对每个 chunk/segment 的 LLM 调用是**顺序同步**执行的，一个完成后才下一个。当文档 chunk 数量较多时，整体耗时会线性叠加。

## 目标

通过 `asyncio.gather` 实现 node 级别的并发 LLM 调用，缩短端到端处理时间。

## 原则

- 线上 DashScope API 支持高并发，不设最大并发数限制
- 保持现有业务逻辑不变，仅改变执行方式
- 错误不中断流程：失败结果以异常形式捕获，最终汇总到 `state["errors"]`

---

## 方案 A（推荐）：全并发（asyncio.gather）

### 改动 1：classify_node

**文件**：`server/parser/nodes/classify_node.py`

```python
import asyncio

def classify_node(state: WorkflowState) -> dict:
    chunk_count = len(state["raw_chunks"])
    _start = time.perf_counter()
    _logger.info("classify_node_start", chunk_count=chunk_count)

    store = RulesStore(state["rules_dir"])

    # 并发执行所有 chunk 的 LLM 调用
    results = await asyncio.gather(
        *[asyncio.to_thread(classify_raw_chunk, chunk, store)
          for chunk in state["raw_chunks"]]
        , return_exceptions=True
    )

    # 分离成功结果和异常
    classified = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            _logger.error("classify_chunk_failed", chunk_index=i, error=str(result))
            errors.append({"node": "classify_node", "chunk_index": i, "error": str(result)})
        else:
            classified.append(result)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="classify_node").observe(duration)
    parser_chunks_processed_total.labels(node="classify_node").inc(len(classified))
    _logger.info(
        "classify_node_done",
        chunk_count=chunk_count,
        success_count=len(classified),
        error_count=len(errors),
        duration_ms=round(duration * 1000, 2),
        model=settings.CLASSIFY_MODEL,
    )
    return {"classified_chunks": classified, "errors": state.get("errors", []) + errors}
```

**关键点**：
- `asyncio.to_thread` 将同步的 `classify_raw_chunk` 扔到线程池执行，避免阻塞事件循环
- `return_exceptions=True` 保证所有 chunk 都执行完，失败转为异常对象而非直接抛出
- `state["errors"]` 贯穿流水线，最终由 `merge_node` 收集

### 改动 2：transform_node

**文件**：`server/parser/nodes/transform_node.py`

```python
async def transform_node(state: WorkflowState) -> dict:
    chunk_count = len(state["classified_chunks"])
    _start = time.perf_counter()
    _logger.info("transform_node_start", chunk_count=chunk_count)

    # 并发执行所有 classified chunk 的 apply_strategy
    tasks = [
        asyncio.to_thread(apply_strategy, classified["segments"], classified["raw_chunk"], state["doc_metadata"])
        for classified in state["classified_chunks"]
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_chunks = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            _logger.error("transform_chunk_failed", chunk_index=i, error=str(result))
            errors.append({"node": "transform_node", "chunk_index": i, "error": str(result)})
        else:
            final_chunks.extend(result)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="transform_node").observe(duration)
    parser_chunks_processed_total.labels(node="transform_node").inc(len(state["classified_chunks"]))
    _logger.info(
        "transform_node_done",
        chunk_count=chunk_count,
        output_chunk_count=len(final_chunks),
        error_count=len(errors),
        duration_ms=round(duration * 1000, 2),
        model=_transform_model(),
    )
    return {
        "final_chunks": final_chunks,
        "errors": state.get("errors", []) + errors,
    }
```

### 错误处理约定

- `return_exceptions=True` 捕获的异常统一 append 到 `state["errors"]`
- `errors` 字段格式：`[{"node": str, "chunk_index": int, "error": str}]`
- `merge_node` 或最终 `ParserResult` 应体现错误数量（`stats["error_count"]`）

---

## 并发生成（asyncio.gather）的条件

由于 `classify_node` 和 `transform_node` 是 LangGraph 节点，LangGraph 的 `StateGraph` 默认是同步调用。需要确认 `parser_graph` 的调用方（`run_parser_workflow`）使用 `ainvoke`（已确认是 async），节点才会以 async 方式执行。

---

## 测试策略

1. **单元测试**：mock `asyncio.gather` 验证并发行为和 `return_exceptions` 处理
2. **集成测试**：使用真实 API（mock patch LLM），验证并发确实发生且顺序无关
3. **回归测试**：现有 parser workflow 测试应全部通过

---

## 性能预估

假设单个 chunk LLM 调用耗时 T 秒，chunk 数量为 N：

| 场景 | 耗时 |
|------|------|
| 顺序执行 | N × T |
| 全并发 | ≈ T（理想情况，并发无上限） |

实际耗时受 token 速率和 API 服务端并发限制影响。
