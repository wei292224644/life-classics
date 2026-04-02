# L2 Service Layer 架构合规审查报告

**审查范围**: `server/services/`
**审查日期**: 2026-04-02
**审查人**: 架构合规审查 Agent

---

## 约束清单

- [约束T2] 禁止L2调用L1
- [约束T5] 禁止Session自管理
- [约束L2→Infra] 通过接口引用Infra，禁止直接操作ChromaDB/Redis
- [约束G4] 禁止Service间直接import

---

## 违规项

### 违规1: [kb_service.py:1-9] - [约束L2→Infra + 约束T5]

**kb_service.py** 是最严重的违规文件，L2层直接操作ChromaDB基础设施，且无任何接口抽象。

```python
# 第1-9行
from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.embeddings import embed_batch
from kb.writer import chroma_writer, fts_writer
```

**违规行为详述**:

KBService 并非"业务编排"层，而是直接执行了所有基础设施操作：

| 行号 | 违规代码 | 操作 |
|------|----------|------|
| 34 | `fts_writer.init_db()` | 直接操作 FTS 基础设施 |
| 38 | `fts_writer.write(chunks, doc_metadata)` | 直接操作 FTS 写入 |
| 68-69 | `col.upsert(ids=..., documents=..., embeddings=..., metadatas=...)` | **直接操作 ChromaDB collection**，绕过了 `chroma_writer` 封装 |
| 77 | `self._get_collection().delete(ids=ids)` | 直接操作 ChromaDB |
| 84, 105, 133, 146, 156, 163, 184 | `get_chroma_client().get_or_create_collection(...)` | 直接获取并操作 ChromaDB client |
| 126-128 | `chroma_writer.write(chunks, doc_metadata)` + `fts_writer.write(...)` | 虽通过 writer，但 KBService 本身在直接调用 Infra writer |
| 139-140 | `collection.delete(...)` + `fts_writer.delete_by_doc_id(...)` | 直接操作 ChromaDB + FTS |
| 171 | `collection.delete(ids=all_ids)` | 直接操作 ChromaDB |
| 203 | `collection.update(ids=ids, metadatas=updated_metadatas)` | 直接操作 ChromaDB |

**核心问题**: `KBService` 充当了"第二个 Infra 层"，它不是编排 Repository，而是直接操作 ChromaDB collection 对象（`col.upsert`、`col.delete`、`col.update` 等），并且自己管理 `get_chroma_client()` 的调用。这完全违背了 L2→Infra 应通过"接口（Protocol）"隔离的约束。

**根本原因**: 项目中完全不存在 `kb/` 的 Protocol 接口定义（搜索 `Protocol` 在 `server/kb/` 和 `server/services/` 中无结果），导致 KBService 只能直接 import concrete infra 类。

---

### 违规2: [agent_service.py:5-6] - [约束L2→Infra]

```python
# 第5-6行
from agent.agent import get_agent
from agent.session_store import get_session_store
```

**违规行为详述**:

```python
# 第12-14行
class AgentService:
    def __init__(self):
        self._session_store = get_session_store()  # 直接引用 Infra 单例
        self._agent = get_agent()                   # 直接引用 Infra 单例
```

`AgentService` 在 `__init__` 中直接持有 `agent/` Infra 的具体实例（`SessionStore`、`Agent`），而非通过接口注入。这使得 L2 对 Infra 产生了强耦合，且无法在测试中替换为 mock 实现。

**对比约束G2的 Session 注入标准**: Service 应通过 Router 层 `Depends` 注入，而非在内部直接实例化 Infra 组件。

---

### 违规3: [parser_workflow_service.py:6-10] - [约束L2→Infra]

```python
# 第6-10行
from workflow_parser_kb.graph import run_parser_workflow_stream
from workflow_parser_kb.models import ClassifiedChunk, TypedSegment
from workflow_parser_kb.nodes.merge_node import merge_node
from workflow_parser_kb.nodes.transform_node import transform_node
from workflow_parser_kb.rules import RulesStore
```

`ParserWorkflowService` 直接 import `workflow_parser_kb` 中的具体节点类（`merge_node`、`transform_node`、`RulesStore`），而非通过接口。这使 L2 与 Infra 实现细节紧耦合——如果 `workflow_parser_kb` 重构（如节点函数签名变化），L2 必须修改。

---

### 违规4: [product_analysis_service.py:4-9] - [约束L2→Infra]

```python
# 第4-9行
from workflow_product_analysis.product_agent.graph import (
    ProductAgentError,
    build_product_analysis_graph,
)
from workflow_product_analysis.product_agent.types import ProductAnalysisState
from workflow_product_analysis.types import IngredientInput
```

`ProductAnalysisService` 直接 import `workflow_product_analysis` 的具体 graph builder 和类型定义，而非通过接口。L2 在第32行直接调用 `build_product_analysis_graph()` 获取编译后的 graph，这是 Infra 实现细节。

---

## 合规项（显著发现）

### 合规1: 无 T2 违规（无跨层逆向调用）
全 services/ 目录未发现任何 `from api.` 或 `from services.` 的跨层 import。未发现 L2 调用 L1 的情况。

### 合规2: 无 T5 违规（无 Session 自管理）
全 services/ 目录未发现 `get_async_session_cm` 或 `async with.*session` 模式。Session 生命周期未在 Service 层被管理。

### 合规3: 无 G4 违规（无 Service 间直接 import）
services/ 内部无交叉引用，各 Service 相互独立（`__init__.py` 仅含 docstring）。

### 合规4: 无 T3 违规（无循环依赖）
services/ 与 api/、db_repositories/ 之间未发现循环依赖。

---

## 严重程度汇总

| 严重程度 | 文件 | 违规数 | 核心问题 |
|----------|------|--------|----------|
| **严重** | `kb_service.py` | 1项（多行） | L2直接操作ChromaDB collection，无接口抽象 |
| **中等** | `agent_service.py` | 1项 | L2持有Infra单例实例，无接口注入 |
| **中等** | `parser_workflow_service.py` | 1项 | L2直接import Infra具体节点 |
| **轻微** | `product_analysis_service.py` | 1项 | L2直接调用Infra graph builder |

---

## 总结

- **违规数量**: 4 项
- **严重程度**: 1项严重（kb_service.py），其余3项中等/轻微
- **最严重问题**: `kb_service.py` 中的 `KBService` 类实际充当了 Infra 操作层而非业务编排层。它直接调用 `collection.upsert()`、`collection.delete()`、`collection.update()` 等 ChromaDB collection 原生方法，并自行管理 `get_chroma_client()` 的调用，而非通过 Repository 层或接口代理。

- **架构缺口**: 本项目不存在任何 `Protocol` 接口定义（`server/kb/` 和 `server/services/` 中无 `Protocol` 文件），导致 L2→Infra 的"通过接口引用"约束在当前代码中**物理上无法遵守**。建议在修复时优先建立 Infra 接口抽象层。
