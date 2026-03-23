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

**无 `fromProductName` 时，Header 副标题按视觉风险等级动态渲染（见"风险等级色系"章节）。**

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

后端枚举定义 6 个值：`t4 / t3 / t2 / t1 / t0 / unknown`（`server/database/models.py`）。

前端保留 **5 档独立视觉等级**（不合并），`unknown` 作为特殊回退态单独处理：

| level 值 | 视觉等级 key | 中文文案 | Header 副标题（无产品上下文时） |
|----------|------------|---------|-------------------------------|
| `t4` | `critical` | 极高风险 | ⛔ 极高风险 · 不建议摄入 |
| `t3` | `high` | 高风险 | ⚠ 高风险 · 谨慎摄入 |
| `t2` | `medium` | 中等风险 | ⚠ 中等风险 · 适量摄入 |
| `t1` | `low` | 低风险 | ✓ 低风险 |
| `t0` | `safe` | 安全 | ✓ 安全 · 天然成分 |
| `unknown` | `unknown` | 暂无评级 | 暂无风险评级数据 |

`analysis` 对象整体为 null 时，视觉等级回退为 `unknown`。

### analysis.results 结构

数据库为 JSONB，无强约束 schema。当前已知字段（`ingredient_summary` 分析类型）：

```json
{
  "summary": "string — AI 生成的配料综合描述"
}
```

**前端渲染策略（以下字段名为暂定，需与后端确认后更新）：**
- `results.summary` → 渲染为"描述"section 的正文；缺失则隐藏描述 section
- `results.risk_factors: string[]` → AI 风险分析列表；字段不存在或空数组则隐藏该 section
- `results.suggestions: { text: string, type: "positive" | "conditional" | unknown }[]` → AI 使用建议列表；`type` 未知值或缺失时按 `conditional`（黄色 ✓）处理；字段不存在或空数组则隐藏该 section
- **所有 `results` 字段均为 provisional，后端确认 schema 后更新本规格**

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
    └── 结果为空数组、null 或加载失败时，v-if 隐藏整个 section（不显示空占位）

底部 sticky bar
├── 咨询 AI 助手 → 跳转 `/pages/chat/index`，携带 query: { context: ingredient.name }
└── 查看相关食品 → 跳转 `/pages/search/index`，携带 query: { ingredientId: IngredientResponse.id }（数据库主键）
```

---

## 设计决策

### 风险等级色系（完整设计规范）

风险等级是贯穿整个 ingredient-detail 页面的核心设计变量，驱动 Header 颜色、风险徽章、谱条针位置和副标题文案。

#### Header 色调

CSS custom properties 在组件级覆盖，不污染全局 Shadcn 变量：

| 视觉等级 key | 亮色 `--risk-bg` | 亮色 `--risk-border` | 暗色 `--risk-bg` | 暗色 `--risk-border` |
|------------|----------------|---------------------|----------------|---------------------|
| `critical`（t4） | `#fff1f2` | `#fca5a5` | `#1a0505` | `#991b1b` |
| `high`（t3） | `#fff4f0` | `#fecaca` | `#1a0808` | `#7f1d1d` |
| `medium`（t2） | `#fefce8` | `#fde68a` | `#1a1500` | `#713f12` |
| `low`（t1） | `#f0fdf4` | `#bbf7d0` | `#051a0a` | `#14532d` |
| `safe`（t0） | `#ecfdf5` | `#6ee7b7` | `#022c22` | `#065f46` |
| `unknown` | `#f9fafb` | `#d1d5db` | `#111827` | `#374151` |

#### Header 文字颜色

| 视觉等级 key | 亮色标题 `--risk-title` | 亮色副标题 `--risk-sub` | 暗色标题 `--risk-title` | 暗色副标题 `--risk-sub` |
|------------|----------------------|----------------------|----------------------|----------------------|
| `critical` | `#7f1d1d` | `#dc2626` | `#fecaca` | `#f87171` |
| `high` | `#7f1d1d` | `#ef4444` | `#fca5a5` | `#f87171` |
| `medium` | `#713f12` | `#a16207` | `#fde68a` | `#fbbf24` |
| `low` | `#14532d` | `#16a34a` | `#86efac` | `#4ade80` |
| `safe` | `#065f46` | `#059669` | `#6ee7b7` | `#34d399` |
| `unknown` | `#374151` | `#6b7280` | `#9ca3af` | `#6b7280` |

