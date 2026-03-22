# Product Detail 页面实现计划 (UniApp)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 v14 设计原型落地为 UniApp 页面，替换现有的 Tab 结构 product 页面，严格遵循 `web/2026-design-system.md` 设计系统。

**Architecture:**
- UniApp + Vue 3 Composition API + SCSS
- 平台兼容：H5 + 微信/支付宝/抖音等小程序
- 采用「主页面 + 原子组件」拆分，每个组件单一职责
- 状态由 `store/product.ts` 提供，主页面组合渲染
- 使用 `onPageScroll` 实现滚动 header 毛玻璃效果
- **不使用原生导航栏**，页面 pages.json 中关闭原生导航栏，由自定义 header 替代

**Tech Stack:** Vue 3 + UniApp + uview-plus + Pinia + SCSS

---

## 文件清单

### 新建文件
- `src/components/ProductHeader.vue` — status-bar + 滚动 header + banner + 低风险徽章
- `src/components/NutritionCard.vue` — 营养成分卡片（网格 + 展开详情）
- `src/components/RiskGroup.vue` — 单个风险分组容器
- `src/components/IngredientCard.vue` — 配料横向滚动卡片
- `src/components/HealthBenefitCard.vue` — 健康益处卡片
- `src/components/AiAdviceCard.vue` — AI 建议卡片
- `src/components/BottomBar.vue` — 底部固定操作栏
- `src/styles/design-system.scss` — 全局 CSS 变量（暗/亮两套主题）

### 修改文件
- `src/pages/product/index.vue` — 完全重写，组合所有组件
- `src/pages.json` — 关闭原生导航栏，配置 statusBar 和 navigationStyle
- `src/styles/uni-theme.scss` — 新建，设计系统 CSS 变量入口
- `src/components/RiskBadge.vue` — 适配 v14 五级风险（t0/t1/t2/t3/t4/unknown）
- `src/components/AnalysisCard.vue` — 移除（v14 中已整合为 HealthBenefitCard + AiAdviceCard）

---

## 第一阶段：全局样式基础设施

### Task 1: 创建设计系统 SCSS 变量文件

**Files:**
- Create: `src/styles/design-system.scss`

- [ ] **Step 1: 创建文件**

```scss
// ============================================
// 2026 Design System — CSS Variables
// 使用方式：在组件 <style lang="scss"> 中 @import "~/@/styles/design-system.scss";
// ============================================

// ---- 暗色模式（默认）----
$dark-theme: true;

:root,
page {
  // 背景
  --bg-base: #{$dark-theme};
  --bg-card: #1a1a1a;
  --bg-card-hover: #222;
  // 文字
  --text-primary: #f5f5f5;
  --text-secondary: #a1a1a1;
  --text-muted: #6b7280;
  // 边框
  --border-color: rgba(255, 255, 255, 0.08);
  // 风险色
  --risk-t4: #ef4444;
  --risk-t3: #f97316;
  --risk-t2: #eab308;
  --risk-t0: #22c55e;
  --risk-unknown: #9ca3af;
  // 强调色
  --accent-pink: #ec4899;
  --accent-pink-light: #f472b6;
  // 营养卡片
  --nutrition-bg: rgba(34, 197, 94, 0.06);
  --nutrition-border: rgba(34, 197, 94, 0.1);
  --nutrition-glow: rgba(34, 197, 94, 0.3);
  // Header
  --header-bg: rgba(15, 15, 15, 0.0);
  --header-scrolled-bg: rgba(20, 20, 20, 0.88);
  // Banner
  --banner-label: #6b7280;
}

// 亮色模式（通过 .light-mode class 切换）
.light-mode {
  --bg-base: #f5f5f5;
  --bg-card: #ffffff;
  --bg-card-hover: #f9fafb;
  --text-primary: #111;
  --text-secondary: #4b5563;
  --text-muted: #9ca3af;
  --border-color: rgba(0, 0, 0, 0.06);
  --risk-t4: #dc2626;
  --risk-t3: #ea580c;
  --risk-t2: #ca8a04;
  --risk-t0: #16a34a;
  --risk-unknown: #9ca3af;
  --accent-pink: #db2777;
  --accent-pink-light: #ec4899;
  --nutrition-bg: rgba(34, 197, 94, 0.04);
  --nutrition-border: rgba(34, 197, 94, 0.12);
  --nutrition-glow: rgba(34, 197, 94, 0.2);
  --header-bg: rgba(255, 255, 255, 0.0);
  --header-scrolled-bg: rgba(255, 255, 255, 0.9);
  --banner-label: #92400e;
}

// ============================================
// 字体
// ============================================
$font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

// ============================================
// 间距（4px 网格）
// ============================================
$space-1: 4rpx;
$space-2: 8rpx;
$space-3: 12rpx;
$space-4: 16rpx;
$space-5: 20rpx;
$space-6: 24rpx;
$space-7: 28rpx;

// ============================================
// 圆角
// ============================================
$radius-sm: 12rpx;
$radius-md: 16rpx;
$radius-lg: 20rpx;
$radius-xl: 24rpx;
$radius-phone: 44rpx;

// ============================================
// 动画
// ============================================
$ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes floatIn {
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .banner-emoji,
  .nutrition-card,
  .health-card,
  .advice-card {
    animation: none !important;
    opacity: 1;
    transform: none;
  }
}
```

