# workflow_product_analysis 重构设计：纯计算模块

## 目标

将 `workflow_product_analysis/` 改造为**纯 LLM 计算组件**，只依赖配置（`Settings`），不持有任何数据库连接、Redis 连接或外部 HTTP 客户端。

所有外部依赖（OCR、数据库、Redis、编排逻辑）全部迁移到 API 层（`server/api/analysis/`）。

---

## 核心原则

1. `workflow_product_analysis/` = 纯函数式计算模块
2. 只接收已准备好的数据，输入输出都是 TypedDict / Pydantic 模型
3. 不持有任何 I/O 资源（DB session、Redis client、HTTP client）
4. 只依赖 `Settings`（配置）和 LLM

---

## `workflow_product_analysis/` 重构后内部结构（对齐 worflow_parser_kb 模式）

`workflow_product_analysis/` 重构后保持 **LangGraph 组件结构**，与 `worflow_parser_kb/` 一致：

```
workflow_product_analysis/
  ├── product_agent/
  │     ├── __init__.py
  │     ├── graph.py          # LangGraph 定义（START → 并行 → 串行 → END）
  │     ├── nodes/
  │     │     ├── verdict_node.py
  │     │     ├── demographics_node.py
  │     │     ├── scenarios_node.py
  │     │     └── advice_node.py
  │     └── types.py          # ProductAnalysisState
  └── types.py                 # AgentOutput、IngredientInput、ProductAnalysisResult
```

### 图结构

```
        START
          │
    ┌─────┴─────┐
    ▼           ▼
demographics  scenarios    （并行）
    │           │
    └─────┬─────┘
          ▼
      advice_node
          │
          ▼
     verdict_node
          │
          ▼
         END
```

API 层调用：
```python
from workflow_product_analysis.product_agent.graph import build_product_analysis_graph

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
```

---

## 重构前后对比

### Before

```
pipeline.py（持有 session、redis、settings）
  ├── run_ocr()                      ← HTTP
  ├── parse_ingredients()           ← LLM
  ├── resolve_food_id()             ← DB (session)
  ├── match_ingredients()           ← DB (session)
  ├── [cache hit]  → assemble_from_db_cache()   ← DB
  ├── [cache miss] → run_agent_analysis()       ← LLM
  │                   → assemble_from_agent_output() ← DB
  └── set_task_done() / set_task_failed()      ← Redis
```

### After

```
workflow_product_analysis/（纯计算模块）
  product_agent/
    graph.py        ← LangGraph（START → 并行 → 串行 → END）
    nodes/
      verdict_node.py        ← LLM
      demographics_node.py   ← LLM
      scenarios_node.py      ← LLM
      advice_node.py         ← LLM
    types.py        ← ProductAnalysisState、AgentOutput

api/analysis/service.py（编排层）
  ├── run_ocr()                      ← HTTP
  ├── parse_ingredients()           ← LLM
  ├── resolve_food_id()               ← DB
  ├── match_ingredients()            ← DB
  ├── 查 ProductAnalysis 缓存
  │     命中 → assemble_from_db_cache() → 直接返回
  │     未命中 → build_product_analysis_graph(settings).ainvoke()
  │                 → assemble_from_agent_output()
  │                 → 写 ProductAnalysis 缓存
  └── 返回客户端
```

---

## 数据类型

### 新增：`IngredientInput`

```python
# workflow_product_analysis/types.py（已存在，保留）
class IngredientInput(TypedDict):
    ingredient_id: int  # 0 表示未匹配成分
    name: str
    category: str  # function_type 拼接，如 "甜味剂 · 增稠剂"
    level: IngredientRiskLevel  # "t0".."t4", "unknown"
    safety_info: str  # 来自 IngredientAnalysis；unknown 成分为空
```

### 新增：`AgentOutput`

```python
# workflow_product_analysis/types.py
class AgentOutput(TypedDict):
    verdict_level: str  # RiskLevel
    verdict_description: str
    advice: str
    demographics: list[DemographicItem]
    scenarios: list[ScenarioItem]
    references: list[str]
```

### `ProductAnalysisResult`（最终输出，保留）

```python
# workflow_product_analysis/types.py
class ProductAnalysisResult(TypedDict):
    source: Literal["db_cache", "agent_generated"]
    ingredients: list[IngredientItem]
    verdict: dict[str, Any]  # {level, description}
    advice: str
    alternatives: list[AlternativeItem]
    demographics: list[DemographicItem]
    scenarios: list[ScenarioItem]
    references: list[str]
```

---

## 改动清单

### 1. `workflow_product_analysis/` 保留文件（修改签名/结构）

| 文件 | 改动 |
|------|------|
| `product_agent/graph.py` | 移除 `session` 依赖，只接收 `ingredient_inputs` 和 `settings` |
| `product_agent/nodes/` | 将 `nodes.py` 拆分为 `verdict_node.py`、`demographics_node.py`、`scenarios_node.py`、`advice_node.py`，各节点移除 `session` 依赖 |
| `types.py` | 补充 `AgentOutput` 类型定义 |

### 2. `workflow_product_analysis/` 删除/迁出

| 文件 | 去向 |
|------|------|
| `food_resolver.py` | 迁至 `api/analysis/service.py`（或 `api/analysis/food_resolver.py`） |
| `ingredient_matcher.py` | 迁至 `api/analysis/service.py` |
| `assembler.py` | 迁至 `api/analysis/service.py` |
| `pipeline.py` | 删除，或仅保留骨架 |
| `redis_store.py` | 迁至 `api/analysis/service.py`（或废弃） |
| `ocr_client.py` | 迁至 `api/analysis/service.py` |
| `ingredient_parser.py` | 迁至 `api/analysis/service.py` |

