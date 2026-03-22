<template>
  <view class="product-header">
    <!-- Status Bar -->
    <view
      class="status-bar"
      :class="{ 'light-mode': isLight }"
      :style="{ height: statusBarHeight + 'px' }"
    >
      <text class="status-time">9:41</text>
    </view>

    <!-- Header (fixed) -->
    <view
      class="header"
      :class="{ 'header--scrolled': isScrolled, 'light-mode': isLight }"
      :style="{ top: statusBarHeight + 'px' }"
    >
      <button type="button" class="header-btn" aria-label="返回" @click="handleBack">
        <up-icon name="arrow-left" size="18" :color="isLight ? '#111' : '#fff'" />
      </button>
      <text class="header-title">{{ name }}</text>
      <button type="button" class="header-btn" aria-label="分享" @click="handleShare">
        <up-icon name="share" size="18" :color="isLight ? '#111' : '#fff'" />
      </button>
    </view>

    <!-- Banner -->
    <view class="banner" :class="{ 'light-mode': isLight }">
      <view class="banner-content">
        <image v-if="imageUrl" :src="imageUrl" class="banner-image" mode="aspectFill" />
        <text v-else class="banner-emoji">🍎</text>
        <text class="banner-label">产品图片</text>
      </view>
      <view class="banner-badge" :class="{ 'light-mode': isLight }">
        <up-icon name="checkmark-circle" size="14" color="var(--risk-t0)" />
        <text class="banner-badge-text">低风险</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useSystemInfo } from "../utils/system";

interface Props {
  name: string;
  imageUrl?: string;
  overallRiskLevel: string; // "t0"|"t1"|"t2"|"t3"|"t4"|"unknown"
}

const props = defineProps<Props>();

const { statusBarHeight } = useSystemInfo();

const isScrolled = ref(false);
const isDark = ref(true); // Default to dark mode

const isLight = computed(() => !isDark.value);

// Expose updateScroll for parent page to call
function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}

// Expose setTheme for parent page to call
function setTheme(dark: boolean) {
  isDark.value = dark;
}

defineExpose({
  updateScroll,
  setTheme,
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
  position: relative;
  width: 100%;
}

// Status Bar
.status-bar {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 50;

  .status-time {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: #fff;
  }

  &.light-mode {
    background: #fff;
    border-bottom: 1px solid rgba(0, 0, 0, 0.04);

    .status-time {
      color: #111;
    }
  }
}

// Header
.header {
  position: fixed;
  width: 100%;
  z-index: 50;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  left: 0;
  background: var(--header-bg);
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);

  &--scrolled {
    background: var(--header-scrolled-bg);
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);

    &.light-mode {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(0, 0, 0, 0.04);
    }

    &:not(.light-mode) {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 1px 0 rgba(255, 255, 255, 0.06);
    }
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

  .light-mode & {
    color: rgba(0, 0, 0, 0.8);
  }

  &:not(.light-mode) {
    color: rgba(255, 255, 255, 0.9);
  }
}

// Banner
.banner {
  height: 260px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;

  &:not(.light-mode) {
    background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);

    &::before {
      background:
        radial-gradient(ellipse 80% 60% at 50% 0%, rgba(34, 197, 94, 0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(236, 72, 153, 0.05) 0%, transparent 50%);
    }
  }

  &.light-mode {
    background: linear-gradient(145deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%);

    &::before {
      background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(251, 191, 36, 0.3) 0%, transparent 60%);
    }
  }

  &::before {
    content: '';
    position: absolute;
    inset: 0;
  }
}

.banner-content {
  text-align: center;
  position: relative;
  z-index: 1;
}

.banner-image {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
  object-fit: cover;
}

.banner-emoji {
  font-size: 80px;
  margin-bottom: 8px;
  filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.3));
  animation: floatIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: scale(0.8);
  transform-origin: center;

  .light-mode & {
    filter: drop-shadow(0 8px 24px rgba(251, 191, 36, 0.3));
  }
}

.banner-label {
  font-size: 13px;
  letter-spacing: 0.1em;

  &:not(.light-mode) {
    color: var(--text-muted);
  }

  .light-mode & {
    color: var(--banner-label);
  }
}

// Banner Badge (低风险徽章)
.banner-badge {
  position: absolute;
  right: 20px;
  bottom: 20px;
  border-radius: 14px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  animation: slideUp 0.6s 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(10px);

  &:not(.light-mode) {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.3));
    border: 1px solid rgba(34, 197, 94, 0.3);
    box-shadow: 0 4px 20px rgba(34, 197, 94, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(22, 163, 74, 0.25));
    border: 1px solid rgba(34, 197, 94, 0.25);
    box-shadow: 0 4px 20px rgba(34, 197, 94, 0.15);
  }
}

.banner-badge-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--risk-t0);
}
</style>