### Task 2: 修改 pages.json 关闭原生导航栏

**Files:**
- Modify: `src/pages.json`

- [ ] **Step 1: 更新 product 页面配置**

```json
{
  "path": "pages/product/index",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "",
    "navigationBarShow": false,
    "statusBarStyle": "dark",
    "statusBarHeight": "44px"
  }
}
```

同时在 `globalStyle` 中加入：
```json
"globalStyle": {
  "navigationStyle": "global",
  ...
}
```
确保其他页面保持原生导航栏。

---

## 第二阶段：RiskBadge 组件适配五级风险

### Task 3: 重构 RiskBadge 支持 t0–t4/unknown

**Files:**
- Modify: `src/components/RiskBadge.vue`

**原 RiskBadge 基于 WHO 等级（Group 1/2A 等），v14 需求是基于 `ingredient.analysis.level`（t0/t1/t2/t3/t4/unknown）显示。**

重构 props：传入 `level: "t0"|"t1"|"t2"|"t3"|"t4"|"unknown"` 直接渲染，不再从 WHO 等级转换。

- [ ] **Step 1: 重写 RiskBadge.vue**

```vue
<template>
  <view :class="['risk-dot-wrapper']" aria-hidden="true">
    <view :class="['risk-dot', `risk-dot--${level}`]"></view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
}>();
</script>

<style lang="scss" scoped>
.risk-dot-wrapper {
  display: inline-flex;
  align-items: center;
}

.risk-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;

  &--t4 { background: var(--risk-t4); }
  &--t3 { background: var(--risk-t3); }
  &--t2 { background: var(--risk-t2); }
  &--t1 { background: var(--risk-t1, #65a30d); }
  &--t0 { background: var(--risk-t0); }
  &--unknown { background: var(--risk-unknown); }
}
</style>
```

注意：`--risk-t1` 在亮/暗色中均未定义，若用到需在 design-system.scss 中补全。

---

## 第三阶段：核心页面组件

### Task 4: ProductHeader.vue — 顶部区域

**Files:**
- Create: `src/components/ProductHeader.vue`

Props: `{ name: string, imageUrl?: string, overallRiskLevel: string }`
Emits: `scroll(y: number)` 供父组件处理 header 状态

**结构：**
```
status-bar (44px)
header (position: fixed, 透明→毛玻璃)
banner (260px) — image 或 emoji + badge
```

**关键实现点：**
- `position: fixed` + `top: 0` + `z-index: 50`
- status-bar 用 `uni.getSystemInfoSync().statusBarHeight` 动态高度
- header 接收 `scrollTop` prop，超过 60px 时加 `.scrolled` class
- banner 背景：暗色用 `linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%)`，亮色用黄色渐变
- 低风险徽章用绿色，位置在 banner 右下角

