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
.info-chip {
  @apply inline-flex items-center text-sm px-4 py-1 rounded font-medium box-border whitespace-nowrap;

  &.chip-risk {
    background: color-mix(in oklch, var(--color-destructive) 10%, transparent);
    color: var(--color-destructive);
    border: 1px solid color-mix(in oklch, var(--color-destructive) 20%, transparent);
  }

  &.chip-warn {
    background: color-mix(in oklch, var(--color-risk-t3) 10%, transparent);
    color: var(--color-risk-t3);
    border: 1px solid color-mix(in oklch, var(--color-risk-t3) 20%, transparent);
  }

  &.chip-neutral {
    background: color-mix(in oklch, var(--color-secondary) 10%, transparent);
    color: var(--color-secondary);
  }
}
</style>
