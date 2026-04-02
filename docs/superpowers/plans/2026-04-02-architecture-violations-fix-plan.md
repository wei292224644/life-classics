# 架构违规修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 server/ 代码对 server-architecture.md 的所有架构违规，建立规范的四层架构。

**Architecture:** 核心思路是按 Phase 逐步修复：① 先修最严重的 Assembler DB 访问，② 再修 L3 commit 越权，③ 再建立 L2 services 层，④ 最后统一清理 api→infra 的直接引用。

**Tech Stack:** Python (FastAPI, SQLAlchemy async, Pydantic)

---

## 涉及文件概览

| 操作类型 | 文件路径 | 说明 |
|----------|----------|------|
| 创建 | `server/services/` | 新建 L2 services 层 |
| 修改 | `server/api/analysis/assembler.py` | 移除 DB 查询，纯数据组装 |
| 修改 | `server/api/analysis/service.py` | 拆分数据查询到 L2 |
| 修改 | `server/api/ingredient_alias/service.py` | 移除 commit，委托 Repository |
| 修改 | `server/api/ingredients/service.py` | 移除 self-managed session |
| 修改 | `server/api/documents/service.py` | 移除 infra 直接引用 |
| 修改 | `server/api/chunks/service.py` | 移除 infra 直接引用 |
| 修改 | `server/api/kb/service.py` | 移除 infra 直接引用 |
| 修改 | `server/api/agent/router.py` | 移除 infra 直接引用 |
| 修改 | `server/db_repositories/ingredient.py` | 移除 5 处 commit |
| 修改 | `server/db_repositories/ingredient_analysis.py` | 移除 1 处 commit |
| 修改 | `server/api/shared.py` | logger.exception → logger.error |

---

## Phase 1: 修复 Assembler DB 访问（T4 违规）

### Task 1: 重构 `api/analysis/assembler.py` — 移除所有 SQL 查询

**文件:**
- 修改: `server/api/analysis/assembler.py`
- 修改: `server/api/analysis/service.py`

- [ ] **Step 1: 阅读现有 assembler.py 确认所有 DB 访问点**

阅读 `server/api/analysis/assembler.py` 全文，确认：
- `_build_ingredients_list()` 中 `session.execute(select(Ingredient)...)` 的行号
- `_build_alternatives()` 中 `repo.get_active_by_ingredient_id()` 的调用位置
- `assemble_from_db_cache()` 中 `analysis_repo.get_active_by_ingredient_id()` 的调用位置
- `assemble_from_agent_output()` 中同样模式

- [ ] **Step 2: 阅读 `api/analysis/service.py` 确认调用 assembler 的位置**

阅读 `server/api/analysis/service.py`，确认 `run_analysis_sync()` 的完整实现（行号、session 管理方式），以及 assembler 被调用的入口点。

- [ ] **Step 3: 修改 assembler.py — 移除所有 DB 查询，改为纯组装**

将 `assemble_from_db_cache()` 和 `assemble_from_agent_output()` 的签名从：
```python
async def assemble_from_db_cache(product_analysis, matched_ids, session):
```
改为（session 不再传入）：
```python
async def assemble_from_db_cache(
    product_analysis,
    matched_ids,
    ingredients_data: list[dict],       # 预查好的 Ingredient 数据
    analyses_data: list[dict],           # 预查好的 IngredientAnalysis 数据
) -> ProductAnalysisResult:
```

同理修改 `assemble_from_agent_output()`：
```python
async def assemble_from_agent_output(
    agent_output,
    matched_ids,
    ingredients_data: list[dict],
    analyses_data: list[dict],
) -> ProductAnalysisResult:
```

删除:
- `from sqlalchemy import select`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `_build_ingredients_list()` 函数（数据组装逻辑下移到 service 层）
- `_build_alternatives()` 函数（数据组装逻辑下移到 service 层）

所有 `await repo.get_active_by_ingredient_id()` 调用全部移除，因为 `analyses_data` 已经预查好。

- [ ] **Step 4: 修改 `api/analysis/service.py` — 将 DB 查询前置，assembler 接收预查数据**

在 `run_analysis_sync()` 中（大约行 20-25 的 `assemble_from_agent_output` 调用处，和 `assemble_from_db_cache` 调用处），在调用 assembler **之前**先查好所有数据：

