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

        <view class="bottom-spacer" />
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
  if (levels.includes("t0") || levels.includes("t1")) return "t0";
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
// ── 页面基础 ──────────────────────────────────────────
.product-page {
  @apply min-h-screen bg-background;
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
    content: '';
    @apply absolute inset-0 z-[1];
  }

  .dark &::before {
    background:
      radial-gradient(ellipse 80% 60% at 50% 0%, color-mix(in oklch, var(--color-risk-t0) 8%, transparent) 0%, transparent 60%),
      radial-gradient(ellipse 60% 40% at 80% 80%, color-mix(in oklch, var(--color-accent) 5%, transparent) 0%, transparent 50%);
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
  @apply absolute right-[40rpx] bottom-[40rpx] rounded-xl px-[32rpx] py-[20rpx] flex items-center gap-[16rpx] backdrop-blur-xl z-[2];
  background: var(--banner-badge-bg);
  border: 1px solid var(--banner-badge-border);
  box-shadow: var(--banner-badge-shadow);
  animation: slideUpBadge 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(10px);
}

.badge-icon {
  @apply w-[28rpx] h-[28rpx] flex-shrink-0;

  .banner-badge.t4 & { fill: var(--color-risk-t4); }
  .banner-badge.t3 & { fill: var(--color-risk-t3); }
  .banner-badge.t2 & { fill: var(--color-risk-t2); }
  .banner-badge.t0 & { fill: var(--color-risk-t0); }
  .banner-badge.unknown & { fill: var(--color-risk-unknown); }
}

.badge-text {
  @apply text-base font-semibold;

  .banner-badge.t4 & { color: var(--color-risk-t4); }
  .banner-badge.t3 & { color: var(--color-risk-t3); }
  .banner-badge.t2 & { color: var(--color-risk-t2); }
  .banner-badge.t0 & { color: var(--color-risk-t0); }
  .banner-badge.unknown & { color: var(--color-risk-unknown); }
}

// ── 内容区 ────────────────────────────────────────────
.content {
  @apply px-6 pt-0;
}

.bottom-spacer {
  height: 180rpx;
}

.section-title {
  @apply block text-2xl font-bold tracking-tight text-foreground;
  margin-top: 56rpx;
  margin-bottom: 28rpx;

  &:first-child {
    margin-top: 0;
  }
}

// ── 营养卡片 ──────────────────────────────────────────
.nutrition-card {
  @apply relative overflow-hidden rounded-2xl p-10 mb-0;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);
  background: var(--nutrition-bg);
  border: 1px solid var(--nutrition-border);

  &::before {
    content: "";
    @apply absolute top-0 left-0 right-0 h-px;
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
  @apply flex flex-col;
}

.nutrition-label {
  @apply text-sm uppercase tracking-widest mb-0.5 text-muted-foreground;
}

.nutrition-value {
  @apply text-[48rpx] font-bold tracking-tighter text-foreground leading-none mt-0.5;
  font-variant-numeric: tabular-nums;
}

.nutrition-unit {
  @apply text-base mt-0.5 text-muted-foreground;
}

.nutrition-toggle {
  @apply w-full flex items-center justify-center gap-4 py-5 bg-transparent border-none text-lg font-medium rounded-lg text-muted-foreground cursor-pointer;
  -webkit-appearance: none;
  appearance: none;
  font-family: inherit;
  transition: background 0.2s;

  &:active { background: color-mix(in oklch, oklch(55% 0.02 265) 10%, transparent); }
  &:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }

  .chevron {
    @apply w-5 h-5 transition-transform duration-300;
    stroke: var(--color-muted);
  }

  &.expanded .chevron {
    transform: rotate(180deg);
  }
}

.nutrition-details {
  @apply border-t border-border pt-8 mt-2;
}

.nutrition-row {
  @apply flex justify-between py-5 border-b border-border text-lg;
  &:last-child { @apply border-b-0; }

  .row-label { @apply text-secondary; }
  .row-value { @apply text-foreground font-medium; font-variant-numeric: tabular-nums; }
}

// ── 健康益处 / 食用建议卡片 ────────────────────────────
.analysis-card {
  @apply rounded-xl p-9 mb-0;
  animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);

  @apply bg-card border border-border;
  box-shadow: var(--shadow-sm);
}

.advice-header {
  @apply flex items-center gap-4 mb-7 text-2xl font-semibold text-foreground;

  .star-icon {
    @apply w-6 h-6 flex-shrink-0;
    fill: oklch(70% 0.18 85);
  }
}

.analysis-list {
  @apply flex flex-col gap-7;
}

.analysis-item {
  @apply flex items-start gap-6;

  .item-icon {
    @apply w-6 h-6 flex-shrink-0 mt-0.5;

    &--check { fill: var(--color-risk-t0); }
    &--dot { fill: var(--color-muted); }
  }

  .item-text {
    @apply text-lg leading-relaxed text-secondary flex-1;
  }
}

.empty-text {
  @apply text-lg text-muted-foreground;
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
