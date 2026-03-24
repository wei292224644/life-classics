<template>
  <view class="product-page">
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
      <button type="button" class="retry-btn" @click="goBack">
        返回重新扫码
      </button>
    </view>

    <!-- 错误 -->
    <view v-else-if="store.state === 'error'" class="status-center">
      <text class="status-text">{{
        store.errorMessage || "网络请求失败"
      }}</text>
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
          <text v-if="store.product?.name" class="banner-label">{{
            store.product.name
          }}</text>
        </view>
        <view class="banner-badge" :class="overallRiskLevel">
          <Icon name="badgeCheck" class="badge-icon" />
          <text class="badge-text">{{ riskLabel }}</text>
        </view>
      </view>

      <!-- ── 内容区 ────────────────────────────────── -->
      <view class="content">
        <!-- 营养成分 -->
        <view class="nutrition-card">
          <text class="section-title">营养成分</text>
          <view class="nutrition-grid">
            <view
              v-for="item in primaryNutritions"
              :key="item.name"
              class="nutrition-cell"
            >
              <text class="nutrition-label">{{ item.name }}</text>
              <text class="nutrition-value">{{ item.value }}</text>
              <text class="nutrition-unit">{{
                formatNutritionUnit(item)
              }}</text>
            </view>
          </view>
          <button
            type="button"
            class="nutrition-toggle"
            :class="{ expanded: nutrExpanded }"
            :aria-expanded="nutrExpanded"
            @click="nutrExpanded = !nutrExpanded"
          >
            <text>{{
              nutrExpanded ? "收起详细营养成分" : "查看详细营养成分"
            }}</text>
            <Icon name="chevronDown" class="chevron" />
          </button>
          <view v-show="nutrExpanded" class="nutrition-details">
            <view
              v-for="item in detailNutritions"
              :key="item.name"
              class="nutrition-row"
            >
              <text class="row-label">{{ item.name }}</text>
              <text class="row-value">{{ formatNutritionValueCompact(item) }}</text>
            </view>
          </view>
        </view>

        <!-- 配料与风险 -->
        <!-- <text class="section-title">配料与风险</text> -->
        <IngredientSection :ingredients="mockIngredients" />

        <!-- 健康益处 -->
        <view class="analysis-card">
          <text class="section-title">健康益处</text>
          <view class="analysis-list">
            <view
              v-for="(text, idx) in healthTexts"
              :key="idx"
              class="analysis-item"
            >
              <Icon name="check" class="item-icon item-icon--check" />
              <text class="item-text">{{ text }}</text>
            </view>
          </view>
        </view>

        <!-- 食用建议 -->
        <view class="analysis-card">
          <view class="advice-header">
            <Icon name="star" class="star-icon" />
            <text>AI 健康建议</text>
          </view>
          <text class="advice-text">{{ adviceText }}</text>
        </view>

        <view class="bottom-spacer" />
      </view>
    </scroll-view>

    <BottomBar @add-record="handleAddRecord" @chat="handleChat" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import type { NutritionDetail, IngredientDetail } from "../../types/product";
import ProductHeader from "../../components/ProductHeader.vue";
import IngredientSection from "../../components/IngredientSection.vue";
import BottomBar from "../../components/BottomBar.vue";
import Icon from "../../components/Icon.vue";

const store = useProductStore();
const headerRef = ref<any>(null);
const barcode = ref("");
const nutrExpanded = ref(false);

const PRIMARY_NUTRITION_COUNT = 4;

const UNIT_LABELS: Record<string, string> = {
  g: "克",
  mg: "毫克",
  kJ: "千焦",
  kcal: "千卡",
  mL: "毫升",
};

