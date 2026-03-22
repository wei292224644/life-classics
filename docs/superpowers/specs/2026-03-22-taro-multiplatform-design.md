# 多端适配设计文档（uni-app）

**日期：** 2026-03-22
**状态：** 已批准（2026-03-22 框架由 Taro 改为 uni-app）

---

## 目标

重构 Web 工程结构，新增 uni-app 应用，实现一套代码覆盖：

**本期目标：**
- 微信小程序
- 支付宝小程序
- 抖音/头条小程序
- H5 网页

**二期目标：**
- iOS / Android 原生 App（via uni-app x 自研渲染引擎）

核心功能：**扫描条形码 → 产品营养成分 + 配料 + AI 风险分析展示**

---

## 一、工程架构

### 目录结构

```
web/
├── apps/
│   ├── console/             # 管理后台（Vite/React，独立管理自己的 UI）
│   └── uniapp/              # 新增，多端小程序（Vue 3 + uni-app）
│       ├── src/
│       │   ├── pages/
│       │   │   ├── index/        # 首页 + 扫码入口
│       │   │   ├── scan/         # 扫码页（小程序端）
│       │   │   └── product/      # 产品详情（营养 + 配料 + 分析）
│       │   ├── components/
│       │   │   ├── NutritionTable.vue
│       │   │   ├── IngredientList.vue
│       │   │   ├── AnalysisCard.vue
│       │   │   └── RiskBadge.vue
│       │   ├── services/
│       │   │   └── food.ts       # API 请求封装（uni.request）
│       │   ├── store/
│       │   │   └── product.ts    # 产品状态（Pinia）
│       │   ├── utils/
│       │   │   └── scanner.ts    # 扫码工具（平台差异收口）
│       │   ├── pages.json        # 路由配置（uni-app 路由入口）
│       │   ├── manifest.json     # 应用配置（appid / 平台配置）
│       │   └── App.vue
│       └── package.json
├── tooling/
│   ├── eslint/
│   ├── prettier/
│   └── tsconfig/            # 从 packages/ 移入
└── pnpm-workspace.yaml      # 只声明 apps/** 和 tooling/**
```

**删除的包：** `@acme/nextjs`、`@acme/db`、`@acme/ui`、`@acme/api`、`@acme/auth`、`@acme/validators`、`@acme/tailwind-config`、`@acme/db-seed`

`packages/` 目录整体删除。

### 构建目标

| 命令 | 目标平台 |
|---|---|
| `pnpm dev:mp-weixin` | 微信小程序 |
| `pnpm dev:mp-alipay` | 支付宝小程序 |
| `pnpm dev:mp-toutiao` | 抖音小程序 |
| `pnpm dev:h5` | H5 网页 |
| `pnpm dev:app` | 原生 App（二期，uni-app x）|

---

## 二、数据库 Schema（完整记录）

> **迁移说明：** `@acme/db`（Drizzle）删除后，以下 Schema 由 FastAPI 侧用 SQLAlchemy 重新声明。PostgreSQL 数据库本身不变，表结构不变，只是管理方式从 Drizzle 迁移到 SQLAlchemy。

### 表一览

| 表名 | 说明 |
|---|---|
| `foods` | 食品产品主表 |
| `ingredients` | 配料/添加剂字典库 |
| `food_ingredients` | 食品↔配料 多对多关联 |
| `nutrition_table` | 营养素字典库 |
| `food_nutrition_table` | 食品↔营养素 多对多关联（含数值） |
| `analysis_details` | AI 分析结果（食品级 + 配料级） |

### `foods`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | 自增主键 |
| `barcode` | varchar(32) UNIQUE | 条形码（查询主入口） |
| `name` | varchar(255) | 商品名称 |
| `image_url_list` | varchar(255)[] | 图片 URL 数组 |
| `manufacturer` | varchar(255) | 委托生产商 |
| `production_address` | varchar(255) | 生产地址 |
| `origin_place` | varchar(255) | 产地 |
| `production_license` | varchar(255) | 食品生产许可证编号 |
| `product_category` | varchar(255) | 产品类别 |
| `product_standard_code` | varchar(255) | 执行标准号 |
| `shelf_life` | varchar(100) | 保质期（字符串，格式不固定） |
| `net_content` | varchar(100) | 净含量（如 "500g"） |
| `createdAt` / `lastUpdatedAt` | timestamptz | 审计时间戳 |
| `createdByUser` / `lastUpdatedByUser` | uuid | 审计用户 |
| `deletedAt` | timestamptz | 软删除标记 |

