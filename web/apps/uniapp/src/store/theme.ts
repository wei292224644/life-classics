// src/stores/theme.ts
import { defineStore } from "pinia"
import { ref } from "vue"

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(false)
  const statusBarHeight = ref(0)

  function handleThemeChange({ theme }: { theme: string }) {
    isDark.value = theme === "dark"
  }

  function init() {
    const info = uni.getSystemInfoSync()
    statusBarHeight.value = info.statusBarHeight ?? 0
    isDark.value = info.theme === "dark"
    uni.onThemeChange(handleThemeChange)
  }

  function cleanup() {
    uni.offThemeChange(handleThemeChange)
  }

  return { isDark, statusBarHeight, init, cleanup }
})