- [ ] **Step 1: 创建 ProductHeader.vue**

```vue
<template>
  <view class="product-header">

    <!-- Header -->
    <view :class="['header', { 'header--scrolled': isScrolled }]" :style="headerStyle">
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <up-icon name="arrow-left" size="18" :color="isDark ? '#fff' : '#111'" />
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <up-icon name="share" size="18" :color="isDark ? '#fff' : '#111'" />
      </button>
    </view>

    <!-- Banner -->
    <view class="banner">
      <view class="banner-content">
        <image v-if="imageUrl" :src="imageUrl" class="banner-image" mode="aspectFill" />
        <text v-else class="banner-emoji">🍎</text>
        <text class="banner-label">产品图片</text>
      </view>
      <view class="banner-badge">
        <up-icon name="checkmark-circle" size="14" color="var(--risk-t0)" />
        <text class="banner-badge-text">低风险</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useSystemInfo } from "../../utils/system";

const props = defineProps<{
  name: string;
  imageUrl?: string;
  overallRiskLevel: string;
}>();

const emit = defineEmits<{
  (e: "scroll", y: number): void;
}>();

const { statusBarHeight, safeAreaTop } = useSystemInfo();
const isScrolled = ref(false);

const headerStyle = computed(() => ({
  top: `${statusBarHeight}px`,
}));

// 监听页面滚动（通过 emit 暴露给父组件）
// 实际滚动监听在 ProductPage.vue 的 onPageScroll 中处理

function handleBack() {
  uni.navigateBack();
}

function handleShare() {
  // #ifdef MP-WEIXIN
  uni.share({
    title: props.name,
    path: `/pages/product/index?name=${props.name}`,
  });
  // #endif
  // #ifdef H5
  uni.showToast({ title: "分享功能仅小程序可用", icon: "none" });
  // #endif
}

export function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}
</script>
```

### Task 5: NutritionCard.vue — 营养成分

**Files:**
- Create: `src/components/NutritionCard.vue`

**关键实现：**
- 2×2 网格展示（卡路里、蛋白质、脂肪、碳水）
- 数值 32px / 700，`font-variant-numeric: tabular-nums`
- 点击"查看详细营养成分"展开，显示膳食纤维、糖分、维生素C
- `aria-expanded` 状态通过 `ref` 切换
- 动画：`animation: slideUp 0.5s 0.1s $ease-spring forwards`，初始 `opacity: 0; transform: translateY(16rpx)`

- [ ] **Step 1: 创建 NutritionCard.vue**

