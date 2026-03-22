# 产品详情页重写实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按照 v14 设计稿从头重写 UniApp 产品详情页，确保视觉效果与设计稿一致。

**Architecture:** 删除 5 个细碎的旧组件，重写为 4 个文件：`ProductHeader.vue`（固定导航）、`IngredientSection.vue`（配料区）、`BottomBar.vue`（底部操作栏）、`pages/product/index.vue`（页面入口，内联 banner + 营养卡 + 健康/建议卡）。所有尺寸按设计稿 1px = 2rpx 换算，border 保持 1px。

**Tech Stack:** Vue 3 + UniApp + SCSS，pinia store，CSS 变量主题（`design-system.scss`）

**设计参考:** `.superpowers/brainstorm/23968-1774164668/product-detail-v14.html`（直接在浏览器打开比对）

**本地预览:** `http://localhost:5174/#/pages/product/index?barcode=6900000000001`（需先 `cd web && pnpm dev:uniapp:h5`）

---

## 文件清单

| 操作 | 文件 |
|------|------|
| **删除** | `web/apps/uniapp/src/components/NutritionCard.vue` |
| **删除** | `web/apps/uniapp/src/components/RiskGroup.vue` |
| **删除** | `web/apps/uniapp/src/components/IngredientCard.vue` |
| **删除** | `web/apps/uniapp/src/components/HealthBenefitCard.vue` |
| **删除** | `web/apps/uniapp/src/components/AiAdviceCard.vue` |
| **重写** | `web/apps/uniapp/src/components/BottomBar.vue` |
| **重写** | `web/apps/uniapp/src/components/ProductHeader.vue` |
| **新建** | `web/apps/uniapp/src/components/IngredientSection.vue` |
| **重写** | `web/apps/uniapp/src/pages/product/index.vue` |
| **修改** | `web/apps/uniapp/src/styles/design-system.scss` |
| **不动** | `web/apps/uniapp/src/store/product.ts` |
| **不动** | `web/apps/uniapp/src/types/product.ts` |
| **不动** | `web/apps/uniapp/src/utils/system.ts` |

---

## 数据结构速查

```typescript
// store: useProductStore()
store.product: ProductDetail | null
store.state: "idle" | "loading" | "success" | "not_found" | "error"
store.errorMessage: string

// ProductDetail
product.name: string
product.image_url_list: string[]          // 取 [0] 作为 banner 图
product.nutritions: NutritionDetail[]     // 营养成分列表
product.ingredients: IngredientDetail[]   // 配料列表
product.analysis: AnalysisSummary[]       // 分析结果

// NutritionDetail
nutrition.name: string                    // "能量" | "蛋白质" | "脂肪" | "碳水化合物" | ...
nutrition.value: string
nutrition.value_unit: "g" | "mg" | "kJ" | "kcal" | "mL"

// IngredientDetail
ingredient.id: number
ingredient.name: string
ingredient.analysis?.level: "t0"|"t1"|"t2"|"t3"|"t4"|"unknown"
ingredient.analysis?.results: unknown     // { reason?: string, ... }

// AnalysisSummary
analysis.analysis_type: string            // "health_summary"|"health_benefits"|"usage_advice_summary"|"advice"
analysis.results: unknown                 // { summary?: string, advice?: string }
```

---

## Task 1: 清理旧组件，建立干净起点

**Files:**
- Delete: `web/apps/uniapp/src/components/NutritionCard.vue`
- Delete: `web/apps/uniapp/src/components/RiskGroup.vue`
- Delete: `web/apps/uniapp/src/components/IngredientCard.vue`
- Delete: `web/apps/uniapp/src/components/HealthBenefitCard.vue`
- Delete: `web/apps/uniapp/src/components/AiAdviceCard.vue`
- Modify: `web/apps/uniapp/src/pages/product/index.vue`

- [ ] **Step 1: 删除旧组件文件**

```bash
cd web/apps/uniapp/src/components
rm NutritionCard.vue RiskGroup.vue IngredientCard.vue HealthBenefitCard.vue AiAdviceCard.vue
```

- [ ] **Step 2: 清空 product/index.vue 为最小骨架**

将 `web/apps/uniapp/src/pages/product/index.vue` 替换为以下骨架（仅保留 loading/error/not_found 状态，成功状态只显示占位文字，后续任务逐步填入）：

