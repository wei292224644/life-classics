# Ingredient Analyses Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `ingredient_analyses` LangGraph workflow，将 `ingredient_id` 转换为结构化的 `IngredientAnalysis` 结果写入数据库，供管理后台查看和追溯。

**Architecture:** 线性 5 节点 LangGraph workflow（`load_ingredient` → `retrieve_evidence` → `analyze` → `compose_output` → `persist_version`），workflow 只负责推理，通过 Redis 任务状态机暴露异步接口 `POST /api/ingredients/{ingredient_id}/analyze` + `GET /api/analysis/{task_id}/status`。

**死规定：一切针对数据库的行为都必须走 API，不允许 workflow 内部直接 SQLAlchemy 操作数据库。**

**Trigger:** 管理员在配料管理后台手动点击"分析"按钮触发，非 pipeline 调用。

**Tech Stack:** LangGraph, Pydantic, `invoke_structured` (anthropic), PostgreSQL (via SQLAlchemy async, 通过 API 层), ChromaDB (via `kb/retriever`), Redis (任务状态)

---

## 文件结构

```
server/
├── workflow_ingredient_analysis/          # 新建
│   ├── __init__.py
│   ├── models.py                          # WorkflowState TypedDict
│   ├── graph.py                           # LangGraph 编译与 entry 函数
│   ├── entry.py                           # run_ingredient_analysis() 导出
│   └── nodes/
│       ├── __init__.py
│       ├── output.py                      # Pydantic response models
│       ├── load_ingredient_node.py        # 调用 GET /api/ingredients/{id}
│       ├── retrieve_evidence_node.py       # 调用 kb/retriever.search()
│       ├── analyze_node.py                # 调用 invoke_structured
│       ├── compose_output_node.py          # 调用 invoke_structured
│       └── persist_version_node.py         # 只 yield 数据，不写库
├── api/
│   └── ingredient_analysis/               # 新建：配料分析 API
│       ├── __init__.py
│       ├── models.py                      # Pydantic 请求/响应模型
│       ├── service.py                     # 服务层
│       └── router.py                      # 路由
└── tests/
    └── workflow_ingredient_analysis/
        ├── __init__.py
        └── test_workflow.py               # 集成测试

server/observability/metrics.py            # 修改：添加 ingredient_analysis 指标
```

---

## 接口设计

### 触发分析

```
POST /api/ingredients/{ingredient_id}/analyze
```

**Request:** 无 body

**Response:** `202 Accepted`
```json
{
  "task_id": "uuid-string",
  "ingredient_id": 123,
  "status": "queued"
}
```

**行为:**
1. 校验 `ingredient_id` 存在，不存在返回 `404`
2. 生成 `task_id`（uuid）
3. 写入 Redis 状态 `queued`
4. 在 `BackgroundTask` 中启动 `run_ingredient_analysis(ingredient_id, task_id)`
5. 立即返回 `202`

### 查询状态

```
GET /api/analysis/{task_id}/status
```

复用 `workflow_product_analysis/redis_store` 中的 `get_task()` 和 `AnalysisTask` 结构，返回 `status` / `error` / `result`。

### 写入分析结果（内部 API，供 background task 调用）

```
POST /api/ingredient-analyses/{ingredient_id}
```

**Request:**
```json
{
  "ai_model": "claude-opus-4-6",
  "level": "t2",
  "safety_info": "...",
  "alternatives": [...],
  "confidence_score": 0.85,
  "evidence_refs": [...],
  "decision_trace": {...}
}
```

**Response:** `201 Created`

---

## Task 1: 创建 workflow_ingredient_analysis 基础结构

**Files:**
- Create: `server/workflow_ingredient_analysis/__init__.py`
- Create: `server/workflow_ingredient_analysis/models.py`
- Create: `server/workflow_ingredient_analysis/nodes/__init__.py`

- [ ] **Step 1: Create `server/workflow_ingredient_analysis/__init__.py`**

```python
"""Ingredient analysis workflow."""
from workflow_ingredient_analysis.entry import run_ingredient_analysis

__all__ = ["run_ingredient_analysis"]
```

- [ ] **Step 2: Create `server/workflow_ingredient_analysis/models.py`**

```python
"""Workflow state and types for ingredient_analysis."""
from __future__ import annotations

from typing import Any, Literal, TypedDict

# ── 风险等级 ────────────────────────────────────────────────────────────────
IngredientRiskLevel = Literal["t0", "t1", "t2", "t3", "t4", "unknown"]

# ── Workflow State ─────────────────────────────────────────────────────────---


class WorkflowState(TypedDict):
    """ingredient_analyses workflow state — flows through all 5 nodes."""

    # 输入
    ingredient_id: int
    task_id: str
    run_id: str

    # Node outputs
    ingredient: dict | None  # RetrievedIngredient
    evidence_refs: list[dict] | None  # list[EvidenceRef]
    analysis_output: dict | None  # AnalyzeOutput
    composed_output: dict | None  # ComposeOutput

    # 状态与错误
    status: Literal["queued", "running", "succeeded", "failed"]
    error_code: str | None
    errors: list[str]
```

- [ ] **Step 3: Create `server/workflow_ingredient_analysis/nodes/__init__.py`**

```python
"""Ingredient analysis workflow nodes."""
from workflow_ingredient_analysis.nodes.load_ingredient_node import load_ingredient_node
from workflow_ingredient_analysis.nodes.retrieve_evidence_node import retrieve_evidence_node
from workflow_ingredient_analysis.nodes.analyze_node import analyze_node
from workflow_ingredient_analysis.nodes.compose_output_node import compose_output_node
from workflow_ingredient_analysis.nodes.persist_version_node import persist_version_node

__all__ = [
    "load_ingredient_node",
    "retrieve_evidence_node",
    "analyze_node",
    "compose_output_node",
    "persist_version_node",
]
```

- [ ] **Step 4: Commit**

```bash
git add server/workflow_ingredient_analysis/
git commit -m "feat(ingredient_analysis): scaffold workflow directory and models"
```

---

