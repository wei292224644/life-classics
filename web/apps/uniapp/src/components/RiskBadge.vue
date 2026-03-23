<template>
  <view :class="['risk-badge inline-flex items-center', `risk-badge--${level}`]">
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
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 28rpx;

  &--critical { background: var(--risktag-t4-bg); color: var(--risk-t4); }
  &--high     { background: var(--risktag-t3-bg); color: var(--risk-t3); }
  &--medium   { background: var(--risktag-t2-bg); color: var(--risk-t2); }
  &--low      { background: var(--risktag-t1-bg); color: var(--risk-t1); }
  &--unknown  { background: var(--risktag-unknown-bg); color: var(--risk-unknown); }
}
</style>