```vue
<template>
  <view class="nutrition-card" :class="{ 'nutrition-card--expanded': isExpanded }">
    <view class="nutrition-grid">
      <view v-for="item in primaryNutritions" :key="item.name" class="nutrition-cell">
        <text class="nutrition-label">{{ item.name }}</text>
        <text class="nutrition-value">{{ item.value }}</text>
        <text class="nutrition-unit">{{ item.unit }}</text>
      </view>
    </view>
    <button
      type="button"
      class="nutrition-toggle"
      :aria-expanded="isExpanded"
      @click="toggle"
    >
      <text>{{ isExpanded ? "收起详细营养成分" : "查看详细营养成分" }}</text>
      <up-icon :name="isExpanded ? 'arrow-up' : 'arrow-down'" size="16" />
    </button>
    <view v-show="isExpanded" class="nutrition-details" :id="'nutrDetails'">
      <view v-for="item in detailNutritions" :key="item.name" class="nutrition-row">
        <text class="row-label">{{ item.name }}</text>
        <text class="row-value">{{ item.value }}{{ item.unit }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import type { NutritionDetail } from "../../types/product";

const props = defineProps<{ nutritions: NutritionDetail[] }>();
const isExpanded = ref(false);

const MAIN_KEYS = ["能量", "蛋白质", "脂肪", "碳水化合物"];

const primaryNutritions = computed(() =>
  props.nutritions
    .filter((n) => MAIN_KEYS.includes(n.name))
    .slice(0, 4)
    .map((n) => ({
      name: n.name,
      value: n.value,
      unit: n.value_unit === "kcal" ? "kcal" : n.value_unit,
    }))
);

const detailNutritions = computed(() =>
  props.nutritions
    .filter((n) => !MAIN_KEYS.includes(n.name))
    .map((n) => ({
      name: n.name,
      value: n.value,
      unit: n.value_unit,
    }))
);

function toggle() {
  isExpanded.value = !isExpanded.value;
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.nutrition-card {
  border-radius: $radius-xl;
  padding: 40rpx;
  background: var(--nutrition-bg);
  border: 1px solid var(--nutrition-border);
  margin-bottom: 56rpx;
  animation: slideUp 0.5s 0.1s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16rpx);
}

.nutrition-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40rpx;
  margin-bottom: 40rpx;
}

.nutrition-cell {
  display: flex;
  flex-direction: column;
}

.nutrition-label {
  font-size: 22rpx;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 4rpx;
}

.nutrition-value {
  font-size: 64rpx;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  color: var(--text-primary);
}

.nutrition-unit {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-top: 4rpx;
}

.nutrition-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  padding: 20rpx;
  background: transparent;
  border: none;
  font-size: 26rpx;
  font-family: inherit;
  color: var(--text-muted);
  border-radius: $radius-sm;

  &:focus-visible {
    outline: 2px solid var(--accent-pink);
    outline-offset: 4rpx;
  }
}

.nutrition-details {
  border-top: 1px solid var(--border-color);
  padding-top: 32rpx;
  margin-top: 8rpx;
}

.nutrition-row {
  display: flex;
  justify-content: space-between;
  padding: 20rpx 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 28rpx;

  &:last-child { border-bottom: none; }
}

.row-label { color: var(--text-secondary); }
.row-value {
  color: var(--text-primary);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
</style>
```

### Task 6: IngredientCard.vue — 配料滚动卡片

**Files:**
- Create: `src/components/IngredientCard.vue`

**关键实现：**
- 横向滚动容器：`display: flex; overflow-x: auto; scroll-snap-type: x mandatory`
- 隐藏滚动条：`-webkit-scrollbar { display: none }`
- 左侧 6rpx 风险色条（暗色加 glow，亮色不加）
- 卡片点击跳转 `/pages/ingredient/detail?id=xxx`

- [ ] **Step 1: 创建 IngredientCard.vue**

