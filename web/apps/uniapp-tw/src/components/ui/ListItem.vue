<template>
  <view class="list-item">
    <view :class="['list-item-icon', `icon-${icon}`]">
      <Icon v-if="icon === 'x'" name="x" :size="24" />
      <Icon v-else name="check" :size="24" />
    </view>
    <text class="list-item-text">{{ text }}</text>
  </view>
</template>

<script setup lang="ts">
import Icon from './Icon.vue'

defineProps<{
  icon: 'x' | 'check-green' | 'check-yellow';
  text: string;
}>();
</script>

<style lang="scss" scoped>
.list-item {
  @apply flex items-start gap-4;
}

.list-item-icon {
  @apply w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 mt-0.5;

  :deep(.icon-svg) {
    @apply w-6 h-6;
  }

  &.icon-x {
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
    color: var(--color-risk-t4);
  }
  &.icon-check-green {
    background: color-mix(in oklch, var(--color-risk-t0) 12%, transparent);
    color: var(--color-risk-t0);
  }
  &.icon-check-yellow {
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
    color: var(--color-risk-t2);
  }
}

.list-item-text {
  @apply text-lg text-secondary leading-relaxed flex-1;
}
</style>
