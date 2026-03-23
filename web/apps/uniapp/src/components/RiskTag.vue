<template>
  <view :class="['risk-tag inline-flex items-center', `level-${level}`, size === 'sm' && 'risk-tag--sm']">
    <text>{{ config.badge }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { getRiskConfig } from "../utils/riskLevel";
import type { RiskLevel } from "../utils/riskLevel";

const props = withDefaults(
  defineProps<{
    level: RiskLevel;
    size?: "sm" | "md";
  }>(),
  { size: "md" }
);

const config = computed(() => getRiskConfig(props.level));
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.risk-tag {
  padding: 4rpx 16rpx;
  border-radius: 9999rpx;
  font-size: 20rpx;
  font-weight: 600;

  &--sm {
    font-size: 20rpx;
    padding: 4rpx 12rpx;
  }

  // Colors reference CSS vars, auto dark mode
  &.level-t4 { background: var(--risktag-t4-bg); color: var(--risktag-t4-text); }
  &.level-t3 { background: var(--risktag-t3-bg); color: var(--risktag-t3-text); }
  &.level-t2 { background: var(--risktag-t2-bg); color: var(--risktag-t2-text); }
  &.level-t1 { background: var(--risktag-t1-bg); color: var(--risktag-t1-text); }
  &.level-t0 { background: var(--risktag-t0-bg); color: var(--risktag-t0-text); }
  &.level-unknown { background: var(--risktag-unknown-bg); color: var(--risktag-unknown-text); }
}
</style>
