# 项目结构重组实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构项目目录结构，实现前后端分离和 Python 代码模块化

**Architecture:**
- 前端：Turborepo monorepo (`web/`)
  - `web/apps/console/` — 管理后台（原 admin）
- 后端：uv workspace monorepo (`server/`)
  - `server/api/` — FastAPI 入口和路由
  - `server/agent/` — Agent 核心
  - `server/kb/` — 知识库
  - `server/parser/` — 文档处理流水线

**Tech Stack:** uv workspace, Turborepo, pnpm workspaces

---

## Phase 1: 前端重组 (client → web, admin → console)

### Task 1.1: 重命名 client/ → web/

**Files:**
- Modify: `.gitignore` (新目录也需要忽略)
- Modify: `CLAUDE.md` 路径引用

- [ ] **Step 1: 重命名目录**

```bash
mv client web
```

- [ ] **Step 2: 更新 .gitignore**

```bash
# 添加 web/ 相关忽略
echo "web/node_modules/" >> .gitignore
echo "web/.turbo/" >> .gitignore
echo "web/.pnpm-store/" >> .gitignore
```

- [ ] **Step 3: 更新 CLAUDE.md 中的路径引用**

```bash
# 需要更新的引用:
# - agent-server/admin/ → web/apps/console/
# - client/ → web/
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "refactor: rename client/ to web/"
```

---

### Task 1.2: 移动 admin/ → web/apps/console/

**Files:**
- Move: `agent-server/admin/` → `web/apps/console/`

- [ ] **Step 1: 创建目录并移动**

```bash
mkdir -p web/apps/console
mv agent-server/admin/* web/apps/console/
mv agent-server/admin/.* web/apps/console/ 2>/dev/null || true
rmdir agent-server/admin
```

- [ ] **Step 2: 检查 console 中是否有硬编码路径**

```bash
# 检查 package.json, vite.config.ts, index.html 中的路径
grep -r "agent-server" web/apps/console/ || echo "No hardcoded paths found"
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "refactor: move admin/ to web/apps/console/"
```

---

## Phase 2: 后端重组 (agent-server → server)

### Task 2.1: 重命名 agent-server/ → server/

**Files:**
- Move: `agent-server/` → `server/`

- [ ] **Step 1: 重命名目录**

```bash
mv agent-server server
```

- [ ] **Step 2: 更新 CLAUDE.md**

```bash
# 在 worktree 根目录执行
# CLAUDE.md 中所有 agent-server/ 引用改为 server/
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "refactor: rename agent-server/ to server/"
```

---

## Phase 3: Python uv workspace 重构

### Task 3.1: 创建 server/ 的 uv workspace 结构

**Files:**
- Create: `server/pyproject.toml` (workspace root)
- Create: `server/api/pyproject.toml`
- Create: `server/agent/pyproject.toml`
- Create: `server/kb/pyproject.toml`
- Create: `server/parser/pyproject.toml`

- [ ] **Step 1: 创建 workspace root pyproject.toml**

```toml
# server/pyproject.toml
[project]
name = "server"
version = "0.1.0"
description = "知识库系统后端"
requires-python = ">=3.12"

[tool.uv.workspace]
members = [
    "api",
    "agent",
    "kb",
    "parser",
]

[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
]
```

- [ ] **Step 2: 创建 api/pyproject.toml**

