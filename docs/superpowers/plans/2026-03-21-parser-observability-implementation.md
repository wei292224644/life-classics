# Parser Workflow 可观测性埋点实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将整个 parser workflow（9个节点）完整接入 structlog + Prometheus metrics + OpenTelemetry span 追踪。

**Architecture:** 在每个 node 函数内部用 `tracer.start_as_current_span()` 创建 span；token 计数集中在 `invoke_structured()` 成功返回时处理；`graph.py` 的 `run_parser_workflow_stream` 入口创建 root span 贯穿整条 pipeline。

**Tech Stack:** opentelemetry-api, opentelemetry-sdk, structlog, prometheus-client, LangGraph astream_events

---

## 文件概览

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `server/observability/metrics.py` | Modify | 新增 `parser_workflow_duration_seconds` |
| `server/parser/structured_llm/invoker.py` | Modify | token 计数 + print()→structlog |
| `server/parser/graph.py` | Modify | root span + workflow duration |
| `server/parser/nodes/classify_node.py` | Modify | 添加 OTel span |
| `server/parser/nodes/escalate_node.py` | Modify | 添加 OTel span |
| `server/parser/nodes/transform_node.py` | Modify | 添加 OTel span |
| `server/parser/nodes/parse_node.py` | Modify | 添加 span + structlog + metrics |
| `server/parser/nodes/clean_node.py` | Modify | 添加 span + structlog + metrics |
| `server/parser/nodes/structure_node.py` | Modify | 添加 span + structlog + metrics + llm_calls_total |
| `server/parser/nodes/slice_node.py` | Modify | 移除 print() + 添加 span + structlog + metrics |
| `server/parser/nodes/enrich_node.py` | Modify | 添加 span + structlog + metrics |
| `server/parser/nodes/merge_node.py` | Modify | 添加 span + structlog + metrics |

---

## Task 1: metrics.py 新增 pipeline 总耗时指标

**Files:**
- Modify: `server/observability/metrics.py`

- [ ] **Step 1: 在 metrics.py 末尾添加新 Histogram**

```python
parser_workflow_duration_seconds = Histogram(
    "parser_workflow_duration_seconds",
    "Parser 完整流水线处理耗时（秒）",
    ["doc_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)
```

- [ ] **Step 2: 验证指标可导入**

```bash
cd server && uv run python3 -c "from observability.metrics import parser_workflow_duration_seconds; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add server/observability/metrics.py
git commit -m "feat(metrics): add parser_workflow_duration_seconds histogram"
```

---

## Task 2: invoker.py token 计数与 print 替换

**Files:**
- Modify: `server/parser/structured_llm/invoker.py`

- [ ] **Step 1: 读取 invoker.py 第 137-148 行，确认成功返回位置**

确认 `result = create_fn(...)` 和 `return result` 的位置。

- [ ] **Step 2: 在成功返回前添加 token 计数**

在 `result = create_fn(...)` 之后、`return result` 之前添加：

```python
        # Token 计数
        usage = getattr(result, "usage", None)
        if usage:
            llm_tokens_total.labels(node=node_name, model=resolved_model, type="prompt").inc(usage.prompt_tokens or 0)
            llm_tokens_total.labels(node=node_name, model=resolved_model, type="completion").inc(usage.completion_tokens or 0)
```

在文件顶部添加导入（如果还没有）：

```python
from observability.metrics import llm_tokens_total
```

- [ ] **Step 3: 将第 190 行的 `print()` 重试日志改为 structlog**

将：
```python
print(f"[{node_name}] 可恢复错误（timeout/network），第 {attempt + 1}/{max_retries + 1} 次尝试: {e}")
```

替换为：
```python
_logger.warning(
    "structured_llm_retry",
    node_name=node_name,
    provider=resolved_provider,
    model=resolved_model,
    attempt=attempt + 1,
    max_retries=max_retries + 1,
    error=str(e),
)
```

- [ ] **Step 4: 验证语法正确**

```bash
cd server && uv run python3 -c "from parser.structured_llm.invoker import invoke_structured; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add server/parser/structured_llm/invoker.py
git commit -m "feat(parser): add token counting to invoke_structured and replace print with structlog"
```

---

## Task 3: graph.py Root Span + Workflow Duration

**Files:**
- Modify: `server/parser/graph.py`

- [ ] **Step 1: 读取 graph.py 确认 import 区域**

确认 `run_parser_workflow` 和 `run_parser_workflow_stream` 函数位置。

