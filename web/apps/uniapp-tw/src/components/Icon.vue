<script setup lang="ts">
import { icons, type IconName } from "../utils/icons";

interface Props {
  name: IconName;
  size?: string | number;
  spin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 20,
  spin: false,
});

const icon = icons[props.name];
</script>

<template>
  <svg
    class="icon-svg"
    :class="{ 'icon-svg--spin': spin }"
    :viewBox="icon.viewBox"
    :width="size"
    :height="size"
    aria-hidden="true"
    fill="none"
    stroke="currentColor"
    :stroke-width="(icon as any).strokeWidth ?? 2"
    v-if="!icon.filled"
  >
    <path :d="icon.paths" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
  <svg
    class="icon-svg"
    :class="{ 'icon-svg--spin': spin }"
    :viewBox="icon.viewBox"
    :width="size"
    :height="size"
    aria-hidden="true"
    v-else
  >
    <path :d="icon.paths" fill="currentColor" />
  </svg>
</template>

<style lang="scss" scoped>
.icon-svg {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: middle;
  color: currentColor;

  &--spin {
    animation: spin 1.2s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
