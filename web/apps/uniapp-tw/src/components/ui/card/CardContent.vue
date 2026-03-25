<script setup lang="ts">
interface Props {
  class?: string
}

defineProps<Props>()
</script>

<template>
  <view class="card-content" :class="class">
    <slot />
  </view>
</template>

<style lang="scss" scoped>
.card-content {
  @apply p-5 pt-0;
}
</style>
