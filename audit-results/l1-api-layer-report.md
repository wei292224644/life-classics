# L1 API Layer 架构合规审查报告

**审查日期**: 2026-04-02
**审查范围**: `server/api/`
**依据文档**: `docs/architecture/server-architecture.md` (v1.0)

---

## 约束清单

- **[约束T1]** 禁止API层执行业务逻辑
- **[约束T4]** 禁止Assembler访问DB
- **[约束T5]** 禁止Session自管理
- **[约束L1→Infra]** 禁止直接引用基础设施层（kb/llm/workflow_\*/）

---

## 违规项

### 违规1: `server/api/analysis/food_resolver.py:50-56,66-72` - [约束T1] + [约束L1→Infra]

```python
result = await session.execute(
    select(Food).where(
        Food.id == explicit_food_id,
        Food.deleted_at.is_(None),
    )
)
```

**原因**: `food_resolver.py` 位于 `api/analysis/` 包内（L1层），却执行直接 SQL 查询（`session.execute(select(...))`），属于典型的 L3/Repository 逻辑混入 L1。此外，该文件还通过 `from database.models import Food` 违反了 L1 禁止引用 database/ 的约束。

---

### 违规2: `server/api/analysis/ingredient_matcher.py:84-86,95-96` - [约束T1] + [约束L1→Infra]

```python
result = await session.execute(
    select(Ingredient).where(Ingredient.id == ingredient_id)
)
# ...
analysis_repo = IngredientAnalysisRepository(session)
analysis = await analysis_repo.get_active_by_ingredient_id(ingredient_id)
```

**原因**: `ingredient_matcher.py` 在 L1 层直接执行 SQL 查询（`session.execute(select(...))`），并在 L1 层直接实例化 L3 Repository (`IngredientAnalysisRepository`)。这是典型的业务逻辑下推到 L1。

---

### 违规3: `server/api/ingredients/service.py:142-167` - [约束T5]

```python
async def _run_ingredient_analysis_workflow(
    ingredient_dict: dict,
    ingredient_id: int,
    task_id: str,
):
    """后台任务：运行配料分析 workflow 并写入结果."""
    from database.session import get_async_session_cm
    # ...
    async with get_async_session_cm() as session:  # ← T5 违规
        svc = IngredientAnalysisService(session)
        await svc.create(ingredient_id, write_payload)
```

**原因**: `_run_ingredient_analysis_workflow` 函数虽然在注释中声称"此函数由 BackgroundTasks.add_task() 调用，运行于请求周期之外，因此自行管理 session 生命周期，不违反 T5 规则"，但该函数定义在 `api/ingredients/service.py` 内，属于 L1 代码。无论运行上下文如何，L1 代码禁止自行管理 Session 生命周期。

---

### 违规4: `server/api/analysis/service.py:94-223` - [约束T1]

```python
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
    resolved_food_id = await resolve_food_id(...)
    # ④ 成分匹配
    match_result = await match_ingredients(parse_result.ingredients, session)
    # ⑤ 构建 ingredient_inputs
    # ⑥ 预查 Ingredient 和 IngredientAnalysis 数据
    # ⑦ 查 ProductAnalysis 缓存
    # ⑧ Agent 分析
    svc = _get_product_analysis_svc()
    final_state = await svc.run_product_analysis(ingredient_inputs)
    # ⑨ 组装 + 写缓存
    await product_analysis_repo.insert_if_absent(...)
```

**原因**: `run_analysis_sync` 是完整的业务编排逻辑（OCR → 解析 → 查DB → 成分匹配 → Agent分析 → 写缓存），这属于 L2 Service 层职责，却被放置在 L1 的 `api/analysis/service.py` 中。这违反了 L1 的边界约束：**L1 只做 HTTP 入口、路由、参数校验、响应序列化**。

---

### 违规5: `server/api/analysis/assembler.py:7-11` - [约束L1→Infra]

```python
from workflow_product_analysis.types import (
    AlternativeItem,
    IngredientItem,
    ProductAnalysisResult,
)
```

**原因**: `assembler.py` 直接导入 `workflow_product_analysis.types`（infra 层），违反了 L1 禁止直接引用基础设施层的约束。Assembler 应只接收已序列化的数据模型。

---

### 违规6: `server/api/analysis/models.py:8-12` - [约束L1→Infra]

```python
from workflow_product_analysis.types import (
    AnalysisError,
    AnalysisStatus,
    ProductAnalysisResult,
)
```

**原因**: API 的 Pydantic Request/Response 模型直接引用了 infra 层的 `workflow_product_analysis.types`。这意味着 infra 层的类型定义变化会直接影响 L1 的接口模型，违反了分层隔离原则。

---

