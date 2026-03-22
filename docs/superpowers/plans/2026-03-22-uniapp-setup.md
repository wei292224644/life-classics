# uni-app 应用搭建实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `web/apps/uniapp/` 下搭建完整的 uni-app 多端小程序应用，覆盖微信/支付宝/抖音小程序 + H5，实现扫码 → 产品详情（营养成分 + 配料 + AI 分析）完整流程。

**Architecture:** uni-app CLI 模式（Vue 3 + Vite + TypeScript），使用 uview-plus 作为 UI 库，Pinia 管理状态，`uni.request()` 封装 HTTP 请求。H5 扫码降级为手动输入（`#ifdef H5` 条件编译），scan 页通过条件编译在 H5 构建中排除。

**Tech Stack:** uni-app 3.x（CLI）、Vue 3 Composition API、TypeScript、uview-plus、Pinia、SCSS

**前置条件：** Plan A（FastAPI Product API）已完成，`GET /api/product?barcode=xxx` 端点可访问。

---

## 文件结构

```
web/apps/uniapp/
├── src/
│   ├── pages/
│   │   ├── index/
│   │   │   └── index.vue          # 首页：扫码入口 / H5 输入框
│   │   ├── scan/
│   │   │   └── index.vue          # 扫码页（#ifndef H5 条件编译）
│   │   └── product/
│   │       └── index.vue          # 产品详情页（Tab: 营养/配料/分析）
│   ├── components/
│   │   ├── NutritionTable.vue     # 营养成分表格组件
│   │   ├── IngredientList.vue     # 配料列表组件
│   │   ├── AnalysisCard.vue       # AI 分析卡片组件
│   │   └── RiskBadge.vue          # WHO 风险等级徽章
│   ├── services/
│   │   └── food.ts                # API 请求封装
│   ├── store/
│   │   └── product.ts             # Pinia product store
│   ├── utils/
│   │   └── scanner.ts             # 扫码工具
│   ├── types/
│   │   └── product.ts             # ProductDetail 等 TypeScript 类型
│   ├── App.vue
│   ├── main.ts
│   ├── pages.json                 # 路由配置
│   └── manifest.json              # 应用配置（appid 等）
├── .env.development               # 开发环境 API 地址
├── .env.production                # 生产环境 API 地址
├── vite.config.ts
└── package.json
```

---

### Task 1: 脚手架 uni-app 项目

**Files:**
- Create: `web/apps/uniapp/`（整个目录，通过 degit 初始化）

- [ ] **Step 1: 初始化 uni-app Vue 3 + Vite + TS 项目**

```bash
cd web/apps
pnpm dlx degit dcloudio/uni-preset-vue#vite-ts uniapp
cd uniapp
```

> 如果网络问题导致 degit 失败，可改用：
> ```bash
> pnpm create uni-app uniapp --template vite-ts
> ```

- [ ] **Step 2: 修改 `package.json` 设置包名**

将 `package.json` 中的 `name` 字段改为：

```json
{
  "name": "@acme/uniapp",
  ...
}
```

- [ ] **Step 3: 安装依赖**

```bash
cd web/apps/uniapp
pnpm install
```

- [ ] **Step 4: 验证 H5 开发模式可启动**

```bash
cd web/apps/uniapp
pnpm dev:h5
```

预期：Vite 启动，浏览器可访问 `http://localhost:5173`，看到默认 uni-app 页面。Ctrl+C 退出。

- [ ] **Step 5: Commit**

```bash
git add web/apps/uniapp
git commit -m "feat(uniapp): scaffold uni-app vite-ts project"
```

---

### Task 2: 安装 uview-plus 和 Pinia

**Files:**
- Modify: `web/apps/uniapp/package.json`
- Modify: `web/apps/uniapp/src/main.ts`
- Modify: `web/apps/uniapp/vite.config.ts`

- [ ] **Step 1: 安装依赖**

```bash
cd web/apps/uniapp
pnpm add uview-plus pinia
pnpm add -D @pinia/testing
```

- [ ] **Step 2: 在 `src/main.ts` 注册 uview-plus 和 Pinia**

