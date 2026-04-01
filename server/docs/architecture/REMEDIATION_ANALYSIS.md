# 架构违规修复分析文档

**版本**: v1.0
**日期**: 2026-04-01
**基于**: `server/docs/architecture/ARCHITECTURE_STANDARDS.md v1.0`
**审计结果**: 4 类 10+ 处违规

---

## 1. T1 — API Service 跨模块调用

### 违规详情

| 文件 | 行号 | 违规代码 |
|------|------|----------|
| `api/ingredients/service.py` | 107 | `from api.ingredient_analysis.service import IngredientAnalysisService` |

### 根因分析

`IngredientService.trigger_analysis()` 内部直接实例化了另一个 API Service (`IngredientAnalysisService`)：

```python
# api/ingredients/service.py:104-141
async def _run_workflow():
    from api.ingredient_analysis.service import IngredientAnalysisService  # ← 违规

    async with get_async_session_cm() as session:
        svc = IngredientAnalysisService(session)  # ← 违规
        await svc.create(ingredient_id, write_payload)
```

### 修复方案

**问题本质**: `IngredientAnalysisService` 的 `create()` 方法本质是 L3（写数据库），不应位于 `api/` 命名空间下。

**建议修复**:
1. 将 `IngredientAnalysisService.create()` 的数据写入逻辑下沉到 `db_repositories/ingredient_analysis.py` 的 `IngredientAnalysisRepository`
2. `IngredientService.trigger_analysis()` 改为调用 `IngredientAnalysisRepository`，不再引用任何 `api.*.service`
3. 将 `trigger_analysis()` 的后台工作流执行移到独立的 `services/analysis_executor.py`（L2）

**修复后依赖方向**:
```
IngredientService (L2)
  → IngredientAnalysisRepository (L3)
  → workflow_ingredient_analysis (Infra, via interface)
```

---

## 2. T1 — Session 自管理

### 违规详情

| 文件 | 行号 | 违规代码 |
|------|------|----------|
| `api/ingredients/service.py` | 106, 139 | `from database.session import get_async_session_cm`<br>`async with get_async_session_cm() as session:` |

### 根因分析

Service 层绕过了 Router 的依赖注入，自行创建 Session：

```python
# 当前违规写法
async with get_async_session_cm() as session:  # Service 层自建 Session
    svc = IngredientAnalysisService(session)
    await svc.create(ingredient_id, write_payload)
```

### 修复方案

**G2 (Session 注入标准) 要求**:
```python
# Router 层通过 Depends 注入 Session
async def trigger_analysis(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    service: Annotated[IngredientService, Depends(get_ingredient_service)],
):
    return await service.trigger_analysis(session, ingredient_id, background_tasks)
```

**修复后写法**:
```python
# Service 层接收 injected session
async def trigger_analysis(self, session: AsyncSession, ingredient_id: int, background_tasks) -> dict:
    # Session 由 Router 管理生命周期，Service 只使用
    async with session.begin():  # 或使用 existing transaction
        repo = IngredientAnalysisRepository(session)
        await repo.insert_new_version(...)
```

**注意**: 当前问题还混合了「跨模块调用」，两个问题需同时修复（见上方修复方案 1）。

---

## 3. T2 — L1 直接引用 Infra

### 违规详情

| 文件 | 引用内容 | 违规类型 |
|------|----------|----------|
| `api/documents/service.py:9-12` | `kb.clients`, `kb.writer`, `workflow_parser_kb.graph` | L1 → Infra |
| `api/chunks/service.py:14-21` | `kb.*`, `workflow_parser_kb.*` | L1 → Infra |
| `api/ingredients/service.py:105` | `workflow_ingredient_analysis.entry` | L1 → Infra |
| `api/analysis/ingredient_matcher.py:16-19` | `workflow_product_analysis.types` | L1 → Infra |
| `api/analysis/assembler.py:10` | `database.models` | L1 → L4 (via assembler) |
| `api/analysis/ingredient_parser.py:6-7` | `config.Settings`, `workflow_parser_kb.structured_llm` | L1 → Infra |
| `api/analysis/models.py:8-11` | `workflow_product_analysis.types` | L1 → Infra |
| `api/analysis/service.py:17,20-25` | `config.Settings`, `workflow_product_analysis.*` | L1 → Infra |

### 分类处置

#### A. `api/*/service.py` 直接引用 Infra（最严重）

**处置**: 创建 `services/` 目录，将 kb/workflow 操作上浮到 L2：

```
services/
├── kb/
│   ├── documents_service.py    # ← ChromaDB + FTS 写操作
│   └── chunks_service.py       # ← ChromaDB 查询操作
└── analysis/
    └── workflow_executor.py    # ← workflow_ingredient_analysis 封装
```