```python
# 1. 预查 Ingredient 数据（新增）
from db_repositories.ingredient import IngredientRepository
ing_repo = IngredientRepository(session)
ingredients_raw = await ing_repo.fetch_by_ids(matched_ids)  # 需在 IngredientRepository 新增此方法
ingredients_data = [
    {
        "id": ing.id,
        "name": ing.name,
        "function_type": ing.function_type or [],
    }
    for ing in ingredients_raw
]

# 2. 预查 IngredientAnalysis 数据（新增）
from db_repositories.ingredient_analysis import IngredientAnalysisRepository
analysis_repo = IngredientAnalysisRepository(session)
analyses_raw = await analysis_repo.fetch_by_ingredient_ids(matched_ids)  # 需新增此方法
analyses_data = {a.ingredient_id: a for a in analyses_raw}

# 3. 调用 assembler（只传数据，不传 session）
result = await assemble_from_agent_output(
    agent_output=output,
    matched_ids=matched_ids,
    ingredients_data=ingredients_data,
    analyses_data=analyses_data,
)
```

同理处理 `assemble_from_db_cache()` 的调用路径。

- [ ] **Step 5: 在 `IngredientRepository` 新增 `fetch_by_ids()` 方法**

修改 `server/db_repositories/ingredient.py`，在 `IngredientRepository` 类中新增：

```python
async def fetch_by_ids(self, ids: list[int]) -> list[Ingredient]:
    """批量查询 Ingredient，用于 assembler 预填充数据."""
    if not ids:
        return []
    result = await self._session.execute(
        select(Ingredient).where(Ingredient.id.in_(ids))
    )
    return list(result.scalars().all())
```

- [ ] **Step 6: 在 `IngredientAnalysisRepository` 新增 `fetch_by_ingredient_ids()` 方法**

修改 `server/db_repositories/ingredient_analysis.py`，新增：

```python
async def fetch_by_ingredient_ids(self, ingredient_ids: list[int]) -> list[IngredientAnalysis]:
    """批量查询活跃的 IngredientAnalysis，用于 assembler 预填充数据."""
    if not ingredient_ids:
        return []
    result = await self._session.execute(
        select(IngredientAnalysis).where(
            IngredientAnalysis.ingredient_id.in_(ingredient_ids),
            IngredientAnalysis.is_active.is_(True),
            IngredientAnalysis.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
```

- [ ] **Step 7: 运行测试确认 assembler 正常工作**

```bash
cd server
uv run pytest tests/api/analysis/ -v -x
```

预期：所有测试通过，assembler 不再直接访问 DB。

- [ ] **Step 8: 提交**

```bash
git add server/api/analysis/assembler.py server/api/analysis/service.py server/db_repositories/ingredient.py server/db_repositories/ingredient_analysis.py
git commit -m "fix(analysis): remove DB access from assembler, pre-query data in service layer"
```

---

## Phase 2: 修复 L3 Repository commit 越权（Section IV 违规）

### Task 2: 移除 `db_repositories/ingredient.py` 中的 5 处 commit

**文件:**
- 修改: `server/db_repositories/ingredient.py:30,36,85,97,107`

- [ ] **Step 1: 阅读 `ingredient.py` 确认每处 commit 的上下文**

阅读 `server/db_repositories/ingredient.py`，确认每处 `.commit()` 所在方法：
- 行 30: upsert 分支
- 行 36: upsert 新建分支
- 行 85: update_full
- 行 97: update_partial
- 行 107: soft_delete

- [ ] **Step 2: 将所有 `await self._session.commit()` 改为 `await self._session.flush()`**

```python
# 改前
await self._session.commit()

# 改后
await self._session.flush()
```

flush() 将变更同步到 DB 但不提交事务，事务提交权保留在 L1 Router 层。

- [ ] **Step 3: 运行测试确认**

```bash
cd server
uv run pytest tests/db_repositories/test_ingredient_repo.py -v -x
```

- [ ] **Step 4: 提交**

```bash
git add server/db_repositories/ingredient.py
git commit -m "fix(repository): replace commit() with flush() in IngredientRepository"
```

### Task 3: 移除 `db_repositories/ingredient_analysis.py` 中的 1 处 commit

**文件:**
- 修改: `server/db_repositories/ingredient_analysis.py:73`

- [ ] **Step 1: 阅读确认 commit 上下文**

- [ ] **Step 2: 将 `await self._session.commit()` 改为 `await self._session.flush()`**

- [ ] **Step 3: 运行测试确认**

```bash
cd server
uv run pytest tests/db_repositories/test_ingredient_analysis_repo.py -v -x
```

- [ ] **Step 4: 提交**

```bash
git add server/db_repositories/ingredient_analysis.py
git commit -m "fix(repository): replace commit() with flush() in IngredientAnalysisRepository"
```

### Task 4: 修复 `api/ingredient_alias/service.py` 的 2 处 commit

