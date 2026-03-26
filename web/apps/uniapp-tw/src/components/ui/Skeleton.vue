<script setup lang="ts">
import { cn } from "@/utils/cn";

withDefaults(
  defineProps<{
    dclass?: string;
  }>(),
  {
    dclass: "",
  },
);
</script>

<template>
  <view :class="cn('skimmer rounded-sm', dclass)" />
</template>

<style lang="scss" scoped>
@keyframes skimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.skimmer {
  background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
  background-size: 200% 100%;
  animation: skimmer 2s ease-in-out infinite;
}

.dark .skimmer {
  background: linear-gradient(90deg, #1f2937 25%, #374151 50%, #1f2937 75%);
  background-size: 200% 100%;
}

@media (prefers-reduced-motion: reduce) {
  .skimmer {
    animation: none;
  }
}
</style>
