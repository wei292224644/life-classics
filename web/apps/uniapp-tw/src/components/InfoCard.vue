<template>
  <view
    class="info-card"
    :class="[
      paddingClass,
      radiusClass,
    ]"
  >
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

const paddingClass = computed(() => {
  const map: Record<PaddingLevel, string> = {
    sm: "p-4",
    md: "p-5",
    lg: "p-6",
    xl: "p-8",
    "2xl": "p-10",
    "3xl": "p-12",
  };
  return map[props.padding];
});

const radiusClass = computed(() => {
  const map: Record<RadiusLevel, string> = {
    lg: "rounded-xl",
    xl: "rounded-2xl",
  };
  return map[props.radius];
});
</script>

<style lang="scss" scoped>
.info-card {
  @apply bg-card border border-border box-border w-full overflow-hidden;
}
</style>
