<script setup lang="ts">
import Button from "./Button.vue";

const emit = defineEmits<{
  (e: "add-record"): void;
  (e: "chat"): void;
}>();
</script>

<template>
  <view
    class="flex items-center gap-3 px-3 py-3 bg-white/95 dark:bg-black/95 backdrop-saturate-[180%] backdrop-blur-[16px] shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.06)] dark:shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.4)] border-t border-border">
    <Button size="lg" variant="secondary" class="flex-1 !rounded-sm" @click="emit('add-record')">
      添加到记录
    </Button>

    <Button size="lg" variant="default" class="flex-1 !rounded-sm !text-white" @click="emit('chat')">
      咨询 AI 助手
    </Button>
  </view>
</template>