```vue
<template>
  <view class="product-page dark-mode">
    <ProductHeader
      ref="headerRef"
      :name="store.product?.name ?? ''"
      :overall-risk-level="overallRiskLevel"
    />

    <view v-if="store.state === 'loading'" class="status-center">
      <up-loading-icon mode="circle" />
      <text class="status-text">查询中...</text>
    </view>

    <view v-else-if="store.state === 'not_found'" class="status-center">
      <text class="status-text">该产品暂未收录</text>
      <button type="button" class="retry-btn" @click="goBack">返回重新扫码</button>
    </view>

    <view v-else-if="store.state === 'error'" class="status-center">
      <text class="status-text">{{ store.errorMessage || '网络请求失败' }}</text>
      <button type="button" class="retry-btn" @click="load">重试</button>
    </view>

    <scroll-view
      v-else-if="store.product"
      class="scroll-area"
      scroll-y
      @scroll="onScroll"
    >
      <text style="color: red; padding: 40rpx; display: block;">TODO: 内容区（Task 5 填入）</text>
    </scroll-view>

    <BottomBar @add-record="handleAddRecord" @chat="handleChat" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import ProductHeader from "../../components/ProductHeader.vue";
import BottomBar from "../../components/BottomBar.vue";

const store = useProductStore();
const headerRef = ref<any>(null);
const barcode = ref("");

onMounted(() => {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  barcode.value = (current?.options as Record<string, string>)?.barcode ?? "";
  load();
});

function load() {
  if (barcode.value) store.loadProduct(barcode.value);
}

function goBack() {
  uni.navigateBack();
}

function onScroll(e: { detail: { scrollTop: number } }) {
  headerRef.value?.updateScroll(e.detail.scrollTop);
}

function handleAddRecord() {
  uni.showToast({ title: "已添加到记录", icon: "success" });
}

function handleChat() {
  const name = store.product?.name ?? "";
  uni.navigateTo({ url: `/pages/chat/index?product=${encodeURIComponent(name)}` });
}

const overallRiskLevel = computed(() => {
  const levels = (store.product?.ingredients ?? [])
    .map((i) => i.analysis?.level)
    .filter(Boolean) as string[];
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0")) return "t0";
  return "unknown";
});
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.product-page {
  min-height: 100vh;
  background: var(--bg-base);
}

.scroll-area {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  background: var(--bg-base);
}

.status-center {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 48rpx;
  z-index: 10;
  background: var(--bg-base);
}

.status-text {
  font-size: 30rpx;
  color: var(--text-muted);
}

.retry-btn {
  padding: 24rpx 64rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  font-weight: 500;
  font-family: inherit;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}
</style>
```

- [ ] **Step 3: 确认页面不报错**

打开 `http://localhost:5174/#/pages/product/index?barcode=6900000000001`，页面应显示红色"TODO"占位文字，无控制台报错。

- [ ] **Step 4: 提交**

```bash
git add web/apps/uniapp/src/
git commit -m "refactor(uniapp): remove old components, scaffold product page for rewrite"
```

---

## Task 2: 重写 BottomBar.vue

**Files:**
- Rewrite: `web/apps/uniapp/src/components/BottomBar.vue`

- [ ] **Step 1: 完整重写 BottomBar.vue**

```vue
<script setup lang="ts">
const emit = defineEmits<{
  (e: 'add-record'): void;
  (e: 'chat'): void;
}>();
</script>

<template>
  <view class="bottom-bar">
    <button type="button" class="action-btn action-btn--secondary" @click="emit('add-record')">
      添加到记录
    </button>
    <button type="button" class="action-btn action-btn--primary" @click="emit('chat')">
      咨询 AI 助手
    </button>
  </view>
</template>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

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
  background: var(--bottom-bar-bg);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
}

.action-btn {
  flex: 1;
  padding: 28rpx 32rpx;
  border-radius: 28rpx;
  font-size: 28rpx;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s $ease-spring;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  line-height: 1.2;

  &:active {
    transform: scale(0.97);
  }

  &:focus-visible {
    outline: 2px solid var(--accent-pink);
    outline-offset: 2px;
  }

  &--primary {
    color: #fff;
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    box-shadow: 0 4px 20px rgba(236, 72, 153, 0.3);

    &:active {
      box-shadow: 0 6px 28px rgba(236, 72, 153, 0.4);
    }
  }

  &--secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary);

    // 亮色模式覆盖
    .product-page:not(.dark-mode) & {
      background: rgba(0, 0, 0, 0.04);
      border-color: rgba(0, 0, 0, 0.08);
    }
  }
}
</style>
```

- [ ] **Step 2: 浏览器验证**

