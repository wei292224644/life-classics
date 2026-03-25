<script setup lang="ts">
/**
 * Icon — Lucide-style icon component
 */
import { computed, useAttrs } from "vue";
import { iconRegistry, type IconName } from "../icons/iconsRegistry";

interface Props {
  name: IconName;
  size?: number | string;
  strokeWidth?: number | string;
  absoluteStrokeWidth?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  strokeWidth: 2,
  absoluteStrokeWidth: false,
});

const attrs = useAttrs();

const icon = computed(() => iconRegistry[props.name]);

const isFilled = computed(
  () => icon.value?.contents.includes('fill="currentColor"') ?? false,
);

const effectiveStrokeWidth = computed(() => {
  if (props.absoluteStrokeWidth) {
    return Number(props.strokeWidth) * (24 / Number(props.size));
  }
  return props.strokeWidth;
});
</script>

<template>
  <svg
    v-if="icon"
    :class="['block', 'flex-shrink-0', 'leading-none', attrs.class]"
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    :fill="isFilled ? 'currentColor' : 'none'"
    :stroke="isFilled ? undefined : 'currentColor'"
    :stroke-width="isFilled ? undefined : effectiveStrokeWidth"
    :stroke-linecap="isFilled ? undefined : 'round'"
    :stroke-linejoin="isFilled ? undefined : 'round'"
    aria-hidden="true"
    v-html="icon.contents"
  />
  <span
    v-else
    :class="['inline-block', 'text-[0.75em]', 'opacity-50', attrs.class]"
    >{{ name }}</span
  >
</template>
