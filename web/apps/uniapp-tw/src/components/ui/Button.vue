<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'
import type { IconName } from '../icons/iconsRegistry'

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

const buttonClass = computed(() => {
  const base =
    'inline-flex items-center justify-center gap-2 border rounded-lg font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.97] disabled:active:scale-100 border-transparent'

  const cursor = props.loading ? 'cursor-wait' : 'cursor-pointer'
  const disabledCursor = props.disabled && !props.loading ? 'disabled:cursor-not-allowed' : ''

  const sizeClass: Record<ButtonSize, string> = {
    sm: 'h-8 px-3 text-xs rounded-md gap-1.5',
    md: 'h-10 px-4 text-sm rounded-lg',
    lg: 'h-12 px-6 text-base rounded-xl gap-2.5',
    icon: 'h-10 w-10 p-0 rounded-lg',
  }

  const variantClass: Record<ButtonVariant, string> = {
    default:
      'text-white border-transparent bg-[linear-gradient(135deg,var(--accent-pink-light)_0%,var(--accent-pink)_100%)] shadow-[0_2rpx_8rpx_rgba(0,0,0,0.1),0_4rpx_16rpx_color-mix(in_oklch,var(--accent-pink)_25%,transparent)] hover:shadow-[0_4rpx_12rpx_rgba(0,0,0,0.15),0_8rpx_24rpx_color-mix(in_oklch,var(--accent-pink)_35%,transparent)] focus-visible:ring-accent-pink',
    secondary:
      'text-foreground border-border bg-secondary hover:bg-[color-mix(in_oklch,var(--secondary)_85%,transparent)] focus-visible:ring-ring',
    outline:
      'text-foreground border-border bg-transparent hover:bg-accent focus-visible:ring-ring',
    ghost:
      'text-foreground bg-transparent border-transparent hover:bg-[color-mix(in_oklch,var(--foreground)_8%,transparent)] focus-visible:ring-ring',
    destructive:
      'text-white border-transparent bg-destructive shadow-[0_2rpx_8rpx_color-mix(in_oklch,var(--destructive)_30%,transparent)] hover:bg-[color-mix(in_oklch,var(--destructive)_85%,black)] focus-visible:ring-destructive',
  }

  return [
    base,
    cursor,
    disabledCursor,
    sizeClass[props.size],
    variantClass[props.variant],
    props.class,
  ]
    .filter(Boolean)
    .join(' ')
})

function handleClick(event: MouseEvent) {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :class="buttonClass"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <!-- Loading spinner -->
    <view v-if="loading" class="flex items-center justify-center">
      <Icon name="loader" :size="iconSize" class="animate-spin duration-[1200ms]" />
    </view>

    <!-- Left icon -->
    <Icon
      v-else-if="resolvedIconLeft"
      :name="resolvedIconLeft"
      :size="iconSize"
      class="flex-shrink-0 -mr-[2rpx]"
    />

    <!-- Default slot -->
    <text v-if="$slots.default" class="inline-flex items-center justify-center">
      <slot />
    </text>

    <!-- Right icon -->
    <Icon
      v-if="resolvedIconRight && !loading"
      :name="resolvedIconRight"
      :size="iconSize"
      class="flex-shrink-0 -ml-[2rpx]"
    />
  </button>
</template>