在 `http://localhost:5174/#/pages/product/index?barcode=6900000000001` 检查：
- 底部出现两个按钮，毛玻璃背景
- "添加到记录"有淡白色背景和细边框
- "咨询 AI 助手"是粉色渐变
- 点击有缩放动效

- [ ] **Step 3: 提交**

```bash
git add web/apps/uniapp/src/components/BottomBar.vue
git commit -m "feat(uniapp): rewrite BottomBar per v14 design"
```

---

## Task 3: 重写 ProductHeader.vue

**Files:**
- Rewrite: `web/apps/uniapp/src/components/ProductHeader.vue`

- [ ] **Step 1: 完整重写 ProductHeader.vue**

```vue
<template>
  <view class="product-header">
    <view
      class="header"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: statusBarHeight + 'px' }"
    >
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
        </svg>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useSystemInfo } from "../utils/system";

interface Props {
  name: string;
  overallRiskLevel: string;
}

defineProps<Props>();

const { statusBarHeight } = useSystemInfo();
const isScrolled = ref(false);

function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}

defineExpose({ updateScroll });

function handleBack() {
  uni.navigateBack();
}

function handleShare() {
  // TODO: share
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.product-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  pointer-events: none;
}

.header {
  position: fixed;
  left: 0;
  right: 0;
  padding: 16rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
  background: transparent;
  transition: background 0.4s $ease-spring, box-shadow 0.4s $ease-spring;
  pointer-events: auto;

  &--scrolled {
    background: var(--header-scrolled-bg);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 1px 0 rgba(255, 255, 255, 0.06);

    // 亮色模式 shadow
    .product-page:not(.dark-mode) & {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(0, 0, 0, 0.04);
    }
  }
}

.header-btn {
  width: 80rpx;
  height: 80rpx;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
  flex-shrink: 0;
  color: #ffffff;
  transition: all 0.2s ease;

  .header--scrolled & {
    color: var(--text-primary);
  }

  &:active {
    transform: scale(0.92);
    background: rgba(128, 128, 128, 0.15);
  }

  &:focus-visible {
    outline: 2px solid var(--accent-pink);
    outline-offset: 2px;
  }

  svg {
    width: 36rpx;
    height: 36rpx;
    stroke-width: 2;
  }
}

.header-title {
  flex: 1;
  font-size: 34rpx;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  transition: color 0.3s, text-shadow 0.3s;

  .header--scrolled & {
    color: var(--text-primary);
    text-shadow: none;
  }
}
</style>
```

- [ ] **Step 2: 浏览器验证**

在 `http://localhost:5174/#/pages/product/index?barcode=6900000000001`：
- Header 透明叠在页面顶部，白色返回/分享图标可见
- 手动在浏览器 DevTools 执行 `document.querySelectorAll(".uni-scroll-view")[1].scrollTop=200` 后，header 变为毛玻璃背景，图标变色

- [ ] **Step 3: 提交**

```bash
git add web/apps/uniapp/src/components/ProductHeader.vue
git commit -m "feat(uniapp): rewrite ProductHeader per v14 design"
```

---

## Task 4: 新建 IngredientSection.vue

**Files:**
- Create: `web/apps/uniapp/src/components/IngredientSection.vue`

- [ ] **Step 1: 创建 IngredientSection.vue**