#### 按钮背景（Header 内图标按钮）

| 视觉等级 key | `--risk-btn`（亮色） | `--risk-btn`（暗色） |
|------------|--------------------|--------------------|
| `critical` | `rgba(220,38,38,0.15)` | `rgba(248,113,113,0.2)` |
| `high` | `rgba(220,38,38,0.1)` | `rgba(248,113,113,0.15)` |
| `medium` | `rgba(202,138,4,0.1)` | `rgba(251,191,36,0.15)` |
| `low` | `rgba(22,163,74,0.1)` | `rgba(74,222,128,0.15)` |
| `safe` | `rgba(5,150,105,0.1)` | `rgba(52,211,153,0.15)` |
| `unknown` | `rgba(107,114,128,0.1)` | `rgba(156,163,175,0.15)` |

#### 风险徽章文案与图标

| 视觉等级 key | 徽章文案 | 图标 | 徽章背景色 |
|------------|---------|------|----------|
| `critical` | 极高风险 | ⛔（禁止符） | `#dc2626` |
| `high` | 高风险 | ⚠（警告符） | `#ef4444` |
| `medium` | 中等风险 | ⚠（警告符） | `#f59e0b` |
| `low` | 低风险 | ✓（勾选） | `#22c55e` |
| `safe` | 安全 | ✓（勾选） | `#10b981` |
| `unknown` | 暂无评级 | ?（问号） | `#9ca3af` |

#### 风险谱条指示针位置

谱条方向：**左端 = 安全（绿），右端 = 极高风险（红）**。

指示针用绝对定位，`left%` 表示**针中心点**相对于谱条容器宽度的百分比（`transform: translateX(-50%)`）：

| 视觉等级 key | `left` | 对应谱条区域 |
|------------|--------|------------|
| `safe`（t0） | `8%` | 最左侧深绿区 |
| `low`（t1） | `22%` | 浅绿区 |
| `medium`（t2） | `50%` | 黄色中心区 |
| `high`（t3） | `72%` | 橙红区 |
| `critical`（t4） | `88%` | 最右侧深红区 |
| `unknown` | 隐藏针，谱条整体降低透明度至 40% |

`analysis` 对象整体为 null 时，视觉等级回退为 `unknown`。

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

---

## UniApp 实现要点

- **页面路径：** `pages/ingredient-detail/index.vue`（新建）
- **路由参数：** `ingredientId: string`，可选 `fromProductName: string`
- **数据传递：** 从产品详情页跳转时，将 `IngredientResponse` 存入 Pinia `ingredientStore.current`，避免重复请求
- **风险谱条：** 指示针用 computed 映射 `level → left%`，绝对定位 + `transform: translateX(-50%)`；`unknown` 时隐藏针并降低谱条透明度
- **横向滚动：** `<scroll-view scroll-x enable-flex>`，子元素 `white-space: nowrap` 或 flex 布局
- **暗色模式：** 初始化时通过 `uni.getSystemInfoSync().theme` 判断，同时注册 `uni.onThemeChange()` 监听器以响应运行时主题切换，组件销毁时调用 `uni.offThemeChange()` 清除
- **Chips 渲染：** 每个 chip 字段单独 `v-if` 控制，为 null/空数组时不渲染

---

## 不在本次范围内

- 独立配料详情接口 `GET /api/ingredient/{id}`（后续需新建）
- 从搜索/对话入口的数据加载逻辑（接口就绪后补充）
- 低风险 / 中等风险入口的集成测试（颜色变量已定义，结构相同）
- 配料搜索页
- 别名搜索与聚合逻辑（后端）
