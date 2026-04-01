# workflow_product_analysis 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `workflow_product_analysis/` 改造为纯 LLM 计算组件，所有 DB/Redis/HTTP 依赖迁移到 API 层。

**Architecture:**
- `workflow_product_analysis/product_agent/` 保留 LangGraph 结构（graph + 4 个节点），无 session 依赖
- API 层（`api/analysis/`）负责完整编排：OCR → Parse → Resolve → Match → Agent → Assemble
- 移除 Redis 任务状态轮询，`GET /analysis/{task_id}/status` 端点删除

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph, Pydantic

---

## 任务总览

| # | 任务 | 改动范围 |
|---|------|---------|
| 1 | 拆分 `product_agent/nodes.py` → 独立文件 | 新建 4 文件，修改 `__init__.py` |
| 2 | 重命名 `run_product_analysis_agent` → `build_product_analysis_graph` | 修改 `graph.py` + `__init__.py` |
| 3 | 复制迁出文件到 `api/analysis/` | 新建 5 文件 |
| 4 | 编写 `api/analysis/service.py` 编排逻辑 | 重写 `service.py` |
| 5 | 更新 `api/analysis/router.py` | 删除 status 端点 |
| 6 | 删除 `workflow_product_analysis/` 迁出文件 | 删除 7 文件 |
| 7 | 验证测试通过 | 运行 pytest |

---

## 准备工作：确认 types.py 无需修改

`workflow_product_analysis/types.py` 中的既有类型（`IngredientInput`、`ProductAnalysisResult`、`RiskLevel`、`IngredientRiskLevel`、`MatchResult`、`MatchedIngredient` 等）均保留，无需修改。`workflow_product_analysis/product_agent/types.py` 中的 `ProductAnalysisState` 也保留。

---

## Task 1: 拆分 `product_agent/nodes.py` → 独立文件

**Files:**
- Create: `server/workflow_product_analysis/product_agent/nodes/__init__.py`
- Create: `server/workflow_product_analysis/product_agent/nodes/demographics_node.py`
- Create: `server/workflow_product_analysis/product_agent/nodes/scenarios_node.py`
- Create: `server/workflow_product_analysis/product_agent/nodes/advice_node.py`
- Create: `server/workflow_product_analysis/product_agent/nodes/verdict_node.py`
- Modify: `server/workflow_product_analysis/product_agent/__init__.py`

- [ ] **Step 1: 创建 `product_agent/nodes/__init__.py`**

```python
from workflow_product_analysis.product_agent.nodes.demographics_node import demographics_node
from workflow_product_analysis.product_agent.nodes.scenarios_node import scenarios_node
from workflow_product_analysis.product_agent.nodes.advice_node import advice_node
from workflow_product_analysis.product_agent.nodes.verdict_node import verdict_node

__all__ = ["demographics_node", "scenarios_node", "advice_node", "verdict_node"]
```

- [ ] **Step 2: 创建 `product_agent/nodes/demographics_node.py`**

```python
"""Node A: 人群适用性分析"""
from __future__ import annotations

import asyncio

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import DemographicsOutput, ProductAnalysisState


def _build_ingredients_summary(ingredients) -> str:
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def demographics_node(state: ProductAnalysisState, settings) -> dict:
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""分析以下食品成分对不同人群的适用性：

成分列表：
{summary}

请对以下 5 类人群各输出一条评估（level 为该人群面临的风险等级，note 为 1-2 句具体说明）：
- 普通成人
- 婴幼儿
- 孕妇
- 中老年
- 运动人群"""

    result: DemographicsOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=DemographicsOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    demographics = [
        {"group": d.group, "level": d.level, "note": d.note}
        for d in result.demographics
    ]
    return {"demographics": demographics}
```

- [ ] **Step 3: 创建 `product_agent/nodes/scenarios_node.py`**

```python
"""Node B: 食用场景分析"""
from __future__ import annotations

import asyncio

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import ProductAnalysisState, ScenariosOutput


def _build_ingredients_summary(ingredients) -> str:
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def scenarios_node(state: ProductAnalysisState, settings) -> dict:
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""根据以下食品成分，给出 1-3 个具体的食用场景建议：

成分列表：
{summary}

每个场景需包含：title（如"上午加餐"）和 text（具体建议 2-3 句，包含时间段、人群、搭配）。"""

    result: ScenariosOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=ScenariosOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    scenarios = [
        {"title": s.title, "text": s.text}
        for s in result.scenarios
    ]
    return {"scenarios": scenarios}
```

