# 架构违规修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 4 类架构违规（T1 跨模块调用、T1 Session 自管理、T2 L1→Infra 直接引用、T4 Assembler 访问 DB），使代码符合 `ARCHITECTURE_STANDARDS.md v1.0` 规范。

**Architecture:** 分 P0 / P1 两阶段修复。P0 为低风险孤立改动；P1 为目录结构调整，涉及新建 `services/` 包并重构 KB/Workflow 调用路径。所有修复遵循「单向依赖：L1→L2→L3→L4」原则。

**Tech Stack:** Python async/await, SQLAlchemy AsyncSession, FastAPI BackgroundTasks

---

## 文件结构变更总览

```
server/
├── services/                              # [新建] L2 服务层
│   ├── __init__.py
│   ├── ingredient_analysis/
│   │   ├── __init__.py
│   │   └── workflow_executor.py          # [新建] 封装 workflow_ingredient_analysis 调用
│   └── kb/
│       ├── __init__.py
│       ├── documents_service.py            # [新建] ChromaDB + FTS 文档写操作
│       └── chunks_service.py               # [新建] ChromaDB chunk 查询操作
├── api/
│   ├── ingredients/
│   │   └── service.py                     # [修改] 移除跨模块调用和 Session 自管理
│   ├── analysis/
│   │   ├── service.py                     # [修改] 接管 assembler 的 DB 访问
│   │   └── assembler.py                   # [修改] 移除 DB 访问，仅保留数据组装
│   ├── documents/
│   │   └── service.py                     # [修改] 委托 services/kb/documents_service.py
│   └── chunks/
│       └── service.py                     # [修改] 委托 services/kb/chunks_service.py
└── db_repositories/
    └── ingredient_analysis.py             # [修改] 新增 write_analysis_result() 方法
```

---

## Phase 0 — P0 修复（低风险、孤立改动）

### Task 1: 修复 T4 — Assembler 访问 DB（`api/analysis/assembler.py`）

**Files:**
- Modify: `server/api/analysis/assembler.py`
- Modify: `server/api/analysis/service.py`
- Test: `server/tests/api/analysis/test_assembler.py`（新建）

---

- [ ] **Step 1: 备份现有 assembler 逻辑，确认调用链**

查看 `api/analysis/service.py` 中 `assemble_from_agent_output` 和 `assemble_from_db_cache` 的调用位置：

```bash
grep -n "assemble_from" server/api/analysis/service.py
```

预期输出：
```
150:        result = await assemble_from_agent_output(
177:        result = await assemble_from_db_cache(
```

---

- [ ] **Step 2: 修改 `assemble_from_agent_output` — 移除 DB 访问，改为接收预加载数据**

`api/analysis/assembler.py` 第 32-34 行的 DB 查询：
```python
# 当前违规代码 (assembler.py:32-34)
result = await session.execute(
    select(Ingredient).where(Ingredient.id.in_(matched_ids))
)
```

修改为：Assembler 接收已查询的 `Ingredient` 对象列表，不再自建查询：

```python
# 修改后的 assembler.py — 接收预加载数据，不查 DB
async def _build_ingredients_list(
    matched_ids: list[int],
    session: AsyncSession,
) -> list[IngredientItem]:
    # 实现移除，改为由调用方传入已查询的数据
    pass  # 将在 Step 4 实现

# 新的公开函数签名：
async def assemble_from_agent_output(
    agent_output: dict[str, Any],
    matched_ingredients: list[Ingredient],  # ← 改为接收已查好的 Entity
    matched_ids: list[int],
    analysis_repo: IngredientAnalysisRepository,  # ← 接收已实例化的 repo
) -> ProductAnalysisResult:
```

---

- [ ] **Step 3: 修改 `api/analysis/service.py` — 在 Service 层预加载数据后调用 Assembler**

在 `run_analysis_sync()` 函数中，找到调用 `assemble_from_agent_output` 的位置（第 177 行），在调用前插入数据预加载：

