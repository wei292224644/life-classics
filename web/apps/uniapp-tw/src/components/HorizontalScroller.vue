<template>
  <scroll-view scroll-x class="horizontal-scroller" :enhanced="true">
    <view class="horizontal-scroller-inner" :style="{ gap: `${gap}rpx` }">
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

.horizontal-scroller-inner {
  display: flex;
  flex-direction: row;
  width: max-content;
  padding-bottom: var(--space-2);
}
</style>
