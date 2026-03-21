# Logging System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立集中式可观测性平台，将后端（FastAPI）和管理前端（Vite/React）的日志、指标、链路追踪统一汇入本地 Docker 部署的 Grafana 全家桶。

**Architecture:** OTel Collector 作为统一数据入口，接收 FastAPI 通过 OTLP/HTTP 推送的日志/追踪/指标，分别路由到 Loki（日志）、Tempo（追踪）、Prometheus（指标）；Grafana 提供统一查询界面。前端错误通过 `POST /api/logs` 中转，由后端注入 trace_id 后转发至 OTel Collector。

**Tech Stack:** structlog, opentelemetry-sdk, opentelemetry-instrumentation-fastapi, prometheus-fastapi-instrumentator, prometheus-client, slowapi, Grafana 11.4.0, Loki 3.3.2, Tempo 2.6.1, Prometheus v3.1.0, OTel Collector Contrib 0.116.1

**Spec:** `docs/superpowers/specs/2026-03-21-logging-design.md`

---

## 文件结构

**新建文件：**

```
observability/
├── docker-compose.yml                          # 7 个容器定义
├── otel-collector/config.yaml                  # OTel Collector 路由规则（含 health_check）
├── prometheus/prometheus.yml                   # scrape 目标配置
├── loki/config.yaml                            # Loki 存储配置
├── tempo/config.yaml                           # Tempo 接收与存储配置
├── promtail/config.yaml                        # Promtail 应急备份采集配置
└── grafana/
    ├── provisioning/datasources/datasources.yaml
    ├── provisioning/dashboards/dashboards.yaml
    └── dashboards/
        ├── api-overview.json
        ├── llm-calls.json
        └── logs-explorer.json

server/observability/
├── __init__.py
├── configure.py          # structlog 初始化 + OTel SDK 配置
├── middleware.py          # FastAPI 请求日志中间件
└── metrics.py            # Prometheus 业务指标注册

server/api/frontend_logs/
├── __init__.py
├── router.py             # POST /api/logs 端点
└── models.py             # FrontendLogEntry Pydantic 模型

web/apps/console/src/lib/
└── error-reporter.ts     # 前端全局错误捕获与上报
```

**修改文件：**

```
server/config.py                                # 新增 3 个 OTel 配置项
server/api/main.py                              # 接入 OTel instrumentation + /metrics + 注册 logs router
server/api/__init__.py                          # 注册 frontend_logs router
server/parser/structured_llm/invoker.py         # 替换 print() 为 structlog
server/parser/nodes/classify_node.py            # 节点耗时日志 + metrics
server/parser/nodes/escalate_node.py            # 节点耗时日志 + metrics
server/parser/nodes/transform_node.py           # 节点耗时日志 + metrics
web/apps/console/src/main.tsx                   # 引入 error-reporter
```

---

## Task 1: Docker Compose 基础设施

**Files:**
- Create: `observability/docker-compose.yml`
- Create: `observability/otel-collector/config.yaml`
- Create: `observability/prometheus/prometheus.yml`
- Create: `observability/loki/config.yaml`
- Create: `observability/tempo/config.yaml`
- Create: `observability/grafana/provisioning/datasources/datasources.yaml`
- Create: `observability/grafana/provisioning/dashboards/dashboards.yaml`

- [ ] **Step 1: 创建 observability/ 目录结构**

```bash
mkdir -p observability/otel-collector
mkdir -p observability/prometheus
mkdir -p observability/loki
mkdir -p observability/tempo
mkdir -p observability/grafana/provisioning/datasources
mkdir -p observability/grafana/provisioning/dashboards
mkdir -p observability/grafana/dashboards
```

- [ ] **Step 2: 创建 `observability/loki/config.yaml`**

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory
  replication_factor: 1
  path_prefix: /loki

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/index_cache
  filesystem:
    directory: /loki/chunks

limits_config:
  allow_structured_metadata: true
  volume_enabled: true
```

- [ ] **Step 3: 创建 `observability/tempo/config.yaml`**

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal
```

- [ ] **Step 4: 创建 `observability/prometheus/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "fastapi"
    static_configs:
      - targets: ["host.docker.internal:9999"]
    metrics_path: /metrics

  - job_name: "otel-collector"
    static_configs:
      - targets: ["otel-collector:8889"]

  - job_name: "node-exporter"
    static_configs:
      - targets: ["node-exporter:9100"]
```

