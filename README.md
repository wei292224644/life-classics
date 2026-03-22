# life-classics

面向中国食品安全**国家标准（GB）**的 RAG 知识库 monorepo：Python 后端（解析流水线 + 向量/全文检索 + Agent）与前端管理台 / 小程序客户端。

## 仓库结构

```
life-classics/
├── server/                 # FastAPI 后端（uv + pyproject.toml）
├── web/
│   ├── apps/
│   │   ├── console/        # @acme/console — Vite + React 管理台
│   │   └── uniapp/         # @acme/uniapp — UniApp（H5 / 小程序）
│   ├── tooling/            # 共享 ESLint、TSConfig 等
│   └── ui/                 # UI 设计说明与静态 HTML 原型（非 npm 包）
├── docker/postgres/        # 可选：本地 PostgreSQL（docker-compose）
├── CLAUDE.md               # AI 助手（Claude Code 等）工作约定
├── start.sh                # tmux 一键拉起后端 + H5 + console
└── stop.sh                 # 关闭上述 tmux session
```

详细架构与数据流见 **[server/README.md](server/README.md)**。

## 前置条件

| 工具 | 说明 |
|------|------|
| [uv](https://github.com/astral-sh/uv) | Python 依赖与虚拟环境（仅用于 `server/`） |
| [pnpm](https://pnpm.io) | Node 包管理（仅用于 `web/`） |
| Node.js | 版本见 [web/package.json](web/package.json) 中 `engines`（当前为 **22.x** 量级） |
| tmux | 可选；用于 `./start.sh` 多窗格开发 |

## 快速开始

### 1. 后端

```bash
cd server
uv sync
# 按需创建 server/.env，键名见 server/config.py
uv run python3 run.py
```

默认：<http://localhost:9999>，Swagger：<http://localhost:9999/swagger>。

### 2. 前端（在 `web/` 目录）

```bash
cd web
pnpm install
pnpm dev:console      # 管理台 http://localhost:5173 ，/api 代理到 9999
pnpm dev:uniapp:h5    # UniApp H5，默认 http://localhost:5174
```

### 3. 一键开发（tmux）

```bash
./start.sh
```

会创建名为 `dev` 的 tmux session：左侧后端，右上 UniApp H5，右下 console。关闭：`./stop.sh` 或 `tmux kill-session -t dev`。

无 tmux 时，在三个终端分别执行上述 `uv run python3 run.py`、`pnpm dev:uniapp:h5`、`pnpm dev:console` 即可。

### 4. 可选：本地 PostgreSQL

```bash
cd docker/postgres
docker compose up -d
```

随后在 `server/.env` 中配置 `POSTGRES_URL` 或 `POSTGRES_*` 分项（见 [server/config.py](server/config.py)）。

## 配置说明

- 后端所有环境变量集中在 **`server/config.py`**，通过 **`server/.env`** 或环境变量覆盖。
- UniApp 开发环境 API 基址示例见 `web/apps/uniapp/.env.development`（如 `VITE_API_BASE_URL`）。

## 文档索引

| 文档 | 内容 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | Git/uv/pnpm 约定、模块概览、API 与配置速查 |
| [server/README.md](server/README.md) | 服务端架构、数据流、环境变量表、API 一览 |
| [web/README.md](web/README.md) | 前端 monorepo 与脚本说明 |

## 许可证

MIT License（若子目录另有声明，以子目录为准）。
