<script setup lang="ts">
import { computed } from 'vue'

type SeparatorOrientation = 'horizontal' | 'vertical'

interface Props {
  orientation?: SeparatorOrientation
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  orientation: 'horizontal',
  class: '',
})

const separatorClass = computed(() => {
  const base =
    'shrink-0 bg-border'

  const orientationClass =
    props.orientation === 'horizontal'
      ? 'h-[1px] w-full my-3'
      : 'h-full w-[1px] mx-3'

  return [base, orientationClass, props.class]
    .filter(Boolean)
    .join(' ')
})
</script>

<template>
  <view :class="separatorClass"></view>

</template>
