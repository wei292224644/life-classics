<script setup lang="ts">
import DButton from "./DButton.vue";

withDefaults(
  defineProps<{
    primaryLabel?: string;
    secondaryLabel?: string;
  }>(),
  {
    primaryLabel: "咨询 AI 助手",
    secondaryLabel: "添加到记录",
  },
);

const emit = defineEmits<{
  (e: "primary"): void;
  (e: "secondary"): void;
}>();
</script>

<template>
  <view
    class="flex items-center gap-3 px-3 py-3 bg-white/95 dark:bg-black/95 backdrop-saturate-[180%] backdrop-blur-[16px] shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.06)] dark:shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.4)] border-t border-border"
  >
    <DButton
      variant="secondary"
      dclass="flex-1 rounded-md"
      @click="emit('secondary')"
    >
      {{ secondaryLabel }}
    </DButton>

    <DButton
      variant="default"
      dclass="flex-1 rounded-md text-white text-sm"
      @click="emit('primary')"
    >
      {{ primaryLabel }}
    </DButton>
  </view>
</template>
