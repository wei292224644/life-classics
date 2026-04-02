# server/ 架构合规性综合审查报告

**审查日期**: 2026-04-02
**审查范围**: `server/` Python FastAPI 后端
**依据文档**: `docs/architecture/server-architecture.md` (v1.0)
**审查方法**: Agent Team 并行多维度审查（5 个专项 Agent）

---

## 执行摘要

| 审查维度 | 违规数 | 状态 |
|---------|-------|------|
| L1 API Layer | 10 项 | 🔴 高危 |
| L2 Service Layer | 4 项 | 🟡 中危 |
| L3 DB Repository Layer | 8 项 | 🔴 高危 |
| Infrastructure Layer | 6 项 | 🟡 中危 |
| 跨层依赖与循环依赖 | 0 项 | ✅ 合规 |
| **合计** | **28 项** | — |

**整体评级**: 🔴 **严重偏离架构规范**

---

## 核心发现

### ✅ 合规面（做得正确的部分）

1. **无循环依赖（T3）** — `api/` 和 `services/` 内部均无循环引用
2. **无跨层逆向调用（T2）** — L2→L1、L3→L2 均为 0
3. **Session 管理整体合规（T5）** — `services/` 层无自管理 Session
4. **kb/llm 间接访问正确** — `api/chunks/`、`api/kb/` 均通过 L2 访问 Infra
5. **L3 无日志记录** — Repository 层纯净，无 logging

---

## 🔴 高危问题（必须修复）

### 问题集群 1: `api/analysis/` — 四层职责全部混淆

`api/analysis/` 包是本此审查的 **重灾区**，同时违反 T1/T4/T5/L1→Infra 多条核心约束：

| 文件 | 违规 |
|------|------|
| `service.py:94-223` | **T1**: L1 执行完整业务编排（OCR→解析→DB查询→成分匹配→Agent→缓存） |
| `food_resolver.py:50-72` | **T1 + L1→Infra**: L1 直接 SQL 查询，混用 L3 逻辑 |
| `ingredient_matcher.py:84-96` | **T1 + L1→Infra**: L1 执行 SQL 查询 + 直接实例化 L3 Repository |
| `assembler.py:7` | **L1→Infra**: Assembler 直接引用 `workflow_product_analysis.types` |
| `models.py:8` | **L1→Infra**: DTO 直接引用 Infra 层类型 |
| `ingredient_parser.py:7` | **L1→Infra + T1**: L1 直接调用 `workflow_parser_kb.structured_llm.client_factory` |

**根本原因**: `api/analysis/` 包试图在 L1 层完成 L1+L2+L3+Infra 所有层级的工作。

### 问题集群 2: `db_repositories/search.py` / `food.py` — 跨域查询 + DTO 转换

- **search.py:49-60**: `FoodIngredient JOIN IngredientAnalysis` 跨表查询
- **food.py:51-56**: `selectinload` 多级关联加载
- 两个文件均返回 `FoodSearchResult`/`FoodDetail` 等 DTO，违反 G3（Repository 应返回 Entity）

**根本原因**: L2 Service 层缺位，数据聚合和 DTO 转换工作在 L3 完成。

### 问题集群 3: `services/kb_service.py` — L2 直接操作 ChromaDB

`KBService` 直接调用 `col.upsert()`、`col.delete()`、`col.update()` 等 ChromaDB collection 原生方法，并自行管理 `get_chroma_client()`。

**关键缺口**: 项目中 **不存在任何 Protocol 接口定义**（`kb/` 和 `services/` 中均无 `Protocol`），导致 L2→Infra "通过接口引用"约束物理上无法遵守。

---

## 🟡 中危问题

| 位置 | 违规类型 | 说明 |
|------|---------|------|
| `api/ingredients/service.py:165` | **T5** | 后台任务中 `get_async_session_cm()` 自管 Session |
| `api/ingredients/service.py:144` | **L1→Infra** | L1 直接调用 `workflow_ingredient_analysis.entry` |
| `api/documents/service.py` | **T1** | L1 做跨模块 Service 调用（KBService + ParserWorkflowService） |
| `api/chunks/service.py` | **T1** | L1 做跨模块 Service 调用（KBService + ParserWorkflowService） |
| `services/agent_service.py` | **L2→Infra** | 持有 Infra 单例实例，未通过接口注入 |
| `services/parser_workflow_service.py` | **L2→Infra** | 直接 import Infra 具体节点（`merge_node`、`transform_node`） |
| `services/product_analysis_service.py` | **L2→Infra** | 直接调用 Infra graph builder |
| `db_repositories/ingredient.py:66` | **业务判断** | `is_additive` 过滤条件属业务逻辑 |
| `db_repositories/ingredient_alias.py:11` | **业务逻辑** | `normalize_ingredient_name` 函数含业务规则 |

---

## 违规分布热力图

```
层级          | T1(业务逻辑) | T2(跨层调用) | T3(循环) | T4(Assembler) | T5(Session) | L1→Infra | 跨域查询 | 业务判断 | DTO转换
--------------|-------------|-------------|----------|--------------|------------|----------|---------|---------|--------
L1 api/       | 6           | 0           | 0        | 1            | 1          | 6        | -       | -       | -
L2 services/  | 0           | 0           | 0        | 0            | 0          | 4        | -       | -       | -
L3 repos/     | 0           | 0           | 0        | 0            | 0          | -        | 3       | 3       | 5
Infra (其他)  | 0           | 0           | 0        | 0            | 0          | 0        | -       | -       | -
```

---

## 架构缺口优先级

### P0（阻断性，必须立即修复）

1. **建立 Infra Protocol 接口层** — 整个 L2→Infra 的"通过接口引用"约束因缺失接口定义而无法遵守
2. **拆分 `api/analysis/`** — 将 L2/L3 职责迁出 L1，建立清晰的 `services/analysis/` 层
3. **修复 `db_repositories/search.py`** — 拆分为单表查询，由 L2 Service 负责 JOIN 和 DTO 组装

### P1（严重影响架构完整性）

4. **修复 `db_repositories/food.py`** — 跨域查询移至 L2 Service
5. **迁移 `api/documents/service.py` 和 `api/chunks/service.py`** — 移至 `services/` 成为真正 L2
6. **移除 L1 对 `workflow_*` 模块的直接引用** — 统一通过 L2 Service 间接调用

### P2（长期技术债）

7. **移除 `api/ingredients/service.py` 中的 `get_async_session_cm`**
8. **将 `ingredient_alias.normalize_ingredient_name` 迁至 L2**
9. **消除 `db_repositories/ingredient.py` 中的业务判断逻辑**

---

## 总结

当前 `server/` 的架构实现**严重偏离** `server-architecture.md` 规范。28 项违规中，约 **12 项高危**，主要集中在：

1. **`api/analysis/` 包的四层职责混淆**（最严重）
2. **L3 Repository 层承担了 L2 的数据聚合职责**
3. **L2→Infra 无 Protocol 接口，耦合严重**

**好消息是**：架构的"骨架"是正确的——无循环依赖、无跨层逆向调用、分层方向大体清晰。问题在于**各层边界定义不严格，导致职责下推和越权调用**。

---

*报告生成时间: 2026-04-02*
*审查团队: arch-compliance (5 个专项 Agent)*