- [ ] **Step 2: 在文件顶部添加导入**

```python
import time
from opentelemetry import trace
from observability.metrics import parser_workflow_duration_seconds
```

添加：
```python
_tracer = trace.get_tracer(__name__)
```

- [ ] **Step 3: 修改 `run_parser_workflow` 函数**

在 `initial_state = ...` 之前添加计时，在 `result_state = await parser_graph.ainvoke(...)` 之后添加 observe。

在函数入口创建 root span：
```python
async def run_parser_workflow(...) -> ParserResult:
    start_time = time.perf_counter()
    with _tracer.start_as_current_span("parser_workflow") as root_span:
        root_span.set_attribute("parser.doc_id", doc_metadata.get("doc_id", ""))
        initial_state = WorkflowState(...)
        result_state = await parser_graph.ainvoke(initial_state)
        doc_type = result_state.get("doc_metadata", {}).get("doc_type", "unknown")
        root_span.set_attribute("parser.doc_type", doc_type)
    duration = time.perf_counter() - start_time
    parser_workflow_duration_seconds.labels(doc_type=doc_type).observe(duration)
    # ... 现有 return ...
```

- [ ] **Step 4: 修改 `run_parser_workflow_stream` 函数**

```python
async def run_parser_workflow_stream(...) -> AsyncGenerator[dict, None]:
    start_time = time.perf_counter()
    doc_id = doc_metadata.get("doc_id", "")
    with _tracer.start_as_current_span("parser_workflow_stream") as root_span:
        root_span.set_attribute("parser.doc_id", doc_id)
        initial_state = WorkflowState(...)
        async for event in parser_graph.astream_events(initial_state, version="v2"):
            # ... 现有逻辑 ...

    # 在流结束后（finally 或 after loop）计时并 observe
    # 注意：root_span 需要在完整流结束后才关闭，用 try/finally
```

最终方案（确保 span 在流完全结束后才关闭）：
```python
async def run_parser_workflow_stream(...) -> AsyncGenerator[dict, None]:
    start_time = time.perf_counter()
    doc_id = doc_metadata.get("doc_id", "")
    doc_type = "unknown"  # 先置默认值，finally 时会从 workflow_done 事件更新
    initial_state = WorkflowState(...)
    try:
        with _tracer.start_as_current_span("parser_workflow_stream") as root_span:
            root_span.set_attribute("parser.doc_id", doc_id)
            async for event in parser_graph.astream_events(initial_state, version="v2"):
                # 在 "workflow_done" 事件中捕获最终 doc_type
                if event.get("event") == "on_chain_end":
                    output = event.get("data", {}).get("output") or {}
                    doc_type = output.get("doc_metadata", {}).get("doc_type", "unknown")
                    root_span.set_attribute("parser.doc_type", doc_type)
                # ... 现有 yield 逻辑（阶段事件 + workflow_done）...
    finally:
        parser_workflow_duration_seconds.labels(doc_type=doc_type or "unknown").observe(
            time.perf_counter() - start_time
        )
```

> **注意**：`doc_type` 在 `structure_node` 执行后才写入 `doc_metadata`，从 `workflow_done` 事件的 `output` 中读取比依赖 state mutation 更可靠。

- [ ] **Step 5: 验证语法正确**

```bash
cd server && uv run python3 -c "from parser.graph import run_parser_workflow, run_parser_workflow_stream; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add server/parser/graph.py
git commit -m "feat(parser): add root OTel span and workflow duration metric to graph"
```

---

## Task 4: 为已部分埋点节点添加 OTel Span

**Files:**
- Modify: `server/parser/nodes/classify_node.py`
- Modify: `server/parser/nodes/escalate_node.py`
- Modify: `server/parser/nodes/transform_node.py`

每个文件仅需添加 OTel span（structlog + metrics 已存在）。以 `classify_node.py` 为例：

- [ ] **Step 1: 在 classify_node.py 顶部添加导入**

```python
from opentelemetry import trace

_tracer = trace.get_tracer(__name__)
```

- [ ] **Step 2: 在 `classify_node` 函数内包裹现有逻辑**

将 `classify_node` 函数的整个函数体包裹在 `with _tracer.start_as_current_span("classify_node") as span:` 中，并在 span 内设置属性：

