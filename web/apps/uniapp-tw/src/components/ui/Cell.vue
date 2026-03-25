<script setup lang="ts">
import { computed } from 'vue'

type CellOrientation = 'horizontal' | 'vertical'
type CellSize = 'sm' | 'md' | 'lg'

interface Props {
  title?: string
  value?: string | number | null | undefined
  class?: string
  orientation?: CellOrientation
  size?: CellSize
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  value: '',
  class: '',
  orientation: 'horizontal',
  size: 'md',
})

const cellClass = computed(() => {
  const base = 'flex items-center justify-between p-3'
  const orientationClass = props.orientation === 'horizontal' ? 'flex-row' : 'flex-col'
  const sizeClass = {
    sm: 'text-xs py-2',
    md: 'text-sm py-3',
    lg: 'text-base py-3',
  }
  return [base, orientationClass, sizeClass, props.class]
    .filter(Boolean)
    .join(' ')
})

const titleClass = computed(() => {
  const sizeClass = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }
  return `text-foreground font-medium ${sizeClass[props.size]}`
})

const valueClass = computed(() => {
  const sizeClass = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }
  return `text-muted-foreground ${sizeClass[props.size]}`
})
</script>

<template>
  <view :class="cellClass">
    <!-- title -->
    <view v-if="$slots.title" class="flex-shrink-0">
      <slot name="title" />
    </view>
    <text v-else-if="title" :class="titleClass">{{ title }}</text>

    <!-- default slot -->
    <slot />

    <!-- value -->
    <view v-if="$slots.value" class="flex-shrink-0">
      <slot name="value" />
    </view>
    <text v-else-if="value !== '' && value !== null && value !== undefined"
      :class="[valueClass, 'text-right', orientation === 'horizontal' ? 'ml-4' : 'mt-1']">
      {{ value }}
    </text>
  </view>
</template>
