<script setup lang="ts">
interface Props {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
  class?: string
}

withDefaults(defineProps<Props>(), {
  as: 'h3',
})
</script>

<template>
  <component :is="as" class="card-title" :class="class">
    <slot />
  </component>
</template>

<style lang="scss" scoped>
.card-title {
  @apply font-semibold text-foreground leading-none tracking-tight;
  font-size: 1.125em; // 18px at base
  line-height: 1.2;

  &.h1 { @apply text-xl; }
  &.h2 { @apply text-lg; }
  &.h3 { @apply text-base; }
  &.h4 { @apply text-sm; }
}
</style>