```vue
<template>
  <view class="ingredient-scroll">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['ingredient-card', `ingredient-card--${item.analysis?.level ?? 'unknown'}`]"
      @click="goToDetail(item.id)"
    >
      <view :class="['ingredient-risk-bar', `risk-bar--${item.analysis?.level ?? 'unknown'}`]"></view>
      <view class="ingredient-content">
        <view class="ingredient-name">
          <text>{{ item.name }}</text>
        </view>
        <view v-if="item.analysis" :class="['ingredient-reason', `reason--${item.analysis.level}`]">
          {{ getRiskReason(item.analysis) }}
        </view>
      </view>
      <view class="ingredient-arrow" aria-hidden="true">
        <up-icon name="arrow-right" size="14" color="var(--text-muted)" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { IngredientDetail } from "../../types/product";

defineProps<{ ingredients: IngredientDetail[] }>();

function getRiskReason(analysis: { analysis_type: string; results: unknown }): string {
  const r = analysis.results as Record<string, unknown>;
  if (typeof r.reason === "string") return r.reason;
  return "";
}

function goToDetail(id: number) {
  uni.navigateTo({ url: `/pages/ingredient/detail?id=${id}` });
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.ingredient-scroll {
  display: flex;
  gap: 20rpx;
  overflow-x: auto;
  padding-bottom: 8rpx;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;

  &::-webkit-scrollbar { display: none; }
}

.ingredient-card {
  flex: 0 0 auto;
  min-width: 280rpx;
  scroll-snap-align: start;
  border-radius: $radius-md;
  padding: 28rpx;
  position: relative;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-sizing: border-box;

  &:active { transform: scale(0.96); }

  &--t4 { border-color: rgba(239, 68, 68, 0.2); }
  &--t3 { border-color: rgba(249, 115, 22, 0.2); }
  &--t2 { border-color: rgba(234, 179, 8, 0.2); }
  &--t0 { border-color: rgba(34, 197, 94, 0.2); }
  &--unknown { border-color: rgba(156, 163, 175, 0.2); }
}

.ingredient-risk-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6rpx;

  &--t4 { background: var(--risk-t4); }
  &--t3 { background: var(--risk-t3); }
  &--t2 { background: var(--risk-t2); }
  &--t0 { background: var(--risk-t0); }
  &--unknown { background: var(--risk-unknown); }
}

.ingredient-content { padding-left: 16rpx; }

.ingredient-name {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.ingredient-reason {
  display: inline-flex;
  align-items: center;
  font-size: 20rpx;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
  margin-left: 16rpx;

  &--t4 { color: #fca5a5; background: rgba(239, 68, 68, 0.12); }
  &--t3 { color: #fdba74; background: rgba(249, 115, 22, 0.12); }
  &--t2 { color: #fde047; background: rgba(234, 179, 8, 0.12); }
}

.ingredient-arrow {
  position: absolute;
  right: 14rpx;
  top: 14rpx;
  opacity: 0.4;
}
</style>
```

### Task 7: RiskGroup.vue — 风险分组容器

**Files:**
- Create: `src/components/RiskGroup.vue`

**关键实现：**
- 根据 `level` 渲染对应颜色背景 + badge
- 内部 slot 放置 IngredientCard 横向滚动列表
- 风险 dot 带 glow 效果（暗色模式）

- [ ] **Step 1: 创建 RiskGroup.vue**

```vue
<template>
  <view v-if="ingredients.length > 0" :class="['risk-group', `risk-group--${level}`]">
    <view class="risk-header">
      <view :class="['risk-dot', `risk-dot--${level}`]"></view>
      <view :class="['risk-badge', `risk-badge--${level}`]">{{ levelLabel }}</view>
      <text class="risk-count">{{ ingredients.length }} 项</text>
    </view>
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
  ingredients: any[];
}>();

const LEVEL_LABELS: Record<string, string> = {
  t4: "严重风险",
  t3: "高风险",
  t2: "中风险",
  t0: "低风险",
  unknown: "未知",
};

const levelLabel = computed(() => LEVEL_LABELS[props.level] ?? props.level);
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.risk-group {
  border-radius: $radius-lg;
  padding: 32rpx;
  margin-bottom: 24rpx;
  position: relative;
  overflow: hidden;

  &--t4 { background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.15); }
  &--t3 { background: rgba(249, 115, 22, 0.08); border: 1px solid rgba(249, 115, 22, 0.15); }
  &--t2 { background: rgba(234, 179, 8, 0.08);  border: 1px solid rgba(234, 179, 8, 0.15); }
  &--t0 { background: rgba(34, 197, 94, 0.08);  border: 1px solid rgba(34, 197, 94, 0.15); }
  &--unknown { background: rgba(156, 163, 175, 0.08); border: 1px solid rgba(156, 163, 175, 0.15); }
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.risk-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;

  &--t4 { background: var(--risk-t4); box-shadow: 0 0 16rpx var(--risk-t4); }
  &--t3 { background: var(--risk-t3); box-shadow: 0 0 16rpx var(--risk-t3); }
  &--t2 { background: var(--risk-t2); box-shadow: 0 0 16rpx var(--risk-t2); }
  &--t0 { background: var(--risk-t0); box-shadow: 0 0 16rpx var(--risk-t0); }
  &--unknown { background: var(--risk-unknown); }
}

.risk-badge {
  font-size: 24rpx;
  font-weight: 600;
  padding: 8rpx 20rpx;
  border-radius: 16rpx;

  &--t4 { color: #fca5a5; background: rgba(239, 68, 68, 0.15); }
  &--t3 { color: #fdba74; background: rgba(249, 115, 22, 0.15); }
  &--t2 { color: #fde047; background: rgba(234, 179, 8, 0.15); }
  &--t0 { color: #86efac; background: rgba(34, 197, 94, 0.15); }
  &--unknown { color: #d1d5db; background: rgba(156, 163, 175, 0.15); }
}

.risk-count {
  margin-left: auto;
  font-size: 22rpx;
  color: var(--text-muted);
}
</style>
```