const FALLBACK_NUTRITIONS: NutritionDetail[] = [
  {
    name: "热量",
    alias: [],
    value: "52",
    value_unit: "kcal",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "碳水",
    alias: [],
    value: "14",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "膳食纤维",
    alias: [],
    value: "2.4",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "维生素C",
    alias: [],
    value: "4.6",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "蛋白质",
    alias: [],
    value: "0.3",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "脂肪",
    alias: [],
    value: "0.2",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "糖",
    alias: [],
    value: "10",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "钠",
    alias: [],
    value: "1",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "钾",
    alias: [],
    value: "107",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "水分",
    alias: [],
    value: "85.6",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
];

const FALLBACK_HEALTH_TEXTS = [
  "富含膳食纤维，有助于肠道健康",
  "含有抗氧化剂，可延缓细胞衰老",
  "维生素C有助于增强免疫力",
];

const FALLBACK_ADVICE_TEXT =
  "建议每日食用1-2个中等大小的苹果，约200-300克为宜。餐前30分钟食用可增加饱腹感，有助于控制热量摄入。";

const FALLBACK_INGREDIENTS: IngredientDetail[] = [
  {
    id: 9001,
    name: "亚硝酸钠",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Group 2A",
    allergen_info: null,
    function_type: "防腐剂",
    standard_code: null,
    analysis: {
      id: 9101,
      analysis_type: "risk_assessment",
      level: "t4",
      results: { reason: "可能致癌" },
    },
  },
  {
    id: 9002,
    name: "焦糖色",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Group 2B",
    allergen_info: null,
    function_type: "着色剂",
    standard_code: null,
    analysis: {
      id: 9102,
      analysis_type: "risk_assessment",
      level: "t3",
      results: { reason: "潜在致癌" },
    },
  },
  {
    id: 9003,
    name: "天然香料",
    alias: [],
    is_additive: false,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "增香",
    standard_code: null,
    analysis: {
      id: 9103,
      analysis_type: "risk_assessment",
      level: "t0",
      results: {},
    },
  },
  {
    id: 9004,
    name: "复合调味料",
    alias: [],
    is_additive: false,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "调味",
    standard_code: null,
    analysis: {
      id: 9104,
      analysis_type: "risk_assessment",
      level: "t0",
      results: {},
    },
  },
  {
    id: 9005,
    name: "其他添加剂",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "复配",
    standard_code: null,
    analysis: {
      id: 9105,
      analysis_type: "risk_assessment",
      level: "unknown",
      results: {},
    },
  },
];

function formatNutritionUnit(item: {
  value_unit: string;
  reference_unit?: string;
}): string {
  const unit = UNIT_LABELS[item.value_unit] ?? item.value_unit;
  return item.reference_unit ? `${unit} / ${item.reference_unit}` : unit;
}

function formatNutritionValueCompact(item: { value: string; value_unit: string }): string {
  return `${item.value}${item.value_unit}`;
}

const RISK_LABELS: Record<string, string> = {
  t4: "严重风险",
  t3: "较高风险",
  t2: "中风险",
  t0: "低风险",
  unknown: "风险未知",
};

onMounted(() => {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1] as
    | { options?: Record<string, string> }
    | undefined;
  barcode.value = current?.options?.barcode ?? "";
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
  uni.navigateTo({
    url: `/pages/chat/index?product=${encodeURIComponent(name)}`,
  });
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
    .map((i) => i.analysis?.level)
    .filter(Boolean) as string[];
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0") || levels.includes("t1")) return "t0";
  return "unknown";
});

const riskLabel = computed(
  () => RISK_LABELS[overallRiskLevel.value] ?? "风险未知",
);

const primaryNutritions = computed(() =>
  ((store.product?.nutritions?.length ?? 0) > 0
    ? store.product?.nutritions
    : FALLBACK_NUTRITIONS)!.slice(0, PRIMARY_NUTRITION_COUNT),
);

const detailNutritions = computed(() =>
  ((store.product?.nutritions?.length ?? 0) > PRIMARY_NUTRITION_COUNT
    ? store.product?.nutritions
    : FALLBACK_NUTRITIONS)!.slice(PRIMARY_NUTRITION_COUNT),
);

const healthItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) =>
      a.analysis_type === "health_summary" ||
      a.analysis_type === "health_benefits",
  ),
);

const adviceItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) =>
      a.analysis_type === "usage_advice_summary" ||
      a.analysis_type === "advice",
  ),
);

const healthTexts = computed(() => {
  const texts = healthItems.value
    .map((item) => extractText(item.results, "summary"))
    .filter(Boolean);
  return texts.length > 0 ? texts : FALLBACK_HEALTH_TEXTS;
});

