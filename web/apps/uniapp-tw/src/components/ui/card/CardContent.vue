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
  <view :class="cn('p-5 pt-0', props.dclass)">
    <slot />
  </view>
</template>