### `ingredients`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | |
| `name` | varchar(255) | 配料名称 |
| `alias` | varchar(255)[] | 别名数组 |
| `description` | text | 描述 |
| `is_additive` | boolean | 是否为食品添加剂 |
| `additive_code` | varchar(50) | 添加剂编码，如 E330 |
| `standard_code` | varchar(255) | 国标编号，如 GB 2760 |
| `who_level` | enum | WHO 致癌等级：Group 1/2A/2B/3/4/Unknown |
| `allergen_info` | varchar(255) | 过敏信息 |
| `function_type` | varchar(100) | 功能类型：防腐剂/增稠剂等 |
| `origin_type` | varchar(100) | 来源：植物/动物/化学合成 |
| `limit_usage` | varchar(255) | 使用限量 |
| `legal_region` | varchar(255) | 法规适用区域 |
| `metadata` | jsonb | 扩展字段 |

### `food_ingredients`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | |
| `food_id` | integer FK → foods.id | |
| `ingredient_id` | integer FK → ingredients.id | |
| 审计字段 | | |

### `nutrition_table`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | |
| `name` | varchar(255) | 营养素名称 |
| `alias` | varchar(255)[] | 别名 |
| `category` | varchar(255) | 大类，如：维生素 |
| `sub_category` | varchar(255) | 子类，如：维生素B族 |
| `description` | text | 描述 |
| `daily_value` | varchar(255) | 推荐每日摄入量 |
| `upper_limit` | varchar(255) | 安全上限 UL |
| `is_essential` | boolean | 是否为必需营养素 |
| `risk_info` | text | 风险说明 |
| `pregnancy_note` | text | 孕期注意事项 |
| `metabolism_role` | varchar(255) | 代谢功能标签 |
| `metadata` | jsonb | 扩展字段 |

### `food_nutrition_table`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | |
| `food_id` | integer FK → foods.id | |
| `nutrition_id` | integer FK → nutrition_table.id | |
| `value` | numeric(10,4) | 数值 |
| `value_unit` | enum | g / mg / kJ / kcal / mL |
| `reference_type` | enum | PER_100_WEIGHT / PER_100_ENERGY / PER_SERVING / PER_DAY |
| `reference_unit` | enum | g / mg / kcal / mL / kJ / serving / day |
| 审计字段 | | |

### `analysis_details`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer PK | |
| `target_id` | integer | 关联 food.id 或 ingredient.id |
| `target_type` | enum | food / ingredient |
| `analysis_type` | enum | usage_advice_summary / health_summary / pregnancy_safety / risk_summary / recent_risk_summary / ingredient_summary |
| `analysis_version` | enum | v1 |
| `ai_model` | varchar(255) | 使用的 AI 模型名称 |
| `results` | jsonb | 分析结果数组 |
| `level` | enum | t0（低）/ t1 / t2 / t3 / t4（高）/ unknown |
| `confidence_score` | integer | 置信度 0-100 |
| `raw_output` | jsonb | AI 原始输出 |
| 审计字段 | | |

---

## 三、DB 迁移工作

### 迁移策略

**数据库不动**，只迁移"管理方"：从 Drizzle（Node.js）→ SQLAlchemy（Python/FastAPI）。

PostgreSQL 上已有的表和数据原封不动，无需执行任何 ALTER TABLE 或数据迁移 SQL。

### 需要做的事

**① 在 FastAPI 侧新建 SQLAlchemy Models**

在 `server/` 下新增：
```
server/
└── db/
    ├── base.py          # DeclarativeBase
    ├── session.py       # AsyncSession engine（asyncpg）
    ├── models/
    │   ├── food.py      # Food, FoodIngredient, FoodNutritionEntry
    │   ├── ingredient.py
    │   ├── nutrition.py
    │   └── analysis.py
    └── repositories/
        └── food.py      # fetch_by_barcode()
```

**② 配置项**

