<template>
  <view class="scan-page">
    <text class="hint">正在启动扫码...</text>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { scanBarcode, ScanCancelledError } from "../../utils/scanner";

onMounted(async () => {
  try {
    const barcode = await scanBarcode();
    uni.redirectTo({ url: `/pages/product/index?barcode=${barcode}` });
  } catch (err) {
    if (err instanceof ScanCancelledError) {
      uni.navigateBack();
      return;
    }
    uni.showToast({ title: "扫码失败，请重试", icon: "error" });
    uni.navigateBack();
  }
});
</script>

<style lang="scss" scoped>
.scan-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;

  .hint {
    color: #888;
    font-size: var(--text-xl);
  }
}
</style>