```python
def classify_node(state: WorkflowState) -> dict:
    _start = time.perf_counter()
    chunks_in = len(state["raw_chunks"])
    _logger.info("classify_node_start", chunk_count=chunks_in)

    with _tracer.start_as_current_span("classify_node") as span:
        span.set_attribute("parser.node", "classify_node")
        span.set_attribute("parser.doc_id", state.get("doc_metadata", {}).get("doc_id", ""))
        span.set_attribute("parser.chunk_count.in", chunks_in)

        store = RulesStore(state["rules_dir"])
        classified: List[ClassifiedChunk] = [
            classify_raw_chunk(chunk, store) for chunk in state["raw_chunks"]
        ]

        span.set_attribute("parser.chunk_count.out", len(classified))

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="classify_node").observe(duration)
    parser_chunks_processed_total.labels(node="classify_node").inc(len(classified))
    _logger.info(
        "classify_node_done",
        chunk_count=len(classified),
        duration_ms=round(duration * 1000, 2),
        model=settings.CLASSIFY_MODEL,
    )
    return {"classified_chunks": classified, "doc_metadata": state["doc_metadata"], "errors": state.get("errors", [])}
```

> **注意**：需要从 `state["doc_metadata"]` 取 `doc_id` 用于 span 属性。

- [ ] **Step 3: 对 escalate_node.py 重复上述模式**

- [ ] **Step 4: 对 transform_node.py 重复上述模式**

- [ ] **Step 5: 验证三个节点可导入**

```bash
cd server && uv run python3 -c "
from parser.nodes.classify_node import classify_node
from parser.nodes.escalate_node import escalate_node
from parser.nodes.transform_node import transform_node
print('all OK')
"
```

Expected: `all OK`

- [ ] **Step 6: Commit**

```bash
git add server/parser/nodes/classify_node.py server/parser/nodes/escalate_node.py server/parser/nodes/transform_node.py
git commit -m "feat(parser): add OTel spans to classify, escalate, and transform nodes"
```

---

## Task 5: 为未埋点节点添加完整埋点

**Files:**
- Modify: `server/parser/nodes/parse_node.py`
- Modify: `server/parser/nodes/clean_node.py`
- Modify: `server/parser/nodes/structure_node.py`
- Modify: `server/parser/nodes/slice_node.py`
- Modify: `server/parser/nodes/enrich_node.py`
- Modify: `server/parser/nodes/merge_node.py`

### 通用模式（每个文件）

**导入块**（每个文件顶部）：
```python
import time
import structlog
from opentelemetry import trace
from observability.metrics import (
    parser_node_duration_seconds,
    parser_chunks_processed_total,
    llm_calls_total,
)

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)
```

**函数入口/出口模式**：
```python
def <node_name>(state: WorkflowState) -> dict:
    _start = time.perf_counter()
    chunks_in = ...  # 入口 chunk 数
    doc_id = state.get("doc_metadata", {}).get("doc_id", "")

    _logger.info("<node_name>_start", node="<node_name>", doc_id=doc_id, chunks_in=chunks_in)

    with _tracer.start_as_current_span("<node_name>") as span:
        span.set_attribute("parser.node", "<node_name>")
        span.set_attribute("parser.doc_id", doc_id)
        span.set_attribute("parser.chunk_count.in", chunks_in)

        # ... 原有函数逻辑 ...

        chunks_out = ...  # 出口 chunk 数
        span.set_attribute("parser.chunk_count.out", chunks_out)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="<node_name>").observe(duration)
    parser_chunks_processed_total.labels(node="<node_name>").inc(chunks_in)
    _logger.info(
        "<node_name>_done",
        node="<node_name>",
        doc_id=doc_id,
        duration_ms=round(duration * 1000, 2),
        chunks_in=chunks_in,
        chunks_out=chunks_out,
    )
    return {...}
```

### parse_node.py 细节

- [ ] **读取 parse_node.py**，确认输入输出：
  - 输入：`state["md_content"]`（整个文档的字符串）、`state["doc_metadata"]`
  - 输出：返回 `{"doc_metadata": meta, "errors": errors, "md_content": state["md_content"]}`
  - **不产生 raw_chunks**（那是 slice_node 的职责）

- [ ] **添加埋点**：
  - `chunks_in = 1`，`chunks_out = 1`（处理的是一个文档，不是 chunk 列表）
  - `chunks_in` / `chunks_out` 用 `md_content_char_count` 表示更精确：
    ```python
    md_chars = len(state["md_content"])
    span.set_attribute("parser.md_chars.in", md_chars)
    ```
  - doc_id 从 `state["doc_metadata"]["doc_id"]` 取

### clean_node.py 细节

