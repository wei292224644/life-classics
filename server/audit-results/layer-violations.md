# L1-L4 分层违规审计报告（T1-T5 禁忌条款）

**审计范围**: `server/` — API 层（L1）、Service 层（应为 L2）、Repository 层（L3）
**规范文件**: `docs/architecture/server-architecture.md`
**审计日期**: 2026-04-02

---

## T1. 禁止 API 层执行业务逻辑

### T1-1: API Service 跨模块调用 Service（严重）

**文件**: `server/api/ingredients/service.py`
**行号**: 107

```python
from api.ingredient_analysis.service import IngredientAnalysisService  # 函数内部导入
svc = IngredientAnalysisService(session)
```

**问题**: `IngredientService`（位于 `api/ingredients/`）直接实例化并调用 `IngredientAnalysisService`（位于 `api/ingredient_analysis/`）。这是跨子模块的 Service 调用，违反了 API Service 只做参数组装和委托的原则。业务编排逻辑（触发分析并写入结果）应上浮至 Router 层或下沉至 L2 Service。

---

### T1-2: API Service 直接执行 SQL 查询（严重）

**文件**: `server/api/ingredient_alias/service.py`
**行号**: 33-34

```python
result = await self._session.execute(
    select(Ingredient).where(Ingredient.id == ingredient_id)
)
```

**问题**: `IngredientAliasService`（L1）在内部直接执行 SQL `select(Ingredient)` 查询，而非通过 `IngredientRepository`（L3）。这绕过了 Repository 层，违反了"API 层禁止 SQL/Hybrid 查询构造"的禁忌。

**正确做法**: 应在 `IngredientAliasRepository` 中添加 `find_by_id()` 方法（或新增 `IngredientRepository` 方法），然后在 Service 层调用 repository。

---

### T1-3: API Service 自行管理 Session 与 Commit（严重）

**文件**: `server/api/ingredient_alias/service.py`
**行号**: 44, 69

```python
await self._session.commit()  # 行 44（create_alias）
await self._session.commit()  # 行 69（delete_alias）
```

**问题**: 根据架构，Session 由 Router 层通过 `Depends` 注入，Session 的创建和提交应在 L1（Router）完成，不应在 Service 层自行 `commit()`。这同时违反了 T1（API 层业务逻辑）和 T5（Session 自管理）的双重禁忌。

**对比正确示范**: `api/product/service.py` 中的 `ProductService` 仅接收 repository，从不触碰 `session.commit()`。

---

## T2. 禁止跨层逆向调用

### T2-1: L1 调用另一个 L1（跨子模块 Service 调用）

**文件**: `server/api/ingredients/service.py` 第 107 行（见 T1-1）

`IngredientService`（`api/ingredients/`）调用 `IngredientAnalysisService`（`api/ingredient_analysis/`），同属 L1 但跨子模块调用，违反了"L1 → L2 → L3"的单向调用链。

**影响**: 破坏了层级边界，使得 `api/ingredient_analysis/` 的实现细节直接暴露给 `api/ingredients/`。

---

## T3. 禁止循环依赖

**结论**: 未发现循环依赖。

各包间 import 链检查：
- `api/analysis/service.py` → `api/analysis/{assembler,food_resolver,ingredient_matcher}`（同包内部引用，均为 L1 内部模块）
- `api/ingredients/service.py` → `db_repositories/`（单向，无反向引用）
- `db_repositories/*` → `database/models`（单向，无反向引用）
- `services/` 目录不存在（当前代码库没有独立 L2 层）

---

## T4. 禁止 Assembler/Serializer 访问 DB

### T4-1: Assembler 直接执行 SQL 查询（严重）

**文件**: `server/api/analysis/assembler.py`
**行号**: 32-34, 66, 96, 105-107, 149-152

```python
# _build_ingredients_list() 中
result = await session.execute(
    select(Ingredient).where(Ingredient.id.in_(matched_ids))
)

# _build_alternatives() 中
analysis = await repo.get_active_by_ingredient_id(ing_id)

# assemble_from_db_cache() 中
analysis = await analysis_repo.get_active_by_ingredient_id(...)
```

**问题**: `assembler.py` 名为"结果组装器"（负责将各阶段产物组装为响应模型），但其内部的 `_build_ingredients_list()`、`_build_alternatives()`、`assemble_from_db_cache()`、`assemble_from_agent_output()` 都在直接执行 DB 查询。这完全违背了 Assembler "只接收已查询的数据模型做序列化"的设计原则。

**根本原因**: `assemble_from_agent_output()` 和 `assemble_from_db_cache()` 是由 `api/analysis/service.py` 的 `run_analysis_sync()` 调用的，此时 session 已经可用，调用者直接传入了 session，导致 Assembler 可以"顺手"查询 DB。这是一个架构设计缺陷——Service 层应先查好所有数据，再将结果传给 Assembler 做纯组装。

---

## T5. 禁止 Session 在 Service 层自管理

### T5-1: API Service 内手动创建 Session（严重）

**文件**: `server/api/ingredients/service.py`
**行号**: 106, 139

```python
from database.session import get_async_session_cm

async def _run_workflow():
    ...
    async with get_async_session_cm() as session:  # 行 139
        svc = IngredientAnalysisService(session)
        await svc.create(ingredient_id, write_payload)
```

**问题**: `trigger_analysis()` 在后台任务内自行创建 session（`get_async_session_cm()`），而非从 Router 层通过参数注入。这违反了"Session 由 Router 层通过 Depends 注入，Service 接收 Session 参数"的标准范式。

**对比正确示范**: `api/analysis/service.py` 中的 `run_analysis_sync()` 正确接收 `session: AsyncSession` 作为参数。

---

## 总结

| 禁忌 | 违规数 | 严重程度 |
|------|--------|----------|
| T1: API 层执行业务逻辑 | 3 | 高 |
| T2: 跨层逆向调用 | 1 | 高 |
| T3: 循环依赖 | 0 | — |
| T4: Assembler 访问 DB | 1 | 高 |
| T5: Session 自管理 | 1 | 高 |

**核心问题**: 当前 `server/` 代码没有独立的 L2 Service 层（`services/` 目录不存在），所有业务逻辑要么堆在 `api/*/service.py`（实为 L1），要么堆在 `api/analysis/` 的辅助模块（`assembler.py`、`food_resolver.py`、`ingredient_matcher.py`）中。这些 L1 文件承担了 L2/L3 的职责，导致分层形同虚设。

**最优先修复项**:
1. `api/analysis/assembler.py` — 移除所有 SQL 查询，改为纯数据组装
2. `api/ingredient_alias/service.py` — 移除 SQL 查询和 `commit()`，通过 Repository 操作
3. `api/ingredients/service.py` — 移除 `get_async_session_cm()` 自管理 session，将跨模块调用上浮至 Router 层
