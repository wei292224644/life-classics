<script setup lang="ts">
import { computed } from "vue";
import { cn } from "@/utils/cn";

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
})

type CardVariant = "default" | "elevated" | "outlined";

interface Props {
  variant?: CardVariant;
  hoverable?: boolean;
  dclass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "default",
  hoverable: false,
  dclass: "",
});

const cardClass = computed(() => {
  const base = "bg-card rounded-xl text-card-foreground p-4";

  const variantClass: Record<CardVariant, string> = {
    default: "border border-border shadow-sm",
    elevated:
      "border border-transparent shadow-[0_4rpx_12rpx_rgba(0,0,0,0.08),0_8rpx_24rpx_rgba(0,0,0,0.06)]",
    outlined: "border border-border shadow-none",
  };

  const hoverableClass = props.hoverable
    ? "cursor-pointer transition-[transform,box-shadow] duration-200 ease-[cubic-bezier(0.34,1.56,0.64,1)] hover:-translate-y-[2rpx] hover:shadow-[0_8rpx_24rpx_rgba(0,0,0,0.1),0_16rpx_48rpx_rgba(0,0,0,0.06)] active:translate-y-0"
    : "";

  return cn(base, variantClass[props.variant], hoverableClass, props.dclass);
});
</script>

<template>
  <view :class="cardClass">
    <slot />
  </view>
</template>
