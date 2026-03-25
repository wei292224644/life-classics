<script setup lang="ts">
interface Props {
  class?: string
}

defineProps<Props>()
</script>

<template>
  <view :class="class">
    <slot />
  </view>
</template>
