<template>
  <view :class="['risk-badge', `risk-badge--${level}`]">
    <text>{{ label }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  whoLevel: string | null;
}>();

const level = computed(() => {
  switch (props.whoLevel) {
    case "Group 1": return "critical";
    case "Group 2A": return "high";
    case "Group 2B": return "medium";
    case "Group 3": return "low";
    default: return "unknown";
  }
});

const label = computed(() => props.whoLevel ?? "未知");
</script>

<style lang="scss" scoped>
.risk-badge {
  @apply inline-flex px-3 py-1 rounded text-base font-semibold;

  &--critical {
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
    color: var(--color-risk-t4);
  }
  &--high {
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
    color: var(--color-risk-t3);
  }
  &--medium {
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
    color: var(--color-risk-t2);
  }
  &--low {
    background: color-mix(in oklch, var(--color-risk-t1) 12%, transparent);
    color: var(--color-risk-t1);
  }
  &--unknown {
    background: color-mix(in oklch, var(--color-risk-unknown) 12%, transparent);
    color: var(--color-risk-unknown);
  }
}
</style>