- [ ] **Step 4: 创建 `product_agent/nodes/advice_node.py`**

```python
"""Node C: 综合建议"""
from __future__ import annotations

import asyncio

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import AdviceOutput, ProductAnalysisState


def _build_ingredients_summary(ingredients) -> str:
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def advice_node(state: ProductAnalysisState, settings) -> dict:
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    demo_text = "\n".join(
        [f"- {d['group']}: {d['note']}" for d in (state["demographics"] or [])]
    )
    scene_text = "\n".join(
        [f"- {s['title']}: {s['text']}" for s in (state["scenarios"] or [])]
    )

    prompt = f"""综合以下信息，给出面向普通用户的简短建议（1-3 句，语气实用中立，不做绝对化判断）：

成分：
{summary}

各人群评估：
{demo_text}

食用场景：
{scene_text}"""

    result: AdviceOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=AdviceOutput,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"advice": result.advice}
```

- [ ] **Step 5: 创建 `product_agent/nodes/verdict_node.py`**

```python
"""Node D: 整体判断"""
from __future__ import annotations

import asyncio
import logging

from workflow_parser_kb.structured_llm.client_factory import get_structured_client
from workflow_product_analysis.product_agent.types import ProductAnalysisState, VerdictOutput

logger = logging.getLogger(__name__)


def _build_ingredients_summary(ingredients) -> str:
    lines = []
    for ing in ingredients:
        lines.append(
            f"- {ing['name']} (风险等级: {ing['level']}, 类别: {ing['category']}): {ing['safety_info']}"
        )
    return "\n".join(lines) if lines else "（无成分信息）"


async def verdict_node(state: ProductAnalysisState, settings) -> dict:
    create = get_structured_client(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
    )
    summary = _build_ingredients_summary(state["ingredients"])
    prompt = f"""综合所有分析，给出对该产品的最终整体评估：

成分：
{summary}

各人群评估：
{[d['note'] for d in (state['demographics'] or [])]}

食用建议：{state.get('advice', '')}

请输出：
- level：整体风险等级（t0-t4）
- description：对该产品的特有一句话描述（不能是通用模板）
- references：引用的食品安全标准（如 "GB 2760"，仅引用真实存在的标准）"""

    result: VerdictOutput = await asyncio.to_thread(
        create,
        model=settings.DEFAULT_MODEL,
        response_model=VerdictOutput,
        messages=[{"role": "user", "content": prompt}],
    )

    allowlist_raw = settings.ANALYSIS_REFERENCES_ALLOWLIST.split(",")
    allowlist = {
        s.strip().upper().replace("\u3000", " ").replace("　", " ")
        for s in allowlist_raw
    }

    filtered_refs: list = []
    for ref in result.references:
        normalized = ref.strip().upper().replace("\u3000", " ").replace("　", " ")
        matched = any(normalized.startswith(allowed) for allowed in allowlist)
        if matched:
            filtered_refs.append(ref)
        else:
            logger.warning("reference '%s' not in allowlist, discarded", ref)

    return {
        "verdict_level": result.level,
        "verdict_description": result.description,
        "references": filtered_refs,
    }
```

- [ ] **Step 6: 更新 `product_agent/__init__.py`**

```python
from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.nodes import (
    advice_node,
    demographics_node,
    verdict_node,
    scenarios_node,
)
from workflow_product_analysis.product_agent.types import (
    AdviceOutput,
    DemographicsOutput,
    ProductAnalysisState,
    ScenariosOutput,
    VerdictOutput,
)

__all__ = [
    "ProductAgentError",
    "build_product_analysis_graph",
    "demographics_node",
    "scenarios_node",
    "advice_node",
    "verdict_node",
    "ProductAnalysisState",
    "DemographicsOutput",
    "ScenariosOutput",
    "AdviceOutput",
    "VerdictOutput",
]
```

- [ ] **Step 7: 运行验证**

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from workflow_product_analysis.product_agent import build_product_analysis_graph, demographics_node, scenarios_node, advice_node, verdict_node; print('OK')"`
Expected: `OK`（无 import 错误）

- [ ] **Step 8: 提交**