**api/documents/service.py** → 改为委托 `services/kb/documents_service.py`
**api/chunks/service.py** → 改为委托 `services/kb/chunks_service.py`
**api/ingredients/service.py** → 改为委托 `services/analysis/workflow_executor.py`

#### B. `api/analysis/` 子模块引用 Infra（次严重）

**处置**: `api/analysis/` 下的模块（assembler, food_resolver, ingredient_matcher, ingredient_parser）是分析管道的内部组件，本质是 L2 的内部实现细节。可以有两种处置方式：

**方案 A（激进）**: 全部迁移到 `services/analysis/` 下，彻底移除 `api/analysis/` 的业务逻辑
**方案 B（保守）**: 将 `api/analysis/` 视为一个内聚模块"分析服务模块"，但这需要重新定义架构规范的层级边界

**建议**: 方案 A（见下方「重新划分的模块边界建议」）

#### C. `api/analysis/models.py` 引用 `workflow_product_analysis.types`

**处置**: 将 `workflow_product_analysis.types` 的类型定义迁移到 `api/analysis/models.py` 或共享的 `shared/dto.py`，打破 `api/` 对 `workflow_*` 的直接依赖。

---

## 4. T4 — Assembler 访问 DB

### 违规详情

| 文件 | 行号 | 违规代码 |
|------|------|----------|
| `api/analysis/assembler.py` | 10 | `from database.models import Ingredient, ProductAnalysis` |
| `api/analysis/assembler.py` | 32-34 | `await session.execute(select(Ingredient).where(...))` |

### 根因分析

Assembler 做了本不属于它的数据访问工作：

```python
# api/analysis/assembler.py:32-34
result = await session.execute(
    select(Ingredient).where(Ingredient.id.in_(matched_ids))  # ← L3 操作
)
```

### 修复方案

**两种路径**:

**路径 A（推荐）**: 数据在 Service 层预加载后传入 Assembler
```python
# api/analysis/service.py (L2)
ingredients = await ingredient_repo.fetch_by_ids(matched_ids, session)
result = assemble_from_agent_output(ingredients, agent_output)  # 纯组装
```

**路径 B**: 彻底移除 Assembler，合并到 Service 层
```python
# api/analysis/service.py
return ProductAnalysisResult(...)
```

**建议路径 A**。Assembler 保留但改为纯转换函数，不持有 session、不查 DB。

---

## 重新划分的模块边界建议

当前 `api/analysis/` 是一个混乱的模块，混合了：
- Router (`api/analysis/router.py`)
- Service (`api/analysis/service.py`)
- L3 数据访问伪装成 Assembler (`api/analysis/assembler.py`)
- Workflow 封装 (`food_resolver`, `ingredient_matcher`, `ingredient_parser`)
- 外部类型引用 (`workflow_product_analysis.types`)

**建议重构后的清晰边界**:

```
api/analysis/
├── router.py              # L1: HTTP 入口
├── models.py              # L1: DTO 定义
└── schemas.py            # L1: 请求/响应模型

services/analysis/         # 新增 L2 目录
├── analysis_service.py    # 业务编排
├── ingredient_matcher.py  # 成分匹配逻辑
├── food_resolver.py       # 食品解析逻辑
└── assembler.py           # 数据组装（不查 DB）

db_repositories/           # L3: 数据访问
├── ingredient_analysis.py
└── ...
```

---

## 修复优先级

| 优先级 | 违规 | 修复工作量 | 风险 |
|--------|------|------------|------|
| P0 | `api/ingredients/service.py` 跨模块调用 + Session 自管理 | 低 | 低（局部） |
| P0 | `api/analysis/assembler.py` 访问 DB | 中 | 中（涉及数据流重构） |
| P1 | `api/*/service.py` → Infra 直接引用 | 高 | 高（涉及新建 services/ 目录） |
| P1 | `api/analysis/models.py` → `workflow_product_analysis.types` | 低 | 低（只需移动类型定义） |

---

## 总结

| 违规编号 | 违规描述 | 修复方向 |
|----------|----------|----------|
| T1-1 | `api/ingredients/service.py` 跨模块调用 | 下沉到 Repository |
| T1-2 | `api/ingredients/service.py` Session 自管理 | 改用 Router 注入 |
| T2-1 | `api/documents/service.py` → Infra | 新建 `services/kb/documents_service.py` |
| T2-2 | `api/chunks/service.py` → Infra | 新建 `services/kb/chunks_service.py` |
| T2-3 | `api/ingredients/service.py` → Infra | 新建 `services/analysis/workflow_executor.py` |
| T2-4 | `api/analysis/` 多文件 → Infra | 重构分析服务模块边界 |
| T4 | `api/analysis/assembler.py` 访问 DB | 预加载数据后传入 Assembler |
