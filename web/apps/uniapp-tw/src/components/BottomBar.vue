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
.bottom-bar {
  @apply fixed bottom-0 left-0 right-0 z-[40] flex gap-6 px-10 py-8;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  background: var(--bottom-bar-bg);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
}

.action-btn {
  @apply flex-1 py-7 rounded-xl text-xl font-semibold border-none cursor-pointer;
  font-family: inherit;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  -webkit-appearance: none;
  appearance: none;
  line-height: 1.2;
  min-height: 0;
  box-sizing: border-box;

  &:active {
    @apply scale-95;
  }

  &:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  &--primary {
    @apply text-white bg-gradient-to-br from-pink-400 to-pink-500;
    box-shadow: 0 4px 20rpx color-mix(in oklch, var(--color-accent) 30%, transparent);

    &:active {
      box-shadow: 0 6px 28rpx color-mix(in oklch, var(--color-accent) 40%, transparent);
    }
  }

  &--secondary {
    @apply bg-card border border-border text-foreground;
  }
}
</style>