### Task 8: HealthBenefitCard.vue & AiAdviceCard.vue

**Files:**
- Create: `src/components/HealthBenefitCard.vue`
- Create: `src/components/AiAdviceCard.vue`

- [ ] **Step 1: HealthBenefitCard.vue**

```vue
<template>
  <view class="health-card">
    <view class="section-title">健康益处</view>
    <view v-if="items.length > 0" class="health-list">
      <view v-for="item in items" :key="item.id" class="health-item">
        <up-icon name="checkmark-circle" size="36rpx" color="var(--risk-t0)" />
        <text class="health-text">{{ extractSummary(item.results) }}</text>
      </view>
    </view>
    <text v-else class="empty">暂无健康益处数据</text>
  </view>
</template>

<script setup lang="ts">
import type { AnalysisSummary } from "../../types/product";

defineProps<{ items: AnalysisSummary[] }>();

function extractSummary(results: unknown): string {
  if (!results || typeof results !== "object") return "暂无数据";
  const r = results as Record<string, unknown>;
  if (typeof r.summary === "string") return r.summary;
  return JSON.stringify(results);
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.health-card {
  border-radius: $radius-lg;
  padding: 36rpx;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  margin-bottom: 56rpx;
  animation: slideUp 0.5s 0.3s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16rpx);
}

.section-title {
  font-size: 40rpx;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 28rpx;
}

.health-list { display: flex; flex-direction: column; gap: 28rpx; }

.health-item {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;
}

.health-text {
  font-size: 28rpx;
  line-height: 1.5;
  color: var(--text-secondary);
}

.empty { font-size: 28rpx; color: var(--text-muted); }
</style>
```

- [ ] **Step 2: AiAdviceCard.vue**

```vue
<template>
  <view class="advice-card">
    <view class="advice-header">
      <up-icon name="star-fill" size="18" color="#f59e0b" />
      <text>AI 健康建议</text>
    </view>
    <view v-if="items.length > 0" class="advice-list">
      <view v-for="item in items" :key="item.id" class="advice-item">
        <up-icon name="checkmark-circle" size="32rpx" color="var(--text-muted)" />
        <text>{{ extractAdvice(item.results) }}</text>
      </view>
    </view>
    <text v-else class="empty">暂无建议</text>
  </view>
</template>

<script setup lang="ts">
import type { AnalysisSummary } from "../../types/product";

defineProps<{ items: AnalysisSummary[] }>();

function extractAdvice(results: unknown): string {
  if (!results || typeof results !== "object") return "暂无建议";
  const r = results as Record<string, unknown>;
  if (typeof r.advice === "string") return r.advice;
  if (typeof r.summary === "string") return r.summary;
  return JSON.stringify(results);
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.advice-card {
  border-radius: $radius-lg;
  padding: 36rpx;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  margin-bottom: 56rpx;
  animation: slideUp 0.5s 0.4s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16rpx);
}

.advice-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 28rpx;
}

.advice-list { display: flex; flex-direction: column; gap: 24rpx; }

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 20rpx;
  font-size: 28rpx;
  color: var(--text-secondary);
  line-height: 1.5;
}

.empty { font-size: 28rpx; color: var(--text-muted); }
</style>
```

### Task 9: BottomBar.vue — 底部操作栏

**Files:**
- Create: `src/components/BottomBar.vue`

