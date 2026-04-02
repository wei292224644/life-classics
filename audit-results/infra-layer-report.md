# Infrastructure Layer 架构合规审查报告

**审查日期**: 2026-04-02
**审查范围**: `server/kb/`、`server/llm/`、`server/workflow_*/`
**架构规范**: `docs/architecture/server-architecture.md` (v1.0)

---

## 约束清单

| 约束编号 | 描述 |
|----------|------|
| C1 | **L1→Infra 隔离** — `api/` 禁止直接引用 Infra 层（`kb/`、`llm/`、`workflow_*`），只能通过 `services/` 间接访问 |
| C2 | **接口隔离** — Infra 层应通过 `interface.py` / `protocol.py` 暴露能力，内部实现不得外泄 |
| C3 | **禁止 Assembler 访问 DB** — `api/*/assembler.py` 只做数据组装，不得查询 DB 或引用 Infra |

---

## 违规项

### 违规 1: `api/analysis/ingredient_parser.py:7` — [C1] L1 直接引用 Infra 实现

```python
from workflow_parser_kb.structured_llm.client_factory import get_structured_client
```

**原因**: `api/` 层（L1）直接引用了 `workflow_parser_kb.structured_llm.client_factory`，这是 Infra 层的内部实现（调用 `llm/anthropic.py` 的工厂函数）。应通过 `services/` 层间接访问，或定义清晰的接口。

**严重程度**: 高 — 违反核心分层隔离原则，且该导入是功能性调用（非仅类型引用），意味着 L1 实际执行业务逻辑（结构化 LLM 调用）。

---

### 违规 2: `api/ingredients/service.py:144` — [C1] L1 直接调用 Infra Workflow Entry

```python
from workflow_ingredient_analysis.entry import run_ingredient_analysis
...
result = await run_ingredient_analysis(
    ingredient=ingredient_dict,
    task_id=task_id,
    ai_model=settings.DEFAULT_MODEL,
)
```

**原因**: `api/ingredients/service.py` 是 L1 层模块，直接导入并调用了 `workflow_ingredient_analysis` 的 entry point。虽然以 lazy import（函数内部导入）方式出现，但仍然是 L1 直接调用 Infra。

**严重程度**: 高 — 违反 L1/L2 禁止执行业务逻辑的 T1 约束，且该 workflow entry 是纯计算逻辑，应在 L2 服务层封装。

---

### 违规 3: `api/analysis/service.py:129` — [C1] L1 通过函数内 lazy import 引用 Infra 类型

```python
async def start_analysis(...):
    ...
    from workflow_product_analysis.types import IngredientInput  # L1 → Infra
```

**原因**: L1 Service 层（`api/analysis/service.py`）在函数内部 lazy import Infra 层的 `IngredientInput` 类型。lazy import 未改变导入方向，仍然是 L1 → Infra 直接引用。

**严重程度**: 中 — 类型导入影响范围小于功能性调用，但仍然破坏了分层边界。

---

### 违规 4: `api/analysis/assembler.py:7` — [C1 + C3] Assembler 直接引用 Infra 类型

```python
from workflow_product_analysis.types import (
    AlternativeItem,
    IngredientItem,
    ProductAnalysisResult,
)
```

**原因**: 根据架构 T4，Assembler 是"纯数据组装"组件，应仅接收已查询的数据做序列化。本文件直接从 `workflow_product_analysis.types` 导入 result 类型，违反了 Assembler 不访问 Infra 的约束，同时也违反了 L1→Infra 隔离。

**严重程度**: 中 — 属于 L1 层核心逻辑文件对 Infra 的直接引用，且 assembler 位于禁止访问 Infra 的组件类型中。

---

### 违规 5: `api/analysis/ingredient_matcher.py:16` — [C1] L1 直接引用 Infra 类型

```python
from workflow_product_analysis.types import (
    IngredientRiskLevel,
    MatchedIngredient,
    MatchResult,
)
```

**原因**: `api/analysis/ingredient_matcher.py` 是 L1 层组件，直接引用 `workflow_product_analysis.types` 中定义的类型。虽然这些是纯数据 TypedDict，但引用方向仍然是从 L1 到 Infra。