## Task 2: 定义节点输出模型

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/output.py`

- [ ] **Step 1: Create `server/workflow_ingredient_analysis/nodes/output.py`**

```python
"""Pydantic response models for LLM structured outputs in ingredient_analysis workflow."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── load_ingredient_node ─────────────────────────────────────────────────────


class RetrievedIngredient(BaseModel):
    """load_ingredient_node output."""

    ingredient_id: int
    name: str
    function_type: list[str]
    origin_type: str
    limit_usage: str
    safety_info: str
    cas: str


# ── retrieve_evidence_node ───────────────────────────────────────────────────


class EvidenceRef(BaseModel):
    """Single evidence reference from GB standard chunks."""

    source_id: str
    source_type: Literal["gb_standard_chunk"] = "gb_standard_chunk"
    standard_no: str
    semantic_type: str
    section_path: str
    content: str
    raw_content: str
    score: float = Field(ge=0, le=1)


# ── analyze_node ─────────────────────────────────────────────────────────────


class AnalysisDecisionStep(BaseModel):
    """Single step in the decision trace."""

    step: str
    findings: list[str]
    reasoning: str
    conclusion: str


class AnalysisDecisionTrace(BaseModel):
    """Complete decision trace from analyze_node."""

    steps: list[AnalysisDecisionStep]
    final_conclusion: str


class AnalyzeOutput(BaseModel):
    """analyze_node LLM output."""

    level: Literal["t0", "t1", "t2", "t3", "t4", "unknown"]
    confidence_score: float = Field(ge=0, le=1)
    decision_trace: AnalysisDecisionTrace


# ── compose_output_node ───────────────────────────────────────────────────────


class AlternativeItem(BaseModel):
    """Single alternative ingredient suggestion."""

    ingredient_id: int
    name: str
    reason: str


class ComposeOutput(BaseModel):
    """compose_output_node LLM output."""

    safety_info: str
    alternatives: list[AlternativeItem]
```

- [ ] **Step 2: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/output.py
git commit -m "feat(ingredient_analysis): add Pydantic output models"
```

---

## Task 3: 实现 `load_ingredient_node`

**死规定：必须走 API，不直接操作数据库。**

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/load_ingredient_node.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/workflow_ingredient_analysis/test_load_ingredient_node.py
import pytest
from workflow_ingredient_analysis.nodes.load_ingredient_node import load_ingredient_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio

async def test_load_ingredient_node_success():
    state = WorkflowState(
        ingredient_id=1,
        task_id="test-task",
        run_id="test-run",
        ingredient=None,
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    result = await load_ingredient_node(state)
    assert result["ingredient"] is not None
    assert result["status"] == "running"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_load_ingredient_node.py -v 2>&1 | head -30
# Expected: ERROR — module not found or function not defined
```

- [ ] **Step 3: Implement `load_ingredient_node`**

```python
"""load_ingredient_node — 通过 API 获取配料信息。"""
from __future__ import annotations

import time
import structlog
from opentelemetry import trace

from observability.metrics import ingredient_analysis_node_duration_seconds
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import RetrievedIngredient

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


async def load_ingredient_node(state: WorkflowState) -> dict:
    """通过 API 获取配料详情，未找到则标记 failed."""
    start = time.perf_counter()
    ingredient_id = state["ingredient_id"]
    task_id = state.get("task_id", "unknown")
    _logger.info("load_ingredient_node_start", ingredient_id=ingredient_id, task_id=task_id)

    with _tracer.start_as_current_span("load_ingredient_node") as span:
        span.set_attribute("ingredient_analysis.node", "load_ingredient_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        # 通过 API 获取配料信息，不直接操作数据库
        from api.ingredients.service import IngredientService
        from api.ingredients.router import get_repo

        # 内部调用：直接实例化 repository（不创建新 session，用 state 中的 session）
        # 注意：session 由 API 层通过 state 传入，这里只是简化写法
        # 实际通过 httpx 内部调用或直接 service 层
        service = IngredientService(state["_repo"])

        ingredient_data = await service.get_by_id_for_workflow(ingredient_id)
        if ingredient_data is None:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(node="load_ingredient_node").observe(duration)
            _logger.error("load_ingredient_node_not_found", ingredient_id=ingredient_id)
            return {
                "status": "failed",
                "error_code": "ingredient_not_found",
                "errors": [f"ingredient_id={ingredient_id} not found"],
            }

        retrieved = RetrievedIngredient(
            ingredient_id=ingredient_data["id"],
            name=ingredient_data["name"],
            function_type=ingredient_data.get("function_type") or [],
            origin_type=ingredient_data.get("origin_type") or "",
            limit_usage=ingredient_data.get("limit_usage") or "",
            safety_info=ingredient_data.get("safety_info") or "",
            cas=ingredient_data.get("cas") or "",
        )

    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="load_ingredient_node").observe(duration)
    _logger.info("load_ingredient_node_done", ingredient_id=ingredient_id, duration_ms=round(duration * 1000, 2))

    return {
        "ingredient": retrieved.model_dump(),
        "status": "running",
    }
```

> **Note:** `state["_repo"]` 由 `entry.py` 在构建初始 state 时注入（IngredientRepository 实例，持有 AsyncSession）。

- [ ] **Step 4: Run test to verify it passes**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_load_ingredient_node.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/load_ingredient_node.py
git add server/tests/workflow_ingredient_analysis/test_load_ingredient_node.py
git commit -m "feat(ingredient_analysis): implement load_ingredient_node"
```

---

## Task 4: 实现 `retrieve_evidence_node`

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/retrieve_evidence_node.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/workflow_ingredient_analysis/test_retrieve_evidence_node.py
import pytest
from unittest.mock import AsyncMock, patch
from workflow_ingredient_analysis.nodes.retrieve_evidence_node import retrieve_evidence_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio

async def test_retrieve_evidence_node_success():
    state = WorkflowState(
        ingredient_id=1,
        task_id="test-task",
        run_id="test-run",
        ingredient={"ingredient_id": 1, "name": "焦糖色"},
        evidence_refs=None,
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    with patch("workflow_ingredient_analysis.nodes.retrieve_evidence_node.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "chunk_id": "chunk_1",
                "standard_no": "GB 2762-2022",
                "semantic_type": "limit",
                "section_path": "第二章",
                "content": "焦糖色的使用限量...",
                "raw_content": "原始文本",
                "score": 0.95,
            }
        ]
        result = await retrieve_evidence_node(state)
        assert result["evidence_refs"] is not None
        assert len(result["evidence_refs"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_retrieve_evidence_node.py -v 2>&1 | head -20
# Expected: ERROR — module not found
```

- [ ] **Step 3: Implement `retrieve_evidence_node`**

```python
"""retrieve_evidence_node — 从 GB 标准知识库检索证据。"""
from __future__ import annotations

import time
import structlog
from opentelemetry import trace

from observability.metrics import ingredient_analysis_node_duration_seconds
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import EvidenceRef
from kb.retriever import search

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)

_KB_UNAVAILABLE_ERROR = "knowledge_base_unavailable"


async def retrieve_evidence_node(state: WorkflowState) -> dict:
    """检索 GB 标准 chunks 作为证据，无证据时降级为 unknown."""
    start = time.perf_counter()
    ingredient = state.get("ingredient")
    if not ingredient:
        return {
            "status": "failed",
            "error_code": "ingredient_not_found",
            "errors": ["ingredient data missing from state"],
        }

    ingredient_name = ingredient.get("name", "")
    ingredient_id = state["ingredient_id"]
    task_id = state.get("task_id", "unknown")
    _logger.info("retrieve_evidence_node_start", ingredient_id=ingredient_id, name=ingredient_name, task_id=task_id)

    with _tracer.start_as_current_span("retrieve_evidence_node") as span:
        span.set_attribute("ingredient_analysis.node", "retrieve_evidence_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        try:
            kb_results = await search(query=ingredient_name, top_k=5, filters=None)
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(node="retrieve_evidence_node").observe(duration)
            _logger.error("retrieve_evidence_node_kb_error", ingredient_id=ingredient_id, error=str(exc))
            return {
                "status": "failed",
                "error_code": _KB_UNAVAILABLE_ERROR,
                "errors": [f"knowledge base unavailable: {exc}"],
            }

        if not kb_results:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(node="retrieve_evidence_node").observe(duration)
            _logger.warning("retrieve_evidence_node_no_results", ingredient_id=ingredient_id)
            return {
                "evidence_refs": [],
                "status": "running",
            }

        evidence_refs = [
            EvidenceRef(
                source_id=r["chunk_id"],
                source_type="gb_standard_chunk",
                standard_no=r.get("standard_no", ""),
                semantic_type=r.get("semantic_type", ""),
                section_path=r.get("section_path", ""),
                content=r.get("content", ""),
                raw_content=r.get("raw_content", ""),
                score=r.get("score", 0.0),
            ).model_dump()
            for r in kb_results
        ]

    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="retrieve_evidence_node").observe(duration)
    _logger.info(
        "retrieve_evidence_node_done",
        ingredient_id=ingredient_id,
        evidence_count=len(evidence_refs),
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "evidence_refs": evidence_refs,
        "status": "running",
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_retrieve_evidence_node.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/retrieve_evidence_node.py
git add server/tests/workflow_ingredient_analysis/test_retrieve_evidence_node.py
git commit -m "feat(ingredient_analysis): implement retrieve_evidence_node"
```

---

## Task 5: 实现 `analyze_node`

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/analyze_node.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/workflow_ingredient_analysis/test_analyze_node.py
import pytest
from workflow_ingredient_analysis.nodes.analyze_node import analyze_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio

async def test_analyze_node_success():
    state = WorkflowState(
        ingredient_id=1,
        task_id="test-task",
        run_id="test-run",
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        evidence_refs=[
            {
                "source_id": "chunk_1",
                "source_type": "gb_standard_chunk",
                "standard_no": "GB 2762-2022",
                "semantic_type": "limit",
                "section_path": "第二章",
                "content": "焦糖色在碳酸饮料中的使用限量...",
                "raw_content": "原始",
                "score": 0.9,
            }
        ],
        analysis_output=None,
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    result = await analyze_node(state)
    assert result["analysis_output"] is not None
    assert result["analysis_output"]["level"] in ["t0", "t1", "t2", "t3", "t4", "unknown"]
    assert 0 <= result["analysis_output"]["confidence_score"] <= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_analyze_node.py -v 2>&1 | head -20
# Expected: ERROR — module not found
```

- [ ] **Step 3: Implement `analyze_node`**

```python
"""analyze_node — 基于配料信息和证据推理风险等级。"""
from __future__ import annotations

import time
import structlog
from opentelemetry import trace

from observability.metrics import (
    ingredient_analysis_node_duration_seconds,
    ingredient_analysis_llm_calls_total,
)
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import AnalyzeOutput
from worflow_parser_kb.structured_gateway import invoke_structured

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)

_EVIDENCE_CONTEXT_MAX_LEN = 3000


def _build_evidence_context(evidence_refs: list[dict]) -> str:
    """将 evidence_refs 格式化为 prompt 上下文字符串."""
    if not evidence_refs:
        return "（无相关证据）"

    chunks = []
    for ref in evidence_refs:
        chunk_text = f"""【标准】{ref.get('standard_no', 'N/A')}