```typescript
import { createSSRApp } from 'vue'
import * as Pinia from 'pinia'
import uviewPlus from 'uview-plus'
import App from './App.vue'

export function createApp() {
  const app = createSSRApp(App)
  app.use(Pinia.createPinia())
  app.use(uviewPlus)
  return {
    app,
    Pinia,
  }
}
```

- [ ] **Step 3: 在 `App.vue` 引入 uview-plus 样式**

```vue
<style lang="scss">
@import 'uview-plus/index.scss';
</style>
```

- [ ] **Step 4: 在 `vite.config.ts` 配置 uview-plus**

```typescript
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { uviewPlus } from 'uview-plus/lib/config/vite'

export default defineConfig({
  plugins: [
    uni(),
    uviewPlus(),
  ],
})
```

- [ ] **Step 5: 验证 H5 仍可启动**

```bash
cd web/apps/uniapp
pnpm dev:h5
```

预期：启动成功，无报错

- [ ] **Step 6: Commit**

```bash
git add web/apps/uniapp/
git commit -m "feat(uniapp): install uview-plus and pinia"
```

---

### Task 3: 类型定义

**Files:**
- Create: `web/apps/uniapp/src/types/product.ts`

- [ ] **Step 1: 新建 `src/types/product.ts`**

```typescript
export interface IngredientAnalysis {
  id: number
  analysis_type: string
  results: unknown
  level: 't0' | 't1' | 't2' | 't3' | 't4' | 'unknown'
}

export interface IngredientDetail {
  id: number
  name: string
  alias: string[]
  is_additive: boolean
  additive_code: string | null
  who_level: 'Group 1' | 'Group 2A' | 'Group 2B' | 'Group 3' | 'Group 4' | 'Unknown' | null
  allergen_info: string | null
  function_type: string | null
  standard_code: string | null
  analysis?: IngredientAnalysis
}

export interface NutritionDetail {
  name: string
  alias: string[]
  value: string
  value_unit: 'g' | 'mg' | 'kJ' | 'kcal' | 'mL'
  reference_type: 'PER_100_WEIGHT' | 'PER_100_ENERGY' | 'PER_SERVING' | 'PER_DAY'
  reference_unit: string
}

export interface AnalysisSummary {
  id: number
  analysis_type: string
  results: unknown
  level: 't0' | 't1' | 't2' | 't3' | 't4' | 'unknown'
}

export interface ProductDetail {
  id: number
  barcode: string
  name: string
  manufacturer: string | null
  origin_place: string | null
  shelf_life: string | null
  net_content: string | null
  image_url_list: string[]
  nutritions: NutritionDetail[]
  ingredients: IngredientDetail[]
  analysis: AnalysisSummary[]
}
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/types/
git commit -m "feat(uniapp): add ProductDetail TypeScript types"
```

---

### Task 4: 环境变量和 API 服务

**Files:**
- Create: `web/apps/uniapp/.env.development`
- Create: `web/apps/uniapp/.env.production`
- Create: `web/apps/uniapp/src/services/food.ts`

- [ ] **Step 1: 新建 `.env.development`**

```
VITE_API_BASE_URL=http://localhost:9999
```

- [ ] **Step 2: 新建 `.env.production`**

```
VITE_API_BASE_URL=https://your-api-domain.com
```

> 上线前将此处替换为实际部署域名。

- [ ] **Step 3: 新建 `src/services/food.ts`**

```typescript
import type { ProductDetail } from '../types/product'

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string

export class ProductNotFoundError extends Error {
  constructor(barcode: string) {
    super(`Product not found: ${barcode}`)
    this.name = 'ProductNotFoundError'
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

export async function fetchProductByBarcode(barcode: string): Promise<ProductDetail> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/api/product`,
      method: 'GET',
      data: { barcode },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data as ProductDetail)
        } else if (res.statusCode === 404) {
          reject(new ProductNotFoundError(barcode))
        } else {
          reject(new NetworkError(`Unexpected status: ${res.statusCode}`))
        }
      },
      fail(err) {
        reject(new NetworkError(err.errMsg ?? 'Network request failed'))
      },
    })
  })
}
```

- [ ] **Step 4: Commit**

```bash
git add web/apps/uniapp/.env.development web/apps/uniapp/.env.production web/apps/uniapp/src/services/
git commit -m "feat(uniapp): add env config and food API service"
```

---

### Task 5: Pinia Store + 扫码工具

**Files:**
- Create: `web/apps/uniapp/src/store/product.ts`
- Create: `web/apps/uniapp/src/utils/scanner.ts`

- [ ] **Step 1: 新建 `src/store/product.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ProductDetail } from '../types/product'
import { fetchProductByBarcode, ProductNotFoundError, NetworkError } from '../services/food'