**严重程度**: 低（就 L1→Infra 隔离而言）— TypedDict 类型影响有限，但严格遵守架构应将共享类型提升至独立接口定义。

---

### 违规 6: `api/analysis/models.py:8` — [C1] L1 的 DTO 层引用 Infra 类型

```python
from workflow_product_analysis.types import (
    AnalysisError,
    AnalysisStatus,
    ProductAnalysisResult,
)
```

**原因**: `api/analysis/models.py` 是 L1 的 DTO（请求/响应模型）定义层，直接引用了 Infra 层类型。这意味着 Infra 层类型泄漏到了 API 响应模型中。

**严重程度**: 中 — DTO 是 L1 的契约层，引用 Infra 类型会导致 API 契约与 Infra 实现强耦合。

---

## 正面发现（接口定义良好的模块）

### kb/ 通过 services/ 间接访问 — 正确 ✅

`api/chunks/router.py` 和 `api/kb/router.py` 均通过 `services/kb_service.py`（L2）访问 `kb/`（Infra），符合架构要求的 L1→L2→Infra 调用链：

```python
# api/chunks/router.py
from services.kb_service import KBService  # L1 → L2（正确）
```

### llm/ 仅通过 services/ 被间接访问 ✅

`llm/` 模块未被 `api/` 直接引用，均通过 `services/` 间接使用。

### services/ 对 Infra 的引用 — 符合架构 ✅

`services/kb_service.py` 直接 import `kb/clients`、`kb/embeddings`、`kb/writer`，符合架构允许的 L2→Infra 引用关系。

### 无 `api/` 直接 import `kb/` 或 `llm/` ✅

未发现 `api/` 直接 import `kb/` 或 `llm/` 模块的情况。

---

## kb/ 接口缺失问题

### `kb/__init__.py` 为空 — 重构中标识

```python
# kb package — 重构中，旧实现已移除
```

`kb/` 目前无 `interface.py`，包级别无接口定义。`kb/` 作为 Infra 层，应至少通过 `__init__.py` 或 `interface.py` 显式暴露接口，而不是让 consumers 直接引用内部模块（`kb.clients`、`kb.embeddings`、`kb.writer`）。

**建议**: `kb/` 应添加 `interface.py`，定义 `KBReader`、`KBWriter` 等 Protocol，显式声明可用接口。

### `llm/__init__.py` 充当了接口层 ✅

`llm/__init__.py` 定义了 `get_llm()`、`get_embedding()`、`chat()` 等统一接口函数，是 Infra → L2 接口的的良好示范。但其内部直接 `from config import settings`，符合架构"Infra 通过接口接收配置"的要求（配置由调用方通过参数传入）。

---

## 总结

| 项目 | 数值 |
|------|------|
| 违规总数 | 6 |
| 严重（高） | 2（`ingredient_parser.py`、`ingredients/service.py`） |
| 中等 | 3（`assembler.py`、`service.py` lazy import、`models.py`） |
| 轻微 | 1（`ingredient_matcher.py` 类型引用） |

### 最严重问题

**`api/analysis/ingredient_parser.py`** 直接引用 `workflow_parser_kb.structured_llm.client_factory`，是 L1 层实际执行 Infra 业务逻辑（结构化 LLM 调用），违反 T1（禁止 API 层执行业务逻辑）和 C1（L1→Infra 隔离）双重约束。

**`api/ingredients/service.py`** 直接导入并调用 `workflow_ingredient_analysis.entry.run_ingredient_analysis`，是 L1 绕过 services 层直接调用 Infra workflow engine 的典型违规。

### 根本原因

`api/analysis/` 和 `api/ingredients/` 模块在实现时未遵循 L1→L2→Infra 调用链，而是直接从 L1 调用 Infra 层的 entry point 和类型。正确做法应为：
- `api/analysis/` → `services/product_analysis_service.py` → `workflow_product_analysis/`
- `api/ingredients/` → `services/ingredient_analysis_service.py` → `workflow_ingredient_analysis/`
- `workflow_parser_kb` 应通过 `services/parser_workflow_service.py` 对 L1 暴露