**关键实现：**
- `position: fixed; bottom: 0; left: 0; right: 0`
- 高度 176rpx（含底部安全区）+ safe-area-inset-bottom
- 毛玻璃：`backdrop-filter: blur(32rpx) saturate(180%)`
- "添加到记录"：次按钮样式（暗色透明+边框，亮色黑灰）
- "咨询 AI 助手"：主按钮（渐变粉色）

- [ ] **Step 1: 创建 BottomBar.vue**

```vue
<template>
  <view class="bottom-bar">
    <button type="button" class="action-btn action-btn--secondary" @click="handleAddRecord">
      添加到记录
    </button>
    <button type="button" class="action-btn action-btn--primary" @click="handleChat">
      咨询 AI 助手
    </button>
  </view>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  (e: "add-record"): void;
  (e: "chat"): void;
}>();

function handleAddRecord() {
  emit("add-record");
}

function handleChat() {
  emit("chat");
  uni.navigateTo({ url: "/pages/chat/index" });
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32rpx 40rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  display: flex;
  gap: 24rpx;
  z-index: 40;
  background: var(--bg-base);
  border-top: 1px solid var(--border-color);
  backdrop-filter: blur(32rpx) saturate(180%);
  -webkit-backdrop-filter: blur(32rpx) saturate(180%);
  box-shadow: 0 -16rpx 64rpx rgba(0, 0, 0, 0.4);
}

.action-btn {
  flex: 1;
  padding: 28rpx 32rpx;
  border-radius: 28rpx;
  font-size: 28rpx;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border: none;

  &:focus-visible {
    outline: 4rpx solid var(--accent-pink);
    outline-offset: 4rpx;
  }

  &--primary {
    color: #fff;
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    box-shadow: 0 8rpx 40rpx rgba(236, 72, 153, 0.3);
  }

  &--secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
  }
}
</style>
```

---

## 第四阶段：主页面组合

### Task 10: 重写 product/index.vue 主页面

**Files:**
- Modify: `src/pages/product/index.vue`（完全重写）

**关键实现：**
- 使用 `<scroll-view>` 替代原生页面滚动，处理 `onPageScroll`
- 组合所有子组件
- 配料按 `analysis.level` 分组传给 RiskGroup
- 健康益处/AI 建议从 `analysis` 数组中过滤 `analysis_type` 获取
- 状态加载/错误/空态复用现有 store

- [ ] **Step 1: 完全重写 pages/product/index.vue**

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
      <text class="status-text">{{ store.errorMessage || "网络请求失败" }}</text>
      <up-button size="small" @click="load">重试</up-button>
    </view>

    <!-- 产品详情 -->
    <template v-else-if="store.product">
      <ProductHeader
        :name="store.product.name"
        :image-url="store.product.image_url_list?.[0]"
        :overall-risk-level="overallRiskLevel"
        @scroll="handleScroll"
      />

      <scroll-view
        class="scroll-area"
        scroll-y
        @scroll="onScroll"
      >
        <view class="content">
          <!-- 营养成分 -->
          <NutritionCard :nutritions="store.product.nutritions" />

          <!-- 配料信息 -->
          <view class="section-title">配料信息</view>
          <RiskGroup
            v-for="(group, level) in groupedIngredients"
            :key="level"
            :level="level"
            :ingredients="group"
          >
            <IngredientCard :ingredients="group" />
          </RiskGroup>

          <!-- 健康益处 -->
          <HealthBenefitCard :items="healthItems" />

          <!-- AI 建议 -->
          <AiAdviceCard :items="adviceItems" />
        </view>
      </scroll-view>

      <BottomBar
        @add-record="handleAddRecord"
        @chat="handleChat"
      />
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import ProductHeader from "../../components/ProductHeader.vue";
import NutritionCard from "../../components/NutritionCard.vue";
import RiskGroup from "../../components/RiskGroup.vue";
import IngredientCard from "../../components/IngredientCard.vue";
import HealthBenefitCard from "../../components/HealthBenefitCard.vue";
import AiAdviceCard from "../../components/AiAdviceCard.vue";
import BottomBar from "../../components/BottomBar.vue";
import type { IngredientDetail } from "../../types/product";

