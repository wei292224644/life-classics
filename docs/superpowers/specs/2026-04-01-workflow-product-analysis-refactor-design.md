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
  └── types.py                 # IngredientInput、ProductAnalysisResult 等既有类型
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
from workflow_product_analysis.product_agent.types import ProductAnalysisState

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
# final_state 包含: demographics, scenarios, advice, verdict_level, verdict_description, references
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
    types.py        ← ProductAnalysisState

api/analysis/service.py（编排层）
  ├── run_ocr()                      ← HTTP
  ├── parse_ingredients()           ← LLM
  ├── resolve_food_id()               ← DB
  ├── match_ingredients()            ← DB
  ├── 查 ProductAnalysis 缓存
  │     命中 → assemble_from_db_cache() → 直接返回
  │     未命中 → build_product_analysis_graph(settings).ainvoke()
  │                 → assemble_from_agent_output()  ← 依赖 session 组装最终结果
  │                 → 写 ProductAnalysis 缓存
  └── 返回客户端
```

---

## 数据类型

### 既有类型（保留）：`IngredientInput`

```python
# workflow_product_analysis/types.py（已存在，不修改）
class IngredientInput(TypedDict):
    ingredient_id: int  # 0 表示未匹配成分
    name: str
    category: str  # function_type 拼接，如 "甜味剂 · 增稠剂"
    level: IngredientRiskLevel  # "t0".."t4", "unknown"
    safety_info: str  # 来自 IngredientAnalysis；unknown 成分为空
```

### 既有类型（保留）：`ProductAnalysisState`

`ProductAnalysisState` 是 graph 的状态类型，包含 `ingredients`（输入）和 LLM 生成的全部字段（`demographics`、`scenarios`、`advice`、`verdict_level`、`verdict_description`、`references`）。assembler 直接从 `final_state`（即 `ProductAnalysisState`）读取 LLM 输出字段进行组装，不需要额外的中间类型。

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
| `product_agent/graph.py` | 移除 `session` 依赖；重命名 `run_product_analysis_agent` → `build_product_analysis_graph`，与 `worflow_parser_kb/graph.py` 命名一致 |
| `product_agent/nodes/` | 将 `nodes.py` 拆分为 `verdict_node.py`、`demographics_node.py`、`scenarios_node.py`、`advice_node.py`，各节点移除 `session` 依赖 |
| `types.py` | 保留 `ProductAnalysisState`、`IngredientInput`、`ProductAnalysisResult` 等既有类型，不新增 `AgentOutput` |

### 2. `workflow_product_analysis/` 删除/迁出

| 文件 | 去向 |
|------|------|
| `food_resolver.py` | 迁至 `api/analysis/food_resolver.py` |
| `ingredient_matcher.py` | 迁至 `api/analysis/ingredient_matcher.py` |
| `assembler.py` | 迁至 `api/analysis/assembler.py`；`assemble_from_agent_output` / `assemble_from_db_cache` 依赖 `session` 查 Ingredient / IngredientAnalysis 表 |
| `pipeline.py` | 删除 |
| `redis_store.py` | 废弃（`GET /analysis/{task_id}/status` 端点同步删除；后续进度反馈改为 SSE 时由 API 层自行实现） |
| `ocr_client.py` | 迁至 `api/analysis/ocr_client.py` |
| `ingredient_parser.py` | 迁至 `api/analysis/ingredient_parser.py` |

### 3. API 层新增/修改

| 文件 | 职责 |
|------|------|
| `api/analysis/service.py` | 完整编排逻辑（OCR → Parse → Resolve → Match → Agent → Assemble） |
| `api/analysis/food_resolver.py` | 从 `workflow_product_analysis/food_resolver.py` 迁入 |
| `api/analysis/ocr_client.py` | 从 `workflow_product_analysis/ocr_client.py` 迁入 |
| `api/analysis/ingredient_parser.py` | 从 `workflow_product_analysis/ingredient_parser.py` 迁入 |
| `api/analysis/assembler.py` | 从 `workflow_product_analysis/assembler.py` 迁入 |
| `api/analysis/models.py` | 补充 `ProductAnalysisResult` 等类型导入 |
| `api/analysis/ingredient_matcher.py` | 从 `workflow_product_analysis/ingredient_matcher.py` 迁入 |

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
      # 返回: {matched: [MatchedIngredient], unmatched: [str]}
  ⑤ ingredient_inputs = []
      # 对每条 matched 记录：查 Ingredient 表（category）+ IngredientAnalysis 表（level、safety_info）
      for m in match_result.matched:
          details = await fetch_ingredient_details(m.ingredient_id, session)
          ingredient_inputs.append(IngredientInput(
              ingredient_id=m.ingredient_id, name=m.name,
              category=details.category, level=details.level,
              safety_info=details.safety_info,
          ))
      # unmatched 成分：ingredient_id=0, level="unknown", safety_info=""
      for name in match_result.unmatched:
          ingredient_inputs.append(IngredientInput(ingredient_id=0, name=name,
                             category="", level="unknown", safety_info=""))
  │
  ⑥ 查 ProductAnalysis 缓存（按 food_id）
  │     命中 → return assemble_from_db_cache(product_analysis, matched_ids, session)
  │     未命中 →
  ⑦ graph = build_product_analysis_graph(settings)
      final_state = await graph.ainvoke(initial_state)
      # final_state 含: demographics, scenarios, advice, verdict_level, verdict_description, references
  ⑧ result = await assemble_from_agent_output(final_state, matched_ids, session)
  ⑨ await product_analysis_repo.insert_if_absent(food_id, data, ...)
 ⑩ return result
```

