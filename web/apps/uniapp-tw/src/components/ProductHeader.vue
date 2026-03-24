<script setup lang="ts">
import { ref } from 'vue'
import { useSystemInfo } from '../utils/system'
import Icon from './Icon.vue'

interface Props {
  name: string
  overallRiskLevel: string
}

defineProps<Props>()

const { statusBarHeight } = useSystemInfo()
const isScrolled = ref(false)

function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60
}

defineExpose({ updateScroll })

function handleBack() {
  uni.navigateBack()
}

function handleShare() {
  // TODO: share
}
</script>

<template>
  <view class="product-header">
    <view
      class="header"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: `${statusBarHeight}px` }"
    >
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <Icon name="arrowLeft" :size="36" />
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <Icon name="share" :size="36" />
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.product-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  pointer-events: none;
}

.header {
  @apply fixed left-0 right-0 flex items-center;
  height: 128rpx;
  padding-left: 28rpx;
  padding-right: 28rpx;
  background: transparent;
  transition:
    background 0.4s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  pointer-events: auto;

  &--scrolled {
    background: var(--header-scrolled-bg);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--color-border);
    box-shadow:
      0 8rpx 48rpx rgba(0, 0, 0, 0.08),
      0 1px 0 rgba(0, 0, 0, 0.04);
  }
}

.header-btn {
  @apply rounded-2xl flex items-center justify-center bg-transparent border-none shadow-none outline-none appearance-none cursor-pointer flex-shrink-0;
  width: 60rpx;
  height: 60rpx;
  color: var(--color-foreground);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  -webkit-appearance: none;
  appearance: none;

  &:active {
    @apply scale-95;
    background: rgba(128, 128, 128, 0.15);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.header-title {
  @apply flex-1 font-semibold tracking-tight;
  font-size: 34rpx;
  color: var(--color-foreground);
  line-height: 1.15;
}
</style>