```toml
# server/api/pyproject.toml
[project]
name = "api"
version = "0.1.0"
dependencies = [
    "agent = { path = "../agent" }",
    "kb = { path = "../kb" }",
    "parser = { path = "../parser" }",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: 创建 agent/pyproject.toml**

```toml
# server/agent/pyproject.toml
[project]
name = "agent"
version = "0.1.0"
dependencies = [
    "kb = { path = "../kb" }",
    "parser = { path = "../parser" }",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 4: 创建 kb/pyproject.toml**

```toml
# server/kb/pyproject.toml
[project]
name = "kb"
version = "0.1.0"
dependencies = [
    "parser = { path = "../parser" }",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 5: 创建 parser/pyproject.toml**

```toml
# server/parser/pyproject.toml
[project]
name = "parser"
version = "0.1.0"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat(server): create uv workspace structure with api, agent, kb, parser packages"
```

---

### Task 3.2: 移动代码到新包结构

**Files:**
- Move: `server/app/core/parser_workflow/` → `server/parser/`
- Move: `server/app/core/kb/` → `server/kb/`
- Move: `server/app/core/agent/` → `server/agent/`
- Move: `server/app/api/` → `server/api/`
- Move: `server/app/skills/` → `server/agent/` (Agent skills)
- Move: `server/app/core/` → `server/api/` (llm/ 等共享代码)
- Move: `server/app/web/` → `server/api/` (web 路由)
- Move: `server/app/main.py` → `server/api/main.py`
- Move: `server/app/core/config.py` → `server/parser/config.py` (避免循环依赖)

**注意**: `config.py` 放在 `parser/` 而不是 `api/`，因为：
- `parser` 是依赖链的根节点（其他包都依赖它）
- 避免 `agent` 和 `kb` 需要从 `api` 导入 config 造成的循环依赖

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p server/api server/agent server/kb server/parser
```

- [ ] **Step 2: 移动 parser-workflow → parser**

```bash
mv server/app/core/parser_workflow/* server/parser/
rm -rf server/app/core/parser_workflow
```

- [ ] **Step 3: 移动 kb → kb**

```bash
mv server/app/core/kb/* server/kb/
rm -rf server/app/core/kb
```

- [ ] **Step 4: 移动 agent → agent**

```bash
mv server/app/core/agent/* server/agent/
rm -rf server/app/core/agent
```

- [ ] **Step 5: 移动 config.py → parser/config.py**

```bash
# config.py 需要放在 parser/，避免循环依赖
mv server/app/core/config.py server/parser/config.py
```

- [ ] **Step 6: 移动其他共享代码 (llm/, api/, web/, main.py)**

```bash
# 移动 llm/ 等共享代码
mv server/app/core/llm server/api/
# 移动 api 路由
mv server/app/api/* server/api/
# 移动 web 路由
mv server/app/web/* server/api/ 2>/dev/null || true
# 移动 main.py
mv server/app/main.py server/api/main.py
# 移动 skills
mv server/app/skills/* server/agent/ 2>/dev/null || true
```

- [ ] **Step 7: 清理空目录**

```bash
rmdir server/app/core server/app/api server/app/web server/app/skills server/app 2>/dev/null || true
```

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor(server): move app/ contents to workspace packages"
```

---

### Task 3.3: 更新导入路径

**Files:**
- Modify: `server/api/main.py` — `from app.core` → `from agent` / `from kb` / `from parser`
- Modify: `server/agent/factory.py` — 更新导入
- Modify: `server/agent/food_safety_agent.py` — 更新导入
- Modify: `server/kb/` — 更新导入
- Modify: `server/parser/` — 更新导入
- Modify: `server/run.py` — 更新导入

- [ ] **Step 1: 列出所有需要更新的导入**

```bash
# 在 server/ 目录执行
grep -r "from app\." server/ --include="*.py" | head -50
grep -r "import app\." server/ --include="*.py" | head -50
```

- [ ] **Step 2: 更新 api/main.py**

```python
# 原来: from app.core.config import settings
# 现在: from parser.config import settings

# 原来: from app.core.agent import ...
# 现在: from agent import ...

# 原来: from app.core.kb import ...
# 现在: from kb import ...

# 原来: from app.core.parser_workflow import ...
# 现在: from parser import ...
```

- [ ] **Step 3: 更新 agent/factory.py**

```python
# 原来: from app.core.agent.food_safety_agent import FoodSafetyAgent
# 现在: from agent.food_safety_agent import FoodSafetyAgent

# 原来: from app.skills import ...
# 现在: from agent.skills import ...
```

- [ ] **Step 4: 更新 kb/ 中的导入**

```python
# 原来: from app.core.parser_workflow.models import DocumentChunk
# 现在: from parser.models import DocumentChunk
```

- [ ] **Step 5: 更新 parser/ 中的导入**

```python
# parser 内部导入一般不需要改，因为都在 parser/ 目录内
```

- [ ] **Step 6: 更新 run.py**

```python
# 原来: from app.main import app
# 现在: from api.main import app
```

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor(server): update import paths to workspace packages"
```

---

### Task 3.4: 验证 uv sync 和服务启动

**Files:**
- Modify: `server/pyproject.toml` (合并原 agent 依赖)

- [ ] **Step 1: 运行 uv sync**

```bash
cd server
uv sync
```

预期: 成功解析所有包依赖

- [ ] **Step 2: 尝试启动服务**

```bash
cd server
uv run python run.py
```

预期: 服务启动成功，无导入错误

- [ ] **Step 3: 运行测试验证**

```bash
cd server
uv run pytest tests/ -v --tb=short -q 2>&1 | tail -30
```

预期: 测试通过（或只有预存失败）

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "chore(server): verify uv workspace setup"
```

---

### Task 3.5: 更新测试文件中的导入路径

**Files:**
- Modify: `server/tests/` 下的所有测试文件

- [ ] **Step 1: 查找所有需要更新的测试导入**

```bash
cd server
grep -r "from app\." tests/ --include="*.py" | sort -u
grep -r "import app\." tests/ --include="*.py" | sort -u
```

预期输出类似:
```
tests/api/chunks/test_service.py:from app.core.parser_workflow.models import DocumentChunk
tests/api/documents/test_service.py:from app.api.documents.service import ...
tests/core/agent/test_food_safety_agent.py:from app.core.agent.session_store import ...
tests/core/kb/retriever/test_vector_retriever.py:from app.core.kb.embeddings import ...
```

- [ ] **Step 2: 使用 sed 批量替换**

```bash
cd server
find tests/ -name "*.py" -exec sed -i '' \
    -e 's/from app\.core\.parser_workflow\./from parser./g' \
    -e 's/from app\.core\.kb\./from kb./g' \
    -e 's/from app\.core\.agent\./from agent./g' \
    -e 's/from app\.api\./from api./g' \
    -e 's/from app\.skills/from agent.skills/g' \
    -e 's/from app\.main/from api.main/g' \
    {} \;
```

- [ ] **Step 3: 验证无遗漏**

```bash
cd server
grep -r "from app\." tests/ --include="*.py" | wc -l
# 预期: 0
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "refactor(server): update test import paths"
```

---

## Phase 4: 文档更新

### Task 4.1: 更新 CLAUDE.md 和 README.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: 更新项目概览**

```markdown
## 项目概览

本仓库为 monorepo，包含：
- `server/` — Python FastAPI 后端：基于 RAG 的多工具 Agent，用于查询中国食品安全国家标准（GB 标准）
  - `server/api/` — FastAPI 入口和路由
  - `server/agent/` — Agent 核心
  - `server/kb/` — 知识库
  - `server/parser/` — 文档处理流水线
- `web/apps/console/` — React/Vite 管理界面（知识库 Chunk 浏览与编辑）
- `web/apps/nextjs/` — Next.js 前端（Turbo monorepo）
```

- [ ] **Step 2: 更新执行环境说明**

```markdown
### Python 执行环境
`server/` 使用 **uv** 管理 Python 虚拟环境和 workspace。所有 Python 相关命令在 `server/` 目录下执行：

```bash
cd server
uv sync
uv run python run.py
uv run pytest tests/ -v
```
```

- [ ] **Step 3: 更新架构说明中的路径**

所有 `app/core/parser_workflow/` → `server/parser/`
所有 `app/core/kb/` → `server/kb/`
所有 `app/core/agent/` → `server/agent/`
所有 `app/api/` → `server/api/`

- [ ] **Step 4: 更新 README.md**

```bash
# 更新 README.md 中的路径引用
# - agent-server/ → server/
# - app/core/ → 新的包路径
```

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "docs: update CLAUDE.md and README.md for new project structure"
```

---

## Phase 5: 最终验证

### Task 5.1: 完整验证

- [ ] **Step 1: 确认目录结构**

```bash
# 最终结构应该是:
ls -la web/
ls -la web/apps/
ls -la web/apps/console/
ls -la server/
ls -la server/api/
ls -la server/agent/
ls -la server/kb/
ls -la server/parser/
```

- [ ] **Step 2: 确认 git status**

```bash
git status
```

预期: 只有新结构的文件，无遗留文件

- [ ] **Step 3: 最终测试**

```bash
cd server
uv run pytest tests/ -v --tb=no -q 2>&1 | tail -10
```

- [ ] **Step 4: 提交所有更改**

```bash
git add -A
git commit -m "refactor: complete project structure redesign

- Move client/ to web/
- Move admin/ to web/apps/console/
- Rename agent-server/ to server/
- Create uv workspace with api, agent, kb, parser packages
- Update all import paths
- Update documentation"
```

---

## 风险与回滚

**如果出现问题:**
```bash
# 回滚到最后一次正常提交
git worktree remove .worktrees/refactor-project-structure
git worktree prune
git branch -D refactor/project-structure
```

**预期产出:**
- `web/` — Turborepo monorepo (原 client)
- `web/apps/console/` — 管理后台 (原 admin)
- `server/` — Python uv workspace monorepo (原 agent-server)
  - `api/` — FastAPI 入口
  - `agent/` — Agent 核心
  - `kb/` — 知识库
  - `parser/` — 文档处理流水线