**文件:**
- 修改: `server/api/ingredient_alias/service.py:44,69`
- 修改: `server/api/ingredient_alias/router.py`（事务上收）

- [ ] **Step 1: 阅读 router.py 确认 commit 应该在哪里**

阅读 `server/api/ingredient_alias/router.py`，找到调用 `create_alias()` 和 `delete_alias()` 的 router 方法，确认 session 生命周期。

- [ ] **Step 2: 从 service.py 移除 commit 调用**

将 `create_alias()` 和 `delete_alias()` 中的 `await self._session.commit()` 删除。

- [ ] **Step 3: 在 router 层统一提交事务**

在 router 的 POST/DELETE 端点中，在 service 调用后添加 `await session.commit()`：

```python
@router.post("/", response_model=AliasResponse)
async def create_alias(
    body: AliasCreate,
    svc: IngredientAliasService = Depends(get_service),
    session: AsyncSession = Depends(get_async_session),
):
    result = await svc.create_alias(session, body)  # session 作为参数传入
    await session.commit()  # 事务在 L1 提交
    return result
```

**注意**: 需要将 `session` 作为参数传给 service 的 `create_alias`/`delete_alias` 方法，而非在 service 内部管理。

- [ ] **Step 4: 运行测试确认**

```bash
cd server
uv run pytest tests/ -v -x -k "alias"
```

- [ ] **Step 5: 提交**

```bash
git add server/api/ingredient_alias/service.py server/api/ingredient_alias/router.py
git commit -m "fix(ingredient_alias): move commit to router layer, pass session as param"
```

---

## Phase 3: 修复 L1 Session 自管理（T5 违规）

### Task 5: 重构 `api/ingredients/service.py` 的 `trigger_analysis()`

**文件:**
- 修改: `server/api/ingredients/service.py`
- 修改: `server/api/ingredients/router.py`

- [ ] **Step 1: 阅读确认 `get_async_session_cm()` 的使用位置**

确认 `trigger_analysis()` 中 `get_async_session_cm()` 的使用（行 106, 139）。

- [ ] **Step 2: 修改 `trigger_analysis()` 签名，接收 session 参数**

```python
# 改前
async def trigger_analysis(self, ingredient_id: int, background_tasks) -> dict | None:

# 改后
async def trigger_analysis(
    self,
    ingredient_id: int,
    session: AsyncSession,       # 新增
    background_tasks,
) -> dict | None:
```

- [ ] **Step 3: 移除内部的 `get_async_session_cm()` 调用**

删除：
```python
from database.session import get_async_session_cm
# ...
async with get_async_session_cm() as session:  # 删除此行
```

将 service 内创建的 session 替换为从 router 注入的 session。

- [ ] **Step 4: 修改 router 传递 session**

阅读 `server/api/ingredients/router.py`，在调用 `trigger_analysis()` 处传入 `session` 参数。

- [ ] **Step 5: 运行测试确认**

```bash
cd server
uv run pytest tests/ -v -x -k "ingredient"
```

- [ ] **Step 6: 提交**

```bash
git add server/api/ingredients/service.py server/api/ingredients/router.py
git commit -m "fix(ingredients): inject session from router, remove self-managed session"
```

---

## Phase 4: 建立 L2 Services 层（解决 api→infra 违规）

### Task 6: 创建 `services/` 包结构和 KB Service

**文件:**
- 创建: `server/services/__init__.py`
- 创建: `server/services/kb_service.py`
- 创建: `server/services/parser_workflow_service.py`

- [ ] **Step 1: 创建 `services/` 目录和 `__init__.py`**

```python
"""L2 Services 层 — 业务编排、跨 Repository 协调."""
```

- [ ] **Step 2: 创建 `services/kb_service.py`**

将 `api/documents/service.py`、`api/chunks/service.py`、`api/kb/service.py` 中对 `kb/` 的直接引用抽离到 `KBService`：

```python
from typing import AsyncIterator

from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.writer import chroma_writer, fts_writer
from db_repositories.document import DocumentRepository
from db_repositories.chunk import ChunkRepository

class KBService:
    """L2: 知识库业务编排 — 操作 ChromaDB / FTS / Document / Chunk."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
    ):
        self._doc_repo = doc_repo
        self._chunk_repo = chunk_repo

    async def upload_document(
        self,
        session: AsyncSession,
        title: str,
        markdown_content: str,
    ):
        # 1. 写 PostgreSQL
        doc = await self._doc_repo.create(session, title, markdown_content)
        # 2. 写入 ChromaDB + FTS
        chunks = await self._chunk_repo.split_and_store(doc.id, markdown_content)
        await chroma_writer.write(chunks)
        await fts_writer.write_chunks(chunks)
        return doc

    async def delete_document(self, session: AsyncSession, doc_id: int):
        await self._doc_repo.soft_delete(doc_id)
        # 从 ChromaDB 和 FTS 删除
        await chroma_writer.delete_by_document_id(doc_id)
        await fts_writer.delete_by_document_id(doc_id)

    # ... 其他 KB 相关方法
```