type LoadingState = 'idle' | 'loading' | 'success' | 'not_found' | 'error'

export const useProductStore = defineStore('product', () => {
  const product = ref<ProductDetail | null>(null)
  const state = ref<LoadingState>('idle')
  const errorMessage = ref<string>('')

  async function loadProduct(barcode: string) {
    state.value = 'loading'
    product.value = null
    errorMessage.value = ''

    try {
      product.value = await fetchProductByBarcode(barcode)
      state.value = 'success'
    } catch (err) {
      if (err instanceof ProductNotFoundError) {
        state.value = 'not_found'
      } else if (err instanceof NetworkError) {
        state.value = 'error'
        errorMessage.value = err.message
      } else {
        state.value = 'error'
        errorMessage.value = 'Unknown error'
      }
    }
  }

  function reset() {
    product.value = null
    state.value = 'idle'
    errorMessage.value = ''
  }

  return { product, state, errorMessage, loadProduct, reset }
})
```

- [ ] **Step 2: 新建 `src/utils/scanner.ts`**

```typescript
export class ScanCancelledError extends Error {
  constructor() {
    super('Scan cancelled by user')
    this.name = 'ScanCancelledError'
  }
}

export async function scanBarcode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.scanCode({
      onlyFromCamera: true,
      success: (res) => resolve(res.result),
      fail: () => reject(new ScanCancelledError()),
    })
  })
}
```

- [ ] **Step 3: Commit**

```bash
git add web/apps/uniapp/src/store/ web/apps/uniapp/src/utils/
git commit -m "feat(uniapp): add product pinia store and scanner utility"
```

---

### Task 6: 路由配置（pages.json）

**Files:**
- Modify: `web/apps/uniapp/src/pages.json`

- [ ] **Step 1: 更新 `src/pages.json`**

uni-app 的 `pages.json` 支持条件编译注释，scan 页通过 `// #ifndef H5` 在 H5 构建中排除。将文件替换为：

```json
{
  "pages": [
    {
      "path": "pages/index/index",
      "style": {
        "navigationBarTitleText": "食品安全助手"
      }
    },
    // #ifndef H5
    {
      "path": "pages/scan/index",
      "style": {
        "navigationBarTitleText": "扫码"
      }
    },
    // #endif
    {
      "path": "pages/product/index",
      "style": {
        "navigationBarTitleText": "产品详情"
      }
    }
  ],
  "condition": {
    "current": 0,
    "list": [
      {
        "name": "首页",
        "path": "pages/index/index"
      }
    ]
  },
  "subPackages": [],
  "globalStyle": {
    "navigationBarTextStyle": "black",
    "navigationBarTitleText": "食品安全助手",
    "navigationBarBackgroundColor": "#FFFFFF",
    "backgroundColor": "#F8F8F8"
  },
  "uniIdRouter": {}
}
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/pages.json
git commit -m "feat(uniapp): configure pages routing with conditional scan page"
```

---

### Task 7: 首页

**Files:**
- Create: `web/apps/uniapp/src/pages/index/index.vue`

- [ ] **Step 1: 新建 `src/pages/index/index.vue`**

