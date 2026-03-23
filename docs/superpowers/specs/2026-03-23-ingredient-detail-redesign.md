# 配料详情页重设计规格文档

**日期：** 2026-03-23
**状态：** 已批准
**参考原型：** `web/ui/ingredient-detail.html`（旧版）、`web/ui/font-detail.html`（product-detail 风格参考）

---

## 背景与目标

现有 `ingredient-detail.html` 与 product-detail 页面存在明显的设计风格断层，且缺少关键的视觉信息层次。本次为**全面重设计**（方案三），推倒重来以实现：

1. 与 product-detail 设计语言完全统一（Shadcn 颜色变量、卡片结构、圆角、间距）
2. 建立清晰的信息流：**Identity → Risk → Detail → Related**
3. 支持三种入口（产品配料下钻、独立搜索/直接访问、AI 对话跳转），页面自给自足
4. 亮色 + 暗色双模式完整适配

---

## 入口场景与路由参数

| 入口 | 路由参数 | Header 副标题 |
|------|----------|--------------|
| 从产品详情页配料列表点入 | `ingredientId` + `fromProductName`（string，直接展示） | "来自：{fromProductName}" |
| 独立搜索 / 直接访问 | `ingredientId` 只 | 按风险等级动态显示（见下表） |
| AI 对话跳转 | `ingredientId` 只 | 同上 |

`fromProductName` 由上游页面直接传入字符串，**不需要额外请求**。

**无 `fromProductName` 时，Header 副标题按视觉风险等级动态渲染：**

| 视觉等级 | Header 副标题文案 |
|---------|-----------------|
| high | "⚠ 高风险 · 谨慎摄入" |
| medium | "⚠ 中等风险 · 适量摄入" |
| low / unknown | "✓ 低风险" |

---

## 数据接口

### 当前情况

目前**没有独立的配料详情接口**。配料数据随产品接口返回：

```
GET /api/product?barcode=xxx
→ ProductResponse.ingredients[]: IngredientResponse[]
```

### 字段映射

`IngredientResponse` 字段（`server/api/product/models.py`）：

| 字段 | 类型 | 用途 | 空值处理 |
|------|------|------|----------|
| `name` | string | 配料名称（Hero 卡大标题） | 必填，不为空 |
| `additive_code` | string \| null | 代码 chip（如 E250） | null → 隐藏 chip |
| `alias` | string[] | 别名 chips | 空数组 → 隐藏 |
| `function_type` | string \| null | 功能分类 chip（防腐剂等） | null → 隐藏 |
| `who_level` | string \| null | 风险管理表：WHO 致癌等级 | null → 隐藏该行 |
| `allergen_info` | string \| null | 风险管理表：过敏信息，直接展示字符串 | null → 隐藏该行 |
| `standard_code` | string \| null | 风险管理表：执行标准，直接展示字符串 | null → 隐藏该行 |
| `analysis.level` | 枚举（见下表） | 驱动 header 颜色 + 谱条针位置 | `unknown` → 按低风险处理 |
| `analysis.results` | dict | AI 分析内容（结构见下） | 空 dict → 各字段显示"暂无" |

### analysis.level 枚举映射

后端枚举值（`t0-t4`）映射到前端视觉风险等级：

| level 值 | 视觉等级 | 含义 |
|----------|----------|------|
| `t4` | 高风险（high） | 严重风险 |
| `t3` | 高风险（high） | 高风险 |
| `t2` | 中等风险（medium） | 中等风险 |
| `t1` | 低风险（low） | 低风险 |
| `t0` | 低风险（low） | 极低/无风险 |
| `unknown` | 低风险（low） | 未知，默认低风险展示 |

### analysis.results 结构

数据库为 JSONB，无强约束 schema。当前已知字段（`ingredient_summary` 分析类型）：

```json
{
  "summary": "string — AI 生成的配料综合描述"
}
```

**前端渲染策略：**
- `results.summary` → 渲染为"描述"section 的正文
- AI 风险分析和使用建议列表：如后端 `results` 中存在 `risk_factors: string[]` 和 `suggestions: {text: string, type: "positive"|"conditional"}[]` 字段，则按结构渲染；否则将 `summary` 整段展示于描述 section，风险分析和建议 section 隐藏（`v-if`）
- **此字段结构需与后端确认后补充**，本规格以已知字段为准

### 所需新接口（本次范围外，但需规划）

从搜索/对话入口访问时，需要 `GET /api/ingredient/{id}` 独立接口。本次实现以**从产品详情页点入**为主路径，独立入口可在接口就绪后复用相同页面组件。

### 数据流

**产品详情下钻（主路径）：** 产品详情页点击配料时，将 `IngredientResponse` 存入 Pinia `ingredientStore.current`，跳转时无需额外请求。

**搜索/AI 跳转（降级处理）：** 独立配料接口尚未就绪时，若 `ingredientStore.current` 为空且无可用数据，显示**错误状态页**（"数据加载失败，请返回重试"），不强行渲染空页。接口就绪后移除此降级逻辑。

---

## 信息架构（页面区块顺序）

