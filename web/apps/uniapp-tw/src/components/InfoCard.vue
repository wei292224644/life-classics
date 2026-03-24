<template>
  <view class="info-card" :style="cardStyle">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

type PaddingLevel = "sm" | "md" | "lg" | "xl" | "2xl" | "3xl";
type RadiusLevel = "lg" | "xl";

const props = withDefaults(
  defineProps<{
    padding?: PaddingLevel;
    radius?: RadiusLevel;
  }>(),
  {
    padding: "xl",
    radius: "lg",
  }
);

const paddingMap: Record<PaddingLevel, string> = {
  sm: "var(--card-padding-sm)",
  md: "var(--card-padding-md)",
  lg: "var(--card-padding-lg)",
  xl: "var(--card-padding-xl)",
  "2xl": "var(--card-padding-2xl)",
  "3xl": "var(--card-padding-3xl)",
};

const radiusMap: Record<RadiusLevel, string> = {
  lg: "var(--radius-lg)",
  xl: "var(--radius-xl)",
};

const cardStyle = computed(() => ({
  padding: paddingMap[props.padding],
  borderRadius: radiusMap[props.radius],
}));
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;
}
</style>
