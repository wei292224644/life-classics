<template>
  <scroll-view scroll-x class="horizontal-scroller" :enhanced="true">
    <view class="flex flex-row w-max pb-2" :style="{ gap: `${gap}rpx` }">
      <slot />
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    gap?: number;
  }>(),
  { gap: 20 }
);
</script>

<style lang="scss" scoped>
.horizontal-scroller {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar { display: none; }
}

</style>
