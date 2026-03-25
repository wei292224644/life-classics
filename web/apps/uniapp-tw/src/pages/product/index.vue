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
      <view class="banner" :class="overallRiskLevel">
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
        <!-- 风险徽章 -->
        <view class="banner-badge">
          <Icon name="badgeCheck" class="badge-icon" />
          <text class="badge-text">{{ riskLabel }}</text>
        </view>
      </view>

      <!-- ── 内容区 ────────────────────────────────── -->
      <view class="content">
        <!-- 营养成分卡片 -->
        <view class="nutrition-card" :class="overallRiskLevel">
          <view class="nutrition-glow" />
          <text class="nutrition-title">营养成分</text>
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
            <text class="toggle-label">{{
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
        <text class="section-title">配料与风险</text>
        <IngredientSection :ingredients="mockIngredients" />

        <!-- 健康益处卡片 -->
        <view class="health-card">
          <text class="health-title">健康益处</text>
          <view class="health-list">
            <view
              v-for="(text, idx) in healthTexts"
              :key="idx"
              class="health-item"
            >
              <Icon name="check" class="health-icon" />
              <text class="health-text">{{ text }}</text>
            </view>
          </view>
        </view>

        <!-- AI 健康建议卡片 -->
        <view class="advice-card">
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
import ProductHeader from "@/components/business/product/ProductHeader.vue";
import IngredientSection from "@/components/business/ingredient/IngredientSection.vue";
import BottomBar from "@/components/ui/BottomBar.vue";
import Icon from "@/components/ui/Icon.vue";

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
  @apply relative overflow-hidden flex flex-col items-center justify-center;
  width: 100%;
  height: 520rpx;

  .t4 & {
    background: linear-gradient(145deg, #fee2e2 0%, #fecaca 50%, #fca5a5 100%);
  }
  .t3 & {
    background: linear-gradient(145deg, #ffedd5 0%, #fed7aa 50%, #fcd34d 100%);
  }
  .t2 & {
    background: linear-gradient(145deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%);
  }
  .t0 & {
    background: linear-gradient(145deg, #dcfce7 0%, #bbf7d0 50%, #86efac 100%);
  }
  .unknown &,
  .t1 & {
    background: linear-gradient(145deg, #e5e7eb 0%, #d1d5db 50%, #9ca3af 100%);
  }

  .dark & {
    &.t4 { background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%); }
    &.t3 { background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%); }
    &.t2 { background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%); }
    &.t0 { background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%); }
    &.unknown,
    &.t1 { background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%); }
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
  @apply text-sm tracking-widest;
  color: rgba(0, 0, 0, 0.5);

  .dark & {
    color: rgba(255, 255, 255, 0.4);
  }
}

// 风险徽章
.banner-badge {
  @apply absolute right-[32rpx] bottom-[32rpx] rounded-[32rpx] px-[32rpx] py-[14rpx] flex items-center gap-[10rpx] z-[2];
  animation: slideUpBadge 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(10px);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);

  .t4 & {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.3));
    border: 1px solid rgba(239, 68, 68, 0.3);
    box-shadow: 0 8rpx 36rpx rgba(239, 68, 68, 0.2);
  }
  .t3 & {
    background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(234, 88, 12, 0.3));
    border: 1px solid rgba(249, 115, 22, 0.3);
    box-shadow: 0 8rpx 36rpx rgba(249, 115, 22, 0.2);
  }
  .t2 & {
    background: linear-gradient(135deg, rgba(202, 138, 4, 0.2), rgba(234, 179, 8, 0.3));
    border: 1px solid rgba(202, 138, 4, 0.3);
    box-shadow: 0 8rpx 36rpx rgba(202, 138, 4, 0.2);
  }
  .t0 & {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.3));
    border: 1px solid rgba(34, 197, 94, 0.3);
    box-shadow: 0 8rpx 36rpx rgba(34, 197, 94, 0.2);
  }
  .unknown & {
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);
  }
}

.badge-icon {
  @apply w-[24rpx] h-[24rpx] flex-shrink-0;
  fill: currentColor;

  .t4 & { color: var(--color-risk-t4); }
  .t3 & { color: var(--color-risk-t3); }
  .t2 & { color: var(--color-risk-t2); }
  .t0 & { color: var(--color-risk-t0); }
  .unknown & { color: var(--color-risk-unknown); }
}

.badge-text {
  @apply text-sm font-semibold;

  .t4 & { color: var(--color-risk-t4); }
  .t3 & { color: var(--color-risk-t3); }
  .t2 & { color: var(--color-risk-t2); }
  .t0 & { color: var(--color-risk-t0); }
  .unknown & { color: var(--color-risk-unknown); }
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
  @apply block font-bold tracking-tight text-foreground;
  font-size: 40rpx;
  line-height: 1.2;
  margin-top: 48rpx;
  margin-bottom: 28rpx;
}

.nutrition-title {
  @apply block font-bold tracking-tight text-foreground;
  font-size: 40rpx;
  line-height: 1.2;
  margin-bottom: 40rpx;
}

