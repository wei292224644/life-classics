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
  display: inline-flex;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 22rpx;

  &--critical { background: #fee2e2; color: #dc2626; }
  &--high     { background: #ffedd5; color: #ea580c; }
  &--medium   { background: #fef9c3; color: #ca8a04; }
  &--low      { background: #dcfce7; color: #16a34a; }
  &--unknown  { background: #f3f4f6; color: #6b7280; }
}
</style>
