<template>
  <view :class="['risk-tag', `level-${level}`, size === 'sm' && 'risk-tag--sm']">
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
.risk-tag {
  @apply inline-flex items-center px-4 py-1 rounded-full text-sm font-semibold;

  &--sm {
    @apply text-xs px-3;
  }

  &.level-t4 {
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
    color: var(--color-risk-t4);
  }
  &.level-t3 {
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
    color: var(--color-risk-t3);
  }
  &.level-t2 {
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
    color: var(--color-risk-t2);
  }
  &.level-t1 {
    background: color-mix(in oklch, var(--color-risk-t1) 12%, transparent);
    color: var(--color-risk-t1);
  }
  &.level-t0 {
    background: color-mix(in oklch, var(--color-risk-t0) 12%, transparent);
    color: var(--color-risk-t0);
  }
  &.level-unknown {
    background: color-mix(in oklch, var(--color-risk-unknown) 12%, transparent);
    color: var(--color-risk-unknown);
  }
}
</style>
