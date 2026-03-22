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
import { ref, onMounted } from "vue";
import { useProductStore } from "../../store/product";
import NutritionTable from "../../components/NutritionTable.vue";
import IngredientList from "../../components/IngredientList.vue";
import AnalysisCard from "../../components/AnalysisCard.vue";

type TabKey = "nutrition" | "ingredient" | "analysis";

const TABS: { key: TabKey; label: string }[] = [
  { key: "nutrition", label: "营养" },
  { key: "ingredient", label: "配料" },
  { key: "analysis", label: "分析" },
];

const store = useProductStore();
const activeTab = ref<TabKey>("nutrition");

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