---

## API 路由变化

**POST /analysis/start**
- 保持异步：提交图片后立即返回 `task_id`
- 响应格式：`{"task_id": "..."}`（不变）
- 后续可改为 SSE 流式推送 `ProductAnalysisResult`（由 API 层实现，不影响 workflow 模块）

**GET /analysis/{task_id}/status**
- **删除**（Redis 废弃后无状态可查）
- 后续进度推送改为 SSE 时，前端改接 SSE 端点即可

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
- `assembler` 测试：Mock `session`，验证 `assemble_from_agent_output` 和 `assemble_from_db_cache` 输出的 `ProductAnalysisResult` 结构正确
- API 层集成测试：Mock OCR HTTP、Mock DB，验证完整编排流程
- 不在 workflow 内部 mock 数据库

---

## 实施顺序

1. 确认 `workflow_product_analysis/types.py` 既有类型（`IngredientInput`、`ProductAnalysisResult`、`ProductAnalysisState` 等）无需修改；`AgentOutput` 类型的概念不再引入，assembler 直接使用 `ProductAnalysisState`
2. **同步进行**：将 `product_agent/nodes.py` 拆分为独立文件（`verdict_node.py`、`demographics_node.py`、`scenarios_node.py`、`advice_node.py`），同时修改 `product_agent/graph.py` 中的节点引用，移除各节点的 `session` 依赖，验证 LangGraph 仍可正常编译
3. 将迁出文件（`food_resolver.py`、`ingredient_matcher.py`、`assembler.py`、`pipeline.py`、`redis_store.py`、`ocr_client.py`、`ingredient_parser.py`）复制到 `api/analysis/`
4. 在 `api/analysis/service.py` 编写编排逻辑，替换原有 `start_analysis`
5. 删除 `workflow_product_analysis/` 中的迁出文件
6. 更新 API router：
   - 删除 `GET /analysis/{task_id}/status` 端点
   - `POST /analysis/start` 保持异步返回 `task_id`（不变）
   - 后续 SSE 改造在 API 层进行，不影响 workflow 模块
7. 运行测试，修复问题

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
