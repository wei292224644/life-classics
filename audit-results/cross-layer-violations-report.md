# 跨层依赖与循环依赖 检测报告

**审查范围**: `server/` Python FastAPI 后端
**审查标准**: `docs/architecture/server-architecture.md` v1.0
**审查日期**: 2026-04-02

---

## T3 循环依赖

### api/ 内部循环
**无循环依赖。** api/ 子目录之间通过 `api/__init__.py` 聚合路由，不存在 `api.a → api.b → api.a` 形式的直接循环导入。

### services/ 内部循环
**无循环依赖。** `services/` 下各 service 文件之间无互相 import 关系：
- `services/kb_service.py` → 仅引用 `kb/` (infra)
- `services/parser_workflow_service.py` → 仅引用 `workflow_parser_kb/` (infra)
- `services/agent_service.py` → 仅引用 `agent/` (infra)
- `services/product_analysis_service.py` → 仅引用 `workflow_product_analysis/` (infra)

---

## T2 跨层逆向调用

### L2 → L1 调用
**无。** `services/` (L2) 不存在对 `api/` (L1) 的 import。

### L3 → L2 调用
**无。** `db_repositories/` (L3) 不存在对 `services/` (L2) 的 import。

### Infra → L2 调用（架构边界）
`kb/` (infra) 不引用 `services/` (L2)，边界清晰。

---

## T1 禁止 API 层执行业务逻辑

### 核心违规：api/ 目录下的 Service 类实为 L2 编排层

以下 `api/xxx/service.py` 文件按架构规范应属于 **L2 层**，却放置于 `api/` (L1) 包中，并执行跨模块 Service 调用：

| 文件 | 违规描述 | 严重程度 |
|------|----------|----------|
| `api/documents/service.py` | `DocumentsService` 内部直接调用 `KBService` (L2) 和 `ParserWorkflowService` (L2) 的方法，如 `upload_chunks()`、`run_parse_workflow()`，属于 L1 跨模块 Service 调用 | **高** |
| `api/chunks/service.py` | `ChunksService` 内部直接调用 `KBService` 和 `ParserWorkflowService`，执行 `embed_batch()`、`upsert_chunks()`、`reparse_chunk()` 等业务编排 | **高** |
| `api/analysis/service.py` | `run_analysis_sync()` 函数执行完整产品分析管道（OCR → 成分解析 → 匹配 → Agent → 缓存），内部通过 module-level singleton 调用 `ProductAnalysisService` (L2)，属于 L1 执行业务逻辑 | **高** |
| `api/ingredients/service.py` | `IngredientService` 内部 `_run_ingredient_analysis_workflow` 函数（line 143）import `IngredientAnalysisService`（同为 L1 的 service），并在函数内自行管理 session (`get_async_session_cm`)，违反 T5 | **中** |
| `api/ingredient_alias/service.py` | `IngredientAliasService` 直接调用 `IngredientAliasRepository` (L3)，虽为薄封装但仍属于 L1 执行业务逻辑（非纯粹的参数组装） | **低** |
| `api/kb/service.py` | `KBApiService` 直接委托 `KBService` (L2)，属于 L1 → L2 的 thin wrapper，尚在可接受范围 | **低** |

### 违规模式分析

**T1 禁止模式**：
```
api/xxx/service.py（应在 L1，职责为参数组装）
    ↓ 跨模块调用（违规）
services/kb_service.py（真正 L2）
    ↓
kb/（Infra）
```

`api/documents/service.py` 和 `api/chunks/service.py` 的正确做法应是：Router (L1) → Service (L2，搬到 `services/` 下) → Repository (L3)。当前这两者都在 L1 层做了 L2 的编排工作。

---

## T5 禁止 Session 在 Service 层自管理

### 违规实例

**`api/ingredients/service.py:165`**
```python
async with get_async_session_cm() as session:   # ← T5 违规
    svc = IngredientAnalysisService(session)
    await svc.create(ingredient_id, write_payload)
```
此函数为后台任务 (`_run_ingredient_analysis_workflow`)，注释说明"由 BackgroundTasks.add_task() 调用，运行于请求周期之外，因此自行管理 session 生命周期"。

**评估**：虽然后台任务场景下自行创建 session 是实践中的常见做法，但 T5 的本意是禁止在 Service 层管理 Session。上述代码在 `api/ingredients/service.py`（属于 api/ L1 包）而非 `services/` L2 包中，更偏离了规范意图。

---

## 调用方向矩阵

```
         L1 api/   L2 services/   L3 db_repos/   L4 database/   Infra kb/llm/
L1 api/    🔵         ✅             ⚠️             ❌            ❌
L2 svc/    ❌         🔵             ✅             ✅ Model      ✅
L3 repos   ❌         ❌             🔵             ✅ Model      ❌
L4 db      ❌         ❌             ❌             🔵            ❌
Infra      ❌         ✅             ❌             ❌            🔵
```
🔵 同包内自由引用  ✅ 允许  ❌ 禁止  ⚠️ 薄封装可接受但非最佳实践

---

## 总结

| 类别 | 数量 | 最严重违规 |
|------|------|------------|
| T3 循环依赖 | 0 | 无 |
| T2 跨层逆向调用（L2→L1 / L3→L2） | 0 | 无 |
| T1 API 层执行业务逻辑 | 6 | `api/documents/service.py` 和 `api/chunks/service.py` 在 L1 层做 L2 编排（跨模块 Service 调用） |
| T5 Session 自管理 | 1 | `api/ingredients/service.py` 后台任务中自行创建 session |

### 最严重问题

**`api/documents/service.py` 和 `api/chunks/service.py` 的 L1 层跨模块 Service 编排**：

- 违反 T1 核心约束："禁止 API 层执行业务逻辑"
- 违反 G1 生命周期规范："Router → Service (L2) → Repository (L3)"
- 当前架构：`Router (L1) → DocumentsService/ChunksService (L1) → KBService/ParserWorkflowService (L2)`

**建议修复路径**：
1. 将 `api/documents/service.py` 和 `api/chunks/service.py` 搬迁至 `services/` 目录，成为真正的 L2 服务
2. 或者，将 `api/analysis/service.py` 的编排逻辑搬迁至 `services/product_analysis_service.py`
3. 将 `api/ingredient_alias/service.py` 搬迁至 `services/ingredient_alias_service.py`
4. 将 `api/ingredient_analysis/service.py` 搬迁至 `services/ingredient_analysis_service.py`

---

## 附：各 api/xxx/service.py 职责定位速查

| 文件 | 应属层级 | 当前行为 | 判定 |
|------|----------|----------|------|
| `api/documents/service.py` | L2 | 调用 KBService + ParserWorkflowService | **L1 执 L2 之职（违规）** |
| `api/chunks/service.py` | L2 | 调用 KBService + ParserWorkflowService | **L1 执 L2 之职（违规）** |
| `api/analysis/service.py` | L2 | 全流程编排（OCR→匹配→Agent→缓存） | **L1 执 L2 之职（违规）** |
| `api/ingredients/service.py` | L2 | 直接调用 L3 Repository + 后台任务自管 session | **L1 执 L2 之职（违规）+ T5** |
| `api/ingredient_alias/service.py` | L2 | 直接调用 L3 Repository | **L1 执 L2 之职（轻违规）** |
| `api/kb/service.py` | L1 | thin wrapper of L2 KBService | 可接受（薄封装） |
| `api/product/service.py` | L2 | 直接调用 L3 Repository | **L1 执 L2 之职（轻违规）** |