```vue
<template>
  <view class="index-page">
    <view class="hero">
      <text class="title">食品安全助手</text>
      <text class="subtitle">扫码查配料 · 了解你吃的每一口</text>
    </view>

    <!-- 小程序端：扫码按钮 -->
    <!-- #ifndef H5 -->
    <view class="actions">
      <up-button type="primary" @click="handleScan">扫码查成分</up-button>
    </view>
    <!-- #endif -->

    <!-- H5 端：手动输入 -->
    <!-- #ifdef H5 -->
    <view class="actions">
      <up-input
        v-model="manualBarcode"
        placeholder="输入条形码"
        clearable
      />
      <up-button
        type="primary"
        :disabled="!manualBarcode.trim()"
        @click="handleManualInput"
      >
        查询
      </up-button>
    </view>
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { scanBarcode, ScanCancelledError } from '../../utils/scanner'

const manualBarcode = ref('')

async function handleScan() {
  try {
    const barcode = await scanBarcode()
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` })
  } catch (err) {
    if (err instanceof ScanCancelledError) return
    uni.showToast({ title: '扫码失败，请重试', icon: 'error' })
  }
}

function handleManualInput() {
  const barcode = manualBarcode.value.trim()
  if (!barcode) return
  uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` })
}
</script>

<style lang="scss" scoped>
.index-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 40rpx;
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 80rpx;

  .title {
    font-size: 52rpx;
    font-weight: bold;
    color: #1a1a1a;
  }

  .subtitle {
    font-size: 28rpx;
    color: #888;
    margin-top: 16rpx;
  }
}

.actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/pages/index/
git commit -m "feat(uniapp): add index page with scan/manual input"
```

---

### Task 8: 扫码页

**Files:**
- Create: `web/apps/uniapp/src/pages/scan/index.vue`

- [ ] **Step 1: 新建 `src/pages/scan/index.vue`**

```vue
<template>
  <view class="scan-page">
    <text class="hint">正在启动扫码...</text>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { scanBarcode, ScanCancelledError } from '../../utils/scanner'

onMounted(async () => {
  try {
    const barcode = await scanBarcode()
    uni.redirectTo({ url: `/pages/product/index?barcode=${barcode}` })
  } catch (err) {
    if (err instanceof ScanCancelledError) {
      uni.navigateBack()
      return
    }
    uni.showToast({ title: '扫码失败，请重试', icon: 'error' })
    uni.navigateBack()
  }
})
</script>

<style lang="scss" scoped>
.scan-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;

  .hint {
    color: #888;
    font-size: 28rpx;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/pages/scan/
git commit -m "feat(uniapp): add scan page (mini program only)"
```

---

### Task 9: 通用子组件

**Files:**
- Create: `web/apps/uniapp/src/components/RiskBadge.vue`
- Create: `web/apps/uniapp/src/components/NutritionTable.vue`
- Create: `web/apps/uniapp/src/components/IngredientList.vue`
- Create: `web/apps/uniapp/src/components/AnalysisCard.vue`

- [ ] **Step 1: 新建 `src/components/RiskBadge.vue`**

```vue
<template>
  <view :class="['risk-badge', `risk-badge--${level}`]">
    <text>{{ label }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  whoLevel: string | null
}>()

const level = computed(() => {
  switch (props.whoLevel) {
    case 'Group 1': return 'critical'
    case 'Group 2A': return 'high'
    case 'Group 2B': return 'medium'
    case 'Group 3': return 'low'
    default: return 'unknown'
  }
})

const label = computed(() => props.whoLevel ?? '未知')
</script>

<style lang="scss" scoped>
.risk-badge {
  display: inline-flex;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 22rpx;

  &--critical { background: #fee2e2; color: #dc2626; }
  &--high     { background: #ffedd5; color: #ea580c; }
  &--medium   { background: #fef9c3; color: #ca8a04; }
  &--low      { background: #dcfce7; color: #16a34a; }
  &--unknown  { background: #f3f4f6; color: #6b7280; }
}
</style>
```

- [ ] **Step 2: 新建 `src/components/NutritionTable.vue`**

```vue
<template>
  <view class="nutrition-table">
    <view
      v-for="group in grouped"
      :key="group.label"
      class="group"
    >
      <text class="group-label">{{ group.label }}</text>
      <view class="row header">
        <text class="col-name">营养成分</text>
        <text class="col-value">每{{ group.referenceUnit }}</text>
      </view>
      <view
        v-for="item in group.items"
        :key="item.name"
        class="row"
      >
        <text class="col-name">{{ item.name }}</text>
        <text class="col-value">{{ item.value }} {{ item.value_unit }}</text>
      </view>
    </view>
    <text v-if="nutritions.length === 0" class="empty">暂无营养成分数据</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NutritionDetail } from '../types/product'

const props = defineProps<{ nutritions: NutritionDetail[] }>()

const REFERENCE_LABELS: Record<string, string> = {
  PER_100_WEIGHT: '每100g',
  PER_100_ENERGY: '每100kcal',
  PER_SERVING: '每份',
  PER_DAY: '每日',
}

const grouped = computed(() => {
  const map = new Map<string, NutritionDetail[]>()
  for (const n of props.nutritions) {
    const key = n.reference_type
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(n)
  }
  return [...map.entries()].map(([type, items]) => ({
    label: REFERENCE_LABELS[type] ?? type,
    referenceUnit: items[0]?.reference_unit ?? '',
    items,
  }))
})
</script>

<style lang="scss" scoped>
.nutrition-table {
  width: 100%;

  .group { margin-bottom: 32rpx; }

  .group-label {
    font-size: 26rpx;
    color: #888;
    margin-bottom: 8rpx;
    display: block;
  }

  .row {
    display: flex;
    justify-content: space-between;
    padding: 16rpx 0;
    border-bottom: 1rpx solid #f0f0f0;

    &.header { font-weight: bold; }
  }

  .col-name { font-size: 28rpx; color: #333; }
  .col-value { font-size: 28rpx; color: #555; }

  .empty { color: #aaa; font-size: 28rpx; }
}
</style>
```

- [ ] **Step 3: 新建 `src/components/IngredientList.vue`**

```vue
<template>
  <view class="ingredient-list">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['ingredient-item', isHighRisk(item.who_level) && 'ingredient-item--risk']"
    >
      <view class="ingredient-header">
        <text class="ingredient-name">{{ item.name }}</text>
        <RiskBadge :who-level="item.who_level" />
      </view>
      <text v-if="item.function_type" class="ingredient-meta">
        {{ item.function_type }}
      </text>
      <text v-if="item.allergen_info" class="ingredient-allergen">
        过敏提示：{{ item.allergen_info }}
      </text>
    </view>
    <text v-if="ingredients.length === 0" class="empty">暂无配料数据</text>
  </view>
</template>

<script setup lang="ts">
import type { IngredientDetail } from '../types/product'
import RiskBadge from './RiskBadge.vue'

defineProps<{ ingredients: IngredientDetail[] }>()

function isHighRisk(whoLevel: string | null): boolean {
  return whoLevel === 'Group 1' || whoLevel === 'Group 2A'
}
</script>

<style lang="scss" scoped>
.ingredient-list { width: 100%; }

.ingredient-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;

  &--risk { background: #fff8f8; border-radius: 8rpx; padding: 16rpx; }
}

.ingredient-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ingredient-name { font-size: 30rpx; color: #1a1a1a; }

.ingredient-meta {
  display: block;
  font-size: 24rpx;
  color: #888;
  margin-top: 6rpx;
}

.ingredient-allergen {
  display: block;
  font-size: 24rpx;
  color: #dc2626;
  margin-top: 6rpx;
}

.empty { color: #aaa; font-size: 28rpx; }
</style>
```

- [ ] **Step 4: 新建 `src/components/AnalysisCard.vue`**

```vue
<template>
  <view :class="['analysis-card', `analysis-card--${item.level}`]">
    <view class="card-header">
      <text class="card-title">{{ ANALYSIS_LABELS[item.analysis_type] ?? item.analysis_type }}</text>
      <view :class="['level-badge', `level-badge--${item.level}`]">
        <text>{{ LEVEL_LABELS[item.level] ?? item.level }}</text>
      </view>
    </view>
    <text class="card-content">{{ extractSummary(item.results) }}</text>
  </view>
</template>

<script setup lang="ts">
import type { AnalysisSummary } from '../types/product'

defineProps<{ item: AnalysisSummary }>()

const ANALYSIS_LABELS: Record<string, string> = {
  usage_advice_summary: '食用建议',
  health_summary: '健康分析',
  pregnancy_safety: '母婴安全',
  risk_summary: '风险分析',
  recent_risk_summary: '近期风险',
}

const LEVEL_LABELS: Record<string, string> = {
  t0: '低风险',
  t1: '较低',
  t2: '中等',
  t3: '较高',
  t4: '高风险',
  unknown: '信息不足',
}

function extractSummary(results: unknown): string {
  if (!results || typeof results !== 'object') return '暂无数据'
  const r = results as Record<string, unknown>
  if (typeof r.summary === 'string') return r.summary
  return JSON.stringify(results)
}
</script>

<style lang="scss" scoped>
.analysis-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  border-left: 6rpx solid #e5e7eb;

  &--t4 { border-left-color: #dc2626; }
  &--t3 { border-left-color: #ea580c; }
  &--t2 { border-left-color: #ca8a04; }
  &--t1 { border-left-color: #16a34a; }
  &--t0 { border-left-color: #22c55e; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.card-title { font-size: 30rpx; font-weight: bold; color: #1a1a1a; }

.level-badge {
  padding: 4rpx 16rpx;
  border-radius: 100rpx;
  font-size: 22rpx;

  &--t4 { background: #fee2e2; color: #dc2626; }
  &--t3 { background: #ffedd5; color: #ea580c; }
  &--t2 { background: #fef9c3; color: #ca8a04; }
  &--t1, &--t0 { background: #dcfce7; color: #16a34a; }
  &--unknown { background: #f3f4f6; color: #6b7280; }
}

.card-content { font-size: 28rpx; color: #555; line-height: 1.6; }
</style>
```

- [ ] **Step 5: Commit**

```bash
git add web/apps/uniapp/src/components/
git commit -m "feat(uniapp): add RiskBadge, NutritionTable, IngredientList, AnalysisCard components"
```

---

### Task 10: 产品详情页

**Files:**
- Create: `web/apps/uniapp/src/pages/product/index.vue`

- [ ] **Step 1: 新建 `src/pages/product/index.vue`**

```vue
<template>
  <view class="product-page">
    <!-- 加载中 -->
    <view v-if="store.state === 'loading'" class="status-center">
      <up-loading-icon mode="circle" />
      <text class="status-text">查询中...</text>
    </view>

    <!-- 未找到 -->
    <view v-else-if="store.state === 'not_found'" class="status-center">
      <text class="status-text">该产品暂未收录</text>
      <up-button size="small" @click="goBack">返回重新扫码</up-button>
    </view>

    <!-- 网络错误 -->
    <view v-else-if="store.state === 'error'" class="status-center">
      <text class="status-text">{{ store.errorMessage || '网络请求失败' }}</text>
      <up-button size="small" @click="load">重试</up-button>
    </view>

    <!-- 产品详情 -->
    <view v-else-if="store.product" class="content">
      <!-- 基础信息 -->
      <view class="product-header">
        <text class="product-name">{{ store.product.name }}</text>
        <view class="product-meta">
          <text v-if="store.product.manufacturer">{{ store.product.manufacturer }}</text>
          <text v-if="store.product.net_content"> · {{ store.product.net_content }}</text>
          <text v-if="store.product.shelf_life"> · {{ store.product.shelf_life }}</text>
        </view>
      </view>

      <!-- Tab 切换 -->
      <view class="tabs">
        <text
          v-for="tab in TABS"
          :key="tab.key"
          :class="['tab', activeTab === tab.key && 'tab--active']"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </text>
      </view>

      <!-- Tab 内容 -->
      <view class="tab-content">
        <NutritionTable
          v-if="activeTab === 'nutrition'"
          :nutritions="store.product.nutritions"
        />
        <IngredientList
          v-else-if="activeTab === 'ingredient'"
          :ingredients="store.product.ingredients"
        />
        <view v-else-if="activeTab === 'analysis'">
          <AnalysisCard
            v-for="item in store.product.analysis"
            :key="item.id"
            :item="item"
          />
          <text v-if="store.product.analysis.length === 0" class="empty">暂无分析数据</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProductStore } from '../../store/product'
import NutritionTable from '../../components/NutritionTable.vue'
import IngredientList from '../../components/IngredientList.vue'
import AnalysisCard from '../../components/AnalysisCard.vue'

type TabKey = 'nutrition' | 'ingredient' | 'analysis'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'nutrition', label: '营养' },
  { key: 'ingredient', label: '配料' },
  { key: 'analysis', label: '分析' },
]

const store = useProductStore()
const activeTab = ref<TabKey>('nutrition')

const barcode = ref('')

onMounted(() => {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  barcode.value = (current?.options as Record<string, string>)?.barcode ?? ''
  load()
})

function load() {
  if (barcode.value) {
    store.loadProduct(barcode.value)
  }
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.product-page { padding-bottom: 40rpx; }

.status-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 24rpx;
}

.status-text { font-size: 30rpx; color: #888; }

.product-header {
  padding: 32rpx 32rpx 0;

  .product-name {
    font-size: 36rpx;
    font-weight: bold;
    color: #1a1a1a;
    display: block;
  }

  .product-meta {
    font-size: 26rpx;
    color: #888;
    margin-top: 8rpx;
  }
}

.tabs {
  display: flex;
  border-bottom: 1rpx solid #e5e7eb;
  margin: 24rpx 0 0;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  font-size: 28rpx;
  color: #888;

  &--active {
    color: #1a1a1a;
    font-weight: bold;
    border-bottom: 4rpx solid #1a1a1a;
  }
}

.tab-content { padding: 24rpx 32rpx; }

.empty { color: #aaa; font-size: 28rpx; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/pages/product/
git commit -m "feat(uniapp): add product detail page with nutrition/ingredient/analysis tabs"
```

---

### Task 11: manifest.json 配置

**Files:**
- Modify: `web/apps/uniapp/src/manifest.json`

- [ ] **Step 1: 更新 `src/manifest.json`**

将以下字段填入（AppID 需上线前向各平台申请，开发阶段可留空）：

```json
{
  "name": "食品安全助手",
  "appid": "__UNI__XXXXXXX",
  "description": "扫码查配料，了解食品安全",
  "versionName": "1.0.0",
  "versionCode": "100",
  "transformPx": false,
  "mp-weixin": {
    "appid": "",
    "setting": {
      "urlCheck": false
    },
    "usingComponents": true
  },
  "mp-alipay": {
    "usingComponents": true
  },
  "mp-toutiao": {
    "usingComponents": true
  },
  "h5": {
    "devServer": {
      "port": 5173,
      "disableHostCheck": true
    },
    "router": {
      "mode": "hash"
    }
  }
}
```

> 上线前：向微信/支付宝/抖音开放平台分别申请 AppID，填入对应字段。

- [ ] **Step 2: Commit**

```bash
git add web/apps/uniapp/src/manifest.json
git commit -m "feat(uniapp): configure manifest.json for all target platforms"
```

---

### Task 12: 最终验证

- [ ] **Step 1: H5 构建验证**

```bash
cd web/apps/uniapp
pnpm build:h5
```

预期：`dist/build/h5/` 生成，无构建错误

- [ ] **Step 2: 微信小程序构建验证**

```bash
cd web/apps/uniapp
pnpm build:mp-weixin
```

预期：`dist/build/mp-weixin/` 生成，无构建错误

- [ ] **Step 3: 用微信开发者工具导入验证**

打开微信开发者工具 → 导入项目 → 选择 `dist/build/mp-weixin/` → 预览首页显示正常。

- [ ] **Step 4: 更新 web/pnpm-workspace.yaml 确认 uniapp 在 workspace 中**

```bash
cd web
pnpm list -r --depth 0 | grep uniapp
```

预期：显示 `@acme/uniapp`

- [ ] **Step 5: Final commit**

```bash
git add web/apps/uniapp/
git commit -m "feat(uniapp): complete uni-app setup, all pages and components"
```
