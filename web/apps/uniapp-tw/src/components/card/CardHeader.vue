<script setup lang="ts">
interface Props {
  class?: string
}

defineProps<Props>()
</script>

<template>
  <view class="card-header" :class="class">
    <slot />
  </view>
</template>

<style lang="scss" scoped>
.card-header {
  @apply flex flex-col space-y-1.5 p-5;
}
</style>