```vue
<template>
  <view class="ingredient-section">
    <view
      v-for="levelKey in LEVEL_ORDER"
      :key="levelKey"
      v-if="groupedIngredients[levelKey]?.length"
      :class="['risk-group', levelKey]"
    >
      <!-- 组头 -->
      <view class="risk-header">
        <view :class="['risk-dot', levelKey]" />
        <view :class="['risk-badge', levelKey]">{{ LEVEL_LABELS[levelKey] }}</view>
        <text class="risk-count">{{ groupedIngredients[levelKey].length }} 项</text>
      </view>

      <!-- 横向滚动配料卡 -->
      <view class="ingredient-scroll">
        <view
          v-for="item in groupedIngredients[levelKey]"
          :key="item.id"
          :class="['ingredient-card', levelKey]"
          @click="goToDetail(item.id)"
        >
          <!-- 左侧风险色条 -->
          <view :class="['risk-bar', levelKey]" />

          <!-- 右上角装饰圆（CSS ::before 实现） -->

          <!-- 右上角箭头 -->
          <view class="ingredient-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M9 5l7 7-7 7"/>
            </svg>
          </view>

          <!-- 内容 -->
          <view class="ingredient-content">
            <view class="ingredient-name">
              <!-- 低风险：叶子图标（stroke） -->
              <svg v-if="levelKey === 't0'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon" aria-hidden="true">
                <path d="M6.5 21C3 17.5 3 12 6 8c2-2.5 5-4 8.5-4C18 4 21 7 21 10c0 2.5-1.5 4.5-3.5 5.5"/>
                <path d="M12 22V12"/>
              </svg>
              <!-- 未知：问号圆（fill） -->
              <svg v-else-if="levelKey === 'unknown'" viewBox="0 0 20 20" class="icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
              </svg>
              <!-- 其余：警告三角（fill） -->
              <svg v-else viewBox="0 0 20 20" class="icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
              <text class="ingredient-name-text">{{ item.name }}</text>
            </view>
            <view v-if="getReason(item)" :class="['ingredient-reason', levelKey]">
              {{ getReason(item) }}
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { IngredientDetail } from "../types/product";

const props = defineProps<{ ingredients: IngredientDetail[] }>();

const LEVEL_ORDER = ["t4", "t3", "t2", "t0", "unknown"] as const;

const LEVEL_LABELS: Record<string, string> = {
  t4: "严重风险",
  t3: "高风险",
  t2: "中风险",
  t0: "低风险",
  unknown: "未知",
};

const groupedIngredients = computed(() => {
  const groups: Record<string, IngredientDetail[]> = {
    t4: [], t3: [], t2: [], t0: [], unknown: [],
  };
  for (const ing of props.ingredients) {
    const level = ing.analysis?.level ?? "unknown";
    const key = level === "t1" ? "t0" : level; // t1 归入 t0
    if (groups[key]) groups[key].push(ing);
    else groups["unknown"].push(ing);
  }
  return groups;
});

function getReason(item: IngredientDetail): string {
  if (!item.analysis?.results) return "";
  const r = item.analysis.results as Record<string, unknown>;
  if (typeof r.reason === "string") return r.reason;
  return "";
}

function goToDetail(id: number) {
  uni.navigateTo({ url: `/pages/ingredient/detail?id=${id}` });
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

// ── 风险分组容器 ──────────────────────────────────────
.risk-group {
  border-radius: 40rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  position: relative;
  overflow: hidden;

  &.t4 { background: var(--risk-t4-bg); border: 1px solid var(--risk-t4-border); }
  &.t3 { background: var(--risk-t3-bg); border: 1px solid var(--risk-t3-border); }
  &.t2 { background: var(--risk-t2-bg); border: 1px solid var(--risk-t2-border); }
  &.t0 { background: var(--risk-t0-bg); border: 1px solid var(--risk-t0-border); }
  &.unknown { background: var(--risk-unknown-bg); border: 1px solid var(--risk-unknown-border); }
}

// ── 组头 ──────────────────────────────────────────────
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
  flex-shrink: 0;

  &.t4 { background: var(--risk-t4); box-shadow: 0 0 8px var(--risk-t4); }
  &.t3 { background: var(--risk-t3); box-shadow: 0 0 8px var(--risk-t3); }
  &.t2 { background: var(--risk-t2); box-shadow: 0 0 8px var(--risk-t2); }
  &.t0 { background: var(--risk-t0); box-shadow: 0 0 8px var(--risk-t0); }
  &.unknown { background: var(--risk-unknown); }
}

.risk-badge {
  font-size: 24rpx;
  font-weight: 600;
  padding: 8rpx 20rpx;
  border-radius: 16rpx;

  .t4 & { color: var(--risk-t4); background: rgba(239, 68, 68, 0.15); }
  .t3 & { color: var(--risk-t3); background: rgba(249, 115, 22, 0.15); }
  .t2 & { color: var(--risk-t2); background: rgba(234, 179, 8, 0.15); }
  .t0 & { color: var(--risk-t0); background: rgba(34, 197, 94, 0.15); }
  .unknown & { color: var(--risk-unknown); background: rgba(156, 163, 175, 0.15); }
}

.risk-count {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-left: auto;
}

// ── 横向滚动 ──────────────────────────────────────────
.ingredient-scroll {
  display: flex;
  gap: 20rpx;
  overflow-x: auto;
  padding-bottom: 8rpx;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar { display: none; }
}

// ── 配料卡片 ──────────────────────────────────────────
.ingredient-card {
  flex: 0 0 auto;
  min-width: 280rpx;
  scroll-snap-align: start;
  border-radius: 32rpx;
  padding: 28rpx 28rpx 28rpx 28rpx;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s $ease-spring;
  box-sizing: border-box;
  background: var(--bg-card);
  border: 1px solid var(--border-color);

  &.t4 { border-color: var(--risk-t4-border); }
  &.t3 { border-color: var(--risk-t3-border); }
  &.t2 { border-color: var(--risk-t2-border); }
  &.t0 { border-color: var(--risk-t0-border); }
  &.unknown { border-color: var(--risk-unknown-border); }

  &:active { transform: scale(0.96); }

  // 右上角装饰圆
  &::before {
    content: "";
    position: absolute;
    top: -30rpx;
    right: -30rpx;
    width: 100rpx;
    height: 100rpx;
    border-radius: 50%;
    opacity: 0.1;
  }
  &.t4::before { background: var(--risk-t4); }
  &.t3::before { background: var(--risk-t3); }
  &.t2::before { background: var(--risk-t2); }
  &.t0::before { background: var(--risk-t0); }
  &.unknown::before { background: var(--risk-unknown); }
}

// ── 左侧风险色条 ──────────────────────────────────────
.risk-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6rpx;

  .t4 & { background: var(--risk-t4); box-shadow: 0 0 16rpx var(--risk-t4); }
  .t3 & { background: var(--risk-t3); box-shadow: 0 0 16rpx var(--risk-t3); }
  .t2 & { background: var(--risk-t2); box-shadow: 0 0 16rpx var(--risk-t2); }
  .t0 & { background: var(--risk-t0); box-shadow: 0 0 16rpx var(--risk-t0); }
  .unknown & { background: var(--risk-unknown); }
}

// ── 右上角箭头 ────────────────────────────────────────
.ingredient-arrow {
  position: absolute;
  right: 14rpx;
  top: 14rpx;
  width: 28rpx;
  height: 28rpx;
  opacity: 0.4;
  color: var(--text-muted);

  svg { width: 28rpx; height: 28rpx; }
}

// ── 内容区 ────────────────────────────────────────────
.ingredient-content {
  display: flex;
  flex-direction: column;
  padding-left: 16rpx;
}

.ingredient-name {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;

  .icon {
    width: 28rpx;
    height: 28rpx;
    flex-shrink: 0;
  }

  // 图标颜色
  .t4 & .icon { fill: var(--risk-t4); }
  .t3 & .icon { fill: var(--risk-t3); }
  .t2 & .icon { fill: var(--risk-t2); }
  .t0 & .icon { stroke: var(--risk-t0); fill: none; }
  .unknown & .icon { fill: var(--risk-unknown); }
}

.ingredient-name-text {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-primary);
}

// ── 原因标签 ──────────────────────────────────────────
.ingredient-reason {
  display: inline-flex;
  align-items: center;
  font-size: 20rpx;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
  align-self: flex-start;

  &.t4 { color: var(--risk-t4); background: rgba(239, 68, 68, 0.12); }
  &.t3 { color: var(--risk-t3); background: rgba(249, 115, 22, 0.12); }
  &.t2 { color: var(--risk-t2); background: rgba(234, 179, 8, 0.12); }
  &.t0 { color: var(--risk-t0); background: rgba(34, 197, 94, 0.12); }
  &.unknown { color: var(--risk-unknown); background: rgba(156, 163, 175, 0.12); }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/IngredientSection.vue
git commit -m "feat(uniapp): add IngredientSection component per v14 design"
```

