# 日志系统设计文档

**日期**：2026-03-21
**状态**：已确认
**范围**：后端（FastAPI/Python）+ 管理后台（Vite/React）+ 本地 Docker 日志平台

---

## 背景与目标

当前项目（life-classics）的后端和前端均无统一日志基础设施。目标是建立一套集中式可观测性平台，同时满足：

- **开发调试**：快速定位 bug，查看请求链路和 LLM 调用耗时
- **生产监控**：观察系统健康状态、错误告警、业务指标追踪

暂不包含 C 端（小程序/App）日志采集，待多端架构决策明确后另行扩展。

---

## 技术选型

**Grafana 全家桶（本地 Docker Compose 部署）**：

| 组件 | 职责 |
|------|------|
| Grafana | 统一可视化界面与查询入口 |
| Loki | 结构化日志存储与查询 |
| Tempo | 分布式链路追踪存储 |
| Prometheus | 指标采集与存储 |
| OpenTelemetry Collector | 统一数据接收与路由中转 |
| Node Exporter | 宿主机系统指标采集（在 Linux 生产环境有效；Mac Docker Desktop 下采集的是 VM 内部指标，参考价值有限） |
| Promtail | 应急备份：当 OTel SDK 推送失败时，从容器 stdout 兜底采集日志。通过 Docker Compose profile `--profile backup` 控制是否启动；默认启动时使用 `source=promtail` label，查询时可按此 label 过滤去重 |

**选型理由**：
- 资源占用远低于 ELK Stack，本地 Docker 友好
- 三类可观测数据（日志/指标/追踪）在同一 Grafana 界面关联查询
- 业界标准现代可观测性方案，有成熟文档与社区支持

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
│                                                                  │
│  ┌──────────┐    ┌──────────┐                                    │
│  │ FastAPI  │    │ Next.js  │  (暂不集成)                         │
│  │ (Python) │    │ (Node)   │                                    │
│  └────┬─────┘    └──────────┘                                    │
│       │  OTLP/HTTP :4318（应用直连）                              │
│  ┌────▼──────────────────────────┐                               │
│  │      OTel Collector :4318     │                               │
│  │  (接收 traces / metrics / logs)│                              │
│  └────┬────────────┬─────────────┘                               │
│       │            │  内部转发（gRPC）                            │
│  ┌────▼────┐   ┌───▼────┐    ┌─────────────┐                    │
│  │  Loki   │   │ Tempo  │    │ Prometheus  │◄── scrape /metrics  │
│  │  :3100  │   │ :4317  │    │ :9090       │                    │
│  └─────────┘   └────────┘    └──────┬──────┘                    │
│  (Promtail → Loki :3100，应急备份，   │                           │
│   仅在 SDK 不可用时启用，用 label     │                           │
│   source=promtail 区分来源)          │                           │
│                              ┌──────▼──────┐                    │
│                              │ Node Exporter│                   │
│                              │ :9100        │                   │
│                              └─────────────┘                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Grafana :3000                          │  │
│  │   数据源：Loki + Tempo + Prometheus（provisioning 自动加载）│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────┐                                                    │
│  │  React   │ →（sendBeacon）→ POST /api/logs → FastAPI → OTel  │
│  │ (Vite)   │                                                    │
│  └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 后端日志设计（FastAPI/Python）

### 0. 迁移前置

在开始接入前，先清理现有裸调试语句（如 `server/parser/structured_llm/invoker.py` 中的 `print(e)` 等），统一替换为 structlog 调用，作为第一个可验证的改进点。

### 1. 结构化日志（→ Loki）

- 用 `structlog` 替换现有零散 `import logging`，全局输出 JSON 格式
- 每条日志自动附加字段：`trace_id`、`service`、`env`、`timestamp`
- Parser Workflow 各节点记录：`node_name`、`duration_ms`、`chunk_count`、`confidence`、`model`
- 日志级别规范：`DEBUG`（开发详情）、`INFO`（正常流程）、`WARNING`（可恢复异常）、`ERROR`（需关注错误）
- FastAPI 侧 structlog 输出到 **stdout**，由 OTel Collector 的 filelog receiver 或 OTLP 接收，**不单独写文件**，避免与 Promtail 重复采集

### 2. 链路追踪（→ Tempo）

- 使用 `opentelemetry-instrumentation-fastapi` 自动 instrument，每个 HTTP 请求生成根 span
- LLM 调用手动添加子 span，记录：`model`、`prompt_tokens`、`completion_tokens`、`latency_ms`
- Parser Workflow 整条流水线（parse → clean → ... → merge）作为一个 trace，每个节点为子 span
- `trace_id` 注入到结构化日志，实现日志与追踪联动

### 3. 指标（→ Prometheus）

- FastAPI 暴露 `/metrics` 端点（`prometheus-fastapi-instrumentator`）
- 自动采集：`http_requests_total`、`http_request_duration_seconds`、`http_requests_errors_total`
- 业务指标（手动注册）：
  - `llm_calls_total{node, model}` — LLM 调用次数
  - `llm_tokens_total{node, model, type}` — token 用量（prompt/completion）
  - `parser_chunks_processed_total` — chunk 处理总量
  - `parser_node_duration_seconds{node}` — 各节点耗时直方图

