<script setup lang="ts">
import { onMounted, onUnmounted } from "vue"
import { useThemeStore } from "./store/theme"

const themeStore = useThemeStore()
onMounted(() => themeStore.init())
onUnmounted(() => themeStore.cleanup())
</script>

<template>
  <view :class="{ 'dark-mode': themeStore.isDark }">
    <slot />
  </view>
</template>

<style lang="scss">
@import 'uview-plus/index.scss';
</style>