const store = useProductStore();
const barcode = ref("");

const groupedIngredients = computed(() => {
  if (!store.product) return {};
  const groups: Record<string, IngredientDetail[]> = {
    t4: [], t3: [], t2: [], t1: [], t0: [], unknown: [],
  };
  for (const ing of store.product.ingredients) {
    const level = ing.analysis?.level ?? "unknown";
    if (!groups[level]) groups[level] = [];
    groups[level].push(ing);
  }
  return groups;
});

const healthItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) => a.analysis_type === "health_summary" || a.analysis_type === "health_benefits"
  )
);

const adviceItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) => a.analysis_type === "usage_advice_summary" || a.analysis_type === "advice"
  )
);

const overallRiskLevel = computed(() => {
  const ing = store.product?.ingredients ?? [];
  const levels = ing.map((i) => i.analysis?.level).filter(Boolean);
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0")) return "t0";
  return "unknown";
});

function onScroll(e: { detail: { scrollTop: number } }) {
  ProductHeader.updateScroll?.(e.detail.scrollTop);
}

function handleAddRecord() {
  // TODO: 写入本地记录
  uni.showToast({ title: "已添加到记录", icon: "success" });
}

function handleChat() {
  const name = store.product?.name ?? "";
  uni.navigateTo({ url: `/pages/chat/index?product=${encodeURIComponent(name)}` });
}

function goBack() { uni.navigateBack(); }

onMounted(() => {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  barcode.value = (current?.options as Record<string, string>)?.barcode ?? "";
  load();
});

function load() {
  if (barcode.value) store.loadProduct(barcode.value);
}
</script>

<style lang="scss" lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.product-page {
  min-height: 100vh;
  background: var(--bg-base);
}

.status-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 48rpx;
}

.status-text { font-size: 30rpx; color: var(--text-muted); }

.scroll-area {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.content {
  padding: calc(44px + 260px) 40rpx 200rpx;
}

.section-title {
  font-size: 40rpx;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 28rpx;
}
</style>
```

**注意：** 上述 `scroll-area` 定位需要根据 ProductHeader 的实际渲染高度调整。ProductHeader 高度 ≈ `statusBarHeight + 260px`，content padding-top 需要对应。

---

## 第五阶段：工具函数与收尾

### Task 11: 创建 systemInfo 工具

**Files:**
- Create: `src/utils/system.ts`

```ts
// 获取系统信息（安全封装）
export function useSystemInfo() {
  const info = uni.getSystemInfoSync();
  return {
    statusBarHeight: info.statusBarHeight ?? 44,
    safeAreaTop: info.safeArea?.top ?? 0,
    safeAreaBottom: info.safeArea?.bottom ?? 0,
    screenWidth: info.screenWidth ?? 375,
    screenHeight: info.screenHeight ?? 812,
    platform: info.platform,
  };
}
```

### Task 12: 修改 RiskBadge.vue 移除（保留备用）

现有 RiskBadge 在新架构中不再独立使用（风险 dot 已内联在 RiskGroup 中），可暂时保留，后续清理。

### Task 13: 验证与调试

- [ ] **Step 1: 运行 H5 开发服务器验证**
```bash
cd web && pnpm dev:h5
```
访问 http://localhost:5174，确认页面渲染正确。

- [ ] **Step 2: 检查控制台无 Error**
确认无 Vue 组件报错、无 SCSS 变量未定义警告。

- [ ] **Step 3: 测试滚动效果**
在开发者工具模拟器中测试 header 滚动毛玻璃效果。

---

## 实现顺序

```
Phase 1: 样式基础设施
  Task 1 → Task 2

Phase 2: 原子组件
  Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9

Phase 3: 主页面
  Task 10

Phase 4: 工具 + 收尾
  Task 11 → Task 12 → Task 13
```