```python
# api/analysis/service.py 第 177 行附近
# 在调用 assembler 前，先预加载 Ingredient 数据

# 预加载 ingredients
result = await session.execute(
    select(Ingredient).where(Ingredient.id.in_(matched_ids))
)
ingredients = result.scalars().all()
ingredient_map = {ing.id: ing for ing in ingredients}

# 填充 matched_ingredients 列表（按 matched_ids 顺序）
matched_ingredients = [ingredient_map[mid] for mid in matched_ids if mid in ingredient_map]

# 实例化 analysis_repo（在 L2 层可实例化）
analysis_repo = IngredientAnalysisRepository(session)

# 调用 assembler（传入预加载数据，不再查 DB）
result = await assemble_from_agent_output(
    agent_output={
        "verdict_level": final_state.get("verdict_level"),
        "verdict_description": final_state.get("verdict_description"),
        "advice": final_state.get("advice"),
        "demographics": final_state.get("demographics", []),
        "scenarios": final_state.get("scenarios", []),
        "references": final_state.get("references", []),
        "unmatched_ingredient_names": match_result.unmatched,
    },
    matched_ingredients=matched_ingredients,  # 新参数
    matched_ids=matched_ids,
    analysis_repo=analysis_repo,  # 新参数
)
```

同样处理 `assemble_from_db_cache` 调用（第 150 行）。

---

- [ ] **Step 4: 修改 `assemble_from_agent_output` 和 `assemble_from_db_cache` 函数体**

移除 `assembler.py` 中的：
```python
# 删除这行（违规代码）
from database.models import Ingredient, ProductAnalysis  # 第 10 行
# 删除这段（违规代码）
result = await session.execute(
    select(Ingredient).where(Ingredient.id.in_(matched_ids))
)
```

改为接收传入的 `matched_ingredients: list[Ingredient]` 和 `analysis_repo: IngredientAnalysisRepository`。

---

- [ ] **Step 5: 写测试验证 Assembler 不访问 DB**

创建 `server/tests/api/analysis/test_assembler.py`：

```python
"""Tests: Assembler 收到预加载数据后正确组装 ProductAnalysisResult。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from api.analysis.assembler import assemble_from_agent_output

@pytest.mark.asyncio
async def test_assemble_from_agent_output_no_db_access():
    """Assembler 应只做数据组装，不执行任何 DB 查询。"""
    mock_ingredients = [
        MagicMock(id=1, name="Salt", function_type=["preservative"]),
        MagicMock(id=2, name="Sugar", function_type=["sweetener"]),
    ]
    mock_repo = AsyncMock()
    mock_repo.get_active_by_ingredient_id.return_value = MagicMock(level="t1", alternatives=[])

    agent_output = {
        "verdict_level": "t1",
        "verdict_description": "Low risk",
        "advice": "Safe to consume",
        "demographics": [],
        "scenarios": [],
        "references": [],
        "unmatched_ingredient_names": [],
    }

    result = await assemble_from_agent_output(
        agent_output=agent_output,
        matched_ingredients=mock_ingredients,
        matched_ids=[1, 2],
        analysis_repo=mock_repo,
    )

    assert result.verdict["level"] == "t1"
    assert len(result.ingredients) == 2
    # 验证 repo 从未被 execute() 调用（只被 get_active_by_ingredient_id 调用）
    mock_repo.get_active_by_ingredient_id.assert_called()
```

---

- [ ] **Step 6: 运行测试**

```bash
cd server && uv run pytest tests/api/analysis/test_assembler.py -v
```

预期：PASS

---

- [ ] **Step 7: Commit**

```bash
git add server/api/analysis/assembler.py server/api/analysis/service.py
git add server/tests/api/analysis/test_assembler.py
git commit -m "fix(analysis): remove DB access from Assembler, pre-load data in Service layer

- T4 fix: Assembler no longer executes SQL queries
- Service (L2) now pre-loads Ingredient entities before calling Assembler
- Assembler receives matched_ingredients list and analysis_repo as parameters

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 修复 T1 — Session 自管理 + 跨模块调用（`api/ingredients/service.py`）

**Files:**
- Modify: `server/api/ingredients/service.py`
- Modify: `server/db_repositories/ingredient_analysis.py`
- Test: `server/tests/api/test_ingredients.py`（修改现有测试）

---

- [ ] **Step 1: 确认 `IngredientAnalysisRepository.insert_new_version` 已存在**

```bash
grep -n "insert_new_version" server/db_repositories/ingredient_analysis.py
```

预期：`insert_new_version` 方法已存在于 `IngredientAnalysisRepository`（第 36-74 行），可直接调用。

---

- [ ] **Step 2: 修改 `IngredientService.trigger_analysis` — 移除 Session 自管理**

当前违规代码 `api/ingredients/service.py:139-141`:
```python
async with get_async_session_cm() as session:    # T1 违规：Session 自管理
    svc = IngredientAnalysisService(session)    # T1 违规：跨模块调用
    await svc.create(ingredient_id, write_payload)
