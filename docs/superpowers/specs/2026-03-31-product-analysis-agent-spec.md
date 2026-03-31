# Product Analysis Agent Spec

**Date:** 2026-03-31  
**Status:** Approved  
**Scope:** 产品分析 Agent 的内部设计——基于 LangGraph 的 workflow 编排

---

## 1. 概述

产品分析 Agent 接收成分分析数据（`IngredientAnalysis`），通过 LangGraph workflow 编排多次 LLM 调用，生成完整的 `ProductAnalysis`。

**设计目标：**
- 每个推理步骤独立、可热插拔（换 prompt / 换模型不影响其他节点）
- 并行执行互不依赖的步骤，控制总耗时
- 使用 Instructor 保证每步结构化输出，不依赖 Agent 框架做编排决策

---

## 2. Workflow 图结构

```
START
  │
  ├─→ [Node A: demographics] ─┐
  ├─→ [Node B: scenarios]    ─┼→ [Node C: advice] → [Node D: verdict] → END
  └──────────────────────────┘
```

A 和 B 并行执行，C 等待 A、B 完成后执行，D 等待 C 完成后执行。

**预计耗时：** 3 个阶段 × ~3s = **约 9s**（A/B 并行计为 1 个阶段）

---

## 3. State 定义

```python
class ProductAnalysisState(TypedDict):
    # ── 输入 ─────────────────────────────────────────────────────────
    ingredients: list[IngredientInput]  # 来自 IngredientAnalysis 的成分数据

    # ── 中间产物 ──────────────────────────────────────────────────────
    demographics: list[DemographicItem] | None   # Node A 输出
    scenarios:    list[ScenarioItem]    | None   # Node B 输出

    # ── 最终产物 ──────────────────────────────────────────────────────
    advice:              str       | None   # Node C 输出
    verdict_level:       RiskLevel | None   # Node D 输出
    verdict_description: str       | None   # Node D 输出
    references:          list[str] | None   # Node D 输出
```

### 输入数据结构

```python
class IngredientInput(TypedDict):
    name:        str       # 成分规范名称
    category:    str       # function_type 拼接，如 "增稠剂 · 高升糖指数"
    level:       RiskLevel # 来自 IngredientAnalysis
    safety_info: str       # 来自 IngredientAnalysis，喂给 LLM 的安全摘要
```

---

## 4. 各节点设计

### Node A：Demographics（人群适用性）

**输入：** `state.ingredients`  
**输出：** `state.demographics`

```python
class DemographicItem(BaseModel):
    group: Literal["普通成人", "婴幼儿", "孕妇", "中老年", "运动人群"]
    level: RiskLevel
    note:  str  # 1-2 句具体说明

class DemographicsOutput(BaseModel):
    demographics: list[DemographicItem]  # 固定 5 条，顺序固定
```

**Prompt 要点：**
- 针对每类人群，结合该人群的生理特点评估成分风险
- 5 类人群必须全部输出，顺序固定
- `level` 基于该人群对最高风险成分的敏感程度判断

---

### Node B：Scenarios（食用场景）

**输入：** `state.ingredients`  
**输出：** `state.scenarios`

```python
class ScenarioItem(BaseModel):
    title: str  # 如 "上午加餐"
    text:  str  # 具体建议，2-3 句

class ScenariosOutput(BaseModel):
    scenarios: list[ScenarioItem]  # 1-3 个场景
```

**Prompt 要点：**
- 结合成分整体风险，给出实际可行的食用场景建议
- 场景应具体（时间段、人群、搭配），避免泛泛而谈

---

### Node C：Advice（参考建议）

**输入：** `state.ingredients` + `state.demographics` + `state.scenarios`  
**输出：** `state.advice`

```python
class AdviceOutput(BaseModel):
    advice: str  # 1-3 句综合建议
```

**Prompt 要点：**
- 综合各人群判断和食用场景，提炼出面向普通用户的一段建议
- 语气实用、中立，不做绝对化判断

---

### Node D：Verdict（整体判断）

**输入：** `state.ingredients` + `state.demographics` + `state.scenarios` + `state.advice`  
**输出：** `state.verdict_level` + `state.verdict_description` + `state.references`

```python
class VerdictOutput(BaseModel):
    level:       RiskLevel  # 综合所有前序推理得出的整体等级
    description: str        # 产品特有一句话描述
    references:  list[str]  # 引用的标准或来源，如 "GB 2760-2014"
```

**Prompt 要点：**
- `level` 是对所有前序推理的最终综合，不单独看某一成分
- `description` 是对这个产品的特有描述，不能是通用模板
- `references` 仅引用真实存在的食品安全标准，不编造

---

## 5. 热插拔设计

每个节点通过配置独立指定模型，互不影响：

```python
# config.py 新增
ANALYSIS_DEMOGRAPHICS_MODEL: str = "qwen-plus"
ANALYSIS_SCENARIOS_MODEL:    str = "qwen-plus"
ANALYSIS_ADVICE_MODEL:       str = "qwen-plus"
ANALYSIS_VERDICT_MODEL:      str = "qwen-max"  # verdict 用更强的模型
```

节点内部通过 Instructor 做结构化输出，prompt 和 model 各自在节点内维护，更换任意节点不影响 workflow 结构。

---

## 6. 与分析管道的集成

产品分析 Agent 是分析管道（Component 4）的内部实现，在缓存未命中时调用：

```python
async def run_product_analysis(
    ingredients: list[IngredientInput],
    food_id: int,
) -> ProductAnalysis:
    state = ProductAnalysisState(ingredients=ingredients, ...)
    result = await graph.ainvoke(state)
    analysis = assemble_product_analysis(result, food_id)
    await upsert_product_analysis(analysis)
    return analysis
```

`assemble_product_analysis` 负责将 State 中的各字段组装为 `ProductAnalysis` 结构，写入 `product_analyses` 表。

---

## 7. 设计决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| 编排方案 | LangGraph | 固定 DAG，纯代码调度，无 LLM 编排开销；与 parser workflow 保持一致 |
| Agent + Skill 方案 | 不采用 | 工作流固定，Agent 做编排等于让 LLM 做每次答案相同的决策，多余且更慢 |
| A/B 并行 | demographics + scenarios 并行 | 两者均只依赖 ingredients，无依赖关系，并行节省约 3s |
| verdict 放最后 | 综合所有前序推理后得出 | 整体判断是对 demographics / scenarios / advice 的综合，先推后归 |
| 结构化输出 | Instructor | 保证每节点输出格式正确，失败时可单独重试该节点 |
| references 位置 | 归入 Node D（verdict）| 引用来源是对整体分析的依据，与 verdict 语义最接近 |