```bash
git add server/workflow_product_analysis/product_agent/nodes/ server/workflow_product_analysis/product_agent/__init__.py
git commit -m "refactor(product_agent): split nodes.py into individual node files

- Create nodes/ directory with demographics_node.py, scenarios_node.py, advice_node.py, verdict_node.py
- Each node is now a standalone file with single responsibility
- Update product_agent/__init__.py to import from nodes/ package

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 重命名 `run_product_analysis_agent` → `build_product_analysis_graph`

**Files:**
- Modify: `server/workflow_product_analysis/product_agent/graph.py`
- Verify: `server/workflow_product_analysis/product_agent/__init__.py`（已在上个任务更新）

- [ ] **Step 1: 修改 `product_agent/graph.py` — 重命名函数**

找到 `run_product_analysis_agent` 函数定义，重命名为 `build_product_analysis_graph`。

当前代码（第 55 行附近）：
```python
async def run_product_analysis_agent(
    ingredients: list[IngredientInput],
    settings,
) -> dict:
```

改为：
```python
def build_product_analysis_graph(settings) -> StateGraph:
    """
    Build and return the compiled product analysis LangGraph.

    Args:
        settings: Application settings (contains LLM model configs)

    Returns:
        Compiled StateGraph ready for ainvoke()
    """
```

注意：`build_product_analysis_graph` 是**同步**函数，返回编译后的 `StateGraph`。实际 `ainvoke` 在 API 层调用。

- [ ] **Step 2: 更新 `product_agent/graph.py` — 移除 `run_product_analysis_agent` 的 async wrapper**

当前 `run_product_analysis_agent` 是一个 async 函数封装。重构后只保留 `build_product_analysis_graph`（同步，返回编译好的 graph）。`ainvoke` 在 API 层执行。

如果当前文件中 `run_product_analysis_agent` 调用 `build_product_analysis_graph`，删除 wrapper 层。如果当前文件直接构建 graph，则确保 `build_product_analysis_graph` 返回 `graph.compile()`。

- [ ] **Step 3: 验证**

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from workflow_product_analysis.product_agent import build_product_analysis_graph; g = build_product_analysis_graph(None); print(type(g))"`
Expected: `<class 'langgraph.graph.state.StateGraph'>`

- [ ] **Step 4: 提交**

```bash
git add server/workflow_product_analysis/product_agent/graph.py
git commit -m "refactor(product_agent): rename run_product_analysis_agent -> build_product_analysis_graph

- Synchronous function returning compiled StateGraph
- ainvoke called by API layer, not inside this module

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 复制迁出文件到 `api/analysis/`

**Files:**
- Create: `server/api/analysis/ocr_client.py`
- Create: `server/api/analysis/ingredient_parser.py`
- Create: `server/api/analysis/food_resolver.py`
- Create: `server/api/analysis/ingredient_matcher.py`
- Create: `server/api/analysis/assembler.py`

- [ ] **Step 1: 复制 `ocr_client.py`**

从 `server/workflow_product_analysis/ocr_client.py` 完整复制到 `server/api/analysis/ocr_client.py`（内容不变）。

- [ ] **Step 2: 复制 `ingredient_parser.py`**

从 `server/workflow_product_analysis/ingredient_parser.py` 完整复制到 `server/api/analysis/ingredient_parser.py`（内容不变）。

- [ ] **Step 3: 复制 `food_resolver.py`**

从 `server/workflow_product_analysis/food_resolver.py` 完整复制到 `server/api/analysis/food_resolver.py`（内容不变）。

- [ ] **Step 4: 复制 `ingredient_matcher.py`**

从 `server/workflow_product_analysis/ingredient_matcher.py` 完整复制到 `server/api/analysis/ingredient_matcher.py`（内容不变）。

- [ ] **Step 5: 复制 `assembler.py`**

从 `server/workflow_product_analysis/assembler.py` 完整复制到 `server/api/analysis/assembler.py`（内容不变）。

- [ ] **Step 6: 提交**

```bash
git add server/api/analysis/ocr_client.py server/api/analysis/ingredient_parser.py server/api/analysis/food_resolver.py server/api/analysis/ingredient_matcher.py server/api/analysis/assembler.py
git commit -m "refactor(api/analysis): migrate files from workflow_product_analysis

- Copy ocr_client, ingredient_parser, food_resolver, ingredient_matcher, assembler to api/analysis/
- These files handle DB/HTTP operations; will be called by api/analysis/service.py

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 重写 `api/analysis/service.py` 编排逻辑

**Files:**
- Modify: `server/api/analysis/service.py`