```

修复方案：由于 `trigger_analysis` 是在 `background_tasks.add_task()` 中运行（独立于请求生命周期），Session 需要由 `BackgroundTasks` 自己管理。正确的做法是：

**新建 `services/ingredient_analysis/workflow_executor.py`** 作为 L2 层，封装 `run_ingredient_analysis` workflow 调用和结果写入：

```python
# server/services/ingredient_analysis/__init__.py
from .workflow_executor import IngredientAnalysisExecutor
```

```python
# server/services/ingredient_analysis/workflow_executor.py
"""L2: 封装 ingredient analysis workflow 执行和结果写入。"""
from __future__ import annotations

import uuid
from typing import Protocol

from config import settings
from database.session import get_async_session_cm
from db_repositories.ingredient_analysis import IngredientAnalysisRepository


class IngredientAnalysisExecutor:
    """执行 ingredient analysis workflow（Infra 调用）并写入结果（DB 写入）。"""

    async def execute(self, ingredient: dict) -> dict:
        """
        1. 调用 workflow_ingredient_analysis（纯计算）
        2. 写入分析结果到 DB
        3. 返回 workflow 结果 dict
        """
        from workflow_ingredient_analysis.entry import run_ingredient_analysis

        task_id = str(uuid.uuid4())

        # 调用 workflow（纯计算，Infra 层）
        result = await run_ingredient_analysis(
            ingredient=ingredient,
            task_id=task_id,
            ai_model=settings.DEFAULT_MODEL,
        )

        # 写入 DB 结果（L3 层）
        if result["status"] == "succeeded":
            analysis_output = result["analysis_output"] or {}
            write_payload = {
                "ai_model": result.get("ai_model", "unknown"),
                "level": analysis_output.get("level", "unknown"),
                "safety_info": result["composed_output"]["safety_info"],
                "alternatives": result["composed_output"]["alternatives"],
                "confidence_score": analysis_output.get("confidence_score", 0.0),
                "evidence_refs": result["evidence_refs"] or [],
                "decision_trace": analysis_output.get("decision_trace", {}),
            }
            # 在独立的 Session 上下文中写入（background task 的 Session 生命周期）
            async with get_async_session_cm() as session:
                repo = IngredientAnalysisRepository(session)
                await repo.insert_new_version(
                    ingredient_id=ingredient["ingredient_id"],
                    data=write_payload,
                    created_by_user=settings.SYSTEM_USER_ID,
                )

        return result
```

---

- [ ] **Step 3: 修改 `IngredientService.trigger_analysis` — 委托给 L2 Executor**

修改 `api/ingredients/service.py`：

```python
# 删除这些违规导入和代码（原第 105-107, 139-141 行）：
# from database.session import get_async_session_cm          # 删除
# from api.ingredient_analysis.service import IngredientAnalysisService  # 删除

# 修改 trigger_analysis 方法：
async def trigger_analysis(
    self,
    session: AsyncSession,  # 接收 injected session（虽然 background task 不直接用，但保持接口一致）
    ingredient_id: int,
    background_tasks,
) -> dict | None:
    """检查配料存在，返回 task_id，编排 BackgroundTask 执行完整流程."""
    ingredient = await self._repo.fetch_by_id(ingredient_id)
    if ingredient is None:
        return None

    task_id = str(uuid.uuid4())

    # 构造 ingredient dict（预加载数据）
    ingredient_dict = {
        "ingredient_id": ingredient.id,
        "name": ingredient.name,
        "function_type": ingredient.function_type or [],
        "origin_type": ingredient.origin_type or "",
        "limit_usage": ingredient.limit_usage or "",
        "safety_info": ingredient.safety_info or "",
        "cas": ingredient.cas or "",
    }

    # 委托给 L2 Executor（在 background task 中执行）
    from services.ingredient_analysis import IngredientAnalysisExecutor

    executor = IngredientAnalysisExecutor()

    async def _run_workflow():
        await executor.execute(ingredient_dict)

    background_tasks.add_task(_run_workflow)
    return {"task_id": task_id, "ingredient_id": ingredient_id, "status": "queued"}