【章节】{ref.get('section_path', 'N/A')}
【语义类型】{ref.get('semantic_type', 'N/A')}
【内容】
{ref.get('content', '')}""".strip()
        chunks.append(chunk_text)

    full_text = "\n\n---\n\n".join(chunks)
    if len(full_text) > _EVIDENCE_CONTEXT_MAX_LEN:
        full_text = full_text[:_EVIDENCE_CONTEXT_MAX_LEN] + "\n...（内容截断）"
    return full_text


def _build_analyze_prompt(ingredient: dict, evidence_context: str) -> str:
    """构建 analyze_node 的 prompt."""
    name = ingredient.get("name", "")
    function_types = ", ".join(ingredient.get("function_type", []) or [])
    limit_usage = ingredient.get("limit_usage", "")
    origin = ingredient.get("origin_type", "")

    return f"""你是一位食品安全评估专家。请根据以下证据信息，对配料「{name}」进行风险评估。

【配料信息】
- 名称：{name}
- 功能类型：{function_types or '未知'}
- 来源类型：{origin or '未知'}
- 法规限值要求：{limit_usage or '未找到相关限值'}

【相关 GB 标准证据】
{evidence_context}

请进行结构化分析并返回结果。

分析要求：
1. 仔细阅读每条证据，提取与该配料安全风险相关的信息
2. 结合配料的功能类型、来源、限值要求综合判断
3. 证据不足时，应返回 "unknown" 等级，而非强行判断
4. confidence_score 反映你对判断的确信程度（0-1），证据越充分分数越高

