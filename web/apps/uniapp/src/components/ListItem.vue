<template>
  <view class="list-item">
    <view :class="['list-item-icon', `icon-${icon}`]">
      <!-- x icon -->
      <svg v-if="icon === 'x'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M18 6L6 18M6 6l12 12"/>
      </svg>
      <!-- check icon (check-green / check-yellow share the same path) -->
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M20 6L9 17l-5-5"/>
      </svg>
    </view>
    <text class="list-item-text">{{ text }}</text>
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

.list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.list-item-icon {
  width: var(--icon-lg);
  height: var(--icon-lg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 700;
  flex-shrink: 0;
  margin-top: var(--space-1);

  svg {
    width: var(--icon-xs);
    height: var(--icon-xs);
  }

  &.icon-x { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); color: var(--risk-t4); }
  &.icon-check-green { background: color-mix(in oklch, var(--risk-t0) 12%, transparent); color: var(--risk-t0); }
  &.icon-check-yellow { background: color-mix(in oklch, var(--risk-t2) 12%, transparent); color: var(--risk-t2); }
}

.list-item-text {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  line-height: 1.6;
  flex: 1;
}
</style>
