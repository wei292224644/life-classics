<template>
  <text :class="['info-chip inline-flex items-center', `chip-${variant}`]">{{ text }}</text>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
  variant: "risk" | "warn" | "neutral";
}>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.info-chip {
  font-size: 20rpx;
  padding: 4rpx 16rpx;
  border-radius: 24rpx;
  font-weight: 500;
  box-sizing: border-box;
  white-space: nowrap;

  &.chip-risk {
    color: var(--chip-risk-text);
    background: var(--chip-risk-bg);
    border: 1px solid var(--chip-risk-border);
  }

  &.chip-warn {
    color: var(--chip-warn-text);
    background: var(--chip-warn-bg);
    border: 1px solid var(--chip-warn-border);
  }

  &.chip-neutral {
    color: var(--chip-neu-text);
    background: var(--chip-neu-bg);
  }
}
</style>