在 `server/config.py` 新增：
```
POSTGRES_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

**③ 新增 API 端点**

```python
# server/api/product.py
GET /api/product?barcode={barcode}
```

**④ 删除 `@acme/db` 包**

确认 FastAPI 端点测试通过后，从 monorepo 删除：
- `web/packages/db/`
- `web/packages/db-seed/`
- `web/packages/api/`（tRPC router）
- `web/packages/auth/`
- `web/packages/validators/`
- `web/packages/ui/`

**⑤ 移除 Turborepo**

```
删除：web/turbo.json
删除：web/package.json 中 turbo devDependency 和 turbo run 脚本
更新：web/pnpm-workspace.yaml，只保留 apps/** 和 tooling/**
```

**⑥ 删除 nextjs app**

```
删除：web/apps/nextjs/
```

### 迁移顺序（避免服务中断）

```
1. FastAPI 新增 SQLAlchemy models + /api/product 端点
2. 验证端点返回数据正确
3. 删除 packages/（db / api / auth / validators / ui）
4. 移除 Turborepo
5. 删除 web/apps/nextjs/
6. 更新 pnpm-workspace.yaml
```

---

## 四、uni-app 详细设计

### 技术选型

| 关注点 | 选择 | 说明 |
|---|---|---|
| 多端框架 | uni-app（Vue 3 + Vite，CLI 模式） | CLI 模式可接入 pnpm workspace，区别于 HBuilderX 模式 |
| UI 组件库 | `uview-plus`（Vue 3） | uView 的 Vue 3 社区 fork，原 uView 2.x 仅支持 Vue 2 |
| 状态管理 | Pinia | Vue 3 官方推荐，替代 Vuex |
| 请求封装 | `uni.request()` 封装 | 统一处理 baseURL / 错误 / loading |
| 样式方案 | `<style scoped>` + SCSS | uni-app 原生支持，三端行为一致 |
| Tailwind | **不使用** | `weapp-tailwindcss` 主要针对微信设计，支付宝/抖音兼容性不可靠 |
| 路由 | `pages.json` 声明式路由 | uni-app 内置，无需额外路由库 |
| 语言 | TypeScript + Vue 3 Composition API | |
| 环境变量 | `.env.development` / `.env.production` | uni-app Vite 模式支持，`VITE_API_BASE_URL` 控制接口地址 |

### 页面设计

#### `pages/index` — 首页

```
┌─────────────────────┐
│    [App Logo]       │
│    食品安全助手       │
│                     │
│  ┌───────────────┐  │
│  │   扫码查成分   │  │  → 小程序：跳转 scan 页
│  └───────────────┘  │    H5：显示输入框
│                     │
│  ┌───────────────┐  │
│  │  手动输入条码  │  │  → 直接跳转 product 页
│  └───────────────┘  │
└─────────────────────┘
```

H5 端通过 `#ifdef H5` 条件编译隐藏扫码按钮，改为输入框。

#### `pages/scan` — 扫码页

- 调用 `uni.scanCode()`，获得 barcode → 跳转 product
- 通过 `#ifndef H5` 条件编译，H5 不编译此页（`pages.json` 里同样用条件编译排除）
- 扫码失败（用户取消）：静默返回首页

#### `pages/product` — 产品详情页

通过路由参数 `?barcode=xxx` 进入，调用 `/api/product` 获取数据。

```
┌─────────────────────┐
│ ← 返回              │
│ [产品图片]           │
│ 商品名称             │
│ 品牌 / 净含量 / 保质期│
├─────────────────────┤
│ Tab: 营养 | 配料 | 分析│
├─────────────────────┤
│ [Tab 内容区]         │
└─────────────────────┘
```

**营养 Tab**（`NutritionTable.vue`）：
- 展示 `food_nutrition_table` 数据
- 按 `reference_type` 分组（每100g / 每份）
- 每行：营养素名 + 数值 + 单位

**配料 Tab**（`IngredientList.vue`）：
- 展示 `food_ingredients` → `ingredients`
- 每项：配料名 + WHO 等级徽章（`RiskBadge.vue`）+ 功能类型
- 高亮 `who_level` 为 Group 1 / 2A 的配料

**分析 Tab**（`AnalysisCard.vue` 列表）：
- 展示 `analysis_details`（target_type = food）
- 按 `analysis_type` 分卡片：
  - 食用建议（usage_advice_summary）
  - 健康分析（health_summary）
  - 母婴安全（pregnancy_safety）
  - 风险分析（risk_summary）
  - 近期风险（recent_risk_summary）
- 每张卡片：level 色块 + results 内容

### 数据流

```
用户操作
  → scan 页 / 首页输入框 → 获得 barcode 字符串
  → services/food.ts: fetchByBarcode(barcode)
      → uni.request({ url: `${BASE_URL}/api/product?barcode=${barcode}` })
  → 成功：store/product.ts（Pinia）存储结果 → 跳转 product 页渲染
  → 404：跳转"暂无数据"页
  → 网络错误：uni.showToast 提示 + 重试按钮
```

### API 响应结构（FastAPI 返回）

```ts
interface ProductDetail {
  id: number
  barcode: string
  name: string
  manufacturer: string | null
  origin_place: string | null
  shelf_life: string | null
  net_content: string | null
  image_url_list: string[]

  nutritions: Array<{
    name: string
    alias: string[]
    value: string
    value_unit: "g" | "mg" | "kJ" | "kcal" | "mL"
    reference_type: "PER_100_WEIGHT" | "PER_100_ENERGY" | "PER_SERVING" | "PER_DAY"
    reference_unit: string
  }>

  ingredients: Array<{
    id: number
    name: string
    alias: string[]
    is_additive: boolean
    additive_code: string | null
    who_level: "Group 1" | "Group 2A" | "Group 2B" | "Group 3" | "Group 4" | "Unknown"
    allergen_info: string | null
    function_type: string | null
    standard_code: string | null
    analysis?: {
      id: number
      analysis_type: string
      results: unknown
      level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown"
    }
  }>

  analysis: Array<{
    id: number
    analysis_type: string
    results: unknown
    level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown"
  }>
}
```

### 平台差异处理

**扫码**（`src/utils/scanner.ts`）：

```ts
export async function scanBarcode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.scanCode({
      onlyFromCamera: true,
      success: (res) => resolve(res.result),
      fail: () => reject(new Error("SCAN_CANCELLED")),
    })
  })
}
```

**H5 条件编译**（`pages/index/index.vue`）：

```vue
<!-- 小程序端显示扫码按钮 -->
<!-- #ifndef H5 -->
<button @tap="goToScan">扫码查成分</button>
<!-- #endif -->

<!-- H5 端显示输入框 -->
<!-- #ifdef H5 -->
<input v-model="barcode" placeholder="输入条形码" />
<button @tap="goToProduct">查询</button>
<!-- #endif -->
```

---

## 五、错误处理

| 错误场景 | 处理方式 |
|---|---|
| 用户拒绝/取消扫码 | 静默返回首页 |
| 条形码未收录（404） | 展示"暂无数据"页，提示手动搜索 |
| 网络请求失败 | `uni.showToast` 提示 + 重试按钮 |
| H5 不支持扫码 | 条件编译隐藏扫码入口，改为输入框 |
| 数据字段为 null | 对应字段降级显示"暂无数据"，不崩溃 |

---

## 六、上线前置条件

以下事项不是代码工作，但必须在发布前完成：

| 平台 | 需要做的事 |
|---|---|
| 微信小程序 | 注册微信小程序账号，获取 AppID，在 `manifest.json` 填入；后台配置业务域名白名单（FastAPI 域名） |
| 支付宝小程序 | 注册支付宝开放平台，获取 AppID |
| 抖音小程序 | 注册抖音开放平台，获取 AppID |
| FastAPI 后端 | 配置 CORS，允许各小程序平台域名和 H5 域名访问 `/api/product` |

---

## 七、超出本期范围

- 用户登录 / 鉴权（小程序 OAuth）
- 历史扫码记录
- 产品收藏功能
- App 打包上架（AppStore / Google Play）
- Console 的 UI 重构（剥离 @acme/ui 是技术债，本期不动功能）
- 二期 App（uni-app x）

---

## 八、关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 多端框架 | **uni-app**（Vue 3） | 国内同类产品主流选择，社区资源丰富；二期 App 用 uni-app x，性能优于 React Native |
| ~~Taro~~ | ~~已放弃~~ | React 体系，但国内小程序社区资源不如 uni-app |
| UI 组件库 | uView UI 3.x | uni-app 生态内社区最大 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| API 层 | REST fetch，不用 tRPC | tRPC 在小程序环境兼容性差 |
| REST API 位置 | FastAPI（`server/`） | Next.js 将被移除，数据在现有 PostgreSQL |
| DB 管理 | SQLAlchemy + asyncpg | 替代 Drizzle，FastAPI 原生生态 |
| DB 迁移策略 | 只迁移管理方，不动表结构 | PostgreSQL 表/数据原封不动，零迁移风险 |
| H5 差异 | 条件编译 `#ifdef H5` | uni-app 内置机制，无需额外适配层 |
| 构建工具 | 放弃 Turborepo，改用纯 pnpm workspace | Next.js 移除后共享包全部失去意义 |
| 目录结构 | 保持 apps/ + tooling/，删除 packages/ | 结构清晰，tooling/ 统一管理 eslint/prettier/tsconfig |
| 共享包 | 只保留 tooling | validators/tailwind-config 在 console 和 uniapp 之间平台差异太大 |