- [ ] **Step 3: 创建 `services/parser_workflow_service.py`**

将 `api/chunks/service.py` 中对 `workflow_parser_kb/` 的直接引用抽离：

```python
from workflow_parser_kb.graph import run_parser_workflow_stream
from workflow_parser_kb.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState
from workflow_parser_kb.nodes.merge_node import merge_node
from workflow_parser_kb.nodes.transform_node import transform_node
from workflow_parser_kb.rules import RulesStore

class ParserWorkflowService:
    """L2: Parser Workflow 编排 — 调用 workflow_parser_kb."""

    async def run_parse_workflow(self, markdown_content: str):
        async for event in run_parser_workflow_stream(markdown_content):
            yield event
```

- [ ] **Step 4: 提交**

```bash
git add server/services/
git commit -m "feat(services): create L2 services layer with KBService and ParserWorkflowService"
```

### Task 7: 重构 `api/documents/service.py` — 通过 L2 访问 infra

**文件:**
- 修改: `server/api/documents/service.py`
- 修改: `server/api/documents/router.py`

- [ ] **Step 1: 阅读确认 infra 引用位置**

确认 `api/documents/service.py` 中 `from kb.clients`、`from kb.writer` 的使用位置。

- [ ] **Step 2: 修改 `DocumentsService` — 注入 `KBService`，移除 kb 直接引用**

```python
# 改前
from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.writer import chroma_writer, fts_writer

# 改后
from services.kb_service import KBService

class DocumentsService:
    def __init__(self, repo: DocumentRepository, kb_service: KBService):
        self._repo = repo
        self._kb_service = kb_service
```

所有原来直接调用 `chroma_writer`、`fts_writer` 的地方改为 `await self._kb_service.xxx()`。

- [ ] **Step 3: 修改 `api/documents/router.py` — 注入 KBService**

```python
from services.kb_service import KBService

def get_kb_service(
    session: AsyncSession = Depends(get_async_session),
    doc_repo: DocumentRepository = Depends(get_doc_repo),
) -> KBService:
    return KBService(doc_repo=doc_repo)

@router.post("/")
async def upload_document(
    session: AsyncSession = Depends(get_async_session),
    kb_svc: KBService = Depends(get_kb_service),
    # ...
):
    doc = await kb_svc.upload_document(session, title, markdown_content)
    await session.commit()
    return doc
```

- [ ] **Step 4: 运行测试确认**

```bash
cd server
uv run pytest tests/api/ -v -x -k "document"
```

- [ ] **Step 5: 提交**

```bash
git add server/api/documents/
git commit -m "refactor(documents): route KB access through L2 KBService"
```

### Task 8: 重构 `api/chunks/service.py` — 通过 L2 访问 infra

**文件:**
- 修改: `server/api/chunks/service.py`
- 修改: `server/api/chunks/router.py`

- [ ] **Step 1: 阅读确认 infra 引用位置**

确认 `api/chunks/service.py` 中对 `kb/`、`workflow_parser_kb/` 的直接引用。

- [ ] **Step 2: 修改 `ChunksService` — 注入 `KBService` 和 `ParserWorkflowService`**

删除所有 `from kb/...` 和 `from workflow_parser_kb/...` 导入，改为通过 service 层调用。

- [ ] **Step 3: 修改 router.py 注入 L2 service**

- [ ] **Step 4: 运行测试确认**

```bash
cd server
uv run pytest tests/api/ -v -x -k "chunk"
```

- [ ] **Step 5: 提交**

```bash
git add server/api/chunks/
git commit -m "refactor(chunks): route KB and workflow access through L2 services"
```

### Task 9: 重构 `api/kb/service.py` — 通过 L2 访问 infra

**文件:**
- 修改: `server/api/kb/service.py`
- 修改: `server/api/kb/router.py`

- [ ] **Step 1: 同样的模式 — 移除 kb 直接引用，通过 KBService**

- [ ] **Step 2: 提交**

```bash
git add server/api/kb/
git commit -m "refactor(kb): route KB access through L2 KBService"
```

### Task 10: 重构 `api/analysis/service.py` — 通过 L2 访问 workflow