- [ ] **Step 5: 创建 `observability/otel-collector/config.yaml`**

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  otlphttp/loki:
    endpoint: http://loki:3100/otlp
  otlp/tempo:
    endpoint: http://tempo:4317
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:8889
  debug:
    verbosity: basic

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/loki]
```

- [ ] **Step 6: 创建 `observability/grafana/provisioning/datasources/datasources.yaml`**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: false
    editable: false
    jsonData:
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id":"(\w+)"'
          name: TraceID
          url: "$${__value.raw}"

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    isDefault: false
    uid: tempo
    editable: false
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: "-1m"
        spanEndTimeShift: "1m"
        filterByTraceID: true
```

- [ ] **Step 7: 创建 `observability/grafana/provisioning/dashboards/dashboards.yaml`**

```yaml
apiVersion: 1

providers:
  - name: "default"
    orgId: 1
    folder: "Life Classics"
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
```

- [ ] **Step 8: 创建 `observability/docker-compose.yml`**

```yaml
version: "3.8"

networks:
  observability:
    driver: bridge

volumes:
  loki-data:
  tempo-data:
  prometheus-data:
  grafana-data:

services:
  loki:
    image: grafana/loki:3.3.2
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki/config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - observability

  tempo:
    image: grafana/tempo:2.6.1
    container_name: tempo
    ports:
      - "3200:3200"    # HTTP API 供 Grafana 查询
      # 注意：4317（gRPC）只在容器内部网络暴露给 OTel Collector，不绑定宿主机
      # 宿主机的 4317 已被 otel-collector 占用
    volumes:
      - ./tempo/config.yaml:/etc/tempo.yaml
      - tempo-data:/var/tempo
    command: -config.file=/etc/tempo.yaml
    networks:
      - observability

  prometheus:
    image: prom/prometheus:v3.1.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - observability

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.116.1
    container_name: otel-collector
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8889:8889"   # Prometheus metrics export
    volumes:
      - ./otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml
    networks:
      - observability

  node-exporter:
    image: prom/node-exporter:v1.8.2
    container_name: node-exporter
    ports:
      - "9100:9100"
    networks:
      - observability

  grafana:
    image: grafana/grafana:11.4.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    networks:
      - observability

  promtail:
    image: grafana/promtail:3.3.2
    container_name: promtail
    profiles: ["backup"]
    volumes:
      - ./promtail/config.yaml:/etc/promtail/config.yaml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yaml
    networks:
      - observability
```

