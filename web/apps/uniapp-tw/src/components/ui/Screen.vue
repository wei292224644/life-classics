<template>
  <view class="w-screen h-screen flex flex-col overflow-hidden">
    <view class="shrink-0">
      <slot name="header" />
    </view>
    <scroll-view
      class="flex-1 overflow-hidden"
      scroll-y
      :show-scrollbar="false"
      @scroll="$emit('scroll', $event)"
    >
      <slot name="content" />
    </scroll-view>
    <view class="shrink-0">
      <slot name="footer" />
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  header?: VNode;
  content?: VNode;
  footer?: VNode;
}>();

defineEmits<{
  (e: "scroll", event: { detail: { scrollTop: number } }): void;
}>();
</script>