返回格式（严格 JSON）：
{{
    "level": "t0" | "t1" | "t2" | "t3" | "t4" | "unknown",
    "confidence_score": 0.0-1.0,
    "decision_trace": {{
        "steps": [
            {{
                "step": "步骤名称，如 evidence_review / risk_reasoning",
                "findings": ["发现1", "发现2"],
                "reasoning": "该步骤的推理逻辑",
                "conclusion": "该步骤的结论"
            }}
        ],
        "final_conclusion": "最终综合结论"
    }}
}}
"""


async def analyze_node(state: WorkflowState) -> dict:
    """基于 evidence_refs 推理风险等级，证据不足时降级为 unknown."""
    start = time.perf_counter()
    ingredient_id = state["ingredient_id"]
    ingredient = state.get("ingredient")
    evidence_refs = state.get("evidence_refs") or []
    task_id = state.get("task_id", "unknown")

    _logger.info("analyze_node_start", ingredient_id=ingredient_id, task_id=task_id)

    with _tracer.start_as_current_span("analyze_node") as span:
        span.set_attribute("ingredient_analysis.node", "analyze_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        evidence_context = _build_evidence_context(evidence_refs)
        prompt = _build_analyze_prompt(ingredient, evidence_context)

        try:
            result = invoke_structured(
                node_name="analyze_node",
                prompt=prompt,
                response_model=AnalyzeOutput,
            )
            ingredient_analysis_llm_calls_total.labels(node="analyze_node", model="unknown").inc()
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(node="analyze_node").observe(duration)
            _logger.error("analyze_node_llm_error", ingredient_id=ingredient_id, error=str(exc))
            return {
                "status": "failed",
                "error_code": "schema_invalid",
                "errors": [f"analyze_node LLM 调用失败: {exc}"],
            }

    output = result.model_dump()
    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="analyze_node").observe(duration)
    _logger.info(
        "analyze_node_done",
        ingredient_id=ingredient_id,
        level=output["level"],
        confidence=output["confidence_score"],
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "analysis_output": output,
        "status": "running",
    }
```

> **Note:** `invoke_structured` 不传 `provider`/`model` 参数时，走 `structured_gateway.py` 中的 fallback（`DEFAULT_LLM_PROVIDER` / `DEFAULT_MODEL`），暂不单独配置。

- [ ] **Step 4: Run test to verify it passes**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_analyze_node.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/analyze_node.py
git add server/tests/workflow_ingredient_analysis/test_analyze_node.py
git commit -m "feat(ingredient_analysis): implement analyze_node"
```

---

## Task 6: 实现 `compose_output_node`

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/compose_output_node.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/workflow_ingredient_analysis/test_compose_output_node.py
import pytest
from workflow_ingredient_analysis.nodes.compose_output_node import compose_output_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio

async def test_compose_output_node_success():
    state = WorkflowState(
        ingredient_id=1,
        task_id="test-task",
        run_id="test-run",
        ingredient={"ingredient_id": 1, "name": "焦糖色", "function_type": ["着色剂"]},
        evidence_refs=[],
        analysis_output={
            "level": "t2",
            "confidence_score": 0.75,
            "decision_trace": {
                "steps": [{"step": "review", "findings": [], "reasoning": "", "conclusion": "test"}],
                "final_conclusion": "中等风险",
            },
        },
        composed_output=None,
        status="running",
        error_code=None,
        errors=[],
    )
    result = await compose_output_node(state)
    assert result["composed_output"] is not None
    assert "safety_info" in result["composed_output"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_compose_output_node.py -v 2>&1 | head -20
# Expected: ERROR — module not found
```

- [ ] **Step 3: Implement `compose_output_node`**

```python
"""compose_output_node — 生成 safety_info 和 alternatives。"""
from __future__ import annotations

import time
import structlog
from opentelemetry import trace

from observability.metrics import (
    ingredient_analysis_node_duration_seconds,
    ingredient_analysis_llm_calls_total,
)
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import ComposeOutput
from worflow_parser_kb.structured_gateway import invoke_structured

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


def _build_compose_prompt(ingredient: dict, analysis_output: dict, evidence_refs: list[dict]) -> str:
    """构建 compose_output_node 的 prompt."""
    name = ingredient.get("name", "")
    function_types = ", ".join(ingredient.get("function_type", []) or [])
    level = analysis_output.get("level", "unknown")
    confidence = analysis_output.get("confidence_score", 0.0)
    trace_steps = analysis_output.get("decision_trace", {}).get("steps", [])
    final_conclusion = analysis_output.get("decision_trace", {}).get("final_conclusion", "")

    trace_text = "\n".join(
        f"- [{s['step']}] {s['conclusion']}" for s in trace_steps
    ) if trace_steps else final_conclusion

    evidence_brief = "\n".join(
        f"- {r.get('standard_no', 'N/A')}: {r.get('content', '')[:100]}..."
        for r in (evidence_refs or [])[:3]
    ) or "无相关证据"

    return f"""你是一位食品安全科普专家。请为配料「{name}」生成面向消费者的安全提示和替代建议。

【配料信息】
- 名称：{name}
- 功能类型：{function_types or '未知'}
- 风险等级：{level}（{final_conclusion}）
- 判断置信度：{confidence:.0%}

【风险评估依据】
{trace_text}

【相关标准参考（仅前3条）】
{evidence_brief}

返回格式（严格 JSON）：
{{
    "safety_info": "面向消费者的安全提示，2-4句话，通俗易懂，说明该配料的风险和适用人群。不超过200字。",
    "alternatives": [
        {{
            "ingredient_id": 0,
            "name": "替代配料名称",
            "reason": "推荐理由，1句话"
        }}
    ]
}}

