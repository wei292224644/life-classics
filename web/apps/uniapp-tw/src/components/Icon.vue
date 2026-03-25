<script setup lang="ts">
/**
 * Icon — Lucide-style icon component
 */
import { computed } from 'vue';
import { iconRegistry, type IconName } from './icons/iconsRegistry';

interface Props {
  name: IconName;
  size?: number | string;
  strokeWidth?: number | string;
  absoluteStrokeWidth?: boolean;
  spin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  strokeWidth: 2,
  absoluteStrokeWidth: false,
  spin: false,
});

const icon = computed(() => iconRegistry[props.name]);

const isFilled = computed(() => icon.value?.contents.includes('fill="currentColor"') ?? false);

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
    class="icon"
    :class="{ 'icon--spin': spin }"
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
  <span v-else class="icon-placeholder">{{ name }}</span>
</template>

<style lang="scss" scoped>
.icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: middle;
  color: currentColor;

  &--spin {
    animation: spin 1.2s linear infinite;
  }
}

.icon-placeholder {
  font-size: 0.75em;
  opacity: 0.5;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
