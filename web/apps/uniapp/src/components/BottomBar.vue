<script setup lang="ts">
const emit = defineEmits<{
  (e: 'add-record'): void;
  (e: 'chat'): void;
}>();
</script>

<template>
  <view class="bottom-bar">
    <button type="button" class="action-btn secondary" @click="emit('add-record')">
      添加到记录
    </button>
    <button type="button" class="action-btn primary" @click="emit('chat')">
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
  padding: 16px 20px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom));
  display: flex;
  gap: 12px;
  z-index: 40;

  background: var(--bottom-bar-bg);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
}

.action-btn {
  flex: 1;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
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
    outline: 2px solid var(--accent-pink);
    outline-offset: 2px;
  }

  // Primary: pink gradient
  &.primary {
    color: #fff !important;
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink)) !important;
    box-shadow: 0 4px 20px rgba(236, 72, 153, 0.3);

    &:hover {
      box-shadow: 0 6px 28px rgba(236, 72, 153, 0.4);
      transform: translateY(-1px);
    }
  }

  // Secondary: transparent with border (v14 style)
  &.secondary {
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #f5f5f5 !important;

    &:hover {
      background: rgba(255, 255, 255, 0.06) !important;
    }
  }
}
</style>
