<script setup lang="ts">
import { computed } from "vue";
import { cn } from "@/utils/cn";

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
});

type CellOrientation = "horizontal" | "vertical";
type CellSize = "sm" | "md" | "lg";

interface Props {
  title?: string;
  value?: string | number | null | undefined;
  dclass?: string;
  orientation?: CellOrientation;
  size?: CellSize;
}

const props = withDefaults(defineProps<Props>(), {
  title: "",
  value: "",
  dclass: "",
  orientation: "horizontal",
  size: "md",
});

const sizeClass: Record<CellSize, string> = {
  sm: "text-xs h-10 px-3",
  md: "text-sm h-12 px-3",
  lg: "text-base h-14 px-3",
};

const cellClass = computed(() =>
  cn(
    "flex items-center justify-between",
    props.orientation === "horizontal" ? "flex-row" : "flex-col",
    sizeClass[props.size],
    props.dclass,
  ),
);
</script>

<template>
  <view :class="cellClass">
    <!-- title -->
    <view v-if="$slots.title" class="flex-shrink-0">
      <slot name="title" />
    </view>
    <text v-else-if="title" class="text-foreground font-medium">{{
      title
    }}</text>

    <!-- default slot -->
    <slot />

    <!-- value -->
    <view v-if="$slots.value" class="flex-shrink-0">
      <slot name="value" />
    </view>
    <text
      v-else-if="value !== '' && value !== null && value !== undefined"
      class="text-foreground text-sm text-right"
    >
      {{ value }}
    </text>
  </view>
</template>