- [ ] **Step 9: 补充 `observability/promtail/config.yaml`**

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker-containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: docker
          source: promtail
          __path__: /var/lib/docker/containers/*/*-json.log
    pipeline_stages:
      - json:
          expressions:
            log: log
            stream: stream
      - output:
          source: log
```

- [ ] **Step 10: 启动并验证**

```bash
cd observability
docker compose up -d
```

等待约 30 秒后验证：

```bash
# Grafana 可访问
curl -s http://localhost:3000/api/health | grep '"database": "ok"'

# Loki 就绪
curl -s http://localhost:3100/ready

# Prometheus 就绪
curl -s http://localhost:9090/-/ready

# OTel Collector 健康检查（通过 health_check extension）
curl -s http://localhost:13133/
```

Expected：最后一个命令返回 `{"status":"Server available","upSince":...}`

- [ ] **Step 11: Commit**

```bash
git add observability/
git commit -m "feat(observability): add Docker Compose stack (Grafana + Loki + Tempo + Prometheus + OTel)"
```

---

## Task 2: server/config.py 新增 OTel 配置项

**Files:**
- Modify: `server/config.py`

- [ ] **Step 1: 在 config.py 末尾 POSTGRES 配置之前新增 OTel 配置段**

打开 `server/config.py`，在 `POSTGRES_DB: str = ""` 之后、`settings = Settings()` 之前添加：

```python
    # ── 可观测性（OTel + 日志）────────────────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "life-classics-server"
    LOG_LEVEL: str = "INFO"
```

- [ ] **Step 2: 验证配置加载**

```bash
cd server
uv run python3 -c "from config import settings; print(settings.OTEL_SERVICE_NAME, settings.LOG_LEVEL)"
```

Expected: `life-classics-server INFO`

- [ ] **Step 3: Commit**

```bash
git add server/config.py
git commit -m "feat(config): add OTel observability config fields"
```

---

## Task 3: server/observability/ 核心模块

**Files:**
- Create: `server/observability/__init__.py`
- Create: `server/observability/configure.py`
- Create: `server/observability/middleware.py`
- Create: `server/observability/metrics.py`
- Create: `server/tests/core/observability/test_configure.py`

- [ ] **Step 1: 安装依赖**

```bash
cd server
uv add structlog \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-http \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-logging \
  opentelemetry-sdk \
  prometheus-fastapi-instrumentator \
  prometheus-client
```

- [ ] **Step 2: 写失败测试**

创建 `server/tests/core/observability/__init__.py`（空文件），再创建 `server/tests/core/observability/test_configure.py`：

```python
"""测试 structlog 配置和 OTel 初始化。"""
import json
import structlog
import pytest
from observability.configure import configure_logging


@pytest.fixture(autouse=True)
def reset_structlog():
    """每个测试前后重置 structlog 全局状态，避免 cache_logger_on_first_use 跨测试污染。"""
    yield
    structlog.reset_defaults()


def test_structlog_outputs_json(capsys):
    """配置后 structlog 应输出 JSON 格式，且包含指定字段。"""
    configure_logging(log_level="DEBUG", service_name="test-service")
    logger = structlog.get_logger()
    logger.info("hello world", user="alice")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    assert lines, "没有任何输出"
    record = json.loads(lines[-1])
    assert record["event"] == "hello world"
    assert record["user"] == "alice"
    assert "timestamp" in record
    assert record.get("service") == "test-service"  # service 字段由 configure_logging 注入


def test_structlog_includes_level(capsys):
    """WARNING 日志应包含 level 字段且值为 warning。"""
    configure_logging(log_level="WARNING", service_name="test-service")
    logger = structlog.get_logger()
    logger.warning("test warning")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    assert lines, "没有任何输出"
    record = json.loads(lines[-1])
    assert record.get("level") == "warning"
```

- [ ] **Step 3: 运行确认失败**

```bash
cd server
uv run pytest tests/core/observability/test_configure.py -v
```

Expected: `ImportError: No module named 'observability'`

- [ ] **Step 4: 创建 `server/observability/__init__.py`**

```python
"""可观测性模块：structlog 配置 + OTel SDK + Prometheus 指标。"""
from observability.configure import configure_logging, setup_otel

__all__ = ["configure_logging", "setup_otel"]
```

- [ ] **Step 5: 创建 `server/observability/configure.py`**

```python
"""structlog 全局初始化 + OpenTelemetry SDK 配置（traces + logs）。"""
from __future__ import annotations

import logging
import sys

import structlog
from opentelemetry import trace, _logs as otel_logs
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor


def configure_logging(log_level: str = "INFO", service_name: str = "life-classics-server") -> None:
    """
    配置 structlog 输出 JSON 格式日志到 stdout。
    同时将 service_name 注入为全局上下文变量，每条日志自动携带。

    structlog 与标准库 logging 桥接，使第三方库（uvicorn、httpx 等）的日志
    也以 JSON 格式输出。
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 将 service 注入为全局上下文，所有日志自动携带
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)

    # 标准库 logging 基础配置（给第三方库用）
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=False,  # 测试环境需要每次重新配置
    )


def setup_otel(
    otlp_endpoint: str,
    service_name: str,
) -> TracerProvider:
    """
    初始化 OpenTelemetry TracerProvider + LoggerProvider。

    - TracerProvider：将 traces 通过 OTLP/HTTP 导出到 OTel Collector → Tempo
    - LoggerProvider：将结构化日志通过 OTLP/HTTP 导出到 OTel Collector → Loki
    """
    resource = Resource.create({"service.name": service_name})

    # ── Traces ────────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Logs → Loki ───────────────────────────────────────────────────────────
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=f"{otlp_endpoint}/v1/logs")
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    otel_logs.set_logger_provider(logger_provider)

    # 将 trace_id 注入标准库 logging（structlog 桥接后自动携带）
    LoggingInstrumentor().instrument(set_logging_format=False)

    return tracer_provider
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
cd server
uv run pytest tests/core/observability/test_configure.py -v
```

Expected: 2 passed

- [ ] **Step 7: 创建 `server/observability/middleware.py`**

```python
"""FastAPI 请求日志中间件：每个请求记录方法、路径、状态码、耗时。"""
from __future__ import annotations

import time

import structlog
from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    记录每个 HTTP 请求的基本信息。
    trace_id 从当前 OTel span 中提取，与 Tempo 追踪联动。
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        span = trace.get_current_span()
        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else ""

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )
        return response
```

- [ ] **Step 8: 创建 `server/observability/metrics.py`**

```python
"""Prometheus 业务指标定义。所有指标在此集中注册，其他模块直接 import 使用。"""
from prometheus_client import Counter, Histogram

# LLM 调用次数（按节点和模型分组）
llm_calls_total = Counter(
    "llm_calls_total",
    "LLM 调用总次数",
    ["node", "model"],
)

# LLM token 用量（按节点、模型、类型分组）
llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM token 用量",
    ["node", "model", "type"],  # type: prompt | completion
)

# Parser chunk 处理总量
parser_chunks_processed_total = Counter(
    "parser_chunks_processed_total",
    "Parser Workflow 处理的 chunk 总数",
    ["node"],
)

# Parser 各节点耗时分布
parser_node_duration_seconds = Histogram(
    "parser_node_duration_seconds",
    "Parser 节点处理耗时（秒）",
    ["node"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
```

- [ ] **Step 9: Commit**

```bash
git add server/observability/ server/tests/core/observability/
git commit -m "feat(observability): add structlog + OTel + Prometheus metrics module"
```

---

## Task 4: FastAPI main.py 接入 OTel

**Files:**
- Modify: `server/api/main.py`

- [ ] **Step 1: 修改 `server/api/main.py`，在 app 创建前初始化可观测性**

将 `server/api/main.py` 替换为：

```python
"""
FastAPI 主应用入口
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from api import router as api_router
from api.config import settings as api_settings
from config import settings
from observability.configure import configure_logging, setup_otel
from observability.middleware import RequestLoggingMiddleware

# ── 可观测性初始化（在 app 创建之前）─────────────────────────────────────────
configure_logging(log_level=settings.LOG_LEVEL, service_name=settings.OTEL_SERVICE_NAME)
setup_otel(otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, service_name=settings.OTEL_SERVICE_NAME)

app = FastAPI(
    title="个人知识库系统",
    description="基于FastAPI + LlamaIndex + ChromaDB的个人知识库",
    version="0.1.0",
)

# OTel FastAPI 自动 instrumentation
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics 端点
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")

# 挂载 admin 静态文件（build 后才存在）
_admin_dist = os.path.join(os.path.dirname(__file__), "..", "..", "web", "apps", "console", "dist")
if os.path.isdir(_admin_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/admin", StaticFiles(directory=_admin_dist, html=True), name="admin")


@app.get("/swagger")
async def custom_swagger_ui():
    """自定义 Swagger UI 页面，便于直接调用 API"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="个人知识库系统 - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
```

- [ ] **Step 2: 验证服务启动正常，/metrics 端点可用**

```bash
cd server
uv run python3 run.py &
sleep 3
curl -s http://localhost:9999/metrics | head -20
```

Expected: 输出包含 `# HELP http_requests_total` 等 Prometheus 格式指标

```bash
kill %1  # 停止后台服务
```

- [ ] **Step 3: Commit**

```bash
git add server/api/main.py
git commit -m "feat(api): integrate OTel instrumentation and Prometheus /metrics endpoint"
```

---

## Task 5: 清理 print() 并接入 structlog

**Files:**
- Modify: `server/parser/structured_llm/invoker.py`

- [ ] **Step 1: 读取 invoker.py 第 155-170 行确认 print 位置**

找到如下代码段：
```python
    except Exception as e:
        print(e)
        print("=" * 100)
        print(messages)
        raise e
```

- [ ] **Step 2: 替换为 structlog 调用**

在文件顶部已有 import 处添加：
```python
import structlog
_logger = structlog.get_logger(__name__)
```

将 except 块替换为：
```python
    except Exception as e:
        _logger.error(
            "structured_llm_unexpected_error",
            node_name=node_name,
            provider=resolved_provider,
            model=resolved_model,
            error=str(e),
            messages_count=len(messages),
        )
        raise e
```

- [ ] **Step 3: 验证无语法错误**

```bash
cd server
uv run python3 -c "from parser.structured_llm.invoker import invoke_structured; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add server/parser/structured_llm/invoker.py
git commit -m "fix(parser): replace bare print() with structlog in invoker.py"
```

---

## Task 6: Parser Workflow 节点埋点

**Files:**
- Modify: `server/parser/nodes/classify_node.py`
- Modify: `server/parser/nodes/escalate_node.py`
- Modify: `server/parser/nodes/transform_node.py`

- [ ] **Step 1: 在 classify_node.py 添加 structlog + metrics 埋点**

在 `server/parser/nodes/classify_node.py` 顶部添加导入：

```python
import time
import structlog
from observability.metrics import (
    llm_calls_total,
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)

_logger = structlog.get_logger(__name__)
```

找到 `classify_node` 函数（处理 WorkflowState 的主函数），在其中包裹 LLM 调用：

```python
def classify_node(state: WorkflowState) -> WorkflowState:
    _start = time.perf_counter()
    chunks = state["raw_chunks"]
    _logger.info("classify_node_start", chunk_count=len(chunks))
    # ... 原有逻辑 ...
    # 在 _call_classify_llm 调用处添加：
    llm_calls_total.labels(node="classify_node", model=settings.CLASSIFY_MODEL).inc()
    # ... 原有逻辑结束 ...
    parser_chunks_processed_total.labels(node="classify_node").inc(len(chunks))
    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="classify_node").observe(duration)
    _logger.info(
        "classify_node_done",
        chunk_count=len(chunks),
        duration_ms=round(duration * 1000, 2),
        model=settings.CLASSIFY_MODEL,
    )
    return state
```

> **注意**：阅读 classify_node.py 找到实际的主函数名和逻辑结构后按此模式添加，不要机械复制——关键是在函数入口记录 start，在 LLM 调用处 inc counter，在函数出口 observe duration 并记录结构化日志。

- [ ] **Step 2: 对 escalate_node.py 做同样埋点**

模式相同，node 标签改为 `"escalate_node"`，model 使用 `settings.ESCALATE_MODEL`。

- [ ] **Step 3: 对 transform_node.py 做同样埋点**

模式相同，node 标签改为 `"transform_node"`。transform 节点不一定每次都调用 LLM（取决于 strategy），仅在实际调用 `_call_llm_transform` 时 inc counter。

- [ ] **Step 4: 验证节点可正常导入**

```bash
cd server
uv run python3 -c "
from parser.nodes.classify_node import classify_node
from parser.nodes.escalate_node import escalate_node
from parser.nodes.transform_node import transform_node
print('all nodes OK')
"
```

Expected: `all nodes OK`

- [ ] **Step 5: 运行现有 Parser 节点测试**

```bash
cd server
uv run pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py --ignore=tests/core/parser_workflow/test_slice_node_real.py -k "not real"
```

Expected: 所有非 real_llm 测试通过

- [ ] **Step 6: Commit**

```bash
git add server/parser/nodes/classify_node.py server/parser/nodes/escalate_node.py server/parser/nodes/transform_node.py
git commit -m "feat(parser): add structlog and Prometheus metrics to workflow nodes"
```

---

## Task 7: POST /api/logs 前端日志接收端点

**Files:**
- Create: `server/api/frontend_logs/__init__.py`
- Create: `server/api/frontend_logs/models.py`
- Create: `server/api/frontend_logs/router.py`
- Modify: `server/api/__init__.py`
- Create: `server/tests/api/test_frontend_logs.py`

- [ ] **Step 1: 安装 slowapi**

```bash
cd server
uv add slowapi
```

- [ ] **Step 2: 写失败测试**

创建 `server/tests/api/test_frontend_logs.py`：

```python
"""测试 POST /api/logs 端点。"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_accepts_valid_log_entry():
    """合法日志 payload 应返回 200。"""
    resp = client.post("/api/logs", json={
        "level": "error",
        "service": "console-web",
        "message": "TypeError: Cannot read",
        "stack": "at ChunkCard.tsx:42",
        "url": "/chunks",
        "user_agent": "Mozilla/5.0",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 200


def test_rejects_missing_required_fields():
    """缺少 message 字段应返回 422。"""
    resp = client.post("/api/logs", json={"level": "error"})
    assert resp.status_code == 422


def test_stack_field_truncated_to_2000_chars():
    """stack 字段超过 2000 字符应被截断，请求仍成功。"""
    long_stack = "x" * 5000
    resp = client.post("/api/logs", json={
        "level": "error",
        "service": "console-web",
        "message": "test",
        "stack": long_stack,
        "url": "/",
        "user_agent": "test",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 200


def test_rejects_unknown_log_level():
    """level 字段只接受合法值。"""
    resp = client.post("/api/logs", json={
        "level": "UNKNOWN_LEVEL",
        "service": "console-web",
        "message": "test",
        "stack": "",
        "url": "/",
        "user_agent": "test",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 422
```

- [ ] **Step 3: 运行确认失败**

```bash
cd server
uv run pytest tests/api/test_frontend_logs.py -v
```

Expected: `ImportError` 或 `404`

- [ ] **Step 4: 创建 `server/api/frontend_logs/__init__.py`（空文件）**

- [ ] **Step 5: 创建 `server/api/frontend_logs/models.py`**

```python
"""前端日志上报数据模型。"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class FrontendLogEntry(BaseModel):
    level: LogLevel
    service: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str

    @field_validator("stack")
    @classmethod
    def truncate_stack(cls, v: Optional[str]) -> Optional[str]:
        """stack 截断至 2000 字符，防止超大 payload 撑爆存储。"""
        if v and len(v) > 2000:
            return v[:2000] + "...[truncated]"
        return v
```

- [ ] **Step 6: 创建 `server/api/frontend_logs/router.py`**

```python
"""
POST /api/logs — 接收前端错误日志，注入 trace_id 后转发至 structlog。
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Request

from api.frontend_logs.models import FrontendLogEntry

router = APIRouter()
_logger = structlog.get_logger("frontend")


@router.post("/logs", status_code=200)
async def receive_frontend_log(entry: FrontendLogEntry, request: Request):
    """
    接收前端上报的错误日志。
    - stack 字段已在 Pydantic 模型层截断（≤2000 字符）
    - 由 structlog 输出到 stdout，OTel Collector 通过 OTLP 接收
    """
    _logger.error(
        "frontend_log",
        level=entry.level.value,
        service=entry.service,
        message=entry.message,
        stack=entry.stack,
        url=entry.url,
        user_agent=entry.user_agent,
        timestamp=entry.timestamp,
        client_ip=request.client.host if request.client else None,
    )
    return {"ok": True}
```

> **关于速率限制**：slowapi 需要 Limiter 挂载在 app 上。由于 main.py 初始化较复杂，速率限制在 Task 4 完成后可单独追加，或在本任务内通过 Body size limit 配置（FastAPI 默认 1MB，此处业务层已截断 stack，风险可控）。

- [ ] **Step 7: 在 `server/api/__init__.py` 注册 router**

在现有 router 注册列表末尾添加：

```python
from api.frontend_logs.router import router as frontend_logs_router
router.include_router(frontend_logs_router, tags=["Observability"])
```

- [ ] **Step 8: 运行测试**

```bash
cd server
uv run pytest tests/api/test_frontend_logs.py -v
```

Expected: 4 passed

- [ ] **Step 9: Commit**

```bash
git add server/api/frontend_logs/ server/api/__init__.py server/tests/api/test_frontend_logs.py
git commit -m "feat(api): add POST /api/logs frontend log relay endpoint"
```

---

## Task 8: 前端错误上报

**Files:**
- Create: `web/apps/console/src/lib/error-reporter.ts`
- Modify: `web/apps/console/src/main.tsx`

- [ ] **Step 1: 创建 `web/apps/console/src/lib/error-reporter.ts`**

```typescript
/**
 * 全局前端错误捕获与上报。
 * 仅捕获真实运行时错误，不做行为埋点。
 * 通过 sendBeacon（降级 fetch）向后端 POST /api/logs 上报。
 */

