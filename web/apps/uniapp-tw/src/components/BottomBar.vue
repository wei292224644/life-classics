<script setup lang="ts">
const emit = defineEmits<{
  (e: "add-record"): void;
  (e: "chat"): void;
}>();
</script>

<template>
  <view class="bottom-bar">
    <button
      type="button"
      class="action-btn action-btn--secondary"
      @click="emit('add-record')"
    >
      添加到记录
    </button>
    <button
      type="button"
      class="action-btn action-btn--primary"
      @click="emit('chat')"
    >
      咨询 AI 助手
    </button>
  </view>
</template>

<style lang="scss" scoped>
.bottom-bar {
  @apply absolute bottom-0 left-0 right-0 z-50 flex items-center gap-3 px-3 py-3 bg-white;
}

.action-btn {
  @apply flex-1 rounded-sm px-4 py-3 text-sm border-none cursor-pointer transition;

  &:active {
    @apply scale-95;
  }

  &:focus-visible {
    @apply outline-accent;
    @apply outline-offset-2;
  }

  &--primary {
    @apply text-secondary bg-gradient-to-r from-accent-pink-light to-accent-pink shadow-md;

    &:active {
      @apply scale-95;
    }
  }

  &--secondary {
    @apply bg-secondary text-secondary-foreground;
    @apply border border-border;
  }
}
</style>
