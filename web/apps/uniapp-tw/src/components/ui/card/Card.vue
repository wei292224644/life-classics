<script setup lang="ts">
import { computed } from 'vue'

type CardVariant = 'default' | 'elevated' | 'outlined'

interface Props {
  variant?: CardVariant
  hoverable?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  hoverable: false,
  class: '',
})

const cardClass = computed(() => [
  'card',
  `card--${props.variant}`,
  { 'card--hoverable': props.hoverable },
  props.class,
])
</script>

<template>
  <view :class="cardClass">
    <slot />
  </view>
</template>

<style lang="scss" scoped>
// ── Base Card ────────────────────────────────────────────────
.card {
  @apply bg-card rounded-xl text-card-foreground;
  background: var(--card);
  color: var(--card-foreground);

  // Default — subtle border
  &--default {
    @apply border border-border;
    box-shadow: var(--shadow-sm);
  }

  // Elevated — more prominent shadow
  &--elevated {
    @apply border border-transparent;
    box-shadow:
      0 4rpx 12rpx rgba(0, 0, 0, 0.08),
      0 8rpx 24rpx rgba(0, 0, 0, 0.06);
  }

  // Outlined — no shadow, just border
  &--outlined {
    @apply border border-border;
    box-shadow: none;
  }

  // Hoverable state
  &--hoverable {
    cursor: pointer;
    transition:
      transform 0.2s var(--ease-spring),
      box-shadow 0.2s ease;

    &:hover {
      transform: translateY(-2rpx);
      box-shadow:
        0 8rpx 24rpx rgba(0, 0, 0, 0.1),
        0 16rpx 48rpx rgba(0, 0, 0, 0.06);
    }

    &:active {
      transform: translateY(0);
    }
  }
}
</style>