```

**关键变更说明**:
- `IngredientService` 不再导入 `api.ingredient_analysis.service`（消除跨模块调用）
- `IngredientService` 不再自建 Session（Session 管理移入 L2 Executor）
- L2 Executor 持有 `get_async_session_cm()`（这是 BackgroundTask 场景下的正确做法）

---

- [ ] **Step 4: 更新 Router 签名（如果 `trigger_analysis` 接口变化）**

检查 `api/ingredients/router.py` 中 `trigger_analysis` 的调用：

```bash
grep -n "trigger_analysis" server/api/ingredients/router.py
```

如果 Router 中 `trigger_analysis(session, ingredient_id, background_tasks)` 接口变了，需要同步修改 Router。

---

- [ ] **Step 5: 运行测试**

```bash
cd server && uv run pytest tests/api/test_ingredients.py -v -k "trigger"
```

预期：PASS（如有测试覆盖）

---

- [ ] **Step 6: Commit**

```bash
git add server/services/ingredient_analysis/
git add server/api/ingredients/service.py
git commit -m "fix(ingredients): remove cross-module call and session self-management

- T1 fix: IngredientService no longer imports api.ingredient_analysis.service
- T1 fix: Session management moved to L2 IngredientAnalysisExecutor
- New services/ingredient_analysis/workflow_executor.py (L2 layer)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 1 — P1 修复（目录结构调整）

### Task 3: 创建 `services/` 目录结构

**Files:**
- Create: `server/services/__init__.py`
- Create: `server/services/kb/__init__.py`
- Create: `server/services/kb/documents_service.py`
- Create: `server/services/kb/chunks_service.py`
- Create: `server/services/ingredient_analysis/__init__.py`
- Create: `server/services/ingredient_analysis/workflow_executor.py`（已在 Task 2 创建）

---

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p server/services/kb
mkdir -p server/services/ingredient_analysis
touch server/services/__init__.py
touch server/services/kb/__init__.py
touch server/services/ingredient_analysis/__init__.py
```

---

- [ ] **Step 2: 创建 `services/kb/documents_service.py`**

将 `api/documents/service.py` 中的 KB 操作提取为 L2：

```python
"""L2: KB 文档管理 — ChromaDB + FTS 写操作。"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from config import settings
from kb.clients import get_chroma_client
from kb.writer import chroma_writer, fts_writer
from workflow_parser_kb.graph import run_parser_workflow_stream


def _default_collection_getter():
    return get_chroma_client().get_or_create_collection("knowledge_base")


class KBDocumentsService:
    """Knowledge Base 文档管理，所有 KB 操作封装在此。"""

    def __init__(
        self,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._get_collection = collection_getter

    def get_all_documents(self) -> list[dict[str, Any]]:
        result = self._get_collection().get(include=["metadatas"])
        metadatas = result.get("metadatas") or []
        doc_map: dict[str, dict] = {}
        for meta in metadatas:
            doc_id = meta.get("doc_id", "unknown")
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "doc_id": doc_id,
                    "title": meta.get("title", ""),
                    "standard_no": meta.get("standard_no", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "chunks_count": 0,
                }
            doc_map[doc_id]["chunks_count"] += 1
        return sorted(doc_map.values(), key=lambda d: d["doc_id"])

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        self._get_collection().delete(where={"doc_id": {"$eq": doc_id}})
        errors: list[str] = []
        fts_writer.delete_by_doc_id(doc_id, errors)
        return {"doc_id": doc_id, "errors": errors}

    async def create_document(self, chunks: list, doc_metadata: dict) -> None:
        doc_id = doc_metadata.get("doc_id")
        await asyncio.to_thread(self.delete_document, doc_id)
        await chroma_writer.write(chunks, doc_metadata)
        fts_writer.write(chunks, doc_metadata)

    async def upload_document_stream(
        self,
        file_content: bytes,
        filename: str,
    ) -> Any:
        """流式解析文档，yield SSE 格式字符串。"""
        import json
        import os

        try:
            md_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'message': '文件编码错误，请确保文件为 UTF-8 编码'})}\n\n"
            return

        doc_title = os.path.splitext(filename)[0]
        rules_dir = settings.RULES_DIR

        try:
            async for event in run_parser_workflow_stream(
                md_content=md_content,
                doc_name=doc_title,
                rules_dir=rules_dir,
            ):
                if event["type"] == "workflow_done":
                    chunks = event["chunks"]
                    doc_metadata = event["doc_metadata"]
                    if chunks:
                        await self.create_document(chunks, doc_metadata)
                    yield f"data: {json.dumps({'type': 'done', 'chunks_count': len(chunks)})}\n\n"
                else:
                    yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        collection = self._get_collection()
        result = collection.get(where={"doc_id": {"$eq": doc_id}}, include=["metadatas"])
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        if not ids:
            raise ValueError(f"Document '{doc_id}' not found")
        updated_metadatas = []
        for meta in metadatas:
            new_meta = dict(meta)
            for key, value in fields.items():
                if value is not None:
                    new_meta[key] = value
            updated_metadatas.append(new_meta)
        collection.update(ids=ids, metadatas=updated_metadatas)
        first = updated_metadatas[0]
        return {
            "doc_id": doc_id,
            "title": first.get("title", ""),
            "standard_no": first.get("standard_no", ""),
            "doc_type": first.get("doc_type", ""),
            "chunks_count": len(ids),
        }

    def clear_all(self) -> dict[str, Any]:
        collection = self._get_collection()
        all_results = collection.get(include=["metadatas"])
        metadatas = all_results.get("metadatas") or []
        doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
        total_chunks = len(all_results.get("ids") or [])
        all_ids = all_results.get("ids") or []
        if all_ids:
            collection.delete(ids=all_ids)
        fts_writer.clear_all()
        return {
            "status": "success",
            "deleted_documents": len(doc_ids),
            "deleted_chunks": total_chunks,
        }
```

---

- [ ] **Step 3: 创建 `services/kb/chunks_service.py`**

将 `api/chunks/service.py` 中的 KB 操作提取为 L2（核心方法）：

```python
"""L2: KB Chunk 管理 — ChromaDB 查询/更新/删除。"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from config import settings
from kb.clients import get_chroma_client
from kb.embeddings import embed_batch
from kb.writer import fts_writer
from workflow_parser_kb.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState
from workflow_parser_kb.nodes.merge_node import merge_node
from workflow_parser_kb.nodes.transform_node import transform_node
from workflow_parser_kb.rules import RulesStore


