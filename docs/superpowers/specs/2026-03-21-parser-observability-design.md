# Parser Workflow 可观测性埋点设计

> **日期：** 2026-03-21
> **目标：** 将整个 parser workflow（9个节点）完整接入日志系统，包含 structlog 日志、Prometheus 指标、OpenTelemetry 链路追踪

## 1. 背景与现状

### 1.1 当前埋点情况

| 节点 | structlog | Prometheus | OTel Span | 说明 |
|------|-----------|------------|-----------|------|
| parse_node | ❌ | ❌ | ❌ | 无任何埋点 |
| clean_node | ❌ | ❌ | ❌ | 无任何埋点 |
| structure_node | ❌ | ❌ | ❌ | 无埋点；LLM 调用存在但未追踪 `llm_calls_total` |
| slice_node | 仅 `print()` | ❌ | ❌ | 非结构化 |
| classify_node | ✅ start/done | ✅ | ❌ | 缺 OTel span |
| escalate_node | ✅ start/done | ✅ | ❌ | 缺 OTel span |
| enrich_node | ❌ | ❌ | ❌ | 无任何埋点 |
| transform_node | ✅ start/done | ✅ | ❌ | 缺 OTel span |
| merge_node | ❌ | ❌ | ❌ | 无任何埋点 |

- `llm_tokens_total` 定义了但从未 increment（instructor response 有 `.usage` 字段但未被读取）
- `astream_events` 已提供节点级事件（`on_chain_start` / `on_chain_end`），但没有结构化输出到日志

### 1.2 目标

9个节点全部具备：
- **structlog**：节点入口/出口日志，包含耗时、输入 chunk 数、输出 chunk 数、doc_id
- **Prometheus metrics**：
  - `parser_node_duration_seconds`（已有部分，补充缺失节点）
  - `parser_chunks_processed_total`（已有部分，补充缺失节点）
  - `parser_workflow_duration_seconds`：整条流水线的总耗时（Histogram，按 doc_type 标签）
  - `llm_calls_total` / `llm_tokens_total`（补充 structure_node 的 LLM 调用追踪）
- **OpenTelemetry Span**：每个节点一个 span，串在同一 trace_id 下，pipeline 入口创建一个 root span

## 2. 技术方案

### 2.1 Span 创建位置

**方案 A：在每个 node 函数内部手动创建 span（推荐）**

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def classify_node(state: WorkflowState) -> WorkflowState:
    with tracer.start_as_current_span("classify_node") as span:
        span.set_attribute("parser.node", "classify_node")
        span.set_attribute("parser.chunk_count", len(chunks))
        # ... existing logic ...
```

**优点：** 精确控制 span 边界，与现有 structlog 日志对齐
**缺点：** 9个文件都要改，但改动量小（每个文件加3-5行）

**方案 B：利用 `astream_events` 在 `run_parser_workflow_stream` 集中创建**

利用 LangGraph 已有的 `on_chain_start` / `on_chain_end` 事件，在 workflow stream 层面统一创建 span + structlog。

**优点：** 不需要改每个 node 文件
**缺点：** span 边界与 node 函数边界不完全对齐（node 函数内部还有子调用），调试信息不够精细

**结论：** 采用 **方案 A**，在每个 node 内部创建 span，与现有 structlog 埋点模式一致。

### 2.2 Span 属性设计

每个节点 span 的标准属性：

| 属性 | 说明 | 示例 |
|------|------|------|
| `parser.node` | 节点名称 | `classify_node` |
| `parser.doc_id` | 文档ID | `GB7713.1-2021` |
| `parser.doc_type` | 文档类型（structure_node 出口后设置） | `GB7713` |
| `parser.chunk_count.in` | 输入 chunk 数 | `12` |
| `parser.chunk_count.out` | 输出 chunk 数（出口时设置） | `15` |
| `parser.stage` | pipeline 阶段 | `classify` |
| `parser.llm.model` | 调用的 LLM 模型（仅 LLM 调用节点） | `qwen-plus` |
| `parser.llm.retries` | LLM 重试次数（仅 LLM 调用节点） | `0` |

### 2.3 Token 计数方案

`llm_tokens_total` 从未被 increment。修正方案：在 `structured_llm/invoker.py` 的 `invoke_structured()` 每次成功返回后，从 instructor 返回值上读取 `.usage` 属性（instructor 已 patch response 对象附加了 usage 字段）并 increment。

在 `create_fn(...)` 调用成功后、`return result` 之前添加：

```python
result = create_fn(...)
# instructor 1.x 返回值的 usage 字段
usage = getattr(result, "usage", None)
if usage:
    llm_tokens_total.labels(node=node_name, model=resolved_model, type="prompt").inc(usage.prompt_tokens or 0)
    llm_tokens_total.labels(node=node_name, model=resolved_model, type="completion").inc(usage.completion_tokens or 0)
