# Product Analysis Data Schema Design

**Date:** 2026-03-31  
**Status:** Approved (v2，经审阅讨论后更新)  
**Scope:** 结果页（`03-result.html`）所需的完整数据结构，以及产生该数据的管道流程

---

## 1. 背景

用户拍摄食品配料表 → OCR 解析 → 产出结果页分析报告。结果页数据分两类来源：
- **`IngredientAnalysis`（DB）**：单个成分的完整分析，包含风险等级、安全信息、替代方案
- **`ProductAnalysis`（Agent 生成）**：产品级别的综合判断、建议、人群分析、场景

> **设计原则**：舍弃原有 `AnalysisDetail` 表的多切片结构，改用两张独立的统一分析表。`AnalysisDetail` 中 `analysis_target = "food"` 和 `analysis_target = "ingredient"` 的记录均无实际数据，本次设计不复用该表。

---

## 2. 数据管道流程

```
OCR 文本
  └→ 解析出成分名列表
       └→ 按 food_id 查 product_analyses
            ├─ 已有行 ──→ 直接返回该行 → 结果页（本版不写库）
            └─ 无行
                 └→ 逐一匹配配料库，读取每条成分的 IngredientAnalysis
                      └→ 喂给 Agent
                           └→ Agent 生成 ProductAnalysis
                                └→ INSERT 一次 → 结果页
```

**关键约束：**
- 对外轮询 `status` 与内部 OCR/解析/匹配/分析四段的对应关系，以及 **`food_id` 如何从拍照任务得到（含可选 `food_id` 参数、OCR 品名匹配、占位 `food`）**，见 [Analysis Pipeline Spec](./2026-03-31-analysis-pipeline-spec.md) §2.5、§2.6。
- 用户上传图的**长期留存**、**人工报错接口**（与主流程隔离），以及**未来反哺 FoodDetail（异步纠错，非 MVP）**见 [Analysis Pipeline Spec](./2026-03-31-analysis-pipeline-spec.md) §2.7–§2.9。
- **本版**：`product_analyses` 中**已有该 `food_id` 行**则**直接返回、跳过 Agent**，且**不 UPDATE**；**无行**时 Agent 生成后 **INSERT 一次**（与 [Analysis Pipeline Spec](./2026-03-31-analysis-pipeline-spec.md) §4.4 一致）。
- **过期判断（N 天）与 stale-while-revalidate / 条件写回**：留待后续版本；本版可不实现「过期仅提示、后台 UPSERT」等行为。
- Agent 不分析单个成分，只做产品级综合判断
- `alternatives` 来自成分级预分析（`IngredientAnalysis`），非 Agent 实时生成
- `IngredientAnalysis` 在后台录入 `Ingredient` 时生成，先于产品分析流程存在；若某成分尚无记录，管道跳过该成分的 `safety_info`，以 `level: "unknown"` 占位喂给 Agent

---

## 3. 前端接收的完整数据结构

```typescript
type RiskLevel = "t0" | "t1" | "t2" | "t3" | "t4";

type DemographicsGroup = "普通成人" | "婴幼儿" | "孕妇" | "中老年" | "运动人群";

// demographics[].verdict 由前端常量映射，见第 4 节
type DemographicsVerdict = "适量可食" | "建议回避" | "谨慎了解" | "无特殊限制" | "尚无数据";

interface ProductAnalysis {
  // 来源标记（API 层动态注入，不落盘，用于埋点/调试）
  // 本次请求新生成 → "agent_generated"；从 DB 返回缓存 → "db_cache"
  source: "db_cache" | "agent_generated";

  // ① 成分列表 — 读时组装，来自 Ingredient + IngredientAnalysis，不落盘
  ingredients: Array<{
    ingredient_id: number;  // 配料库主键
    name:          string;  // 规范名称，如 "燕麦粉"
    category:      string;  // 由 Ingredient.function_type 拼接，如 "增稠剂 · 高升糖指数"
    level:         RiskLevel;
  }>;

  // ② 总体判断 — Agent 生成，落盘
  verdict: {
    level:       RiskLevel;
    description: string;  // 产品特有一句话描述
  };

  // ③ 参考建议 — Agent 生成，落盘（1-3 句话）
  advice: string;

  // ④ 替代方案 — 读时组装，来自 IngredientAnalysis.alternatives，不落盘
  // 仅展示当前产品中 level ≥ t2 的成分的替代方案
  alternatives: Array<{
    current_ingredient_id: number;  // 当前问题成分（level ≥ t2）
    better_ingredient_id:  number;  // 推荐替代成分（配料库已有记录）
    reason:                string;  // 替换理由
  }>;

  // ⑤ 人群适用性 — Agent 生成，落盘（固定 5 类人群，顺序固定）
  demographics: Array<{
    group:   DemographicsGroup;
    level:   RiskLevel;
    note:    string;  // 1-2 句具体说明
    // verdict 由前端从 level 推导，不由 Agent 生成，不落盘
  }>;

  // ⑥ 食用场景 — Agent 生成，落盘（1-3 个场景）
  scenarios: Array<{
    title: string;
    text:  string;
  }>;

  // ⑦ 分析依据 — Agent 生成，落盘
  references: string[];
}
```