---

## Task 5: 重写 product/index.vue（主体内容区）

**Files:**
- Rewrite: `web/apps/uniapp/src/pages/product/index.vue`

这是最大的一个任务，将 banner + 营养卡 + 健康/建议卡全部内联在页面文件中。

- [ ] **Step 1: 完整重写 product/index.vue**

```vue
<template>
  <view class="product-page dark-mode">
    <ProductHeader
      ref="headerRef"
      :name="store.product?.name ?? ''"
      :overall-risk-level="overallRiskLevel"
    />

    <!-- 加载中 -->
    <view v-if="store.state === 'loading'" class="status-center">
      <up-loading-icon mode="circle" />
      <text class="status-text">查询中...</text>
    </view>

    <!-- 未找到 -->
    <view v-else-if="store.state === 'not_found'" class="status-center">
      <text class="status-text">该产品暂未收录</text>
      <button type="button" class="retry-btn" @click="goBack">返回重新扫码</button>
    </view>

    <!-- 错误 -->
    <view v-else-if="store.state === 'error'" class="status-center">
      <text class="status-text">{{ store.errorMessage || '网络请求失败' }}</text>
      <button type="button" class="retry-btn" @click="load">重试</button>
    </view>

    <!-- 成功 -->
    <scroll-view
      v-else-if="store.product"
      class="scroll-area"
      scroll-y
      @scroll="onScroll"
    >
      <!-- ── Banner ─────────────────────────────────── -->
      <view class="banner">
        <image
          v-if="store.product.image_url_list?.[0]"
          :src="store.product.image_url_list[0]"
          class="banner-img"
          mode="aspectFill"
        />
        <view v-else class="banner-placeholder">
          <text class="banner-emoji">🍎</text>
          <text class="banner-label">产品图片</text>
        </view>
        <view class="banner-badge" :class="overallRiskLevel">
          <svg viewBox="0 0 20 20" class="badge-icon" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <text class="badge-text">{{ riskLabel }}</text>
        </view>
      </view>

      <!-- ── 内容区 ────────────────────────────────── -->
      <view class="content">

        <!-- 营养成分 -->
        <text class="section-title">营养成分</text>
        <view class="nutrition-card">
          <view class="nutrition-grid">
            <view v-for="item in primaryNutritions" :key="item.name" class="nutrition-cell">
              <text class="nutrition-label">{{ item.name }}</text>
              <text class="nutrition-value">{{ item.value }}</text>
              <text class="nutrition-unit">{{ item.value_unit }}</text>
            </view>
          </view>
          <button
            type="button"
            class="nutrition-toggle"
            :class="{ expanded: nutrExpanded }"
            :aria-expanded="nutrExpanded"
            @click="nutrExpanded = !nutrExpanded"
          >
            <text>{{ nutrExpanded ? '收起详细营养成分' : '查看详细营养成分' }}</text>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron" aria-hidden="true">
              <path d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          <view v-show="nutrExpanded" class="nutrition-details">
            <view v-for="item in detailNutritions" :key="item.name" class="nutrition-row">
              <text class="row-label">{{ item.name }}</text>
              <text class="row-value">{{ item.value }}{{ item.value_unit }}</text>
            </view>
          </view>
        </view>

        <!-- 配料信息 -->
        <text class="section-title">配料信息</text>
        <IngredientSection :ingredients="store.product.ingredients" />

        <!-- 健康益处 -->
        <text class="section-title">健康益处</text>
        <view class="analysis-card">
          <view v-if="healthItems.length > 0" class="analysis-list">
            <view v-for="item in healthItems" :key="item.id" class="analysis-item">
              <svg viewBox="0 0 20 20" class="item-icon item-icon--check" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <text class="item-text">{{ extractText(item.results, 'summary') }}</text>
            </view>
          </view>
          <text v-else class="empty-text">暂无健康益处数据</text>
        </view>

        <!-- 食用建议 -->
        <text class="section-title">食用建议</text>
        <view class="analysis-card">
          <view class="advice-header">
            <svg viewBox="0 0 20 20" class="star-icon" aria-hidden="true">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            <text>AI 健康建议</text>
          </view>
          <view v-if="adviceItems.length > 0" class="analysis-list">
            <view v-for="item in adviceItems" :key="item.id" class="analysis-item">
              <svg viewBox="0 0 20 20" class="item-icon item-icon--dot" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <text class="item-text">{{ extractText(item.results, 'advice', 'summary') }}</text>
            </view>
          </view>
          <text v-else class="empty-text">暂无食用建议</text>
        </view>

      </view>
    </scroll-view>

    <BottomBar @add-record="handleAddRecord" @chat="handleChat" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import type { NutritionDetail, AnalysisSummary } from "../../types/product";
import ProductHeader from "../../components/ProductHeader.vue";
import IngredientSection from "../../components/IngredientSection.vue";
import BottomBar from "../../components/BottomBar.vue";

const store = useProductStore();
const headerRef = ref<any>(null);
const barcode = ref("");
const nutrExpanded = ref(false);

const MAIN_NUTRITION_KEYS = ["能量", "蛋白质", "脂肪", "碳水化合物"];

const RISK_LABELS: Record<string, string> = {
  t4: "严重风险", t3: "高风险", t2: "中风险", t0: "低风险", unknown: "风险未知",
};

onMounted(() => {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  barcode.value = (current?.options as Record<string, string>)?.barcode ?? "";
  load();
});

function load() {
  if (barcode.value) store.loadProduct(barcode.value);
}

function goBack() { uni.navigateBack(); }

function onScroll(e: { detail: { scrollTop: number } }) {
  headerRef.value?.updateScroll(e.detail.scrollTop);
}

function handleAddRecord() {
  uni.showToast({ title: "已添加到记录", icon: "success" });
}

function handleChat() {
  const name = store.product?.name ?? "";
  uni.navigateTo({ url: `/pages/chat/index?product=${encodeURIComponent(name)}` });
}

function extractText(results: unknown, ...keys: string[]): string {
  if (!results || typeof results !== "object") return "";
  const r = results as Record<string, unknown>;
  for (const key of keys) {
    if (typeof r[key] === "string") return r[key] as string;
  }
  return "";
}

// ── Computed ─────────────────────────────────────────

const overallRiskLevel = computed(() => {
  const levels = (store.product?.ingredients ?? [])
    .map((i) => i.analysis?.level).filter(Boolean) as string[];
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0")) return "t0";
  return "unknown";
});

const riskLabel = computed(() => RISK_LABELS[overallRiskLevel.value] ?? "风险未知");

const primaryNutritions = computed(() =>
  (store.product?.nutritions ?? []).filter((n) => MAIN_NUTRITION_KEYS.includes(n.name))
);

const detailNutritions = computed(() =>
  (store.product?.nutritions ?? []).filter((n) => !MAIN_NUTRITION_KEYS.includes(n.name))
);

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
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

// ── 页面基础 ──────────────────────────────────────────
.product-page {
  min-height: 100vh;
  background: var(--bg-base);
}

.scroll-area {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  background: var(--bg-base);
}

// ── 状态页 ────────────────────────────────────────────
.status-center {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 48rpx;
  z-index: 10;
  background: var(--bg-base);
}

.status-text {
  font-size: 30rpx;
  color: var(--text-muted);
}

.retry-btn {
  padding: 24rpx 64rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  font-weight: 500;
  font-family: inherit;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

// ── Banner ────────────────────────────────────────────
.banner {
  width: 100%;
  height: 520rpx;
  position: relative;
  overflow: hidden;
  background: var(--banner-bg);
  display: flex;
  align-items: center;
  justify-content: center;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 1;
  }

  .dark-mode &::before {
    background:
      radial-gradient(ellipse 80% 60% at 50% 0%, rgba(34, 197, 94, 0.08) 0%, transparent 60%),
      radial-gradient(ellipse 60% 40% at 80% 80%, rgba(236, 72, 153, 0.05) 0%, transparent 50%);
  }
}

.banner-img {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
}

.banner-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  position: relative;
  z-index: 2;
}

.banner-emoji {
  font-size: 160rpx;
  filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.3));
  animation: floatIn 0.8s $ease-spring forwards;
  opacity: 0;
  transform: scale(0.8);
  transform-origin: center;
}

.banner-label {
  font-size: 26rpx;
  color: var(--banner-label);
  letter-spacing: 0.1em;
}

.banner-badge {
  position: absolute;
  right: 40rpx;
  bottom: 40rpx;
  border-radius: 28rpx;
  padding: 20rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 2;
  background: var(--banner-badge-bg);
  border: 1px solid var(--banner-badge-border);
  box-shadow: var(--banner-badge-shadow);
  animation: slideUpBadge 0.6s 0.2s $ease-spring forwards;
  opacity: 0;
  transform: translateY(10px);
}

.badge-icon {
  width: 28rpx;
  height: 28rpx;
  fill: var(--risk-t0);
  flex-shrink: 0;
}

.badge-text {
  font-size: 24rpx;
  font-weight: 600;
  color: var(--risk-t0);
}

// ── 内容区 ────────────────────────────────────────────
.content {
  padding: 48rpx 40rpx 200rpx;
}

.section-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-top: 56rpx;
  margin-bottom: 28rpx;

  &:first-child {
    margin-top: 0;
  }
}

// ── 营养卡片 ──────────────────────────────────────────
.nutrition-card {
  position: relative;
  overflow: hidden;
  border-radius: $radius-xl;
  padding: 40rpx;
  margin-bottom: 0;
  animation: slideUp 0.5s 0.1s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16px);
  background: var(--nutrition-bg);
  border: 1px solid var(--nutrition-border);

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--nutrition-glow), transparent);
  }
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
  margin-bottom: 4rpx;
  color: var(--text-muted);
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
  margin-top: 4rpx;
  color: var(--text-muted);
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
  -webkit-appearance: none;
  appearance: none;
  font-size: 26rpx;
  font-weight: 500;
  font-family: inherit;
  border-radius: 24rpx;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.2s;

  &:active { background: rgba(128, 128, 128, 0.1); }
  &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }

  .chevron {
    width: 32rpx;
    height: 32rpx;
    transition: transform 0.3s ease;
    stroke: var(--text-muted);
  }

  &.expanded .chevron {
    transform: rotate(180deg);
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

  .row-label { color: var(--text-secondary); }
  .row-value { color: var(--text-primary); font-weight: 500; font-variant-numeric: tabular-nums; }
}

// ── 健康益处 / 食用建议卡片 ────────────────────────────
.analysis-card {
  border-radius: 40rpx;
  padding: 36rpx;
  margin-bottom: 0;
  animation: slideUp 0.5s 0.3s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16px);

  // 暗色
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);

  // 亮色
  .product-page:not(.dark-mode) & {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  }
}

.advice-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 28rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary);

  .star-icon {
    width: 36rpx;
    height: 36rpx;
    fill: #f59e0b;
    flex-shrink: 0;
  }
}

.analysis-list {
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.analysis-item {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;

  .item-icon {
    width: 36rpx;
    height: 36rpx;
    flex-shrink: 0;
    margin-top: 2rpx;

    &--check { fill: var(--risk-t0); }
    &--dot { fill: var(--text-muted); }
  }

  .item-text {
    font-size: 28rpx;
    line-height: 1.5;
    color: var(--text-secondary);
    flex: 1;
  }
}

.empty-text {
  font-size: 28rpx;
  color: var(--text-muted);
}

// ── 动画 ─────────────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji,
  .banner-badge,
  .nutrition-card,
  .analysis-card {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>
```