- [ ] **Step 1: 重写 `service.py`**

完整重写 `server/api/analysis/service.py`：

```python
"""Analysis orchestration service — coordinates OCR, parsing, DB ops, and LLM agent."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.assembler import assemble_from_agent_output, assemble_from_db_cache
from api.analysis.food_resolver import InvalidFoodIdError, resolve_food_id
from api.analysis.ingredient_matcher import match_ingredients
from api.analysis.ingredient_parser import NoIngredientsFoundError, parse_ingredients
from api.analysis.models import FeedbackRequest, FeedbackResponse
from api.analysis.ocr_client import OcrServiceError, run_ocr
from config import Settings
from database.models import AnalysisFeedback
from db_repositories.product_analysis import ProductAnalysisRepository
from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState
from workflow_product_analysis.types import IngredientInput

if TYPE_CHECKING:
    import redis.asyncio as redis


class AnalysisError(Exception):
    """通用分析错误（不区分具体类型，供 router 捕获转换为 HTTP 状态码）。"""
    def __init__(self, message: str, http_status: int = 500):
        super().__init__(message)
        self.http_status = http_status


class TaskNotFoundError(Exception):
    pass


async def start_analysis(
    image_bytes: bytes,
    food_id: int | None,
    background_tasks: BackgroundTasks,
    redis: "redis.Redis",
    session: AsyncSession,
    settings: Settings,
) -> str:
    """
    启动异步分析任务，立即返回 task_id。
    实际分析在后台 BackgroundTasks 中执行。
    """
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_analysis_in_background,
        task_id=task_id,
        image_bytes=image_bytes,
        explicit_food_id=food_id,
        redis=redis,
        session=session,
        settings=settings,
    )
    return task_id


async def run_analysis_in_background(
    task_id: str,
    image_bytes: bytes,
    explicit_food_id: int | None,
    redis: "redis.Redis",
    session: AsyncSession,
    settings: Settings,
) -> None:
    """
    后台分析管道（由 BackgroundTasks 调用）。
    不返回结果，结果写入 Redis 后由 SSE/轮询端点推送。
    """
    try:
        result = await run_analysis_sync(
            image_bytes=image_bytes,
            explicit_food_id=explicit_food_id,
            session=session,
            settings=settings,
        )
        # TODO: SSE推送结果（后续实现）
        # 目前仅写 Redis，后续 SSE 改造时在此处触发
    except Exception as e:
        # TODO: 错误处理写入 Redis（后续 SSE 改造时统一处理）
        pass


async def run_analysis_sync(
    image_bytes: bytes,
    explicit_food_id: int | None,
    session: AsyncSession,
    settings: Settings,
) -> dict:
    """
    同步分析管道（可直接调用，跳过 BackgroundTasks）。
    返回完整 ProductAnalysisResult。
    """
    # ① OCR
    ocr_text = await run_ocr(image_bytes, settings)

    # ② 解析成分
    try:
        parse_result = await parse_ingredients(ocr_text, settings)
    except NoIngredientsFoundError:
        raise AnalysisError("无法从图片中提取到配料表", http_status=422)

    # ③ resolve_food_id
    try:
        resolved_food_id = await resolve_food_id(
            explicit_food_id=explicit_food_id,
            product_name=parse_result.product_name,
            task_id=str(uuid.uuid4()),
            session=session,
            settings=settings,
        )
    except InvalidFoodIdError:
        raise AnalysisError("food_id 无效或不存在", http_status=400)

    # ④ 成分匹配
    match_result = await match_ingredients(parse_result.ingredients, session)

    # ⑤ 构建 ingredient_inputs（含 level、safety_info）
    from api.analysis.ingredient_matcher import fetch_ingredient_details
    ingredient_inputs: list[IngredientInput] = []
    matched_ids: list[int] = []
    for m in match_result.matched:
        details = await fetch_ingredient_details(m["ingredient_id"], session)
        if details is None:
            continue
        name_db, category_str, level = details
        ingredient_inputs.append(IngredientInput(
            ingredient_id=m["ingredient_id"],
            name=name_db,
            category=category_str,
            level=level,
            safety_info="",
        ))
        matched_ids.append(m["ingredient_id"])
    for name in match_result.unmatched:
        ingredient_inputs.append(IngredientInput(
            ingredient_id=0,
            name=name,
            category="",
            level="unknown",
            safety_info="",
        ))

    # ⑥ 查 ProductAnalysis 缓存
    product_analysis_repo = ProductAnalysisRepository(session)
    existing = await product_analysis_repo.get_by_food_id(resolved_food_id)
    if existing is not None:
        return await assemble_from_db_cache(
            product_analysis=existing,
            matched_ids=matched_ids,
            session=session,
        )

    # ⑦ Agent 分析
    try:
        graph = build_product_analysis_graph(settings)
        initial_state = ProductAnalysisState(
            ingredients=ingredient_inputs,
            demographics=None,
            scenarios=None,
            advice=None,
            verdict_level=None,
            verdict_description=None,
            references=None,
        )
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        raise ProductAgentError(f"Agent failed: {exc}") from exc

    # ⑧ 组装 + 写缓存
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
        matched_ids=matched_ids,
        unmatched_names=match_result.unmatched,
        session=session,
    )

    await product_analysis_repo.insert_if_absent(
        food_id=resolved_food_id,
        data={
            "ai_model": settings.DEFAULT_MODEL,
            "level": final_state.get("verdict_level", "t3"),
            "description": final_state.get("verdict_description", ""),
            "advice": final_state.get("advice", ""),
            "demographics": final_state.get("demographics", []),
            "scenarios": final_state.get("scenarios", []),
            "references": final_state.get("references", []),
        },
        created_by_user=settings.SYSTEM_USER_ID,
    )

    return result


async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    session: AsyncSession,
) -> FeedbackResponse:
    import hashlib

    client_ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest() if client_ip else None
    ua = request.headers.get("user-agent", "")[:512]

    record = AnalysisFeedback(
        task_id=req.task_id,
        food_id=req.food_id,
        category=req.category,
        message=req.message,
        client_context=req.client_context,
        reporter_user_id=None,
        source_ip_hash=ip_hash,
        user_agent=ua,
    )
    session.add(record)
    await session.flush()
    return FeedbackResponse(accepted=True)
```

