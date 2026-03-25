// src/stores/theme.ts
import { defineStore } from "pinia"
import { ref } from "vue"

// H5 浏览器有 window.matchMedia，小程序没有
const isH5 = typeof window !== "undefined" && typeof window.matchMedia !== "undefined"

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(false)
  const statusBarHeight = ref(0)

  function handleThemeChange({ theme }: { theme: string }) {
    isDark.value = theme === "dark"
  }

  function init() {
    const info = uni.getSystemInfoSync()
    statusBarHeight.value = info.statusBarHeight ?? 0

    if (isH5) {
      // H5：使用浏览器原生 matchMedia
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
      isDark.value = mediaQuery.matches
      mediaQuery.addEventListener("change", (e) => {
        isDark.value = e.matches
      })
    } else {
      // 小程序：使用 UniApp API
      isDark.value = info.theme === "dark"
      uni.onThemeChange(handleThemeChange)
    }
  }

  function cleanup() {
    if (!isH5) {
      uni.offThemeChange(handleThemeChange)
    }
    // H5 下 matchMedia 的匿名监听无法精确移除，忽略 cleanup
  }

  return { isDark, statusBarHeight, init, cleanup }
})