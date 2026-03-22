<template>
  <view class="product-page dark-mode">
    <!-- ProductHeader: status-bar (44px) + fixed header + banner (260px) -->
    <ProductHeader
      ref="headerRef"
      :name="store.product?.name ?? ''"
      :image-url="store.product?.image_url_list?.[0]"
      :overall-risk-level="overallRiskLevel"
    />

    <!-- Loading state -->
    <view v-if="store.state === 'loading'" class="status-center">
      <up-loading-icon mode="circle" />
      <text class="status-text">查询中...</text>
    </view>

    <!-- Not found state -->
    <view v-else-if="store.state === 'not_found'" class="status-center">
      <text class="status-text">该产品暂未收录</text>
      <up-button size="small" @click="goBack">返回重新扫码</up-button>
    </view>

    <!-- Error state -->
    <view v-else-if="store.state === 'error'" class="status-center">
      <text class="status-text">{{ store.errorMessage || '网络请求失败' }}</text>
      <up-button size="small" @click="load">重试</up-button>
    </view>

    <!-- Success state: scrollable content -->
    <scroll-view
      v-else-if="store.product"
      class="scroll-area"
      scroll-y
      @scroll="onScroll"
    >
      <view class="content">
        <!-- Nutrition Card -->
        <NutritionCard :nutritions="store.product.nutritions" />

        <!-- Ingredient Section Title -->
        <view class="section-title">配料信息</view>

        <!-- Risk Groups with Ingredient Cards -->
        <RiskGroup
          v-for="(group, level) in groupedIngredients"
          :key="level"
          :level="level"
          :ingredients="group"
        >
          <IngredientCard :ingredients="group" />
        </RiskGroup>

        <!-- Health Benefit Card -->
        <HealthBenefitCard :items="healthItems" />

        <!-- AI Advice Card -->
        <AiAdviceCard :items="adviceItems" />
      </view>
    </scroll-view>

    <!-- BottomBar: fixed bottom, z-index 40 -->
    <BottomBar @add-record="handleAddRecord" @chat="handleChat" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import type { IngredientDetail } from "../../types/product";
import ProductHeader from "../../components/ProductHeader.vue";
import NutritionCard from "../../components/NutritionCard.vue";
import RiskGroup from "../../components/RiskGroup.vue";
import IngredientCard from "../../components/IngredientCard.vue";
import HealthBenefitCard from "../../components/HealthBenefitCard.vue";
import AiAdviceCard from "../../components/AiAdviceCard.vue";
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
  if (barcode.value) {
    store.loadProduct(barcode.value);
  }
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

// Computed: group ingredients by risk level
const groupedIngredients = computed(() => {
  if (!store.product) return {};
  const groups: Record<string, IngredientDetail[]> = {
    t4: [],
    t3: [],
    t2: [],
    t0: [],
    unknown: [],
  };
  for (const ing of store.product.ingredients) {
    const level = ing.analysis?.level ?? "unknown";
    if (!groups[level]) groups[level] = [];
    groups[level].push(ing);
  }
  return groups;
});

// Computed: health-related analysis items
const healthItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) => a.analysis_type === "health_summary" || a.analysis_type === "health_benefits"
  )
);

// Computed: advice-related analysis items
const adviceItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) => a.analysis_type === "usage_advice_summary" || a.analysis_type === "advice"
  )
);

// Computed: overall risk level based on ingredients
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

.status-center {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 48rpx;
  z-index: 10;
}

.status-text {
  font-size: 30rpx;
  color: var(--text-muted);
}

.scroll-area {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-base);
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
