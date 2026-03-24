<template>
  <text :class="['info-chip', `chip-${variant}`]">{{ text }}</text>
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
  display: inline-flex;
  align-items: center;
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-sm);
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