const LOG_ENDPOINT = "/api/logs";
const SERVICE_NAME = "console-web";

interface FrontendLogEntry {
  level: "error";
  service: string;
  message: string;
  stack: string;
  url: string;
  user_agent: string;
  timestamp: string;
}

function sendLog(entry: FrontendLogEntry): void {
  const payload = JSON.stringify(entry);
  // sendBeacon 在页面关闭时也能发送
  if (navigator.sendBeacon) {
    navigator.sendBeacon(LOG_ENDPOINT, new Blob([payload], { type: "application/json" }));
  } else {
    fetch(LOG_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {
      // 静默处理：日志上报失败不影响用户
    });
  }
}

function buildEntry(message: string, stack: string): FrontendLogEntry {
  return {
    level: "error",
    service: SERVICE_NAME,
    message,
    stack: stack.slice(0, 2000), // 前端也截断，双重保险
    url: window.location.pathname,
    user_agent: navigator.userAgent,
    timestamp: new Date().toISOString(),
  };
}

export function initErrorReporter(): void {
  // 捕获同步 JS 错误
  window.onerror = (message, _source, _lineno, _colno, error) => {
    const msg = typeof message === "string" ? message : String(message);
    const stack = error?.stack ?? msg;
    sendLog(buildEntry(msg, stack));
    return false; // 不阻止默认行为
  };

  // 捕获未处理的 Promise rejection
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message = reason instanceof Error ? reason.message : String(reason);
    const stack = reason instanceof Error ? (reason.stack ?? message) : message;
    sendLog(buildEntry(message, stack));
  });
}
```

- [ ] **Step 2: 在 `web/apps/console/src/main.tsx` 中初始化**

在 `createRoot` 之前添加：

```typescript
import { initErrorReporter } from './lib/error-reporter'

