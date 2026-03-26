<script setup lang="ts">
import { computed } from "vue";
import DIcon from "./DIcon.vue";
import type { IconName } from "../icons/iconsRegistry";
import { cn } from "@/utils/cn";

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
})

type TagVariant =
  | "default"
  | "secondary"
  | "outline"
  | "ghost"
  | "destructive"
  | "success"
  | "warning";
type TagSize = "sm" | "md" | "lg";

interface Props {
  variant?: TagVariant;
  size?: TagSize;
  removable?: boolean;
  icon?: IconName;
  dclass?: string;
  textClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "default",
  size: "md",
  removable: false,
  icon: undefined,
  dclass: "",
  textClass: "",
});

const emit = defineEmits<{
  (e: "remove"): void;
}>();

const variantClass = computed(() => {
  switch (props.variant) {
    case "default":
      return "border-transparent text-muted";
    case "secondary":
      return "border-transparent text-secondary-foreground bg-[var(--secondary)]";
    case "outline":
      return "text-muted border-border bg-transparent";
    case "ghost":
      return "border-transparent text-muted bg-transparent";
    case "destructive":
      return "border-transparent text-muted bg-[var(--destructive)]";
    case "success":
      return "border-transparent text-muted bg-[var(--color-risk-t0)]";
    case "warning":
      return "border-transparent text-muted bg-[var(--color-risk-t2)]";
    default:
      return "border-transparent text-muted";
  }
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case "sm":
      return {
        tag: "px-2 py-0.5 text-xs gap-0.5",
        icon: "w-3 h-3",
        removeIcon: "w-3 h-3",
      };
    case "lg":
      return {
        tag: "px-4 py-1.5 text-sm gap-1.5",
        icon: "w-4 h-4",
        removeIcon: "w-4 h-4",
      };
    case "md":
    default:
      return {
        tag: "px-3 py-1 text-xs gap-1",
        icon: "w-3.5 h-3.5",
        removeIcon: "w-3.5 h-3.5",
      };
  }
});

const iconClass = computed(() => cn("flex-shrink-0", sizeClasses.value.icon));
const removeClass = computed(() =>
  cn(
    "flex items-center justify-center rounded-full -mr-0.5 p-0.5",
    "hover:opacity-80 active:opacity-60",
    "transition-opacity duration-150 ease",
  ),
);
const removeIconClass = computed(() => cn("opacity-70", sizeClasses.value.removeIcon));
</script>

<template>
  <view
    :class="cn(
      'inline-flex items-center gap-1 font-medium border rounded-full transition-all duration-150',
      variantClass,
      sizeClasses.tag,
      props.dclass,
    )"
  >
    <DIcon v-if="icon" :name="icon" :dclass="iconClass" />
    <text :class="cn('leading-none', props.textClass)">
      <slot />
    </text>
    <view v-if="removable" :class="removeClass" @tap="emit('remove')">
      <DIcon name="x" :dclass="removeIconClass" />
    </view>
  </view>
</template>