---

## 4. 前端推导字段（不进 DB）

```typescript
// 统计数字（结果页 Hero Stats）
const total_ingredients = analysis.ingredients.length;
const caution_count     = analysis.ingredients.filter(i => ["t2","t3","t4"].includes(i.level)).length;

// 合规标准 — 从 /api/product 接口取，无则不展示
// compliance_standard: product.compliance_standard ?? null

// 判断标签（结果页大字）
const VERDICT_LABEL: Record<RiskLevel, string> = {
  t0: "成分优质 ✓",
  t1: "成分较优 ✓",
  t2: "成分一般 ⚠",
  t3: "成分存疑 ✗",
  t4: "成分较差 ✗",
};

// 成分风险标签（risk pill 文字）
const INGREDIENT_LEVEL_LABEL: Record<RiskLevel, string> = {
  t0: "安全",
  t1: "较安全",
  t2: "谨慎",
  t3: "存在风险",
  t4: "高风险",
};

// 人群适用性结论（由 level 推导，保证同级措辞一致）
const DEMOGRAPHICS_VERDICT: Record<RiskLevel, DemographicsVerdict> = {
  t0: "无特殊限制",
  t1: "适量可食",
  t2: "谨慎了解",
  t3: "建议回避",
  t4: "建议回避",
};
```

---

## 5. Agent 输入 Prompt 结构

Agent 收到的输入（由管道从 `IngredientAnalysis` 组装）：

```
产品成分分析数据：
[
  { name: "燕麦粉", category: "主要原料·全谷物", level: "t0", safety_info: "..." },
  { name: "麦芽糊精", category: "增稠剂·高升糖指数", level: "t2", safety_info: "..." },
  { name: "阿斯巴甜", category: "人工甜味剂·争议成分", level: "t3", safety_info: "..." },
  ...
]

请根据以上成分数据，输出以下 JSON 格式的产品分析：
- verdict（overall risk level + description）
- advice（综合建议，1-3 句）
- demographics（5 类人群各自的 level + note，不输出 verdict 文字）
- scenarios（1-3 个食用场景）
- references（引用标准来源）
```

> `alternatives` 不由 Agent 输出，由管道从 `IngredientAnalysis.alternatives` 读取组装。

---

## 6. DB 存储方案

### 6.1 `IngredientAnalysis` 表

单个成分的完整分析，作为 Agent 生成 `ProductAnalysis` 的输入素材。

```python
class IngredientAnalysis(Base):
    __tablename__ = "ingredient_analyses"

    # ── 元数据 ──────────────────────────────────────────────────────────
    id:              Mapped[int]       # PK
    ingredient_id:   Mapped[int]       # FK → ingredients.id，UNIQUE
    ai_model:        Mapped[str]
    version:         Mapped[str]       # 如 "v1"

    # ── 风险评估（标量，产品列表页可直接读）─────────────────────────────
    level:           Mapped[str]       # RiskLevel: t0-t4
    safety_info:     Mapped[str]       # TEXT，喂给 Agent 的安全信息摘要

    # ── 替代方案（JSONB）────────────────────────────────────────────────
    # [{better_ingredient_id: int, reason: str}]
    alternatives:    Mapped[dict]      # JSONB

    # ── 时间戳 ───────────────────────────────────────────────────────────
    created_at:      Mapped[datetime]
    created_by_user: Mapped[UUID]
```

