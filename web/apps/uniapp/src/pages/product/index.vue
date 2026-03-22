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
