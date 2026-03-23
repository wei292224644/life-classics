<script setup lang="ts">
const emit = defineEmits<{
  (e: 'add-record'): void;
  (e: 'chat'): void;
}>();
</script>

<template>
  <view class="bottom-bar flex gap-6">
    <button type="button" class="action-btn action-btn--secondary flex-1" @click="emit('add-record')">
      添加到记录
    </button>
    <button type="button" class="action-btn action-btn--primary flex-1" @click="emit('chat')">
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
  padding: var(--space-8) var(--space-10);
  padding-bottom: calc(var(--space-8) + env(safe-area-inset-bottom));
  z-index: 40;
  background: var(--bottom-bar-bg);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
}

.action-btn {
  flex: 1;
  padding: var(--space-7) var(--btn-padding-x);
  border-radius: var(--btn-radius);
  font-size: var(--text-xl);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s $ease-spring;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  line-height: 1.2;
  min-height: 0;
  box-sizing: border-box;

  &:active {
    transform: scale(0.97);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &--primary {
    color: #fff;
    background: linear-gradient(135deg, var(--accent-light), var(--accent));
    box-shadow: 0 4px 20rpx color-mix(in oklch, var(--accent) 30%, transparent);

    &:active {
      box-shadow: 0 6px 28rpx color-mix(in oklch, var(--accent) 40%, transparent);
    }
  }

  &--secondary {
    background: color-mix(in oklch, #ffffff 6%, transparent);
    border: 1px solid color-mix(in oklch, #ffffff 10%, transparent);
    color: var(--text-primary);

    // 亮色模式覆盖
    .product-page:not(.dark-mode) & {
      background: color-mix(in oklch, var(--palette-gray-900) 4%, transparent);
      border-color: color-mix(in oklch, var(--palette-gray-900) 8%, transparent);
    }
  }
}
</style>
