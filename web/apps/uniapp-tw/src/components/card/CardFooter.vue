<script setup lang="ts">
interface Props {
  class?: string
}

defineProps<Props>()
</script>

<template>
  <view class="card-footer" :class="class">
    <slot />
  </view>
</template>

<style lang="scss" scoped>
.card-footer {
  @apply flex items-center p-5 pt-0;
}
</style>
