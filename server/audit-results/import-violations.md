# 包间引用权限审计报告（Section III）

**审计范围**: `server/` 所有 Python 包
**规范文件**: `docs/architecture/server-architecture.md`
**审计日期**: 2026-04-02

---

## 权限矩阵（Section III）

| 从 → 到 | api/ | services/ | db_repositories/ | database/ | infra (kb/llm/workflow_*) |
|---------|------|-----------|------------------|-----------|--------------------------|
| **api/** | 🔵内部 | ✅可引用 | ❌禁止 | ❌禁止 | ❌禁止（通过 services） |
| **services/** | ❌禁止 | 🔵内部 | ✅可引用 | ✅可引用 Model | ✅可引用（接口） |
| **db_repositories/** | ❌禁止 | ❌禁止 | 🔵内部 | ✅可引用 Model | ❌禁止 |
| **database/** | ❌禁止 | ❌禁止 | ❌禁止 | 🔵内部 | ❌禁止 |
| **infra/** | ❌禁止 | ✅可引用 | ❌禁止 | ❌禁止 | 🔵内部 |

---

## 前置说明

`services/` 目录在代码库中**不存在**。当前 `api/` 下的 `service.py` 文件（如 `api/documents/service.py`、`api/chunks/service.py` 等）从架构定义上属于 **L1 API 层**（做参数组装和委托），而非独立的 L2 services 层。因此矩阵中 `api/ → services/` 的引用规则在当前 codebase 中无对应实体。

以下违规均属于 **api/ 直接引用 infra 层**，违反 `api/ → ❌infra` 规则。

---

## 违规汇总

### 类别 A：api/ 直接引用 kb/（infra）

| 文件 | 行号 | 导入语句 | 违规说明 |
|------|------|----------|----------|
| `api/documents/service.py` | 10 | `from kb.clients import get_chroma_client, KB_COLLECTION_NAME` | api/ 禁止直接引用 kb/ |
| `api/documents/service.py` | 11 | `from kb.writer import chroma_writer, fts_writer` | api/ 禁止直接引用 kb/ |
| `api/kb/service.py` | 3 | `from kb.clients import get_chroma_client, KB_COLLECTION_NAME` | api/ 禁止直接引用 kb/ |
| `api/kb/service.py` | 4 | `from kb.writer import fts_writer` | api/ 禁止直接引用 kb/ |
| `api/chunks/service.py` | 15 | `from kb.clients import get_chroma_client, KB_COLLECTION_NAME` | api/ 禁止直接引用 kb/ |
| `api/chunks/service.py` | 16 | `from kb.embeddings import embed_batch` | api/ 禁止直接引用 kb/ |
| `api/chunks/service.py` | 17 | `from kb.writer import fts_writer` | api/ 禁止直接引用 kb/ |

**影响**: L1 层直接操作 ChromaDB/FTS 基础设施，绕过了 L2 业务编排层，违反 T1 禁忌（API 层禁止执行业务逻辑/直接操作 DB）。

---

### 类别 B：api/ 直接引用 workflow_*（infra）

| 文件 | 行号 | 导入语句 | 违规说明 |
|------|------|----------|----------|
| `api/documents/service.py` | 12 | `from workflow_parser_kb.graph import run_parser_workflow_stream` | api/ 禁止直接引用 workflow_ |
| `api/chunks/service.py` | 18 | `from workflow_parser_kb.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState` | api/ 禁止直接引用 workflow_ |
| `api/chunks/service.py` | 19 | `from workflow_parser_kb.nodes.merge_node import merge_node` | api/ 禁止直接引用 workflow_ |
| `api/chunks/service.py` | 20 | `from workflow_parser_kb.nodes.transform_node import transform_node` | api/ 禁止直接引用 workflow_ |
| `api/chunks/service.py` | 21 | `from workflow_parser_kb.rules import RulesStore` | api/ 禁止直接引用 workflow_ |
| `api/analysis/ingredient_parser.py` | 7 | `from workflow_parser_kb.structured_llm.client_factory import get_structured_client` | api/ 禁止直接引用 workflow_ |
| `api/analysis/models.py` | 8-12 | `from workflow_product_analysis.types import AnalysisError, AnalysisStatus, ProductAnalysisResult` | api/ 禁止直接引用 workflow_ |
| `api/analysis/assembler.py` | 11-15 | `from workflow_product_analysis.types import AlternativeItem, IngredientItem, ProductAnalysisResult` | api/ 禁止直接引用 workflow_ |
| `api/analysis/ingredient_matcher.py` | 16-20 | `from workflow_product_analysis.types import IngredientRiskLevel, MatchedIngredient, MatchResult` | api/ 禁止直接引用 workflow_ |
| `api/analysis/service.py` | 20-23 | `from workflow_product_analysis.product_agent.graph import ProductAgentError, build_product_analysis_graph` | api/ 禁止直接引用 workflow_ |
| `api/analysis/service.py` | 24 | `from workflow_product_analysis.product_agent.types import ProductAnalysisState` | api/ 禁止直接引用 workflow_ |
| `api/analysis/service.py` | 25 | `from workflow_product_analysis.types import IngredientInput` | api/ 禁止直接引用 workflow_ |

**影响**: L1 直接调用 workflow engine，绕过了 L2 编排层，违反了 L1 禁止直接操作基础设施的架构约束。

---

### 类别 C：api/ 直接引用 agent/（infra）

| 文件 | 行号 | 导入语句 | 违规说明 |
|------|------|----------|----------|
| `api/agent/router.py` | 9 | `from agent.session_store import get_session_store` | api/ 禁止直接引用 infra（agent/） |
| `api/agent/router.py` | 19 | `from agent.agent import get_agent` | api/ 禁止直接引用 infra（agent/） |

**说明**: `agent/` 包属于 Infra 层。根据矩阵，infra 只能被 `services/` 引用，不能被 api/ 直接引用。

---

## 未发现违规的区域

以下引用**符合**权限矩阵：

- `api/documents/router.py` → `api/documents/service`（🔵内部） ✅
- `api/chunks/router.py` → `api/chunks/service`（🔵内部） ✅
- `api/ingredients/router.py` → `db_repositories/ingredient` ✅（api/ 可引用 services/，而 db_repositories 在 services/ 的可引用范围内）
- `api/analysis/router.py` → `api/analysis/service`（🔵内部） ✅
- `api/analysis/food_resolver.py` → `database/models` ✅（仅引用 Model）
- `api/analysis/assembler.py` → `db_repositories/ingredient_analysis` ✅
- `db_repositories/*` → `database/models` ✅（L3 可引用 L4 Model）
- `db_repositories/*` → `database/session` ✅（session 工厂属 Model 层）
- `kb/*` → `kb/*`（🔵内部） ✅
- `llm/*` → `llm/*`（🔵内部） ✅
- `workflow_*` → `llm/*`（infra → infra，🔵内部） ✅
- `workflow_*` → `kb/*`（infra → infra，🔵内部） ✅
- `agent/*` → `kb/retriever`（agent 为 infra 内部引用） ✅
- `agent/*` → `agent/*`（🔵内部） ✅

---

## 根本问题分析

当前 codebase 缺失独立的 `services/` 层（L2）。`api/` 下的 `service.py` 文件实为 L1 的 HTTP 参数组装层，但它们直接操作 kb/ 和 workflow_*，承担了本应由 L2 services 层承担的职责。

**期望的调用链**:
```
api/ (L1) → services/ (L2, 缺失) → kb/, llm/, workflow_* (infra)
```

**实际的调用链**:
```
api/documents/service.py (L1) → kb/, workflow_parser_kb  ❌违规
api/chunks/service.py (L1) → kb/, workflow_parser_kb    ❌违规
api/analysis/service.py (L1) → workflow_product_analysis ❌违规
```

---

## 建议

1. **引入 L2 services 层**：将 `api/*/service.py` 中的 kb/workflow 调用抽离到独立的 `services/` 包（如 `services/kb_service.py`、`services/parser_workflow_service.py`），api 层仅通过 Depends 注入 service
2. **api/ 不直接引用 infra**：按矩阵规则，api/ 对 infra 的访问必须经由 services/ 层
3. **agent/ 归属确认**：明确 agent/ 包在 infra 层的定位，其被 api/ 引用需通过 services/ 层中转
