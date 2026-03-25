# uniapp-tw 亮暗色系统自动切换设计

## 背景

uniapp-tw 项目需要在 H5 和小程序双端实现主题（亮色/暗色）跟随系统自动切换。

## 现状

- `src/store/theme.ts`：使用 UniApp 的 `uni.getSystemInfoSync().theme` 获取初始主题，`uni.onThemeChange` 监听主题变化
- `src/App.vue`：通过 `watchEffect` 监听 `isDark`，控制 `document.documentElement.classList.toggle("dark", ...)`
- `tailwind.config.ts`：`darkMode: "class"` — 通过 `.dark` class 切换暗色
- `src/style.scss`：`:root` 和 `.dark` 两套 CSS 变量定义

## 问题

UniApp 的主题 API（`uni.getSystemInfoSync().theme` 和 `uni.onThemeChange`）**在 H5 浏览器环境下不支持**，导致 H5 无法自动响应系统的亮/暗色切换。

## 解决方案

H5 端使用浏览器原生 `window.matchMedia('(prefers-color-scheme: dark)')` API，小程序端继续使用 UniApp API。

### 实现细节

**文件：** `src/store/theme.ts`

```ts
// src/stores/theme.ts
import { defineStore } from "pinia"
import { ref } from "vue"
import { isMp } from "../../platform"

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(false)
  const statusBarHeight = ref(0)

  function handleThemeChange({ theme }: { theme: string }) {
    isDark.value = theme === "dark"
  }

  function init() {
    const info = uni.getSystemInfoSync()
    statusBarHeight.value = info.statusBarHeight ?? 0

    if (isMp) {
      // 小程序：使用 UniApp API
      isDark.value = info.theme === "dark"
      uni.onThemeChange(handleThemeChange)
    } else {
      // H5：使用浏览器原生 matchMedia
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
      isDark.value = mediaQuery.matches
      mediaQuery.addEventListener("change", (e) => {
        isDark.value = e.matches
      })
    }
  }

  function cleanup() {
    if (isMp) {
      uni.offThemeChange(handleThemeChange)
    } else {
      // H5 下 matchMedia 无法精确移除单次监听，简单清理即可
    }
  }

  return { isDark, statusBarHeight, init, cleanup }
})
```

**新增导入：** 从 `platform.ts` 导入 `isMp` 判断平台（该文件已存在）

### 变更范围

| 文件 | 改动 |
|------|------|
| `src/store/theme.ts` | 修改 `init()` 和 `cleanup()`，H5 使用 `matchMedia` |

`App.vue`、`style.scss`、`tailwind.config.ts` **无需改动**。

## 风险与验证

- H5 开发服务器（`pnpm dev:uniapp:h5`）在浏览器中打开，切换系统主题，页面应自动响应
- 微信小程序开发者工具中测试，保持原有行为不变
