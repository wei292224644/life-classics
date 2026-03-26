<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/utils/cn'

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
})

type SeparatorOrientation = 'horizontal' | 'vertical'

interface Props {
  orientation?: SeparatorOrientation
  dclass?: string
}

const props = withDefaults(defineProps<Props>(), {
  orientation: 'horizontal',
  dclass: '',
})

const separatorClass = computed(() => {
  const base = 'shrink-0 bg-border'

  const orientationClass =
    props.orientation === 'horizontal'
      ? 'h-[1px] w-full my-3'
      : 'h-full w-[1px] mx-3'

  return cn(base, orientationClass, props.dclass)
})
</script>

<template>
  <view :class="separatorClass"></view>
</template>