- [ ] **读取 clean_node.py**，确认：
  - 输入：`state["md_content"]`（整个文档的字符串）
  - 输出：返回 `{"md_content": cleaned}`，其中 `cleaned` 是清洗后的字符串
  - `chunks_in = 1`，`chunks_out = 1`（处理的是同一篇文档，只是内容被清洗）
  - 也可用 `md_content` 字符数作为属性：`span.set_attribute("parser.md_chars.in", len(state["md_content"]))`

### structure_node.py 细节

- [ ] **读取 structure_node.py**，确认：
  - 输入：`state["md_content"]`
  - 输出：`state["doc_metadata"]["doc_type"]` 被写入
  - `chunks_in = 1`，`chunks_out = 1`（只改 metadata）
  - **额外**：在 `_infer_doc_type_with_llm()` 函数内部、`invoke_structured(...)` 调用之后添加：
    ```python
    llm_calls_total.labels(node="structure_node", model=settings.DOC_TYPE_LLM_MODEL or "unknown").inc()
    ```

### slice_node.py 细节

- [ ] **读取 slice_node.py**，确认：
  - 输入：`state["raw_chunks"]`（来自 clean_node 的输出）
  - 输出：`state["raw_chunks"]`（重新写入切分后的 chunks）
  - **移除所有 `print()` 调用**，替换为 `_logger.info(...)`
  - `chunks_in = len(state["raw_chunks"])`，`chunks_out = len(sliced_chunks)`

### enrich_node.py 细节

- [ ] **读取 enrich_node.py**，确认：
  - 输入：`state["classified_chunks"]`
  - 输出：修改后的 `classified_chunks`
  - `chunks_in = len(state["classified_chunks"])`，`chunks_out = len(enriched_chunks)`

### merge_node.py 细节

- [ ] **读取 merge_node.py**，确认：
  - 输入：`state["final_chunks"]`
  - 输出：`final_chunks`（合并后的列表）
  - `chunks_in = len(chunks)`，`chunks_out = len(merged)`（变量名为 `chunks` 非 `input_chunks`）

- [ ] **验证所有 6 个节点可导入**

```bash
cd server && uv run python3 -c "
from parser.nodes.parse_node import parse_node
from parser.nodes.clean_node import clean_node
from parser.nodes.structure_node import structure_node
from parser.nodes.slice_node import slice_node
from parser.nodes.enrich_node import enrich_node
from parser.nodes.merge_node import merge_node
print('all OK')
"
```

Expected: `all OK`

- [ ] **Commit**

```bash
git add server/parser/nodes/parse_node.py server/parser/nodes/clean_node.py server/parser/nodes/structure_node.py server/parser/nodes/slice_node.py server/parser/nodes/enrich_node.py server/parser/nodes/merge_node.py
git commit -m "feat(parser): add full instrumentation (span + structlog + metrics) to 6 uninstrumented nodes"
```

---

## Task 6: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd server && uv run python3 run.py &
sleep 3
```

- [ ] **Step 2: 检查 Prometheus 指标**

```bash
curl http://localhost:9999/metrics | grep -E "^parser_workflow_duration_seconds|^llm_tokens_total"
```

Expected: 看到 `parser_workflow_duration_seconds` 和 `llm_tokens_total` 指标定义（无需有数据，未运行 pipeline 前为空）

- [ ] **Step 3: 触发 pipeline**（通过上传文档或直接调用 workflow）

```bash
curl -X POST http://localhost:9999/api/documents/upload ...
```

- [ ] **Step 4: 检查日志输出**

```bash
curl http://localhost:9999/metrics | grep parser_
```

Expected: 看到各节点的 `parser_node_duration_seconds` bucket 分布

- [ ] **Step 5: Commit（无代码变更，仅记录验证结果）**

```bash
git add -A && git commit --allow-empty -m "test(parser): verify parser workflow observability end-to-end"
```

---

## 验证摘要

| 检查项 | 预期 |
|--------|------|
| `parser_workflow_duration_seconds` 指标存在 | ✅ `curl` 输出包含 |
| `llm_tokens_total` 有 increment | ✅ `curl` 输出包含 |
| 所有 9 个节点 structlog 输出 | ✅ JSON 格式日志含 `{node}_done` 事件 |
| Grafana Tempo 可查完整链路 | ✅ 9 个 span 串在同一 trace_id |
| Grafana Loki 有结构化日志 | ✅ 查询 `{service_name="life-classics-server"}` 含各节点日志 |