```
Header（sticky）
└── 风险色调背景 + "配料详情" + 副标题（来自产品名 or 风险摘要）

Hero 风险卡
├── 成分名称（name）+ 风险徽章（analysis.level 映射文案）
├── 风险谱条（低→中→高色阶 + 指示针）
└── Chips（有值才显示）：
    ├── additive_code → "E250" chip（红色功能类）
    ├── function_type → "防腐剂"等 chip（红色功能类）
    ├── 来源 chip（如有，灰色中性）
    ├── 孕妇警告 chip（由 analysis.results 中特定字段驱动，黄色警告类）
    └── alias[] → 别名 chips（灰色中性）

描述（section card）
└── analysis.results.description 字段

AI 风险分析（section card）
└── analysis.results.risk_factors[]，每项 ✕ 红色图标

风险管理信息（section card）
└── KV 对：who_level / 母婴等级 / allergen_info / 使用限量 / 适用区域 / standard_code

AI 使用建议（section card）
└── analysis.results.suggestions[]
    ├── type="positive" → 绿色 ✓ 图标
    └── type="conditional" → 黄色 ✓ 图标（非 ⚠ 符号，统一使用 checkmark）

含此配料的产品（section card）
└── 从 Pinia 全局产品列表中过滤含此 ingredientId 的产品
    └── 无匹配时隐藏整个 section（不显示空占位）

底部 sticky bar
├── 咨询 AI 助手 → 跳转 `/pages/chat/index`，携带 query: { context: ingredient.name }
└── 查看相关食品 → 跳转 `/pages/search/index`，携带 query: { ingredientId }
```

---

## 设计决策

### Header：风险色调（方案 B）

Header 背景随 `analysis.level`（映射后的视觉等级）动态变色：

| 风险等级 | 亮色 bg | 亮色 border | 暗色 bg | 暗色 border |
|---------|---------|------------|---------|------------|
| `high` | `#fff1f2` | `#fecaca` | `#1a0808` | `#7f1d1d` |
| `medium` | `#fefce8` | `#fde68a` | `#1a1500` | `#713f12` |
| `low` | `#f0fdf4` | `#bbf7d0` | `#051a0a` | `#14532d` |

CSS custom properties 在组件级覆盖，不污染全局变量。

**本次实现范围：** 仅 `high` 颜色完整实现并充分测试；`medium`/`low` 颜色值已在上表定义，结构相同，颜色替换即可。

### 风险谱条指示针位置

谱条方向：**左端 = 低风险（绿），右端 = 高风险（红）**，指示针用 `left%` 定位：

| 视觉等级 | left | 说明 |
|---------|------|------|
| `low`（t0/t1/unknown） | `12%` | 靠近左侧绿区 |
| `medium`（t2） | `50%` | 居中黄区 |
| `high`（t3/t4） | `82%` | 靠近右侧红区 |

前端使用 computed property 将 `analysis.level`（t0-t4）映射到上表 `left` 值，**不使用 `right`**。

### 图标语义（统一定义）

| 场景 | 图标 | 颜色 |
|------|------|------|
| 风险项（AI 风险分析列表） | ✕ 圆形 | 红色 |
| 正向建议（AI 使用建议，type="positive"） | ✓ 圆形 | 绿色 |
| 条件性建议（type="conditional"） | ✓ 圆形 | **黄色**（不使用 ⚠ 符号） |

信息架构中的 `⚠ 图标` 描述为旧版措辞，以本表为准。

### Section 结构统一

每个 section card 包含：
- 20×20 图标容器（border-radius 6px，有色背景）
- 标题（`font-size: 13px; font-weight: 700`）
- AI 标签（渐变文字，仅 AI 生成内容的 section 显示）

### 含此配料的产品：空状态处理

当 Pinia 全局产品列表中无匹配产品时，**完全隐藏该 section**（`v-if`），不显示空占位文案，避免误导用户认为没有含此配料的产品（可能是数据未加载）。

---

## 颜色变量完整映射

| 变量 | 高风险亮色 | 高风险暗色 | 中风险亮色 | 中风险暗色 | 低风险亮色 | 低风险暗色 |
|------|-----------|-----------|-----------|-----------|-----------|-----------|
| `--risk-bg` | `#fff1f2` | `#1a0808` | `#fefce8` | `#1a1500` | `#f0fdf4` | `#051a0a` |
| `--risk-border` | `#fecaca` | `#7f1d1d` | `#fde68a` | `#713f12` | `#bbf7d0` | `#14532d` |
| `--risk-btn` | `rgba(220,38,38,0.1)` | `rgba(248,113,113,0.15)` | `rgba(202,138,4,0.1)` | `rgba(251,191,36,0.15)` | `rgba(22,163,74,0.1)` | `rgba(74,222,128,0.15)` |
| `--risk-title` | `#7f1d1d` | `#fca5a5` | `#713f12` | `#fde68a` | `#14532d` | `#86efac` |
| `--risk-sub` | `#dc2626` | `#f87171` | `#a16207` | `#fbbf24` | `#16a34a` | `#4ade80` |

---

## UniApp 实现要点

- **页面路径：** `pages/ingredient-detail/index.vue`（新建）
- **路由参数：** `ingredientId: string`，可选 `fromProductName: string`
- **数据传递：** 从产品详情页跳转时，将 `IngredientResponse` 存入 Pinia `ingredientStore.current`，避免重复请求
- **风险谱条：** 指示针用 computed 映射 `level → right%`，使用绝对定位
- **横向滚动：** `<scroll-view scroll-x enable-flex>`，子元素 `white-space: nowrap` 或 flex 布局
- **暗色模式：** 通过 `uni.getSystemInfoSync().theme` 判断，切换 CSS custom property 值
- **Chips 渲染：** 每个 chip 字段单独 `v-if` 控制，为 null/空数组时不渲染

---

## 不在本次范围内

- 独立配料详情接口 `GET /api/ingredient/{id}`（后续需新建）
- 从搜索/对话入口的数据加载逻辑（接口就绪后补充）
- 低风险 / 中等风险入口的集成测试（颜色变量已定义，结构相同）
- 配料搜索页
- 别名搜索与聚合逻辑（后端）
