<template>
  <view class="product-header">
    <view
      class="header"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: statusBarHeight + 'px' }"
    >
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
        </svg>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useSystemInfo } from "../utils/system";

interface Props {
  name: string;
  overallRiskLevel: string;
}

defineProps<Props>();

const { statusBarHeight } = useSystemInfo();
const isScrolled = ref(false);

function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}

defineExpose({ updateScroll });

function handleBack() {
  uni.navigateBack();
}

function handleShare() {
  // TODO: share
}
</script>

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
  @apply fixed left-0 right-0 flex items-center px-8 gap-6;
  padding-top: 16rpx;
  padding-bottom: 16rpx;
  // 初始背景：半透明渐变，滚动后变为 glassmorphism
  background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 100%);
  transition: background 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  pointer-events: auto;

  &--scrolled {
    background: var(--header-scrolled-bg);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--color-border);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 1px 0 rgba(255, 255, 255, 0.06);

    .dark & {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(0, 0, 0, 0.04);
    }
  }
}

.header-btn {
  @apply w-6 h-6 rounded-2xl flex items-center justify-center bg-transparent border-none shadow-none outline-none appearance-none cursor-pointer flex-shrink-0;
  color: #ffffff;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  -webkit-appearance: none;
  appearance: none;

  .header--scrolled & {
    color: var(--color-foreground);
  }

  &:active {
    @apply scale-95;
    background: rgba(128, 128, 128, 0.15);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  svg {
    @apply w-5 h-5;
    stroke-width: 2;
  }
}

.header-title {
  @apply flex-1 text-2xl font-semibold tracking-tight;
  color: #ffffff;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  transition: color 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), text-shadow 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

  .header--scrolled & {
    color: var(--color-foreground);
    text-shadow: none;
  }
}
</style>