**注意：** `assemble_from_agent_output` 的签名在当前 `assembler.py` 中是：
```python
async def assemble_from_agent_output(
    agent_output: dict[str, Any],
    matched_ids: list[int],
    session: AsyncSession,
) -> ProductAnalysisResult:
```
需要确认 `assembler.py` 中 `assemble_from_agent_output` 的实际签名，特别是 `matched_ids` 参数——在迁入后直接使用，**不需要改 assembler 的签名**。

- [ ] **Step 2: 验证 import**

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from api.analysis.service import start_analysis, run_analysis_sync, AnalysisError; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add server/api/analysis/service.py
git commit -m "refactor(api/analysis): rewrite service.py as orchestration layer

- run_analysis_sync: OCR -> parse -> resolve -> match -> agent -> assemble
- start_analysis: returns task_id, runs analysis in BackgroundTasks
- Caches ProductAnalysis by food_id

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 更新 `api/analysis/router.py` — 删除 status 端点

**Files:**
- Modify: `server/api/analysis/router.py`

- [ ] **Step 1: 修改 `router.py` — 删除 status 端点**

删除 `GET /{task_id}/status` 端点（及其 `get_task_status` import 和 `TaskNotFoundError` import）。保留 `POST /start` 和 `POST /feedback`。

更新后的 `router.py` 应为：

```python
"""FastAPI router for analysis endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.analysis.models import (
    FeedbackRequest,
    FeedbackResponse,
    StartAnalysisResponse,
)
from api.analysis.service import (
    start_analysis,
    submit_feedback,
)
from database.session import get_async_session
from workflow_product_analysis.redis_store import get_redis_client

router = APIRouter()


@router.post(
    "/start",
    response_model=StartAnalysisResponse,
    status_code=201,
    summary="启动产品分析",
)
async def api_start_analysis(
    background_tasks: BackgroundTasks,
    redis: Annotated[Redis, Depends(get_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    image: UploadFile = File(...),
    food_id: int | None = Form(default=None),
) -> StartAnalysisResponse:
    from config import settings as app_settings

    image_bytes = await image.read()
    task_id = await start_analysis(
        image_bytes=image_bytes,
        food_id=food_id,
        background_tasks=background_tasks,
        redis=redis,
        session=session,
        settings=app_settings,
    )
    return StartAnalysisResponse(task_id=task_id)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="提交分析反馈",
)
async def api_feedback(
    req: FeedbackRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FeedbackResponse:
    return await submit_feedback(req=req, request=request, session=session)
```