### 6.2 `ProductAnalysis` 表

产品级完整分析文档，结果页直接消费。`ingredients` 和 `alternatives` 读时组装，不落盘。

```python
class ProductAnalysis(Base):
    __tablename__ = "product_analyses"

    # ── 元数据 ──────────────────────────────────────────────────────────
    id:              Mapped[int]       # PK
    food_id:         Mapped[int]       # FK → foods.id，UNIQUE
    ai_model:        Mapped[str]
    version:         Mapped[str]       # 如 "v1"

    # ── 总体判断（标量，列表页直接读）───────────────────────────────────
    level:           Mapped[str]       # RiskLevel: t0-t4
    description:     Mapped[str]       # verdict.description

    # ── Agent 生成的文本字段 ─────────────────────────────────────────────
    advice:          Mapped[str]       # TEXT
    references:      Mapped[list[str]] # ARRAY(Text)

    # ── 结构化数组（JSONB）──────────────────────────────────────────────
    # [{group, level, note}]  ← 无 verdict，前端推导
    demographics:    Mapped[dict]      # JSONB

    # [{title, text}]
    scenarios:       Mapped[dict]      # JSONB

    # ── 时间戳 ───────────────────────────────────────────────────────────
    created_at:      Mapped[datetime]
    created_by_user: Mapped[UUID]
```

### 6.3 缓存命中与写库逻辑（本版）

```
查询 product_analyses WHERE food_id = ?
  ├─ 无记录 → Agent 生成后 INSERT（source: "agent_generated"）
  └─ 有记录 → 直接返回该记录（source: "db_cache"），跳过 Agent；本版不 UPDATE / UPSERT
```

**后续版本（非本版）**：可恢复或调整「过期阈值 N 天、返回旧数据 + 后台重跑、按条件决定是否写回」等策略；届时以产品决策为准，并同步修订本节与 Pipeline §4.4。

（原设想的过期阈值默认 30 天、lazy invalidation 等保留为**未来迭代备选**，本版实现可不启用。）

---

## 7. 快捷问题 Pills（独立接口）

底部 suggest pills（"糖尿病可以吃吗？"等）不在此 schema 内。

来源：收集该产品在 Agent 对话中的高频问题，存独立表，单独接口返回。无记录时不显示 pills。

---

## 8. 设计决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| 舍弃 `AnalysisDetail` | 不复用，新建两张独立表 | `AnalysisDetail` 无实际数据；多切片结构与"结果页整体消费"的场景不匹配 |
| `ingredients[]` 不落盘 | 读时从 `Ingredient` + `IngredientAnalysis` 组装 | 成分数据随配料库更新自动保持最新，无需缓存失效逻辑 |
| `alternatives` 不由 Agent 生成 | 来自 `IngredientAnalysis.alternatives` | 消除 Agent 幻觉风险，ID 来自 DB，可溯源 |
| `demographics.verdict` | 前端常量映射（DEMOGRAPHICS_VERDICT），不落盘 | 同 `verdict.label`——固定 level→文字关系，Agent 自由生成会导致措辞不一致 |
| `verdict.label` | 前端常量映射，不进 DB | level→label 是固定关系 |
| `compliance_standard` | 从 `/api/product` 取，不进分析表 | 产品合规标准是结构化数据，已在产品库，无则不显示 |
| 缓存 / 写库（本版） | 有 `food_id` 行则只读；无行则 INSERT 一次 | 先落首版详情；是否覆盖与过期重算后续再定 |
| 缓存失效策略（后续） | 懒失效 + stale-while-revalidate 等 | 本版可不实现；留待与「是否写库」规则一并产品化 |
| 过期阈值（后续） | 可配置，默认 30 天（原建议） | 待启用写回/重跑策略后再落地 |
| `source` 字段 | API 层动态注入，不落盘 | 是响应级别的标记，DB 无需存储；每次请求根据是否新生成判断 |
| `IngredientAnalysis` 生成时机 | 后台录入 `Ingredient` 时触发 | 与产品分析流程解耦；成分先于产品存在，保证管道有数据可读 |
| `alternatives` 展示范围 | 仅 level ≥ t2 的成分 | t0/t1 成分无需替代，展示替代方案无实际意义 |
| 快捷问题 pills | 独立接口 | 来源是用户行为数据，与分析结果生命周期不同 |
