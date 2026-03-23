<template>
  <view class="section-header flex items-center gap-4 mb-5 pb-4">
    <view :class="['section-icon-wrap', `icon-bg-${icon}`]">
      <slot name="icon" />
    </view>
    <text class="section-title flex-1">{{ title }}</text>
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
@import "@/styles/design-system.scss";

.section-header {
  border-bottom: 1px solid var(--border-color);
}

.section-icon-wrap {
  width: 36rpx;
  height: 36rpx;
  border-radius: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.icon-bg-blue { background: color-mix(in oklch, var(--palette-blue-500) 12%, transparent); }
  &.icon-bg-red { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); }
  &.icon-bg-purple { background: color-mix(in oklch, var(--palette-purple-500) 12%, transparent); }
  &.icon-bg-green { background: color-mix(in oklch, var(--palette-green-500) 12%, transparent); }
  &.icon-bg-orange { background: color-mix(in oklch, var(--risk-t3) 12%, transparent); }
}

.section-title {
  font-size: 26rpx;
  font-weight: 700;
  color: var(--text-primary);
}

.ai-label {
  font-size: 20rpx;
  font-weight: 700;
  padding: 4rpx 12rpx;
  border-radius: 24rpx;
  background: var(--ai-label-bg);
  color: #fff;
}
</style>