- [ ] **Step 2: 验证**

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from api.analysis.router import router; print([r.path for r in router.routes])"`
Expected: `['/start', '/feedback']`（无 `/{task_id}/status`）

- [ ] **Step 3: 提交**

```bash
git add server/api/analysis/router.py
git commit -m "refactor(api/analysis): remove GET /{task_id}/status endpoint

- Redis-based polling removed; async result delivery deferred to SSE implementation
- POST /start and POST /feedback remain

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 删除 `workflow_product_analysis/` 迁出文件

**Files:**
- Delete: `server/workflow_product_analysis/food_resolver.py`
- Delete: `server/workflow_product_analysis/ingredient_matcher.py`
- Delete: `server/workflow_product_analysis/assembler.py`
- Delete: `server/workflow_product_analysis/pipeline.py`
- Delete: `server/workflow_product_analysis/redis_store.py`
- Delete: `server/workflow_product_analysis/ocr_client.py`
- Delete: `server/workflow_product_analysis/ingredient_parser.py`

- [ ] **Step 1: 确认文件已迁移**

确认上述 7 个文件都已复制到 `api/analysis/` 目录，且 `api/analysis/service.py` 已正确引用它们。

- [ ] **Step 2: 删除文件**

```bash
git rm server/workflow_product_analysis/food_resolver.py \
        server/workflow_product_analysis/ingredient_matcher.py \
        server/workflow_product_analysis/assembler.py \
        server/workflow_product_analysis/pipeline.py \
        server/workflow_product_analysis/redis_store.py \
        server/workflow_product_analysis/ocr_client.py \
        server/workflow_product_analysis/ingredient_parser.py
```

- [ ] **Step 3: 验证 import 不受影响**

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from workflow_product_analysis.product_agent.graph import build_product_analysis_graph; print('OK')"`
Expected: `OK`

Run: `cd /Users/wwj/Desktop/self/life-classics/server && uv run python -c "from api.analysis.service import start_analysis; print('OK')"`
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git commit -m "refactor(workflow_product_analysis): remove migrated files, keep only pure compute

- Deleted: food_resolver, ingredient_matcher, assembler, pipeline, redis_store, ocr_client, ingredient_parser
- Module now contains only product_agent/ (LangGraph) + types.py

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 验证测试通过

**Files:**
- Modify: `server/tests/`（如有测试需要更新）

- [ ] **Step 1: 运行相关测试**

```bash
cd /Users/wwj/Desktop/self/life-classics/server
uv run pytest tests/api/test_product.py -v --tb=short
```

- [ ] **Step 2: 如有 import 错误，修复**

常见问题：
- `from workflow_product_analysis.pipeline import ...` → 移除或 mock
- `from workflow_product_analysis.redis_store import ...` → 移除
- `from workflow_product_analysis.ocr_client import ...` → 改为 `from api.analysis.ocr_client import ...`
- `from workflow_product_analysis.assembler import ...` → 改为 `from api.analysis.assembler import ...`
- `from workflow_product_analysis.ingredient_matcher import ...` → 改为 `from api.analysis.ingredient_matcher import ...`
- `from workflow_product_analysis.food_resolver import ...` → 改为 `from api.analysis.food_resolver import ...`
- `from workflow_product_analysis.ingredient_parser import ...` → 改为 `from api.analysis.ingredient_parser import ...`

- [ ] **Step 3: 验证 workflow_product_analysis 自身可 import**

```bash
uv run pytest tests/ -v --ignore=tests/api --ignore=tests/db_repositories --tb=short -k "product" 2>&1 | head -50
```

- [ ] **Step 4: 提交测试修复**

```bash
git add server/tests/...
git commit -m "test: fix imports after workflow_product_analysis refactor

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 实施后验证清单

- [ ] `from workflow_product_analysis.product_agent import build_product_analysis_graph` 无错误
- [ ] `from api.analysis.service import start_analysis, run_analysis_sync` 无错误
- [ ] `api/analysis/router.py` routes 为 `['/start', '/feedback']`
- [ ] `GET /analysis/{task_id}/status` 端点不存在
- [ ] `workflow_product_analysis/` 仅含：`product_agent/`、`types.py`、`__init__.py`
- [ ] `api/analysis/` 包含：`ocr_client.py`、`ingredient_parser.py`、`food_resolver.py`、`ingredient_matcher.py`、`assembler.py`、`service.py`、`router.py`、`models.py`
