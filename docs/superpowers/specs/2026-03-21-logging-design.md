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
| Node Exporter | 宿主机系统指标采集 |
| Promtail | 容器日志文件兜底采集 |

**选型理由**：
- 资源占用远低于 ELK Stack，本地 Docker 友好
- 三类可观测数据（日志/指标/追踪）在同一 Grafana 界面关联查询
- 业界标准现代可观测性方案，有成熟文档与社区支持

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                          │
│                                                              │
│  ┌──────────┐    ┌──────────┐                               │
│  │ FastAPI  │    │ Next.js  │  (暂不集成)                    │
│  │ (Python) │    │ (Node)   │                               │
│  └────┬─────┘    └──────────┘                               │
│       │                                                      │
│  ┌────▼──────────────────────────┐                          │
│  │      OTel Collector :4318     │                          │
│  │  (接收 traces / metrics / logs)│                         │
│  └────┬────────────┬─────────────┘                          │
│       │            │                                         │
│  ┌────▼──┐    ┌────▼──┐    ┌─────────────┐                 │
│  │ Loki  │    │ Tempo │    │ Prometheus  │                  │
│  │ :3100 │    │ :4317 │    │ :9090       │                  │
│  └───────┘    └───────┘    └──────┬──────┘                  │
│                                   │                          │
│                            ┌──────▼──────┐                  │
│                            │ Node Exporter│                  │
│                            │ :9100        │                  │
│                            └─────────────┘                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Grafana :3000                        │   │
│  │   统一查询入口，数据源：Loki + Tempo + Prometheus      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────┐                                               │
│  │  React   │ → POST /api/logs → FastAPI → OTel Collector   │
│  │ (Vite)   │                                               │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 后端日志设计（FastAPI/Python）

### 1. 结构化日志（→ Loki）

- 用 `structlog` 替换现有零散 `import logging`，全局输出 JSON 格式
- 每条日志自动附加字段：`trace_id`、`service`、`env`、`timestamp`
- Parser Workflow 各节点记录：`node_name`、`duration_ms`、`chunk_count`、`confidence`、`model`
- 日志级别规范：`DEBUG`（开发详情）、`INFO`（正常流程）、`WARNING`（可恢复异常）、`ERROR`（需关注错误）

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

接收前端上报的日志，转发给 OTel Collector，不写入业务数据库。

---

## 前端日志设计（Vite/React 管理后台）

### 采集范围

仅捕获真实报错，不做行为埋点：
- `window.onerror` — 全局 JS 运行时错误
- `window.addEventListener('unhandledrejection', ...)` — 未处理的 Promise 拒绝

### 上报格式

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

### 容器清单

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `grafana` | grafana/grafana:latest | 3000 | 可视化界面 |
| `loki` | grafana/loki:latest | 3100 | 日志存储 |
| `tempo` | grafana/tempo:latest | 4317 | 链路追踪存储 |
| `prometheus` | prom/prometheus:latest | 9090 | 指标存储 |
| `otel-collector` | otel/opentelemetry-collector-contrib | 4318 | 数据中转 |
| `node-exporter` | prom/node-exporter:latest | 9100 | 系统指标 |
| `promtail` | grafana/promtail:latest | — | 兜底日志收集 |

### 数据持久化

Loki、Tempo、Prometheus 各自挂载命名 volume，重启不丢数据。

### 预置 Grafana Dashboard

1. **API Overview** — 请求量、P50/P95/P99 延迟、错误率（按路由分组）
2. **LLM Calls** — 各 Parser 节点调用次数、token 用量趋势、耗时分布
3. **Logs Explorer** — 结构化日志全文搜索，支持按 `service`、`level`、`trace_id` 过滤

---

## 目录结构变更

```
life-classics/
├── observability/               # 新增：日志平台配置
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
│       │   ├── datasources/
│       │   └── dashboards/
│       └── dashboards/
│           ├── api-overview.json
│           ├── llm-calls.json
│           └── logs-explorer.json
└── server/
    └── logging/                 # 新增：后端日志工具
        ├── __init__.py
        ├── setup.py             # structlog 全局初始化
        └── middleware.py        # FastAPI 请求日志中间件
```

---

## 扩展性说明

- **新端接入**：任何平台（小程序/App）只需向 `POST /api/logs` 发送符合格式的 JSON 即可接入，无需改动日志平台
- **Next.js 集成**：确定保留 Next.js 后，用 `pino` + OTel Node.js SDK 接入同一个 OTel Collector，无需改动平台侧配置
- **生产部署**：将 OTel Collector 地址、Prometheus 抓取目标改为生产服务器 IP 即可，Grafana 平台本身可保持本地