const adviceText = computed(() => {
  const fromAnalysis =
    adviceItems.value
      .map((item) => extractText(item.results, "advice", "summary"))
      .find(Boolean) ?? "";
  return fromAnalysis || FALLBACK_ADVICE_TEXT;
});

const mockIngredients = computed(() =>
  (store.product?.ingredients?.length ?? 0) > 0
    ? store.product!.ingredients
    : FALLBACK_INGREDIENTS,
);
</script>

<style lang="scss" scoped>
// ── 页面基础 ──────────────────────────────────────────
.product-page {
  @apply min-h-screen bg-background overflow-hidden;
}

.scroll-area {
  @apply fixed inset-0 z-10 bg-background;
}

// ── 状态页 ────────────────────────────────────────────
.status-center {
  @apply fixed inset-0 flex flex-col items-center justify-center gap-12 z-20 bg-background;
}

.status-text {
  @apply text-3xl text-muted-foreground;
}

.retry-btn {
  @apply px-8 py-3 rounded-xl text-lg font-medium bg-card border border-border text-foreground;
}

// ── Banner ────────────────────────────────────────────
.banner {
  @apply relative overflow-hidden;
  width: 100%;
  height: 520rpx;
  background: var(--banner-bg);
  display: flex;
  align-items: center;
  justify-content: center;

  &::before {
    content: "";
    @apply absolute inset-0 z-[1];
  }

  .dark &::before {
    background:
      radial-gradient(
        ellipse 80% 60% at 50% 0%,
        color-mix(in oklch, var(--color-risk-t0) 8%, transparent) 0%,
        transparent 60%
      ),
      radial-gradient(
        ellipse 60% 40% at 80% 80%,
        color-mix(in oklch, var(--color-accent) 5%, transparent) 0%,
        transparent 50%
      );
  }
}

.banner-img {
  @apply absolute inset-0 w-full h-full;
}

.banner-placeholder {
  @apply relative z-[2] flex flex-col items-center justify-center gap-4;
}

.banner-emoji {
  @apply text-[160rpx];
  filter: drop-shadow(0 8rpx 24rpx rgba(0, 0, 0, 0.3));
  animation: floatIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: scale(0.8);
  transform-origin: center;
}

.banner-label {
  @apply text-lg tracking-widest;
  color: var(--banner-label);
}

.banner-badge {
  @apply absolute right-[32rpx] bottom-[32rpx] rounded-[32rpx] px-[32rpx] py-[14rpx] flex items-center gap-[10rpx] z-[2];
  animation: slideUpBadge 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(10px);
  border: 1px solid transparent;

  &.t4 {
    background: color-mix(in oklch, var(--color-risk-t4) 24%, white);
    border-color: color-mix(in oklch, var(--color-risk-t4) 40%, white);
  }
  &.t3 {
    background: color-mix(in oklch, var(--color-risk-t3) 24%, white);
    border-color: color-mix(in oklch, var(--color-risk-t3) 40%, white);
  }
  &.t2 {
    background: color-mix(in oklch, var(--color-risk-t2) 24%, white);
    border-color: color-mix(in oklch, var(--color-risk-t2) 40%, white);
  }
  &.t0 {
    background: linear-gradient(
      135deg,
      rgba(134, 239, 172, 0.5),
      rgba(74, 222, 128, 0.55)
    );
    border-color: rgba(34, 197, 94, 0.35);
    box-shadow: 0 8rpx 36rpx rgba(34, 197, 94, 0.2);
  }
  &.unknown {
    background: oklch(100% 0 0 / 85%);
    border: 1px solid oklch(14.5% 0.016 265 / 10%);
  }
}

.badge-icon {
  @apply w-[24rpx] h-[24rpx] flex-shrink-0;
  fill: currentColor;

  .banner-badge.t0 & {
    color: var(--color-risk-t0);
  }
  .banner-badge.t2 & {
    color: var(--color-risk-t2);
  }
  .banner-badge.t3 & {
    color: var(--color-risk-t3);
  }
  .banner-badge.t4 & {
    color: var(--color-risk-t4);
  }
  .banner-badge.unknown & {
    color: var(--color-risk-unknown);
  }
}

