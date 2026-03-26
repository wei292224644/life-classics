<script setup lang="ts">
import { cn } from '@/utils/cn'

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
})

interface Props {
  dclass?: string
}

const props = defineProps<Props>()
</script>

<template>
  <text :class="cn('font-semibold text-foreground leading-none tracking-tight text-base', props.dclass)">
    <slot />
  </text>
</template>