// ── 营养卡片 ──────────────────────────────────────────
.nutrition-card {
  @apply relative overflow-hidden rounded-[40rpx] p-5 mb-0;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);

  .t4 & {
    background: linear-gradient(145deg, rgba(239, 68, 68, 0.04), rgba(220, 38, 38, 0.02));
    border: 1px solid rgba(239, 68, 68, 0.12);
  }
  .t3 & {
    background: linear-gradient(145deg, rgba(249, 115, 22, 0.04), rgba(234, 88, 12, 0.02));
    border: 1px solid rgba(249, 115, 22, 0.12);
  }
  .t2 & {
    background: linear-gradient(145deg, rgba(202, 138, 4, 0.04), rgba(234, 179, 8, 0.02));
    border: 1px solid rgba(202, 138, 4, 0.12);
  }
  .t0 & {
    background: linear-gradient(145deg, rgba(34, 197, 94, 0.04), rgba(22, 163, 74, 0.02));
    border: 1px solid rgba(34, 197, 94, 0.12);
  }
  .unknown &,
  .t1 & {
    background: linear-gradient(145deg, rgba(0, 0, 0, 0.02), rgba(0, 0, 0, 0.01));
    border: 1px solid rgba(0, 0, 0, 0.06);
  }

  .dark & {
    &.t4 { background: rgba(239, 68, 68, 0.06); border-color: rgba(239, 68, 68, 0.1); }
    &.t3 { background: rgba(249, 115, 22, 0.06); border-color: rgba(249, 115, 22, 0.1); }
    &.t2 { background: rgba(202, 138, 4, 0.06); border-color: rgba(202, 138, 4, 0.1); }
    &.t0 { background: rgba(34, 197, 94, 0.06); border-color: rgba(34, 197, 94, 0.1); }
    &.unknown,
    &.t1 { background: rgba(255, 255, 255, 0.02); border-color: rgba(255, 255, 255, 0.06); }
  }
}

.nutrition-glow {
  @apply absolute top-0 left-0 right-0 h-px;
  background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.3), transparent);

  .t4 & { background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.3), transparent); }
  .t3 & { background: linear-gradient(90deg, transparent, rgba(249, 115, 22, 0.3), transparent); }
  .t2 & { background: linear-gradient(90deg, transparent, rgba(202, 138, 4, 0.3), transparent); }
  .t0 & { background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.3), transparent); }
}

.nutrition-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40rpx;
  margin-bottom: 32rpx;
}

.nutrition-cell {
  @apply flex flex-col;
}

.nutrition-label {
  @apply text-[22rpx] tracking-[0.08em] uppercase mb-0.5 text-muted-foreground;
}

.nutrition-value {
  @apply text-[64rpx] font-bold tracking-[-0.03em] leading-none mt-0.5 text-foreground;
  font-variant-numeric: tabular-nums;
}

.nutrition-unit {
  @apply text-[22rpx] mt-0.5 text-muted-foreground;
}

.nutrition-toggle {
  @apply w-full flex items-center justify-center gap-2 py-[20rpx] bg-transparent border-none cursor-pointer;
  font-family: inherit;

  &:active {
    background: rgba(128, 128, 128, 0.08);
  }
  &:focus-visible {
    @apply outline-accent outline-offset-2;
  }

  .toggle-label {
    @apply text-[26rpx] font-medium text-muted-foreground;
  }

  .chevron {
    @apply w-[32rpx] h-[32rpx] transition-transform duration-300 text-muted-foreground;
  }

  &.expanded .chevron {
    transform: rotate(180deg);
  }
}

.nutrition-details {
  @apply border-t border-border pt-4 mt-1;
}

.nutrition-row {
  @apply flex justify-between py-[20rpx] border-b border-border text-sm;
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

// ── 健康益处卡片 ───────────────────────────────────────
.health-card {
  @apply rounded-[40rpx] p-[36rpx] mb-7;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);

  .dark & {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .light & {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
  }
}

.health-title {
  @apply text-[30rpx] font-semibold tracking-tight mb-4 text-foreground;
}

.health-list {
  @apply flex flex-col gap-3.5;
}

.health-item {
  @apply flex items-start gap-3;
}

.health-icon {
  @apply w-[36rpx] h-[36rpx] flex-shrink-0 mt-0.5;
  fill: var(--color-risk-t0);
}

.health-text {
  @apply text-sm leading-[1.5] flex-1 text-secondary;
}

// ── AI 建议卡片 ───────────────────────────────────────
.advice-card {
  @apply rounded-[40rpx] p-[36rpx] mb-7;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);

  .dark & {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .light & {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
  }
}

.advice-header {
  @apply flex items-center gap-2 mb-[28rpx] text-foreground;

  .star-icon {
    @apply w-[36rpx] h-[36rpx] flex-shrink-0;
    fill: #f59e0b;
  }

  .advice-title-text {
    @apply text-[30rpx] font-semibold;
  }
}

.advice-text {
  @apply text-sm leading-[1.65] text-secondary;
}

// ── 动画 ─────────────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji,
  .banner-badge,
  .nutrition-card,
  .health-card,
  .advice-card {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>
