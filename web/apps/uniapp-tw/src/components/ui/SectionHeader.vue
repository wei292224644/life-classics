<template>
  <view class="section-header">
    <view :class="['section-icon-wrap', `icon-bg-${icon}`]">
      <slot name="icon" />
    </view>
    <text class="section-title">{{ title }}</text>
    <view v-if="showAiBadge" class="ai-label">AI</view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  icon: "blue" | "red" | "purple" | "green" | "orange";
  title: string;
  showAiBadge?: boolean;
}>();
</script>

<style lang="scss" scoped>
.section-header {
  @apply flex items-center gap-4 mb-5 pb-4;
  border-bottom: 1px solid var(--color-border);
}

.section-icon-wrap {
  @apply w-10 h-10 rounded flex items-center justify-center flex-shrink-0;

  &.icon-bg-blue {
    background: color-mix(in oklch, var(--palette-blue-500) 12%, transparent);
  }
  &.icon-bg-red {
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
  }
  &.icon-bg-purple {
    background: color-mix(in oklch, var(--palette-purple-500) 12%, transparent);
  }
  &.icon-bg-green {
    background: color-mix(in oklch, var(--palette-green-500) 12%, transparent);
  }
  &.icon-bg-orange {
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
  }
}

.section-title {
  @apply text-lg font-bold text-foreground flex-1;
}

.ai-label {
  @apply text-xs font-bold px-3 py-1 rounded text-white;
  background: var(--ai-label-bg);
}
</style>
