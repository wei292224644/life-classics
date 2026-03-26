<script setup lang="ts">
import { computed } from "vue";
import { getRiskConfig, riskCls } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import type { RiskLevel } from "@/utils/riskLevel";

type RiskTagSize = "sm" | "md";

type Props = {
  level: RiskLevel;
  size?: RiskTagSize;
};
const props = withDefaults(defineProps<Props>(), { size: "md" });

const config = computed(() => getRiskConfig(props.level));

const tagClass = computed(() => {
  const baseClass = "inline-flex items-center rounded-sm font-semibold border";
  const sizeClass: Record<RiskTagSize, string> = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
  };
  return cn(
    baseClass,
    sizeClass[props.size],
    riskCls(props.level, "bg/12 text border/50"),
  );
});
</script>

<template>
  <view :class="tagClass">
    <text>{{ config.badge }}</text>
  </view>
</template>
