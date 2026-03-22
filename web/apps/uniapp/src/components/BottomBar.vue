<script setup lang="ts">
const emit = defineEmits<{
  (e: 'add-record'): void;
  (e: 'chat'): void;
}>();
</script>

<template>
  <view class="bottom-bar">
    <button type="button" class="action-btn action-btn--secondary" @click="emit('add-record')">
      添加到记录
    </button>
    <button type="button" class="action-btn action-btn--primary" @click="emit('chat')">
      咨询 AI 助手
    </button>
  </view>
</template>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32rpx 40rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  display: flex;
  gap: 24rpx;
  z-index: 40;
  background: var(--bottom-bar-bg);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
}

.action-btn {
  flex: 1;
  padding: 28rpx 32rpx;
  border-radius: 28rpx;
  font-size: 28rpx;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s $ease-spring;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  line-height: 1.2;

  &:active {
    transform: scale(0.97);
  }

  &:focus-visible {
    outline: 2px solid var(--accent-pink);
    outline-offset: 2px;
  }

  &--primary {
    color: #fff;
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    box-shadow: 0 4px 20px rgba(236, 72, 153, 0.3);

    &:active {
      box-shadow: 0 6px 28px rgba(236, 72, 153, 0.4);
    }
  }

  &--secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary);

    // 亮色模式覆盖
    .product-page:not(.dark-mode) & {
      background: rgba(0, 0, 0, 0.04);
      border-color: rgba(0, 0, 0, 0.08);
    }
  }
}
</style>
