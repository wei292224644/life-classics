<template>
  <view class="product-header">
    <!-- Status Bar -->
    <view
      class="status-bar"
      :style="{ height: statusBarHeight + 'px' }"
    >
      <text class="status-time">9:41</text>
    </view>

    <!-- Header (fixed) -->
    <view
      class="header"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: statusBarHeight + 'px' }"
    >
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <up-icon name="arrow-left" size="18" color="#fff" />
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <up-icon name="share" size="18" color="#fff" />
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useSystemInfo } from "../utils/system";

interface Props {
  name: string;
  imageUrl?: string;
  overallRiskLevel: string;
}

const props = defineProps<Props>();

const { statusBarHeight } = useSystemInfo();

const isScrolled = ref(false);

// Expose updateScroll for parent page to call
function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}

defineExpose({
  updateScroll,
});

function handleBack() {
  uni.navigateBack();
}

function handleShare() {
  // Share functionality to be implemented
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.product-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  pointer-events: none;
}

// Status Bar
.status-bar {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: transparent;
  pointer-events: none;

  .status-time {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: #fff;
  }
}

// Header
.header {
  position: fixed;
  width: 100%;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  left: 0;
  background: transparent;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  pointer-events: auto;

  &--scrolled {
    background: var(--header-scrolled-bg);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--border-color);
  }
}

.header-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  border: none;
  -webkit-appearance: none;
  appearance: none;

  &:active {
    transform: scale(0.92);
  }

  &:focus-visible {
    outline: 2px solid var(--accent-pink);
    outline-offset: 2px;
  }
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  flex: 1;
  letter-spacing: -0.02em;
  transition: color 0.3s;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);

  .header--scrolled & {
    color: var(--text-primary);
    text-shadow: none;
  }
}
</style>