- [ ] **Step 2: 浏览器全面验证**

打开 `http://localhost:5174/#/pages/product/index?barcode=6900000000001`，对照 v14 设计稿检查：

**Banner**
- [ ] 高度约为屏幕高度的 2/5，不超过屏幕高度一半
- [ ] 有产品图时图片填满，无图时显示 emoji + "产品图片" 文字
- [ ] 右下角风险徽章显示正确文字

**营养成分**
- [ ] "营养成分"章节标题在卡片上方
- [ ] 2×2 网格，数值大字（约 32px 等效）
- [ ] 点击"查看详细营养成分"可展开/收起
- [ ] chevron 旋转动画正常

**配料信息**
- [ ] "配料信息"章节标题
- [ ] 各风险等级分组，背景色与设计稿一致
- [ ] 每组内横向滚动配料卡片
- [ ] 左侧风险色条显示正确颜色

**健康益处 / 食用建议**
- [ ] 两个章节标题均在卡片外
- [ ] 食用建议卡内有"AI 健康建议"小标题行（星星图标）
- [ ] 暗色模式卡片几乎透明（区别于 bg-card 的不透明深色）

**Header**
- [ ] 滚动后透明变毛玻璃，图标变色

**Bottom Bar**
- [ ] 两个按钮正确样式，紧贴页面底部

