<template>
  <view class="index-page">
    <view class="hero">
      <text class="title">食品安全助手</text>
      <text class="subtitle">扫码查配料 · 了解你吃的每一口</text>
    </view>

    <!-- 小程序端：扫码按钮 -->
    <!-- #ifndef H5 -->
    <view class="actions">
      <up-button type="primary" @click="handleScan">扫码查成分</up-button>
    </view>
    <!-- #endif -->

    <!-- H5 端：手动输入 -->
    <!-- #ifdef H5 -->
    <view class="actions">
      <up-input
        v-model="manualBarcode"
        placeholder="输入条形码"
        clearable
      />
      <up-button
        type="primary"
        :disabled="!manualBarcode.trim()"
        @click="handleManualInput"
      >
        查询
      </up-button>
    </view>
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { scanBarcode, ScanCancelledError } from "../../utils/scanner";

const manualBarcode = ref("");

async function handleScan() {
  try {
    const barcode = await scanBarcode();
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` });
  } catch (err) {
    if (err instanceof ScanCancelledError) return;
    uni.showToast({ title: "扫码失败，请重试", icon: "error" });
  }
}

function handleManualInput() {
  const barcode = manualBarcode.value.trim();
  if (!barcode) return;
  uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` });
}
</script>

<style lang="scss" scoped>
.index-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 40rpx;
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 80rpx;

  .title {
    font-size: 52rpx;
    font-weight: bold;
    color: #1a1a1a;
  }

  .subtitle {
    font-size: 28rpx;
    color: #888;
    margin-top: 16rpx;
  }
}

.actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
</style>