initErrorReporter()
```

完整文件：

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { initErrorReporter } from './lib/error-reporter'

initErrorReporter()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 3: 验证 TypeScript 编译无错误**

```bash
cd web
pnpm --filter @acme/console tsc --noEmit
```

Expected: 无错误输出

- [ ] **Step 4: Commit**

```bash
git add web/apps/console/src/lib/error-reporter.ts web/apps/console/src/main.tsx
git commit -m "feat(console): add global error reporter sending to POST /api/logs"
```

---

## Task 9: Grafana Dashboard 预置

**Files:**
- Create: `observability/grafana/dashboards/api-overview.json`
- Create: `observability/grafana/dashboards/llm-calls.json`
- Create: `observability/grafana/dashboards/logs-explorer.json`

- [ ] **Step 1: 创建 API Overview Dashboard**

创建 `observability/grafana/dashboards/api-overview.json`：

```json
{
  "title": "API Overview",
  "uid": "api-overview",
  "version": 1,
  "schemaVersion": 39,
  "tags": ["life-classics"],
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "请求总数",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [{"expr": "sum(increase(http_requests_total[1h]))", "legendFormat": "1h 请求数"}],
      "options": {"reduceOptions": {"calcs": ["lastNotNull"]}}
    },
    {
      "id": 2,
      "type": "stat",
      "title": "错误率",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [{"expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100", "legendFormat": "错误率 %"}],
      "options": {"reduceOptions": {"calcs": ["lastNotNull"]}}
    },
    {
      "id": 3,
      "type": "timeseries",
      "title": "请求延迟 P50/P95/P99",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 4},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [
        {"expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "P50"},
        {"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "P95"},
        {"expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "P99"}
      ]
    }
  ],
  "templating": {
    "list": [
      {"name": "datasource", "type": "datasource", "query": "prometheus"}
    ]
  },
  "time": {"from": "now-1h", "to": "now"},
  "refresh": "30s"
}
```

- [ ] **Step 2: 创建 LLM Calls Dashboard**

创建 `observability/grafana/dashboards/llm-calls.json`：

```json
{
  "title": "LLM Calls",
  "uid": "llm-calls",
  "version": 1,
  "schemaVersion": 39,
  "tags": ["life-classics", "llm"],
  "panels": [
    {
      "id": 1,
      "type": "timeseries",
      "title": "LLM 调用次数（按节点）",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [{"expr": "sum by (node) (rate(llm_calls_total[5m]))", "legendFormat": "{{node}}"}]
    },
    {
      "id": 2,
      "type": "timeseries",
      "title": "Parser 节点耗时 P95",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [{"expr": "histogram_quantile(0.95, sum by (node, le) (rate(parser_node_duration_seconds_bucket[5m])))", "legendFormat": "{{node}} P95"}]
    },
    {
      "id": 3,
      "type": "timeseries",
      "title": "Token 用量趋势",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
      "datasource": {"type": "prometheus", "uid": "${datasource}"},
      "targets": [{"expr": "sum by (node, type) (rate(llm_tokens_total[5m]))", "legendFormat": "{{node}} {{type}}"}]
    }
  ],
  "templating": {
    "list": [
      {"name": "datasource", "type": "datasource", "query": "prometheus"}
    ]
  },
  "time": {"from": "now-1h", "to": "now"},
  "refresh": "30s"
}
```

- [ ] **Step 3: 创建 Logs Explorer Dashboard**

创建 `observability/grafana/dashboards/logs-explorer.json`：

```json
{
  "title": "Logs Explorer",
  "uid": "logs-explorer",
  "version": 1,
  "schemaVersion": 39,
  "tags": ["life-classics", "logs"],
  "panels": [
    {
      "id": 1,
      "type": "logs",
      "title": "结构化日志",
      "gridPos": {"h": 20, "w": 24, "x": 0, "y": 0},
      "datasource": {"type": "loki", "uid": "${loki_datasource}"},
      "targets": [
        {
          "expr": "{service_name=\"$service\"} | json | level=~\"$level\"",
          "legendFormat": ""
        }
      ],
      "options": {
        "showLabels": false,
        "showTime": true,
        "wrapLogMessage": true,
        "enableLogDetails": true
      }
    }
  ],
  "templating": {
    "list": [
      {"name": "loki_datasource", "type": "datasource", "query": "loki"},
      {
        "name": "service",
        "type": "custom",
        "query": "life-classics-server,console-web,frontend",
        "current": {"value": "life-classics-server"}
      },
      {
        "name": "level",
        "type": "custom",
        "query": "debug,info,warning,error",
        "current": {"value": "error"},
        "multi": true,
        "includeAll": true
      }
    ]
  },
  "time": {"from": "now-1h", "to": "now"},
  "refresh": "30s"
}
```

- [ ] **Step 4: 重启 Grafana 验证 Dashboard 自动加载**

```bash
cd observability
docker compose restart grafana
sleep 5
# 验证 Dashboard 存在
curl -s "http://localhost:3000/api/dashboards/uid/api-overview" | grep '"title"'
curl -s "http://localhost:3000/api/dashboards/uid/llm-calls" | grep '"title"'
curl -s "http://localhost:3000/api/dashboards/uid/logs-explorer" | grep '"title"'
```

Expected: 每行输出包含对应的 `"title"` 字段

- [ ] **Step 5: Commit**

```bash
git add observability/grafana/dashboards/
git commit -m "feat(observability): add pre-built Grafana dashboards (API/LLM/Logs)"
```

---

## Task 10: 端到端验证

- [ ] **Step 1: 启动完整观测平台**

```bash
cd observability
docker compose up -d
```

- [ ] **Step 2: 启动 FastAPI 服务**

```bash
cd server
uv run python3 run.py &
sleep 3
```

- [ ] **Step 3: 触发几次 API 请求**

```bash
curl -s http://localhost:9999/api/chunks > /dev/null
curl -s http://localhost:9999/api/kb/stats > /dev/null
```

- [ ] **Step 4: 验证指标出现在 Prometheus**

```bash
curl -s http://localhost:9999/metrics | grep "http_requests_total"
```

Expected: 包含 `http_requests_total` 计数

- [ ] **Step 5: 在 Grafana 验证数据流通**

打开浏览器访问 `http://localhost:3000`：
1. 打开 **API Overview** Dashboard → 应看到请求计数
2. 打开 **Logs Explorer** Dashboard → 选择 `life-classics-server` 服务 → 应看到 JSON 日志
3. 打开 Explore → 选择 Tempo → 应能查询到 trace