- [ ] **Step 3: 提交**

```bash
git add web/apps/uniapp/src/pages/product/index.vue
git commit -m "feat(uniapp): rewrite product page with v14 design - banner, nutrition, health, advice"
```

---

## Task 6: 收尾 — design-system.scss SCSS 变量校准

**Files:**
- Modify: `web/apps/uniapp/src/styles/design-system.scss`

当前 `design-system.scss` 的 `$radius-*` 变量不匹配规范，需对齐：

- [ ] **Step 1: 更新 SCSS 变量**

找到 `design-system.scss` 中的 border-radius 变量，替换为：

```scss
$radius-sm: 24rpx;   // 12px → 24rpx
$radius-md: 32rpx;   // 16px → 32rpx
$radius-lg: 40rpx;   // 20px → 40rpx
$radius-xl: 48rpx;   // 24px → 48rpx
```

- [ ] **Step 2: 浏览器最终检查**

再次打开页面，确认整体圆角视觉没有异常。

- [ ] **Step 3: 最终提交**

```bash
git add web/apps/uniapp/src/styles/design-system.scss
git commit -m "chore(uniapp): align design-system SCSS radius vars to rpx"
```

---

## 完成标志

- [ ] 页面视觉与 `product-detail-v14.html` 设计稿高度一致
- [ ] 暗色模式（`.dark-mode`）和亮色模式（去掉 `.dark-mode`）均正确显示
- [ ] 所有章节标题（营养成分/配料信息/健康益处/食用建议）均在卡片外
- [ ] banner 高度适中，emoji 大小适中（不超过 banner 高度 1/2）
- [ ] 横向滚动配料卡正常工作，点击可跳转
- [ ] 展开/收起营养成分正常工作
- [ ] Header 滚动透明/毛玻璃切换正常
- [ ] 无控制台报错