return result
```

**注意**：部分 provider（如某些兼容端点）可能不返回 usage，此时 `usage` 为 None，跳过计数不做报错。

### 2.4 新增 Pipeline 总耗时指标

新增 `parser_workflow_duration_seconds` Histogram，记录完整 pipeline 从 parse 到 merge 的总耗时：

```python
parser_workflow_duration_seconds = Histogram(
    "parser_workflow_duration_seconds",
    "Parser 完整流水线处理耗时（秒）",
    ["doc_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)
```

**`run_parser_workflow`（同步）**：入口记录 `start_time`，出口 `observe(duration)`。

**`run_parser_workflow_stream`（异步 SSE 流）**：异步上下文下 `time.perf_counter()` 同样适用，因为计时起点到流消费完毕的总时长不受 `async` 影响。注意 span 的 root 应在流开始时创建、流关闭时结束，与 pipeline 计时保持同步。

统一在 `run_parser_workflow_stream` 层面创建 root span，并将 `doc_id` / `doc_type` 作为 root span 属性。

### 2.5 structlog 日志格式标准化与 trace_id 传播

**trace_id 传播机制**：`configure.py` 中 `LoggingInstrumentor().instrument(set_logging_format=False)` 将 OTel trace context 自动注入 structlog 的 context vars，使每条日志自动携带当前 span 的 trace_id。LangGraph 节点 span 作为 root span 的 child，自动继承，无需额外手动传播。

**日志格式标准化**：

每个节点出口统一格式：

```json
{
  "event": "parse_node_done",
  "node": "parse_node",
  "doc_id": "GB7713.1-2021",
  "duration_ms": 12.34,
  "chunks_in": 1,
  "chunks_out": 8,
  "trace_id": "a1b2c3d4..."
}
```

入口统一格式：

```json
{
  "event": "parse_node_start",
  "node": "parse_node",
  "doc_id": "GB7713.1-2021",
  "chunks_in": 1
}
```

## 3. 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `server/parser/nodes/parse_node.py` | 添加 tracer span + structlog start/done + metrics |
| `server/parser/nodes/clean_node.py` | 添加 tracer span + structlog start/done + metrics |
| `server/parser/nodes/structure_node.py` | 添加 tracer span + structlog start/done + metrics + `llm_calls_total` increment（LLM 调用已有但未追踪） |
| `server/parser/nodes/slice_node.py` | 移除 `print()`，替换为 structlog + span + metrics |
| `server/parser/nodes/classify_node.py` | 添加 OTel span（structlog + metrics 已存在） |
| `server/parser/nodes/escalate_node.py` | 添加 OTel span（structlog + metrics 已存在） |
| `server/parser/nodes/enrich_node.py` | 添加 tracer span + structlog start/done + metrics |
| `server/parser/nodes/transform_node.py` | 添加 OTel span（structlog + metrics 已存在） |
| `server/parser/nodes/merge_node.py` | 添加 tracer span + structlog start/done + metrics |
| `server/parser/structured_llm/invoker.py` | 成功返回后读取 `result.usage` 并 increment `llm_tokens_total`；`print()` 重试日志改为 structlog |
| `server/observability/metrics.py` | 添加 `parser_workflow_duration_seconds` Histogram |
| `server/parser/graph.py` | 在 `run_parser_workflow` / `run_parser_workflow_stream` 入口创建 root span；`doc_type` 作为 root span 属性 |

## 4. 验证方法

```bash
# 1. 上传一个文档，触发 pipeline
curl -X POST http://localhost:9999/api/documents/upload ...

# 2. 查看 Prometheus 指标
curl http://localhost:9999/metrics | grep parser_

# 3. 在 Grafana Logs Explorer 查看结构化日志
# 查询: {service_name="life-classics-server"} |= "parse_node_done"

# 4. 在 Grafana Tempo 查看完整链路
# 搜索 trace_id，应该看到 parse → clean → structure → ... → merge 的 9 个 span
```

## 5. 风险与限制

- **LangGraph OTel 自动注入冲突**：FastAPI 的 `FastAPIInstrumentor.instrument_app(app)` 会自动为所有 ASGI 应用创建 spans。若 `opentelemetry-instrumentation-langgraph` 也被启用（或通过 `OTEL_AUTO_INSTRUMENTATION` 全局开启），LangGraph 的 `ainvoke()` 会被自动创建 span，与我们手动创建的节点 span 产生嵌套/重复。**解决方案**：验证 `metrics.py` 中 `LoggingInstrumentor` 只instrument了 logging，未主动 instrument langgraph；我们的手动 span 与 FastAPIInstrumentor 的父子关系通过 trace context 自动传播，无需额外配置。
- **Token 计数兼容性**：依赖 instructor 返回值上的 `.usage` 属性。部分 provider（如某些兼容端点）可能不返回 usage，`getattr(result, "usage", None)` 可安全降级。
- **向后兼容**：所有新增 metrics 为 **额外标签**，不影响现有 metrics 定义。
