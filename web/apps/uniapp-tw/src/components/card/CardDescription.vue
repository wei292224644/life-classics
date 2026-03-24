<script setup lang="ts">
interface Props {
  class?: string
}

defineProps<Props>()
</script>

<template>
  <view class="card-description" :class="class">
    <slot />
  </view>
</template>

<style lang="scss" scoped>
.card-description {
  @apply text-sm text-muted-foreground;
  line-height: 1.5;
}
</style>