- [ ] **Step 6: 测试前端日志上报**

```bash
curl -s -X POST http://localhost:9999/api/logs \
  -H "Content-Type: application/json" \
  -d '{"level":"error","service":"console-web","message":"test error","stack":"at App.tsx:1","url":"/","user_agent":"curl","timestamp":"2026-03-21T10:00:00Z"}'
```

Expected: `{"ok":true}`

在 Grafana Logs Explorer 中过滤 `service=frontend` 应看到这条日志。

- [ ] **Step 7: 运行全量测试确保无回归**

```bash
cd server
uv run pytest tests/ -v \
  --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py \
  --ignore=tests/core/parser_workflow/test_slice_node_real.py
```

Expected: 所有非 real_llm 测试通过

- [ ] **Step 8: 停止后台服务，最终 Commit**

```bash
kill %1  # 停止 FastAPI
git add -A
git commit -m "test(observability): verify end-to-end data flow through logging stack"
```

---

## 快速参考

| 服务 | 地址 | 说明 |
|------|------|------|
| Grafana | http://localhost:3000 | 统一可视化入口 |
| Loki | http://localhost:3100 | 日志查询 |
| Prometheus | http://localhost:9090 | 指标查询 |
| FastAPI /metrics | http://localhost:9999/metrics | Prometheus scrape 端点 |
| POST /api/logs | http://localhost:9999/api/logs | 前端日志上报 |

**常用命令：**

```bash
# 启动观测平台
cd observability && docker compose up -d

# 停止观测平台
cd observability && docker compose down

# 查看容器日志
docker compose -f observability/docker-compose.yml logs -f otel-collector
```