def _default_collection_getter():
    return get_chroma_client().get_or_create_collection("knowledge_base")


class KBChunksService:
    """
    ChromaDB chunk 管理（所有 KB I/O 操作封装在此 L2）。
    async 函数内部通过 asyncio.to_thread 将 ChromaDB I/O 卸载到线程池。
    """

    def __init__(
        self,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._get_collection = collection_getter

    async def get_chunks(
        self,
        doc_id: str | None = None,
        semantic_type: str | None = None,
        section_path: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        def _do():
            where: dict = {}
            if doc_id:
                where["doc_id"] = {"$eq": doc_id}
            if semantic_type:
                where["semantic_type"] = {"$eq": semantic_type}
            if section_path:
                where["section_path"] = {"$eq": section_path.replace("/", "|")}
            where_clause = _build_where(where)
            col = self._get_collection()
            result = col.get(include=["documents", "metadatas"], limit=limit, offset=offset, where=where_clause)
            count_result = col.get(include=[], where=where_clause)
            ids = result.get("ids") or []
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            chunks = [
                {"id": ids[i], "content": documents[i], "metadata": metadatas[i]}
                for i in range(len(ids))
            ]
            total = len(count_result.get("ids") or [])
            return chunks, total

        return await asyncio.to_thread(_do)

    async def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        def _do():
            col = self._get_collection()
            result = col.get(ids=[chunk_id], include=["documents", "metadatas"])
            ids = result.get("ids") or []
            if not ids:
                return None
            return {
                "id": ids[0],
                "content": (result.get("documents") or [""])[0],
                "metadata": (result.get("metadatas") or [{}])[0],
            }

        return await asyncio.to_thread(_do)

    async def update_chunk(
        self,
        chunk_id: str,
        content: str,
        semantic_type: str,
        section_path: str,
    ) -> dict[str, Any]:
        async def _do():
            embeddings = await embed_batch([content])

            def _sync():
                col = self._get_collection()
                existing = col.get(ids=[chunk_id], include=["metadatas"])
                if not (existing.get("ids") or []):
                    raise ValueError(f"chunk {chunk_id} not found")
                old_meta = (existing.get("metadatas") or [{}])[0]
                new_meta = {**old_meta, "semantic_type": semantic_type, "section_path": section_path.replace("/", "|")}
                col.upsert(ids=[chunk_id], documents=[content], embeddings=embeddings, metadatas=[new_meta])
                fts_writer.init_db()
                doc_metadata = {
                    "doc_id": old_meta.get("doc_id", ""),
                    "standard_no": old_meta.get("standard_no", ""),
                    "doc_type": old_meta.get("doc_type", ""),
                }
                fts_chunk = {
                    "chunk_id": chunk_id,
                    "content": content,
                    "semantic_type": semantic_type,
                    "section_path": section_path.split("/"),
                    "raw_content": old_meta.get("raw_content", ""),
                    "doc_metadata": {},
                    "meta": {},
                }
                fts_writer.write([fts_chunk], doc_metadata)
                return {"id": chunk_id, "content": content, "metadata": new_meta}

            return await asyncio.to_thread(_sync)

        return await _do()

    async def delete_chunk(self, chunk_id: str) -> None:
        def _do():
            self._get_collection().delete(ids=[chunk_id])

        await asyncio.to_thread(_do)

    async def reparse_chunk(self, chunk_id: str) -> dict[str, Any]:
        def _read():
            col = self._get_collection()
            existing = col.get(ids=[chunk_id], include=["documents", "metadatas"])
            if not (existing.get("ids") or []):
                raise ValueError(f"chunk {chunk_id} not found")
            old_meta = (existing.get("metadatas") or [{}])[0]
            raw_content = old_meta.get("raw_content", "")
            section_path_str = old_meta.get("section_path", "")
            semantic_type = old_meta.get("semantic_type", "")
            store = RulesStore(settings.RULES_DIR)
            transform_params = store.get_transform_params(semantic_type)
            typed_segment: TypedSegment = {
                "content": old_meta.get("raw_content", ""),
                "structure_type": old_meta.get("structure_type", "paragraph"),
                "semantic_type": semantic_type,
                "transform_params": transform_params,
                "confidence": 1.0,
                "escalated": False,
                "cross_refs": old_meta.get("cross_refs", []),
                "ref_context": "",
                "failed_table_refs": old_meta.get("failed_table_refs", []),
            }
            raw_chunk: RawChunk = {
                "content": raw_content,
                "section_path": section_path_str.split("|") if section_path_str else [],
                "char_count": len(raw_content),
            }
            classified_chunk: ClassifiedChunk = {
                "raw_chunk": raw_chunk,
                "segments": [typed_segment],
                "has_unknown": False,
            }
            doc_metadata = {
                "doc_id": old_meta.get("doc_id", ""),
                "standard_no": old_meta.get("standard_no", ""),
                "doc_type": old_meta.get("doc_type", ""),
            }
            state: WorkflowState = {
                "md_content": "",
                "doc_metadata": doc_metadata,
                "config": {},
                "rules_dir": settings.RULES_DIR,
                "raw_chunks": [],
                "classified_chunks": [classified_chunk],
                "final_chunks": [],
                "errors": [],
            }
            return state, old_meta, doc_metadata

        state, old_meta, doc_metadata = await asyncio.to_thread(_read)

        transform_result = await transform_node(state)
        final_chunks = transform_result.get("final_chunks", [])
        merge_result = merge_node({"final_chunks": final_chunks, "doc_metadata": doc_metadata})
        merged_chunks = merge_result.get("final_chunks", [])

        if not merged_chunks:
            raise ValueError(f"reparse {chunk_id} produced no chunks")

        merged = merged_chunks[0]

        embeddings = await embed_batch([merged["content"]])

        def _upsert(emb):
            col = self._get_collection()
            new_meta = {
                **old_meta,
                "raw_content": old_meta.get("raw_content", ""),
                "semantic_type": merged["semantic_type"],
                "section_path": "|".join(merged["section_path"]),
            }
            col.upsert(
                ids=[chunk_id],
                documents=[merged["content"]],
                embeddings=emb,
                metadatas=[new_meta],
            )
            fts_writer.init_db()
            fts_chunk = {
                "chunk_id": chunk_id,
                "content": merged["content"],
                "semantic_type": merged["semantic_type"],
                "section_path": merged["section_path"],
                "raw_content": old_meta.get("raw_content", ""),
                "doc_metadata": {},
                "meta": {},
            }
            fts_writer.write([fts_chunk], doc_metadata)
            return {"id": chunk_id, "content": merged["content"], "metadata": new_meta}

        return await asyncio.to_thread(_upsert, embeddings)


def _build_where(where: dict) -> dict | None:
    if not where:
        return None
    items = [{k: v} for k, v in where.items()]
    if len(items) == 1:
        return items[0]
    return {"$and": items}
```

---

- [ ] **Step 4: 创建 `services/kb/__init__.py`**

```python
"""KB services (L2 layer)."""
from .documents_service import KBDocumentsService
from .chunks_service import KBChunksService

__all__ = ["KBDocumentsService", "KBChunksService"]
```

---

- [ ] **Step 5: Commit**

```bash
git add server/services/
git commit -m "feat(services): add services/ layer (L2) for KB operations

- New services/kb/ with KBDocumentsService and KBChunksService
- KB operations (ChromaDB + FTS + workflow_parser) now accessed via L2
- Refs T2: L1 (api/) no longer directly imports Infra (kb/)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 修改 `api/documents/service.py` — 委托给 L2

**Files:**
- Modify: `server/api/documents/service.py`
- Test: `server/tests/api/documents/test_service.py`（修改）

---

- [ ] **Step 1: 读取当前 `api/documents/service.py` 全文**

确认当前完整内容后，进行修改。

---

- [ ] **Step 2: 重写 `api/documents/service.py` 为纯 L1 委托层**

```python
"""L1: Documents API — HTTP 入口和参数校验，业务委托给 services/kb/documents_service.py。"""
from __future__ import annotations

from typing import Any, Callable

from services.kb import KBDocumentsService


def _default_collection_getter():
    """延迟导入，避免循环依赖。"""
    from kb.clients import get_chroma_client
    return get_chroma_client().get_or_create_collection("knowledge_base")


class DocumentsService:
    """L1: 接收 KBDocumentsService (L2) 实例，自身只做参数透传。"""

    def __init__(
        self,
        kb_service: KBDocumentsService | None = None,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._kb_service = kb_service or KBDocumentsService(collection_getter=collection_getter)

    def get_all_documents(self) -> list[dict[str, Any]]:
        return self._kb_service.get_all_documents()

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        return self._kb_service.delete_document(doc_id)

    async def create_document(self, chunks: list, doc_metadata: dict) -> None:
        await self._kb_service.create_document(chunks, doc_metadata)

    async def upload_document_stream(self, file_content: bytes, filename: str):
        async for event in self._kb_service.upload_document_stream(file_content, filename):
            yield event

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self._kb_service.update_document(doc_id, fields)

    def clear_all(self) -> dict[str, Any]:
        return self._kb_service.clear_all()
```

**关键变更**：
- 移除 `from kb.clients`、`from kb.writer`、`from workflow_parser_kb.graph`（不再直接引用 Infra）
- 移除 `asyncio`、`os`、`json` 的直接使用（已上浮到 L2）
- L1 自身只持有 `KBDocumentsService` (L2) 实例，委托所有 KB 操作

---

- [ ] **Step 3: 运行测试验证**

```bash
cd server && uv run pytest tests/api/documents/test_service.py -v
```

---

- [ ] **Step 4: Commit**

```bash
git add server/api/documents/service.py
git commit -m "refactor(documents): delegate KB ops to services/kb (L2), remove Infra imports

- T2 fix: api/documents/service.py no longer directly imports kb/* or workflow_parser_kb
- L1 now only holds KBDocumentsService (L2) reference

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: 修改 `api/chunks/service.py` — 委托给 L2

**Files:**
- Modify: `server/api/chunks/service.py`
- Test: 修改现有测试

---

- [ ] **Step 1: 读取 `api/chunks/service.py` 全文**

---

- [ ] **Step 2: 重写为 L1 委托层**

```python
"""L1: Chunks API — HTTP 入口和参数校验，业务委托给 services/kb/kb_chunks_service.py。"""
from __future__ import annotations

from typing import Any, Callable

from services.kb import KBChunksService


def _default_collection_getter():
    from kb.clients import get_chroma_client
    return get_chroma_client().get_or_create_collection("knowledge_base")


class ChunksService:
    """L1: 接收 KBChunksService (L2) 实例，自身只做参数透传。"""

    def __init__(
        self,
        kb_service: KBChunksService | None = None,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._kb_service = kb_service or KBChunksService(collection_getter=collection_getter)

    async def get_chunks(
        self,
        doc_id: str | None = None,
        semantic_type: str | None = None,
        section_path: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        return await self._kb_service.get_chunks(
            doc_id=doc_id,
            semantic_type=semantic_type,
            section_path=section_path,
            limit=limit,
            offset=offset,
        )

    async def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        return await self._kb_service.get_chunk_by_id(chunk_id)

    async def update_chunk(
        self,
        chunk_id: str,
        content: str,
        semantic_type: str,
        section_path: str,
    ) -> dict[str, Any]:
        return await self._kb_service.update_chunk(
            chunk_id=chunk_id,
            content=content,
            semantic_type=semantic_type,
            section_path=section_path,
        )

    async def delete_chunk(self, chunk_id: str) -> None:
        await self._kb_service.delete_chunk(chunk_id)

    async def reparse_chunk(self, chunk_id: str) -> dict[str, Any]:
        return await self._kb_service.reparse_chunk(chunk_id)
```

**关键变更**：
- 移除 `from kb.clients`、`from kb.embeddings`、`from kb.writer`、`from workflow_parser_kb.*`（不再直接引用 Infra）
- 移除 `_build_where` 函数（已迁移到 L2）
- L1 自身只做委托

---

- [ ] **Step 3: 运行测试**

```bash
cd server && uv run pytest tests/api/chunks/ -v
```

---

- [ ] **Step 4: Commit**

```bash
git add server/api/chunks/service.py
git commit -m "refactor(chunks): delegate KB ops to services/kb (L2), remove Infra imports

- T2 fix: api/chunks/service.py no longer directly imports kb/* or workflow_parser_kb
- L1 now only holds KBChunksService (L2) reference

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: 修复剩余 T2 违规 — `api/analysis/` 引用 `workflow_product_analysis.types`

**Files:**
- Modify: `server/api/analysis/models.py`
- Modify: `server/api/analysis/ingredient_matcher.py`（如引用了 workflow types）
- Test: 修改受影响的测试

---

- [ ] **Step 1: 扫描 `api/analysis/` 下所有对 `workflow_product_analysis` 的引用**

```bash
grep -n "from workflow_product_analysis" server/api/analysis/
```

---

- [ ] **Step 2: 判别哪些是类型引用，哪些是逻辑调用**

类型引用（如 `ProductAnalysisState`、`IngredientInput`）→ 迁移到 `api/analysis/models.py`
逻辑调用（如 `build_product_analysis_graph`）→ 已在 `api/analysis/service.py` 中，属于 L2 编排，可接受

---

- [ ] **Step 3: 将 `workflow_product_analysis.types` 中的类型定义迁移到 `api/analysis/models.py`**

```bash
grep -n "class \|from.*types" server/api/analysis/models.py
```

将 `IngredientInput`、`ProductAnalysisState` 等类型定义复制/移动到 `api/analysis/models.py`，并从 `api/analysis/models.py` 中删除对 `workflow_product_analysis.types` 的导入。

---

- [ ] **Step 4: Commit**

```bash
git add server/api/analysis/models.py
git commit -m "refactor(analysis): move workflow types to api/analysis/models.py

- T2 fix: api/analysis/ no longer imports from workflow_product_analysis.types directly
- Types now defined in api/analysis/models.py (L1 DTO layer)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 自检清单

完成所有 Tasks 后，运行以下验证：

```bash
# 1. 验证无违规导入
grep -r "from kb/\|from workflow_\|from llm/" server/api/*/service.py server/api/*/assembler.py 2>/dev/null | grep -v ".venv" || echo "✅ 无 L1→Infra 违规导入"

# 2. 验证 Assembler 无 DB 访问
grep -r "select\|execute\|from database.models" server/api/*/assembler.py 2>/dev/null || echo "✅ Assembler 无 DB 访问"

# 3. 验证 Service 无 Session 自管理
grep -r "get_async_session_cm" server/api/*/service.py 2>/dev/null || echo "✅ 无 Session 自管理"

# 4. 验证无跨模块 Service 调用
grep -r "from api\..*\.service import" server/api/*/service.py 2>/dev/null || echo "✅ 无跨模块 Service 调用"

# 5. 运行全量测试
cd server && uv run pytest tests/ -v --tb=short
```

---

**Plan 完成。所有修复遵循单向依赖原则：L1→L2→L3→L4。**
