<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'
import type { IconName } from '../utils/icons'

type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive'
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon'

interface Props {
  variant?: ButtonVariant
  size?: ButtonSize
  disabled?: boolean
  loading?: boolean
  iconLeft?: IconName
  iconRight?: IconName
  icon?: IconName // alias for iconLeft
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  disabled: false,
  loading: false,
  iconLeft: undefined,
  iconRight: undefined,
  icon: undefined,
  class: '',
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const resolvedIconLeft = computed(() => props.icon ?? props.iconLeft)
const resolvedIconRight = computed(() => props.iconRight)

const iconSize = computed(() => {
  const sizes: Record<ButtonSize, number> = { sm: 14, md: 16, lg: 18, icon: 18 }
  return sizes[props.size]
})

function handleClick(event: MouseEvent) {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :class="[
      'btn',
      `btn--${variant}`,
      `btn--${size}`,
      { 'btn--loading': loading, 'btn--icon-only': size === 'icon' && !$slots.default },
      props.class,
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <!-- Loading spinner -->
    <view v-if="loading" class="btn__loading" :class="`btn__loading--${size}`">
      <Icon name="loader" :size="iconSize" spin />
    </view>

    <!-- Left icon -->
    <Icon
      v-else-if="resolvedIconLeft"
      :name="resolvedIconLeft"
      :size="iconSize"
      class="btn__icon btn__icon--left"
    />

    <!-- Default slot -->
    <text v-if="$slots.default" class="btn__text">
      <slot />
    </text>

    <!-- Right icon -->
    <Icon
      v-if="resolvedIconRight && !loading"
      :name="resolvedIconRight"
      :size="iconSize"
      class="btn__icon btn__icon--right"
    />
  </button>
</template>

<style lang="scss" scoped>
// ── Base Button ─────────────────────────────────────────────
.btn {
  @apply inline-flex items-center justify-center gap-2 cursor-pointer;
  @apply font-semibold transition-all duration-200;
  @apply border border-transparent rounded-lg;
  @apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2;
  @apply disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none;

  // Spring easing for press effect
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  &:active:not(:disabled) {
    transform: scale(0.97);
  }
}

// ── Sizes ────────────────────────────────────────────────────
.btn--sm {
  @apply h-8 px-3 text-xs rounded-md;
  @apply gap-1.5;
}

.btn--md {
  @apply h-10 px-4 text-sm rounded-lg;
}

.btn--lg {
  @apply h-12 px-6 text-base rounded-xl;
  @apply gap-2.5;
}

.btn--icon {
  @apply h-10 w-10 rounded-lg;
  @apply p-0;

  &.btn--sm { @apply h-8 w-8 rounded-md; }
  &.btn--lg { @apply h-12 w-12 rounded-xl; }
}

.btn--icon-only {
  aspect-ratio: 1;
}

// ── Variants ─────────────────────────────────────────────────

// Default — accent pink gradient
.btn--default {
  @apply text-white border-transparent;
  background: linear-gradient(135deg, var(--accent-pink-light) 0%, var(--accent-pink) 100%);
  box-shadow:
    0 2rpx 8rpx rgba(0, 0, 0, 0.1),
    0 4rpx 16rpx color-mix(in oklch, var(--accent-pink) 25%, transparent);

  &:hover:not(:disabled) {
    box-shadow:
      0 4rpx 12rpx rgba(0, 0, 0, 0.15),
      0 8rpx 24rpx color-mix(in oklch, var(--accent-pink) 35%, transparent);
  }

  &:focus-visible {
    @apply ring-2 ring-offset-2;
    ring-color: var(--accent-pink);
  }
}

// Secondary — muted background
.btn--secondary {
  @apply text-foreground border-border;
  background: var(--secondary);
  border-color: var(--border);

  &:hover:not(:disabled) {
    background: color-mix(in oklch, var(--secondary) 85%, transparent);
  }

  &:focus-visible {
    @apply ring-2 ring-offset-2;
    ring-color: var(--ring);
  }
}

// Outline — transparent with border
.btn--outline {
  @apply text-foreground border-border bg-transparent;

  &:hover:not(:disabled) {
    background: var(--accent);
  }

  &:focus-visible {
    @apply ring-2 ring-offset-2;
    ring-color: var(--ring);
  }
}

// Ghost — fully transparent
.btn--ghost {
  @apply text-foreground bg-transparent border-transparent;

  &:hover:not(:disabled) {
    background: color-mix(in oklch, var(--foreground) 8%, transparent);
  }

  &:focus-visible {
    @apply ring-2 ring-offset-2;
    ring-color: var(--ring);
  }
}

// Destructive — red/destructive color
.btn--destructive {
  @apply text-white border-transparent;
  background: var(--destructive);
  box-shadow: 0 2rpx 8rpx color-mix(in oklch, var(--destructive) 30%, transparent);

  &:hover:not(:disabled) {
    background: color-mix(in oklch, var(--destructive) 85%, black);
  }

  &:focus-visible {
    @apply ring-2 ring-offset-2;
    ring-color: var(--destructive);
  }
}

// ── Elements ────────────────────────────────────────────────
.btn__loading {
  @apply flex items-center justify-center;
}

.btn__icon {
  @apply flex-shrink-0;

  &--left {
    margin-right: -2rpx;
  }

  &--right {
    margin-left: -2rpx;
  }
}

.btn__text {
  @apply inline-flex items-center justify-center;
}

// ── Loading state ────────────────────────────────────────────
.btn--loading {
  cursor: wait;
}
</style>