### 3. API 层新增/修改

| 文件 | 职责 |
|------|------|
| `api/analysis/service.py` | 完整编排逻辑（OCR → Parse → Resolve → Match → Agent → Assemble） |
| `api/analysis/food_resolver.py` | 从 `food_resolver.py` 迁入 |
| `api/analysis/ocr_client.py` | 从 `ocr_client.py` 迁入 |
| `api/analysis/ingredient_parser.py` | 从 `ingredient_parser.py` 迁入 |
| `api/analysis/models.py` | 补充 `AgentOutput` 导入（从 workflow 导入） |

---

## API 层编排流程

```
start_analysis(image_bytes, food_id, session, settings)
  │
  ① ocr_text = await run_ocr(image_bytes, settings)
  ② parse_result = await parse_ingredients(ocr_text, settings)
  ③ food_id = await resolve_food_id(product_name=parse_result.product_name,
                                     explicit_food_id=food_id, ...)
  ④ match_result = await match_ingredients(parse_result.ingredients, session)
  ⑤ ingredient_inputs = await build_ingredient_inputs(match_result, session)
  │
  ⑥ 查 ProductAnalysis 缓存（按 food_id）
  │     命中 → return assemble_from_db_cache(product_analysis, matched_ids, session)
  │     未命中 →
  ⑦ agent_output = await run_agent_analysis(ingredient_inputs, settings)
  ⑧ result = await assemble_from_agent_output(agent_output, matched_ids, session)
  ⑨ await product_analysis_repo.insert_if_absent(food_id, data, ...)
 ⑩ return result
```

---

## 进度反馈（暂时搁置）

当前重构**不包含进度反馈机制**：

- 移除 Redis 任务状态读写
- 移除前端轮询 `/analysis/{task_id}/status`
- API 改为**同步响应**（分析完成 → 直接返回 `ProductAnalysisResult`）

后续如需进度反馈（如 SSE 推送），由 API 层透传，不影响 workflow 模块。

---

## 缓存策略（API 层负责）

| 步骤 | 说明 |
|------|------|
| 查缓存 | `product_analysis_repo.get_by_food_id(food_id)` |
| 命中 | 直接 assemble 返回，`source="db_cache"` |
| 未命中 | 调 workflow → assemble → `insert_if_absent` → 返回，`source="agent_generated"` |
| 写入 | `product_analysis_repo.insert_if_absent(food_id, data)` |

缓存粒度：按 `food_id`，非按 `ingredient_inputs`。

---

## 错误处理

| 异常 | 含义 | 处理 |
|------|------|------|
| `OcrServiceError` | OCR 失败 | HTTP 422 |
| `NoIngredientsFoundError` | 成分解析为空 | HTTP 422 |
| `InvalidFoodIdError` | food_id 无效 | HTTP 400 |
| `ProductAgentError` | Agent 执行失败 | HTTP 500 |

---

## 测试策略

- `workflow_product_analysis/` 单元测试：Mock `Settings`，验证 `build_product_analysis_graph(settings).ainvoke(state)` 输入输出
- 各节点独立测试：给定 `ingredient_inputs`，验证节点返回符合预期的结构
- API 层集成测试：Mock OCR HTTP、Mock DB，验证完整编排流程
- 不在 workflow 内部 mock 数据库

---

## 实施顺序

1. 新增 `AgentOutput` 类型，修改 `workflow_product_analysis/types.py`
2. 将 `product_agent/nodes.py` 拆分为独立文件（`verdict_node.py`、`demographics_node.py`、`scenarios_node.py`、`advice_node.py`），移除各节点的 `session` 依赖
3. 修改 `product_agent/graph.py` — 移除 `session` 依赖，验证 LangGraph 仍可正常编译
4. 将迁出文件（`food_resolver.py`、`ingredient_matcher.py`、`assembler.py`、`pipeline.py`、`redis_store.py`、`ocr_client.py`、`ingredient_parser.py`）复制到 `api/analysis/`
5. 在 `api/analysis/service.py` 编写编排逻辑，替换原有 `start_analysis`
6. 删除 `workflow_product_analysis/` 中的迁出文件
7. 更新 API router（如有参数签名变化）
8. 运行测试，修复问题

---

## 两个 workflow 模块架构对比

| 维度 | `worflow_parser_kb/` | `workflow_product_analysis/`（重构后） |
|------|----------------------|----------------------------------------|
| 图结构 | 线性链式（parse→clean→...→merge→END） | 并行→串行（START→demographics+scenarios→advice→verdict→END） |
| 状态类型 | `WorkflowState`（TypedDict） | `ProductAnalysisState`（TypedDict） |
| 节点文件 | `nodes/` 目录下单职责文件 | `product_agent/nodes/` 目录下单职责文件 |
| 外部依赖 | 无（纯 LLM + 规则文件） | 无（纯 LLM + Settings） |
| 入口调用 | `run_parser_workflow(md_content, doc_metadata, ...)` | `build_product_analysis_graph(settings).ainvoke(initial_state)` |
| 调用方 | API 层（`api/documents/service.py`） | API 层（`api/analysis/service.py`） |

两者架构模式一致，都是：
- **外部调用方**负责编排 + I/O
- **workflow 模块**负责纯计算
- **LangGraph**定义节点流转

---

## 未纳入范围

- Redis 进度轮询机制（SSE 等）
- 图片上传对象存储
- 其他 workflow 模块（`worflow_parser_kb/` 等）