### 违规7: `server/api/analysis/ingredient_parser.py:7` - [约束L1→Infra]

```python
from workflow_parser_kb.structured_llm.client_factory import get_structured_client
```

**原因**: L1 的 `ingredient_parser.py` 直接导入并调用 `workflow_parser_kb`（infra 层）的 `get_structured_client`。这是 L1 直接调用 infra 的明确违规。

---

### 违规8: `server/api/analysis/ingredient_matcher.py:16-20` - [约束L1→Infra]

```python
from workflow_product_analysis.types import (
    IngredientRiskLevel,
    MatchedIngredient,
    MatchResult,
)
```

**原因**: L1 模块直接导入 workflow infra 类型。

---

### 违规9: `server/api/analysis/service.py:129` - [约束L1→Infra]

```python
from workflow_product_analysis.types import IngredientInput
```

**原因**: 在 L1 的 service 函数内部导入 infra 类型，但函数本身位于 L1（`api/analysis/service.py`）。

---

### 违规10: `server/api/ingredients/service.py:144` - [约束L1→Infra]

```python
from workflow_ingredient_analysis.entry import run_ingredient_analysis
```

**原因**: L1 的 `_run_ingredient_analysis_workflow` 函数直接调用 `workflow_ingredient_analysis` infra 模块。

---

## 合规项（显著发现）

- `server/api/kb/service.py` - **合规**：通过 `L2KBService` 委托执行，完全符合 L1 边界，仅做路由编排。
- `server/api/chunks/service.py` - **基本合规**：通过 `KBService` (L2) 和 `ParserWorkflowService` (L2) 代理操作，未直接访问 infra。
- `server/api/product/service.py` - **合规**：仅做数据组装，委托 `FoodRepository` (L3) 执行 DB 操作。
- `server/api/ingredient_alias/service.py` - **合规**：委托 `IngredientAliasRepository` (L3) 执行数据操作。
- `server/api/ingredient_analysis/service.py` - **合规**：委托 `IngredientAnalysisRepository` (L3) 执行数据操作。

---

## 违规分类统计

| 违规编号 | 文件 | 行号 | 约束类型 |
|---------|------|------|----------|
| 1 | `analysis/food_resolver.py` | 50-56, 66-72 | T1 + L1→Infra |
| 2 | `analysis/ingredient_matcher.py` | 84-86, 95-96 | T1 + L1→Infra |
| 3 | `ingredients/service.py` | 165 | T5 |
| 4 | `analysis/service.py` | 94-223 | T1 |
| 5 | `analysis/assembler.py` | 7-11 | L1→Infra |
| 6 | `analysis/models.py` | 8-12 | L1→Infra |
| 7 | `analysis/ingredient_parser.py` | 7 | L1→Infra |
| 8 | `analysis/ingredient_matcher.py` | 16-20 | L1→Infra |
| 9 | `analysis/service.py` | 129 | L1→Infra |
| 10 | `ingredients/service.py` | 144 | L1→Infra |

---

## 总结

- **违规数量**: 10 项（涉及 5 个文件）
- **严重程度**:
  - **高** (阻断): 违规4 (`run_analysis_sync` 在 L1 执行业务编排) - 核心架构混乱
  - **高** (阻断): 违规1、2 (`food_resolver.py`、`ingredient_matcher.py` 在 L1 直接操作 DB) - L1/L3 边界完全混淆
  - **中** (严重): 违规3 (`get_async_session_cm` 在 L1 自管理 Session) - T5 硬性禁令
  - **低** (累积): 违规5-10 (L1 直接引用 infra 层) - 长期导致系统耦合

### 核心问题

`server/api/analysis/` 包是本次审查的重灾区。该包实际上混合了：
1. **L1 组件**：HTTP 入口、路由定义（`router.py`）
2. **L2 组件**：`service.py` 中的 `run_analysis_sync`（业务编排）
3. **L3 组件**：`food_resolver.py`、`ingredient_matcher.py`（数据访问）
4. **infra 组件**：直接导入 `workflow_*` 模块

这导致 `api/analysis/` 承担了 L1 + L2 + L3 + 部分 Infra 的所有职责，完全违背了分层架构原则。

### 修复建议优先级

1. **P0**: 将 `run_analysis_sync` 及其依赖的 `food_resolver.py`、`ingredient_matcher.py` 移入 `services/` (L2)
2. **P0**: 将 `_run_ingredient_analysis_workflow` 的 Session 管理移出 L1
3. **P1**: 移除 L1 对 `workflow_product_analysis`、`workflow_parser_kb` 的直接导入，改为通过 L2 Service 接口调用
4. **P2**: `assembler.py` 的 Pydantic 模型不应引用 infra 类型，需在 L1 定义独立的 Response 模型
