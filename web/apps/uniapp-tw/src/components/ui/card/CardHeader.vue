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
  <view :class="cn('flex flex-col space-y-1.5 p-6', props.dclass)">
    <slot />
  </view>
</template>