### 4. 新增 API 端点

```
POST /api/logs
```

- 接收前端上报的日志，转发给 OTel Collector，不写入业务数据库
- **安全防护**（内部工具，同域 CORS 天然限制）：
  - Body 大小上限：16KB（FastAPI 默认可配）
  - 速率限制：同 IP 每分钟最多 60 次（`slowapi` 实现）
  - `stack` 字段截断至 2000 字符

### 5. config.py 新增配置项

以下配置项加入 `server/config.py`（Pydantic Settings），支持 `.env` 覆盖：

```python
OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
OTEL_SERVICE_NAME: str = "life-classics-server"
LOG_LEVEL: str = "INFO"
```

> **注意**：Docker Compose 运行时 FastAPI 容器应通过服务名访问 OTel Collector，需在 `.env` 中覆盖：
> ```
> OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
> ```
> 直接在宿主机运行 FastAPI（开发模式）时使用默认值 `localhost:4318`。

---

## 前端日志设计（Vite/React 管理后台）

### 采集范围

仅捕获真实报错，不做行为埋点：
- `window.onerror` — 全局 JS 运行时错误
- `window.addEventListener('unhandledrejection', ...)` — 未处理的 Promise 拒绝

### 上报格式

前端日志无法生成合法 OTel `trace_id`，由后端 `POST /api/logs` 处理时注入新 `trace_id`，前端上报格式不含此字段：

```json
{
  "level": "error",
  "service": "console-web",
  "message": "TypeError: Cannot read properties of undefined",
  "stack": "at ChunkCard.tsx:42:15...",
  "url": "/chunks",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2026-03-21T10:00:00Z"
}
```

### 上报方式

- 使用 `navigator.sendBeacon` 优先（页面关闭时不丢失），降级用 `fetch`
- 目标地址：`POST /api/logs`（同域，无需跨域配置）
- 失败静默处理，不影响用户操作

---

## Docker Compose 基础设施

### 容器清单（固定版本号）

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `grafana` | grafana/grafana:11.4.0 | 3000 | 可视化界面 |
| `loki` | grafana/loki:3.3.2 | 3100 | 日志存储 |
| `tempo` | grafana/tempo:2.6.1 | 4317（内部） | 链路追踪存储 |
| `prometheus` | prom/prometheus:v3.1.0 | 9090 | 指标存储 |
| `otel-collector` | otel/opentelemetry-collector-contrib:0.116.1 | 4318 | 数据中转 |
| `node-exporter` | prom/node-exporter:v1.8.2 | 9100 | 系统指标 |
| `promtail` | grafana/promtail:3.3.2 | — | 应急备份采集 |

> 固定版本号确保 `docker compose pull` 后配置文件格式不因大版本升级而静默失效。

### 数据持久化

Loki、Tempo、Prometheus 各自挂载命名 volume，重启不丢数据。

### 预置 Grafana Dashboard（provisioning 自动加载）

通过 Grafana provisioning 机制，`docker compose up` 后即可直接使用，无需手动配置：

1. **API Overview** — 请求量、P50/P95/P99 延迟、错误率（按路由分组）
2. **LLM Calls** — 各 Parser 节点调用次数、token 用量趋势、耗时分布
3. **Logs Explorer** — 结构化日志全文搜索，支持按 `service`、`level`、`trace_id` 过滤

---

## 目录结构变更

```
life-classics/
├── observability/               # 新增：日志平台 Docker Compose 配置
│   ├── docker-compose.yml
│   ├── otel-collector/
│   │   └── config.yaml
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── loki/
│   │   └── config.yaml
│   ├── tempo/
│   │   └── config.yaml
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/     # 数据源自动配置
│       │   └── dashboards/      # Dashboard 自动加载配置
│       └── dashboards/
│           ├── api-overview.json
│           ├── llm-calls.json
│           └── logs-explorer.json
└── server/
    └── observability/           # 新增：后端日志工具（避免与 Python stdlib logging 冲突）
        ├── __init__.py
        ├── configure.py         # structlog 全局初始化 + OTel SDK 配置
        └── middleware.py        # FastAPI 请求日志中间件
```

> **注意**：后端模块命名为 `observability/` 而非 `logging/`，因为 Python 标准库有同名的 `logging` 模块，在 `server/` 作为包根路径时会造成 `import logging` 命名冲突。

---

## 扩展性说明

- **新端接入**：任何平台（小程序/App）只需向 `POST /api/logs` 发送符合格式的 JSON 即可接入，无需改动日志平台
- **Next.js 集成**：确定保留 Next.js 后，用 `pino` + OTel Node.js SDK 接入同一个 OTel Collector，无需改动平台侧配置
- **生产部署**：将 OTel Collector 地址、Prometheus 抓取目标改为生产服务器地址即可；生产环境的持久化存储策略（对象存储替代本地 volume）超出本文档范围，见专项生产部署文档
