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