.badge-text {
  @apply text-sm font-semibold;
  color: currentColor;

  .banner-badge.t0 & {
    color: var(--color-risk-t0);
  }
  .banner-badge.t2 & {
    color: var(--color-risk-t2);
  }
  .banner-badge.t3 & {
    color: var(--color-risk-t3);
  }
  .banner-badge.t4 & {
    color: var(--color-risk-t4);
  }
  .banner-badge.unknown & {
    color: var(--color-risk-unknown);
  }
}

// ── 内容区 ────────────────────────────────────────────
.content {
  @apply px-3;
  padding-top: 24rpx;
}

.bottom-spacer {
  height: 200rpx;
}

.section-title {
  @apply block font-bold tracking-tight text-foreground text-base;
  margin-top: 40rpx;
  margin-bottom: 20rpx;

  &:first-child {
    margin-top: 0;
  }
}

// ── 营养卡片 ──────────────────────────────────────────
.nutrition-card {
  @apply relative overflow-hidden rounded-[32rpx] p-5 mb-0;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);
  background: var(--nutrition-bg);
  border: 1px solid var(--nutrition-border);

  &::before {
    content: "";
    @apply absolute top-0 left-0 right-0 h-px;
    background: linear-gradient(
      90deg,
      transparent,
      var(--nutrition-glow),
      transparent
    );
  }
}

.nutrition-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24rpx 32rpx;
  margin-bottom: 24rpx;
}

.nutrition-cell {
  @apply flex flex-col;
}

.nutrition-label {
  @apply text-[22rpx] tracking-[0.08em] mb-0.5 text-muted-foreground;
}

.nutrition-value {
  @apply text-[56rpx] font-bold tracking-tighter text-foreground leading-none mt-0.5;
  font-variant-numeric: tabular-nums;
}

.nutrition-unit {
  @apply text-[22rpx] mt-0.5 text-muted-foreground;
}

.nutrition-toggle {
  @apply w-full flex items-center justify-center gap-2 py-[10rpx] bg-transparent border-none text-[26rpx] font-medium rounded-xl text-muted-foreground cursor-pointer;
  -webkit-appearance: none;
  appearance: none;
  font-family: inherit;
  transition: background 0.2s;

  &:active {
    background: color-mix(in oklch, oklch(55% 0.02 265) 10%, transparent);
  }
  &:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .chevron {
    @apply w-4 h-4 transition-transform duration-300;
    stroke: var(--color-muted);
  }

  &.expanded .chevron {
    transform: rotate(180deg);
  }
}

.nutrition-details {
  @apply border-t border-border pt-4 mt-1;
}

.nutrition-row {
  @apply flex justify-between py-3 border-b border-border text-sm;
  &:last-child {
    @apply border-b-0;
  }

  .row-label {
    @apply text-secondary;
  }
  .row-value {
    @apply text-foreground font-medium;
    font-variant-numeric: tabular-nums;
  }
}

// ── 健康益处 / 食用建议卡片 ────────────────────────────
.analysis-card {
  @apply rounded-[32rpx] p-[36rpx] mb-0;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);

  @apply bg-card border border-border;
  box-shadow: var(--shadow-sm);
}

.advice-header {
  @apply flex items-center gap-2 mb-4 text-[30rpx] font-semibold text-foreground;

  .star-icon {
    @apply w-[36rpx] h-[36rpx] flex-shrink-0;
    fill: oklch(70% 0.18 85);
  }
}

.analysis-list {
  @apply flex flex-col gap-4;
}

.analysis-item {
  @apply flex items-start gap-3;

  .item-icon {
    @apply w-[28rpx] h-[28rpx] flex-shrink-0 mt-0.5;

    &--check {
      fill: var(--color-risk-t0);
    }
    &--dot {
      fill: var(--color-muted);
    }
  }

  .item-text {
    @apply text-sm leading-relaxed text-secondary-foreground flex-1;
  }
}

.advice-text {
  @apply text-sm leading-relaxed text-secondary-foreground;
}

.empty-text {
  @apply text-sm text-muted-foreground;
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