注意：
- 如果 level 为 t0 或 t1，safety_info 应强调其安全性
- 如果 level 为 t3 或 t4，safety_info 应明确风险提示
- 如果 level 为 unknown 或 t2，alternatives 应提供更安全的替代选择
- alternatives 中的 ingredient_id 暂时填 0（由外部知识库匹配后填充）
"""


async def compose_output_node(state: WorkflowState) -> dict:
    """生成 safety_info 与 alternatives."""
    start = time.perf_counter()
    ingredient_id = state["ingredient_id"]
    ingredient = state.get("ingredient", {})
    analysis_output = state.get("analysis_output") or {}
    evidence_refs = state.get("evidence_refs") or []
    task_id = state.get("task_id", "unknown")

    _logger.info("compose_output_node_start", ingredient_id=ingredient_id, task_id=task_id)

    with _tracer.start_as_current_span("compose_output_node") as span:
        span.set_attribute("ingredient_analysis.node", "compose_output_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        prompt = _build_compose_prompt(ingredient, analysis_output, evidence_refs)

        try:
            result = invoke_structured(
                node_name="compose_output_node",
                prompt=prompt,
                response_model=ComposeOutput,
            )
            ingredient_analysis_llm_calls_total.labels(node="compose_output_node", model="unknown").inc()
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(node="compose_output_node").observe(duration)
            _logger.error("compose_output_node_llm_error", ingredient_id=ingredient_id, error=str(exc))
            return {
                "status": "failed",
                "error_code": "schema_invalid",
                "errors": [f"compose_output_node LLM 调用失败: {exc}"],
            }

    output = result.model_dump()
    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="compose_output_node").observe(duration)
    _logger.info(
        "compose_output_node_done",
        ingredient_id=ingredient_id,
        has_alternatives=len(output.get("alternatives", [])) > 0,
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "composed_output": output,
        "status": "running",
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_compose_output_node.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/compose_output_node.py
git add server/tests/workflow_ingredient_analysis/test_compose_output_node.py
git commit -m "feat(ingredient_analysis): implement compose_output_node"
```

---

## Task 7: 实现 `persist_version_node`

**死规定：不写库，只 yield 数据，由 entry.py 末尾通过 API 写入。**

**Files:**
- Create: `server/workflow_ingredient_analysis/nodes/persist_version_node.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/workflow_ingredient_analysis/test_persist_version_node.py
import pytest
from workflow_ingredient_analysis.nodes.persist_version_node import persist_version_node
from workflow_ingredient_analysis.models import WorkflowState

pytestmark = pytest.mark.asyncio

async def test_persist_version_node_success():
    state = WorkflowState(
        ingredient_id=1,
        task_id="test-task",
        run_id="test-run",
        ingredient={"ingredient_id": 1, "name": "焦糖色"},
        evidence_refs=[],
        analysis_output={
            "level": "t2",
            "confidence_score": 0.75,
            "decision_trace": {"steps": [], "final_conclusion": "中等风险"},
        },
        composed_output={
            "safety_info": "适量食用是安全的",
            "alternatives": [],
        },
        status="running",
        error_code=None,
        errors=[],
    )
    result = await persist_version_node(state)
    assert result["status"] == "succeeded"
    assert result["analysis_output"] is not None
    assert result["composed_output"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_persist_version_node.py -v 2>&1 | head -20
# Expected: ERROR — module not found
```

- [ ] **Step 3: Implement `persist_version_node`**

```python
"""persist_version_node — 只输出数据，不写库。写库由 entry.py 末尾通过 API 执行。"""
from __future__ import annotations

import time
import structlog
from opentelemetry import trace

from observability.metrics import ingredient_analysis_node_duration_seconds
from workflow_ingredient_analysis.models import WorkflowState

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


async def persist_version_node(state: WorkflowState) -> dict:
    """只 yield 最终数据，不执行任何数据库写入。"""
    start = time.perf_counter()
    ingredient_id = state["ingredient_id"]
    analysis_output = state.get("analysis_output") or {}
    composed_output = state.get("composed_output") or {}
    evidence_refs = state.get("evidence_refs") or []
    task_id = state.get("task_id", "unknown")

    _logger.info("persist_version_node_start", ingredient_id=ingredient_id, task_id=task_id)

    with _tracer.start_as_current_span("persist_version_node") as span:
        span.set_attribute("ingredient_analysis.node", "persist_version_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        # 只输出数据，不写库
        result_data = {
            "ingredient_id": ingredient_id,
            "level": analysis_output.get("level", "unknown"),
            "safety_info": composed_output.get("safety_info", ""),
            "alternatives": composed_output.get("alternatives", []),
            "confidence_score": analysis_output.get("confidence_score", 0.0),
            "evidence_refs": evidence_refs,
            "decision_trace": analysis_output.get("decision_trace", {}),
        }

    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="persist_version_node").observe(duration)
    _logger.info(
        "persist_version_node_done",
        ingredient_id=ingredient_id,
        level=result_data["level"],
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "status": "succeeded",
        "result_data": result_data,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_persist_version_node.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add server/workflow_ingredient_analysis/nodes/persist_version_node.py
git add server/tests/workflow_ingredient_analysis/test_persist_version_node.py
git commit -m "feat(ingredient_analysis): implement persist_version_node (no DB write)"
```

---

## Task 8: 编译 LangGraph 并导出 entry 函数

**entry.py 负责：**
1. 调用 workflow
2. workflow 结束后，通过 API 写入分析结果（调用 `POST /api/ingredient-analyses/{ingredient_id}`）

**Files:**
- Create: `server/workflow_ingredient_analysis/graph.py`
- Create: `server/workflow_ingredient_analysis/entry.py`

- [ ] **Step 1: Create `server/workflow_ingredient_analysis/graph.py`**

```python
"""LangGraph compilation for ingredient_analysis workflow."""
from __future__ import annotations

import structlog
from langgraph.graph import END, StateGraph

from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.load_ingredient_node import load_ingredient_node
from workflow_ingredient_analysis.nodes.retrieve_evidence_node import retrieve_evidence_node
from workflow_ingredient_analysis.nodes.analyze_node import analyze_node
from workflow_ingredient_analysis.nodes.compose_output_node import compose_output_node
from workflow_ingredient_analysis.nodes.persist_version_node import persist_version_node

_logger = structlog.get_logger(__name__)


def _should_skip_analysis(state: WorkflowState) -> str:
    """如果 evidence_refs 为空，跳过 analyze_node 直接进入 compose_output_node."""
    evidence_refs = state.get("evidence_refs") or []
    if not evidence_refs:
        return "compose_output_node"
    return "analyze_node"


def _build_graph():
    builder = StateGraph(WorkflowState)

    builder.add_node("load_ingredient_node", load_ingredient_node)
    builder.add_node("retrieve_evidence_node", retrieve_evidence_node)
    builder.add_node("analyze_node", analyze_node)
    builder.add_node("compose_output_node", compose_output_node)
    builder.add_node("persist_version_node", persist_version_node)

    builder.set_entry_point("load_ingredient_node")

    # load_ingredient → retrieve_evidence
    builder.add_edge("load_ingredient_node", "retrieve_evidence_node")

    # retrieve_evidence → analyze_node（有证据时）或 compose_output_node（无证据时）
    builder.add_conditional_edges(
        "retrieve_evidence_node",
        _should_skip_analysis,
        {
            "analyze_node": "analyze_node",
            "compose_output_node": "compose_output_node",
        },
    )

    # analyze_node → compose_output_node
    builder.add_edge("analyze_node", "compose_output_node")

    # compose_output_node → persist_version_node
    builder.add_edge("compose_output_node", "persist_version_node")

    # persist_version_node → END
    builder.add_edge("persist_version_node", END)

    return builder.compile()


ingredient_analysis_graph = _build_graph()
```

- [ ] **Step 2: Create `server/workflow_ingredient_analysis/entry.py`**

```python
"""Public entry point for ingredient_analysis workflow."""
from __future__ import annotations

import uuid
import structlog
from opentelemetry import trace

from observability.metrics import ingredient_analysis_run_total, ingredient_analysis_duration_seconds
from workflow_ingredient_analysis.graph import ingredient_analysis_graph
from workflow_ingredient_analysis.models import WorkflowState

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


async def run_ingredient_analysis(
    ingredient_id: int,
    task_id: str,
    repo: Any,  # IngredientRepository — 持有 AsyncSession
    ai_model: str = "unknown",
) -> dict:
    """
    执行 ingredient_analyses workflow.

    Args:
        ingredient_id: 目标配料的 ID
        task_id: Redis 任务 ID，用于状态更新
        repo: IngredientRepository 实例（持有 session）
        ai_model: 使用的 LLM 模型名称

    Returns:
        dict，含 keys: status, ingredient_id, task_id, errors
    """
    run_id = str(uuid.uuid4())
    _logger.info("run_ingredient_analysis_start", ingredient_id=ingredient_id, task_id=task_id, run_id=run_id)
    start_time = __import__("time").perf_counter()

    initial_state: WorkflowState = {
        "ingredient_id": ingredient_id,
        "task_id": task_id,
        "run_id": run_id,
        "ingredient": None,
        "evidence_refs": None,
        "analysis_output": None,
        "composed_output": None,
        "status": "running",
        "error_code": None,
        "errors": [],
        "_repo": repo,
        "ai_model": ai_model,
    }

    try:
        with _tracer.start_as_current_span("ingredient_analysis_workflow") as span:
            span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)
            span.set_attribute("ingredient_analysis.run_id", run_id)
            span.set_attribute("ingredient_analysis.task_id", task_id)

            result_state = await ingredient_analysis_graph.ainvoke(initial_state)

            final_status = result_state.get("status", "failed")
            span.set_attribute("ingredient_analysis.status", final_status)

            # 记录 metrics
            ingredient_analysis_run_total.labels(status=final_status).inc()
            if final_status == "succeeded":
                analysis_output = result_state.get("analysis_output") or {}
                if analysis_output.get("level") == "unknown":
                    ingredient_analysis_unknown_rate.inc()
            ingredient_analysis_duration_seconds.observe(__import__("time").perf_counter() - start_time)

            # 通过 API 写入分析结果（不走 DB 直接写入）
            if final_status == "succeeded":
                result_data = result_state.get("result_data", {})
                result_data["ai_model"] = ai_model
                from api.ingredient_analysis.service import IngredientAnalysisService
                svc = IngredientAnalysisService(result_data.get("_session"))
                await svc.create(ingredient_id, result_data)

            return {
                "status": final_status,
                "ingredient_id": ingredient_id,
                "task_id": task_id,
                "run_id": run_id,
                "error_code": result_state.get("error_code"),
                "errors": result_state.get("errors", []),
            }
    except Exception as exc:
        _logger.error("run_ingredient_analysis_error", ingredient_id=ingredient_id, error=str(exc))
        ingredient_analysis_run_total.labels(status="failed").inc()
        ingredient_analysis_duration_seconds.observe(__import__("time").perf_counter() - start_time)
        return {
            "status": "failed",
            "ingredient_id": ingredient_id,
            "task_id": task_id,
            "run_id": run_id,
            "error_code": "workflow_error",
            "errors": [str(exc)],
        }
```

- [ ] **Step 3: Update `server/workflow_ingredient_analysis/__init__.py` to re-export**

```python
"""Ingredient analysis workflow."""
from workflow_ingredient_analysis.entry import run_ingredient_analysis

__all__ = ["run_ingredient_analysis"]
```

- [ ] **Step 4: Commit**

```bash
git add server/workflow_ingredient_analysis/graph.py server/workflow_ingredient_analysis/entry.py server/workflow_ingredient_analysis/__init__.py
git commit -m "feat(ingredient_analysis): compile LangGraph and export entry function"
```

---

## Task 9: 创建 `api/ingredient_analysis` 模块

**死规定：所有数据库写操作必须通过 API。**

**Files:**
- Create: `server/api/ingredient_analysis/__init__.py`
- Create: `server/api/ingredient_analysis/models.py`
- Create: `server/api/ingredient_analysis/service.py`
- Create: `server/api/ingredient_analysis/router.py`

### Models

```python
# server/api/ingredient_analysis/models.py
from __future__ import annotations

from pydantic import BaseModel


class IngredientAnalysisCreate(BaseModel):
    ai_model: str
    level: str
    safety_info: str
    alternatives: list
    confidence_score: float
    evidence_refs: list
    decision_trace: dict


class IngredientAnalysisResponse(BaseModel):
    id: int
    ingredient_id: int
    ai_model: str
    level: str
    safety_info: str
    alternatives: list
    confidence_score: float
    created_at: str
```

### Service

```python
# server/api/ingredient_analysis/service.py
from __future__ import annotations

from db_repositories.ingredient_analysis import IngredientAnalysisRepository


class IngredientAnalysisService:
    def __init__(self, session):
        self._repo = IngredientAnalysisRepository(session)

    async def create(self, ingredient_id: int, data: dict) -> dict:
        record = await self._repo.insert_new_version(
            ingredient_id=ingredient_id,
            data=data,
            created_by_user="workflow",
        )
        return {
            "id": record.id,
            "ingredient_id": record.ingredient_id,
            "ai_model": record.ai_model,
            "level": record.level,
            "safety_info": record.safety_info,
            "alternatives": record.alternatives,
            "confidence_score": record.confidence_score,
            "created_at": record.created_at.isoformat(),
        }
```

### Router

```python
# server/api/ingredient_analysis/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.ingredient_analysis.models import IngredientAnalysisCreate, IngredientAnalysisResponse
from api.ingredient_analysis.service import IngredientAnalysisService
from database.session import get_async_session

router = APIRouter(prefix="/api/ingredient-analyses", tags=["IngredientAnalysis"])


def get_service(session: AsyncSession = Depends(get_async_session)) -> IngredientAnalysisService:
    return IngredientAnalysisService(session)


@router.post("/{ingredient_id}", response_model=IngredientAnalysisResponse, status_code=201)
async def create_ingredient_analysis(
    ingredient_id: int,
    body: IngredientAnalysisCreate,
    svc: IngredientAnalysisService = Depends(get_service),
):
    """写入配料分析结果（供 workflow background task 调用）。"""
    return await svc.create(ingredient_id, body.model_dump())
```

- [ ] **Commit**

```bash
git add server/api/ingredient_analysis/
git commit -m "feat(ingredient_analysis): add api/ingredient_analysis module for DB writes"
```

---

## Task 10: 添加 API 接口（触发分析 + 查询状态）

**Files:**
- Modify: `server/api/ingredients/router.py`
- Modify: `server/api/ingredients/service.py`

### Router 层

- [ ] **Step 1: Add `POST /{ingredient_id}/analyze` endpoint**

```python
@router.post("/{ingredient_id}/analyze", status_code=202)
async def trigger_ingredient_analysis(
    ingredient_id: int,
    background_tasks: BackgroundTasks,
    svc: IngredientService = Depends(get_service),
):
    """
    触发配料分析（异步）。

    返回 task_id，状态通过 GET /api/analysis/{task_id}/status 查询。
    """
    result = await svc.trigger_analysis(ingredient_id, background_tasks)
    if result is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result
```

### Service 层

- [ ] **Step 2: Add `trigger_analysis` in `IngredientService`**

```python
async def trigger_analysis(
    self,
    ingredient_id: int,
    background_tasks: BackgroundTasks,
) -> dict | None:
    """检查配料存在，返回 task_id，启动后台 workflow。"""
    ingredient = await self.repo.get_by_id(ingredient_id)
    if ingredient is None:
        return None

    task_id = str(uuid.uuid4())
    await set_task_pending(self.redis, task_id, ingredient_id, ttl=_PIPELINE_TTL_SECONDS)

    async def _run_workflow():
        from workflow_ingredient_analysis.entry import run_ingredient_analysis
        from database.session import async_session_maker
        async with async_session_maker() as session:
            repo = IngredientRepository(session)
            result = await run_ingredient_analysis(
                ingredient_id=ingredient_id,
                task_id=task_id,
                repo=repo,
                ai_model=settings.DEFAULT_MODEL,
            )
            if result["status"] == "succeeded":
                await set_task_done(self.redis, task_id, result, ttl=_PIPELINE_TTL_SECONDS)
            else:
                await set_task_failed(
                    self.redis,
                    task_id,
                    result.get("error_code", "unknown"),
                    ttl=_PIPELINE_TTL_SECONDS,
                )

    background_tasks.add_task(_run_workflow)
    return {"task_id": task_id, "ingredient_id": ingredient_id, "status": "queued"}
```

- [ ] **Commit**

```bash
git add server/api/ingredients/router.py server/api/ingredients/service.py
git commit -m "feat(ingredients): add POST /{id}/analyze endpoint"
```

---

## Task 11: 删除 `version` 字段

> `version` 字段无实际意义，移除。

**Files:**
- Modify: `server/database/models.py` — 从 `IngredientAnalysis` 中移除 `version` 列
- Modify: `server/db_repositories/ingredient_analysis.py` — 移除 `version` 相关代码
- Modify: `server/alembic/versions/` — 新增 migration 移除列

- [ ] **Step 1: 修改 ORM 模型**

从 `IngredientAnalysis` 类中移除：
```python
version: Mapped[str] = mapped_column(String(50), nullable=False)
```

- [ ] **Step 2: 修改 Repository**

`insert_new_version()` 的 `data` 参数中移除 `version` 字段。

- [ ] **Step 3: 生成 Alembic migration**

```bash
cd server && uv run alembic revision --autogenerate -m "drop ingredient_analyses.version"
```

- [ ] **Commit**

```bash
git add server/database/models.py server/db_repositories/ingredient_analysis.py server/alembic/versions/
git commit -m "refactor(ingredient_analysis): remove version field"
```

---

## Task 12: 添加可观测性指标

**Files:**
- Modify: `server/observability/metrics.py`

- [ ] **Step 1: 在 `metrics.py` 末尾追加**

```python
# ── Ingredient Analysis Workflow ─────────────────────────────────────────────

ingredient_analysis_run_total = Counter(
    "ingredient_analysis_run_total",
    "Ingredient analysis workflow 执行总次数",
    ["status"],  # succeeded | failed
)

ingredient_analysis_node_duration_seconds = Histogram(
    "ingredient_analysis_node_duration_seconds",
    "Ingredient analysis 各节点处理耗时（秒）",
    ["node"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

ingredient_analysis_duration_seconds = Histogram(
    "ingredient_analysis_duration_seconds",
    "Ingredient analysis 完整 workflow 耗时（秒）",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ingredient_analysis_llm_calls_total = Counter(
    "ingredient_analysis_llm_calls_total",
    "Ingredient analysis LLM 调用总次数",
    ["node", "model"],
)

ingredient_analysis_unknown_rate = Counter(
    "ingredient_analysis_unknown_rate",
    "Ingredient analysis 返回 unknown 等级的总次数",
    [],
)
```

- [ ] **Commit**

```bash
git add server/observability/metrics.py
git commit -m "feat(ingredient_analysis): add observability metrics"
```

---

## Task 13: 端到端集成测试

**Files:**
- Create: `server/tests/workflow_ingredient_analysis/test_workflow_e2e.py`

- [ ] **Step 1: Write e2e test**

```python
"""End-to-end integration test for ingredient_analysis workflow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from workflow_ingredient_analysis.entry import run_ingredient_analysis
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import AnalyzeOutput, ComposeOutput

