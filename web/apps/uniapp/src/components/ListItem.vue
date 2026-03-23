<template>
  <view class="flex items-start gap-4">
    <view :class="['list-item-icon', `icon-${icon}`, 'flex items-center justify-center flex-shrink-0 mt-1']">
      <!-- x icon -->
      <svg v-if="icon === 'x'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M18 6L6 18M6 6l12 12"/>
      </svg>
      <!-- check icon (check-green / check-yellow share the same path) -->
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M20 6L9 17l-5-5"/>
      </svg>
    </view>
    <text class="list-item-text flex-1">{{ text }}</text>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  icon: 'x' | 'check-green' | 'check-yellow';
  text: string;
}>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.list-item-icon {
  width: 36rpx;
  height: 36rpx;
  border-radius: 50%;
  font-size: 20rpx;
  font-weight: 700;

  svg {
    width: 24rpx;
    height: 24rpx;
  }

  &.icon-x { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); color: var(--risk-t4); }
  &.icon-check-green { background: color-mix(in oklch, var(--risk-t0) 12%, transparent); color: var(--risk-t0); }
  &.icon-check-yellow { background: color-mix(in oklch, var(--risk-t2) 12%, transparent); color: var(--risk-t2); }
}

.list-item-text {
  font-size: 26rpx;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