**文件:**
- 修改: `server/api/analysis/service.py`
- 修改: `server/api/analysis/router.py`

- [ ] **Step 1: 阅读确认 workflow 直接引用位置**

确认 `api/analysis/service.py` 中 `from workflow_product_analysis.product_agent.graph import ...` 的使用位置。

- [ ] **Step 2: 创建 `services/product_analysis_service.py`**

```python
from workflow_product_analysis.product_agent.graph import build_product_analysis_graph, ProductAgentError
from workflow_product_analysis.product_agent.types import ProductAnalysisState

class ProductAnalysisService:
    """L2: 产品分析业务编排 — 调用 workflow_product_analysis."""

    async def run_product_analysis(
        self,
        ingredients: list[dict],
        session: AsyncSession,
    ):
        graph = build_product_analysis_graph()
        # ... 调用 workflow
```

- [ ] **Step 3: 修改 `api/analysis/service.py` — 通过 L2 调用 workflow**

- [ ] **Step 4: 运行测试确认**

- [ ] **Step 5: 提交**

```bash
git add server/api/analysis/ server/services/
git commit -m "refactor(analysis): route workflow access through L2 ProductAnalysisService"
```

### Task 11: 重构 `api/agent/router.py` — 通过 L2 访问 agent infra

**文件:**
- 修改: `server/api/agent/router.py`

- [ ] **Step 1: 创建 `services/agent_service.py`**

```python
from agent.session_store import get_session_store
from agent.agent import get_agent

class AgentService:
    """L2: Agent 业务编排 — 调用 agent/ infra."""

    async def chat(self, session_id: str, message: str):
        store = get_session_store()
        agent = get_agent()
        return await agent.run(session_id, message)
```

- [ ] **Step 2: 修改 router.py — 注入 AgentService，移除 infra 直接引用**

- [ ] **Step 3: 运行测试确认**

- [ ] **Step 4: 提交**

```bash
git add server/api/agent/ server/services/
git commit -m "refactor(agent): route agent access through L2 AgentService"
```

---

## Phase 5: 修复剩余违规

### Task 12: 修复 `api/shared.py` logger.exception

**文件:**
- 修改: `server/api/shared.py:11`

- [ ] **Step 1: 将 `logger.exception()` 改为 `logger.error()`**

- [ ] **Step 2: 提交**

```bash
git add server/api/shared.py
git commit -m "fix(api): replace logger.exception with logger.error to avoid stack leakage"
```

---

## 验证阶段

### Task 13: 完整回归测试

- [ ] **Step 1: 运行全部测试**

```bash
cd server
uv run pytest tests/ -v --tb=short
```

- [ ] **Step 2: 审计报告自检 — 确认所有违规已修复**

重新运行 4 个审计 agent（或人工检查），确认：
- T1-T5: 6 项违规全部修复
- Section III: 20 处违规全部修复
- Section IV/IX: 9 处违规全部修复
- Section VII/X: 0 项（原本无违规）

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "refactor(server): complete architecture compliance - all violations fixed"
```

---

## 任务依赖关系

```
Phase 1 (Task 1)
  └─ Assembler 重构 → 为后续 L2 service 提供数据预查模式

Phase 2 (Task 2, 3, 4)
  └─ 可并行执行：各修各的 commit 越权

Phase 3 (Task 5)
  └─ 依赖 Phase 2 完成（session 事务上收模式建立后）

Phase 4 (Task 6 → 7 → 8 → 9 → 10 → 11)
  └─ Task 6 先行（建 L2 services 基础）
  └─ Task 7, 8, 9 可并行（各自重构一个 api module）
  └─ Task 10, 11 可并行（analysis 和 agent）

Phase 5 (Task 12)
  └─ 可独立执行

验证 (Task 13)
  └─ 依赖所有 Phase 完成
```

---

## 修复后预期架构

```
api/                    ← L1: HTTP 入口、路由、参数校验
  └─ */*.py            ← Service 类（仅做参数组装，不操作 infra）
  └─ shared.py         ← 共享工具

services/               ← L2 (新建): 业务编排、跨 Repo 协调
  ├─ kb_service.py     ← 操作 ChromaDB/FTS
  ├─ parser_workflow_service.py  ← 调用 workflow_parser_kb
  └─ agent_service.py  ← 调用 agent/

db_repositories/        ← L3: 单表 CRUD
  └─ *Repo             ← 全部 flush()，无 commit()

database/               ← L4: ORM 模型、Session 工厂

kb/, llm/, workflow_*   ← Infra: 外部依赖封装
```
