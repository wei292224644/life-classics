<template>
  <view
    :class="
      cn(
        'w-screen  flex flex-col overflow-hidden bg-background',
        isRootPage ? 'flex-1' : 'h-screen',
      )
    "
  >
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
import { cn } from "@/utils/cn";

defineProps<{
  header?: VNode;
  content?: VNode;
  footer?: VNode;
  isRootPage?: boolean;
}>();

defineEmits<{
  (e: "scroll", event: { detail: { scrollTop: number } }): void;
}>();
</script>
