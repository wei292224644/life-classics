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
@import "@/styles/design-system.scss";

.risk-badge {
  display: inline-flex;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--space-2);
  font-size: var(--text-base);

  &--critical { background: var(--risktag-t4-bg); color: var(--risk-t4); }
  &--high     { background: var(--risktag-t3-bg); color: var(--risk-t3); }
  &--medium   { background: var(--risktag-t2-bg); color: var(--risk-t2); }
  &--low      { background: var(--risktag-t1-bg); color: var(--risk-t1); }
  &--unknown  { background: var(--risktag-unknown-bg); color: var(--risk-unknown); }
}
</style>
