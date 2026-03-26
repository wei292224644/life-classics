<script setup lang="ts">
withDefaults(
  defineProps<{
    dclass?: string;
  }>(),
  {
    dclass: '',
  },
);
</script>

<template>
  <div :class="['skimmer', dclass]" />
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
  background: linear-gradient(
    90deg,
    theme("colors.gray.200") 25%,
    theme("colors.gray.100") 50%,
    theme("colors.gray.200") 75%
  );
  background-size: 200% 100%;
  animation: skimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}

.dark .skimmer {
  background: linear-gradient(
    90deg,
    theme("colors.gray.800") 25%,
    theme("colors.gray.700") 50%,
    theme("colors.gray.800") 75%
  );
  background-size: 200% 100%;
}

@media (prefers-reduced-motion: reduce) {
  .skimmer {
    animation: none;
  }
}
</style>
