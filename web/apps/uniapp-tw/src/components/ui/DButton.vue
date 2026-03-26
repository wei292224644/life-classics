<script setup lang="ts">
import { computed } from "vue";
import DIcon from "./DIcon.vue";
import type { IconName } from "../icons/iconsRegistry";
import { cn } from "@/utils/cn";

defineOptions({
  options: {
    virtualHost: true,
    addGlobalClass: true,
  },
});

type ButtonVariant =
  | "default"
  | "secondary"
  | "outline"
  | "ghost"
  | "destructive";
type ButtonSize = "sm" | "md" | "lg" | "icon";

interface Props {
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  iconLeft?: IconName;
  iconRight?: IconName;
  icon?: IconName;
  dclass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "default",
  size: "md",
  disabled: false,
  loading: false,
  iconLeft: undefined,
  iconRight: undefined,
  icon: undefined,
  dclass: "",
});

const emit = defineEmits<{
  (e: "click", event: Event): void;
}>();

const resolvedIconLeft = computed(() => props.icon ?? props.iconLeft);
const resolvedIconRight = computed(() => props.iconRight);

const iconSize = computed(() => {
  const sizes: Record<ButtonSize, number> = {
    sm: 14,
    md: 16,
    lg: 18,
    icon: 18,
  };
  return sizes[props.size];
});

const buttonClass = computed(() => {
  const base =
    "inline-flex items-center justify-center gap-2 border rounded-lg font-semibold transition-all duration-200 active:scale-[0.97] border-transparent";

  const cursor = props.loading ? "cursor-wait" : "cursor-pointer";
  const disabledClass =
    props.disabled || props.loading ? "opacity-50 pointer-events-none" : "";

  const sizeClass: Record<ButtonSize, string> = {
    sm: "h-8 px-3 text-xs rounded-md gap-1.5",
    md: "h-10 px-4 text-sm rounded-lg",
    lg: "h-12 px-6 text-base rounded-xl gap-2.5",
    icon: "h-10 w-10 p-0 rounded-lg",
  };

  const variantClass: Record<ButtonVariant, string> = {
    default:
      "text-foreground border-transparent bg-[linear-gradient(135deg,var(--accent-pink-light)_0%,var(--accent-pink)_100%)] shadow-[0_2rpx_8rpx_rgba(0,0,0,0.1),0_4rpx_16rpx_color-mix(in_oklch,var(--accent-pink)_25%,transparent)] focus-visible:ring-accent-pink",
    secondary:
      "text-foreground border-border bg-secondary focus-visible:ring-ring",
    outline:
      "text-foreground border-border bg-transparent focus-visible:ring-ring",
    ghost:
      "text-foreground bg-transparent border-transparent focus-visible:ring-ring",
    destructive:
      "text-white border-transparent bg-destructive focus-visible:ring-destructive",
  };

  return cn(
    base,
    cursor,
    disabledClass,
    sizeClass[props.size],
    variantClass[props.variant],
    props.dclass,
  );
});

function handleClick(event: Event) {
  if (!props.disabled && !props.loading) {
    emit("click", event);
  }
}
</script>

<template>
  <view :class="buttonClass" @tap="handleClick">
    <view v-if="loading" class="flex items-center justify-center">
      <DIcon
        name="loader"
        :size="iconSize"
        dclass="animate-spin duration-[1200ms]"
      />
    </view>

    <DIcon
      v-else-if="resolvedIconLeft"
      :name="resolvedIconLeft"
      :size="iconSize"
      dclass="flex-shrink-0 -mr-[2rpx]"
    />

    <slot />

    <DIcon
      v-if="resolvedIconRight && !loading"
      :name="resolvedIconRight"
      :size="iconSize"
      dclass="flex-shrink-0 -ml-[2rpx]"
    />
  </view>
</template>
