# 项目结构重组设计

**日期**: 2026-03-19
**状态**: 待评审

## 背景

当前项目存在以下问题：
- `agent-server/` 名称与内容不符（包含 admin 前端）
- 两个 Agent 混在一起，职责边界不清
- 前端项目（admin、client）放在 Python 后端目录下不合理
- Monorepo 结构不清晰

## 目标

1. 清晰的前后端分离
2. Python 代码用 uv workspace 模块化
3. 保持 Turborepo 在前端的使用
4. 明确各模块职责边界

## 目录结构

```
life-classics/
├── web/                              # Turborepo monorepo
│   ├── apps/
│   │   └── console/                  # 管理后台（原 admin/）
│   ├── packages/                      # Turborepo shared packages
│   ├── turbo.json
│   ├── pnpm-workspace.yaml
│   └── package.json
│
└── server/                            # Python uv workspace monorepo
    ├── api/                           # FastAPI 入口、路由、 schemas
    ├── agent/                         # Agent 核心
    │   ├── factory.py                 # Agent 工厂（路由逻辑）
    │   ├── food_safety_agent.py       # 食品安全助手
    │   ├── llm_adapter.py
    │   ├── session_store.py
    │   └── skill_loader.py
    ├── kb/                            # 知识库
    │   ├── clients.py                 # ChromaDB 连接管理
    │   ├── embeddings.py              # 嵌入模型
    │   ├── writer/                    # 写入（chroma_writer, fts_writer）
    │   └── retriever/                 # 检索（vector, fts, rrf, rerank）
    ├── parser/                        # 文档处理流水线（原 parser-workflow）
    │   ├── graph.py                   # LangGraph 图定义
    │   ├── models.py                  # 核心数据模型
    │   ├── nodes/                     # 各处理节点
    │   ├── rules/                     # 分类规则
    │   └── structured_llm/            # Instructor LLM 封装
    ├── pyproject.toml                 # uv workspace 定义
    ├── uv.lock
    └── run.py                         # 服务入口
```

## 模块职责

### api/
- FastAPI 应用入口
- 路由定义（`app/api/`）
- Request/Response schemas
- CORS、中间件配置

### agent/
- Agent 工厂：根据 `agent_type` 路由到具体 Agent
- 国标 RAG Agent：基于 Deep Agents + LangGraph 的多工具 Agent
- 食品安全助手：基于 Agno 框架的 Agent
- 技能加载（skill_loader）
- Session 存储

### kb/
- ChromaDB 客户端封装
- 嵌入模型封装
- 写入层：向量写入、全文索引写入
- 检索层：向量检索、BM25检索、RRF融合、重排序

### parser/
- 文档处理流水线（LangGraph）
- 核心数据模型（DocumentChunk、TypedSegment、WorkflowState）
- 各处理节点：parse、clean、structure、slice、classify、escalate、enrich、transform、merge
- 分类规则和 Instructor LLM 封装

## uv Workspace 配置

```toml
# server/pyproject.toml
[tool.uv.workspace]
members = [
    "api",
    "agent",
    "kb",
    "parser",
]
```

成员之间通过路径引用：
```toml
# api/pyproject.toml
[project]
dependencies = [
    "agent = { path = "../agent" }",
    "kb = { path = "../kb" }",
    "parser = { path = "../parser" }",
]
```

## 迁移步骤

1. **创建新目录结构**
   - `web/apps/console/` ← 移动 `agent-server/admin/`
   - `server/{api,agent,kb,parser}/` ← 从 `agent-server/app/` 拆分

2. **更新导入路径**
   - 所有 `from app.core` → `from agent` / `from kb` / `from parser`
   - API 中的 `from app.api` → `from api`

3. **更新 pyproject.toml**
   - 在 `server/` 创建 uv workspace 配置
   - 各子包创建独立的 pyproject.toml

4. **更新配置和启动脚本**
   - `run.py` 移入 `server/`
   - 环境变量路径可能需要调整

5. **更新文档**
   - CLAUDE.md 中的路径引用
   - README.md

6. **测试验证**
   - `uv sync` 验证依赖
   - `uv run python run.py` 验证启动
   - API 测试通过

## 风险与注意事项

1. **导入路径变更** — 涉及文件多，需要仔细验证
2. **环境变量** — 确认 `.env` 路径和变量名不变
3. **admin 前端** — 需要检查是否有硬编码的 API 路径需要更新
4. **测试文件** — 测试中的导入路径也需要同步更新