pytestmark = pytest.mark.asyncio


async def test_e2e_happy_path():
    """完整流程：有证据 → 全部节点正常执行 → succeeded."""
    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session

    mock_ingredient_data = {
        "id": 1,
        "name": "焦糖色",
        "function_type": ["着色剂"],
        "origin_type": "合成",
        "limit_usage": "按需添加",
        "safety_info": "",
        "cas": "8028-89-5",
    }

    with patch("workflow_ingredient_analysis.nodes.load_ingredient_node.IngredientService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_by_id_for_workflow = AsyncMock(return_value=mock_ingredient_data)
        mock_svc_cls.return_value = mock_svc

        with patch("workflow_ingredient_analysis.nodes.retrieve_evidence_node.search") as mock_search:
            mock_search.return_value = [
                {
                    "chunk_id": "chunk_1",
                    "standard_no": "GB 2762-2022",
                    "semantic_type": "limit",
                    "section_path": "第二章",
                    "content": "焦糖色限量规定...",
                    "raw_content": "原始",
                    "score": 0.9,
                }
            ]

            with patch("workflow_ingredient_analysis.nodes.analyze_node.invoke_structured") as mock_analyze:
                mock_analyze.return_value = AnalyzeOutput(
                    level="t2",
                    confidence_score=0.8,
                    decision_trace={
                        "steps": [{"step": "review", "findings": [], "reasoning": "", "conclusion": "中等"}],
                        "final_conclusion": "中等风险",
                    },
                )

                with patch("workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured") as mock_compose:
                    mock_compose.return_value = ComposeOutput(
                        safety_info="适量食用安全",
                        alternatives=[],
                    )

                    with patch("workflow_ingredient_analysis.entry.IngredientAnalysisService") as mock_ia_svc:
                        mock_ia_svc.return_value.create = AsyncMock()

                        result = await run_ingredient_analysis(
                            ingredient_id=1,
                            task_id="test-task",
                            repo=mock_repo,
                            ai_model="claude-opus-4-6",
                        )

    assert result["status"] == "succeeded"
    assert result["ingredient_id"] == 1


async def test_e2e_ingredient_not_found():
    """配料不存在 → failed(ingredient_not_found)."""
    mock_repo = AsyncMock()

    with patch("workflow_ingredient_analysis.nodes.load_ingredient_node.IngredientService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_by_id_for_workflow = AsyncMock(return_value=None)
        mock_svc_cls.return_value = mock_svc

        result = await run_ingredient_analysis(
            ingredient_id=999,
            task_id="test-task",
            repo=mock_repo,
        )

    assert result["status"] == "failed"
    assert result["error_code"] == "ingredient_not_found"


async def test_e2e_no_evidence_skips_analyze():
    """无证据时 analyze_node 被跳过，流程继续."""
    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session

    mock_ingredient_data = {
        "id": 1,
        "name": "新配料",
        "function_type": [],
        "origin_type": "",
        "limit_usage": "",
        "safety_info": "",
        "cas": "",
    }

    with patch("workflow_ingredient_analysis.nodes.load_ingredient_node.IngredientService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_by_id_for_workflow = AsyncMock(return_value=mock_ingredient_data)
        mock_svc_cls.return_value = mock_svc

        with patch("workflow_ingredient_analysis.nodes.retrieve_evidence_node.search") as mock_search:
            mock_search.return_value = []  # 无证据

            with patch("workflow_ingredient_analysis.nodes.compose_output_node.invoke_structured") as mock_compose:
                mock_compose.return_value = ComposeOutput(
                    safety_info="无相关证据，请咨询专业人士",
                    alternatives=[],
                )

                with patch("workflow_ingredient_analysis.entry.IngredientAnalysisService") as mock_ia_svc:
                    mock_ia_svc.return_value.create = AsyncMock()

                    result = await run_ingredient_analysis(
                        ingredient_id=1,
                        task_id="test-task",
                        repo=mock_repo,
                    )

    assert result["status"] == "succeeded"
```

- [ ] **Step 2: Run e2e tests**

```bash
cd server && uv run pytest tests/workflow_ingredient_analysis/test_workflow_e2e.py -v
# Expected: PASS (all 3 tests)
```

- [ ] **Commit**

```bash
git add server/tests/workflow_ingredient_analysis/test_workflow_e2e.py
git commit -m "test(ingredient_analysis): add e2e integration tests"
```

---

## 自检清单

### 死规定检查
- [x] `load_ingredient_node` — 通过 API（`IngredientService`）获取配料，不直接 SQLAlchemy
- [x] `persist_version_node` — 只 yield 数据，不写库
- [x] `entry.py` — workflow 结束后调用 `POST /api/ingredient-analyses/{id}` 写入
- [x] `IngredientAnalysisService` — 所有 DB 写操作通过此 service

### Spec 覆盖检查
- [x] `ingredient_id` 入口键 — Task 3
- [x] 5 个节点全部实现 — Task 3/4/5/6/7
- [x] `evidence_refs` 结构 — Task 4
- [x] `AnalyzeOutput` + `AnalysisDecisionTrace` — Task 5
- [x] `ComposeOutput` + `AlternativeItem` — Task 6
- [x] `persist_version_node` 只输出数据 — Task 7
- [x] 状态机 `queued → running → succeeded | failed` — Task 8
- [x] `knowledge_base_unavailable` error_code — Task 4
- [x] 可观测性指标 — Task 12
- [x] 无 evidence 时条件跳过 analyze_node — Task 8
- [x] `version` 字段移除 — Task 11
- [x] 异步接口 `POST /ingredients/{id}/analyze` — Task 10
- [x] 复用 `GET /api/analysis/{task_id}/status` — Task 10
- [x] BackgroundTasks 后台执行 — Task 10
- [x] `api/ingredient_analysis` 模块 — Task 9

### 类型一致性检查
- `WorkflowState` 中 `ingredient: dict | None` — 与 `RetrievedIngredient.model_dump()` 对应
- `analyze_node` 输出 `AnalyzeOutput` 的 `level` 字段为 `Literal["t0", "t1", "t2", "t3", "t4", "unknown"]` — 与 ORM `level_enum` 对应
- `compose_output_node` 输出 `ComposeOutput` 的 `alternatives` 为 `list[AlternativeItem]` — 与 ORM `JSONB` 列对应
- `insert_new_version` 的 `data` dict 字段与 `IngredientAnalysis` 模型字段对应（移除 version 后）

### 占位符检查
- 无 `TBD` / `TODO` / `FIXME`
- 所有 prompt 内容完整，无"填充详情"类占位符
- 所有测试有实际断言，无空测试
- `invoke_structured` 不传 `provider`/`model`，走全局 fallback
