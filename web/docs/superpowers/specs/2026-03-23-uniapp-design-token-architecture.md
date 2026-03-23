# UniApp 设计 Token 架构

> 日期：2026-03-23
> 状态：设计完成，待实现

## 1. 背景与目标

**问题：** UniApp 项目中颜色/主题管理混乱，具体表现为：
- 每个页面都在 `computed` 里手写 CSS 变量映射（参考 `ingredient-detail/index.vue` 的 `pageStyle`）
- 每个页面各自管理 `isDark` 状态，重复监听 `uni.onThemeChange`
- `riskLevel.ts` 包含颜色配置，与 `design-system.scss` 存在重复
- `design-system.scss` 有完整 CSS 变量定义但从未在运行时生效

**目标：**
- 建立统一的 ThemeStore，集中管理 `isDark` 和 `statusBarHeight`
- 所有 CSS 颜色通过 CSS 变量获取，页面不再手写颜色映射
- `riskLevel.ts` 只保留纯数据（badge/icon/needleLeft），颜色全部来自 design-system token
- 全局 `.dark-mode` class 在 App.vue 根节点挂载一次，所有子页面天然继承

## 2. 架构概览

```
App.vue（根节点）
  └── :class="{ 'dark-mode': themeStore.isDark }"
        + uni.onThemeChange 监听

ThemeStore（新增 stores/theme.ts）
  ├── isDark: boolean          — 全局暗色模式状态
  ├── statusBarHeight: number — 系统状态栏高度
  ├── init()                   — 初始化 + 监听
  └── cleanup()               — 取消监听

design-system.scss
  ├── palette-*    — 基础色调（已有）
  ├── semantic-*   — 语义色，亮/暗两套（已有）
  ├── risk-header-* — 风险 Header 专用色（新增）
  └── component-*  — 组件色（已有）

riskLevel.ts（改造）
  ├── RISK_CONFIG — 只保留 badge/icon/needleLeft
  └── getRiskConfig() / levelToVisualKey()（不变）

各页面
  ├── 删除 local ref(isDark) + onThemeChange
  ├── 引入 useThemeStore()
  └── 颜色全部通过 class + var(--xxx) 获取
```

## 3. 新增 Token 定义

在 `design-system.scss` 的 `.dark-mode` 之前、`page` 层级的 COMPONENT 段之后，新增 `RISK HEADER` 语义色段落。

### 亮色模式

```scss
// Risk Header 语义色 — 亮色
--risk-critical-header-bg: var(--palette-red-50);      // #fef2f2
--risk-critical-header-border: var(--palette-red-200); // #fecaca
--risk-critical-header-title: var(--palette-red-800);   // #7f1d1d
--risk-critical-header-sub: var(--palette-red-600);     // #b91c1c
--risk-critical-header-btn: color-mix(in oklch, var(--palette-red-500) 15%, transparent);

--risk-high-header-bg: var(--palette-orange-50);       // #fff7ed
--risk-high-header-border: var(--palette-orange-200);   // #fed7aa
--risk-high-header-title: var(--palette-orange-800);    // #9a3412
--risk-high-header-sub: var(--palette-orange-600);      // #ea580c
--risk-high-header-btn: color-mix(in oklch, var(--palette-orange-500) 15%, transparent);

--risk-medium-header-bg: var(--palette-yellow-50);      // #fefce8
--risk-medium-header-border: var(--palette-yellow-200);  // #fef08a
--risk-medium-header-title: var(--palette-yellow-800);   // #713f12
--risk-medium-header-sub: var(--palette-yellow-700);    // #a16207
--risk-medium-header-btn: color-mix(in oklch, var(--palette-yellow-500) 15%, transparent);

--risk-low-header-bg: var(--palette-green-50);          // #f0fdf4
--risk-low-header-border: var(--palette-green-200);     // #bbf7d0
--risk-low-header-title: var(--palette-green-800);     // #14532d
--risk-low-header-sub: var(--palette-green-600);       // #16a34a
--risk-low-header-btn: color-mix(in oklch, var(--palette-green-500) 15%, transparent);

--risk-safe-header-bg: var(--palette-green-50);         // #f0fdf4
--risk-safe-header-border: var(--palette-green-200);   // #bbf7d0
--risk-safe-header-title: var(--palette-green-800);    // #14532d
--risk-safe-header-sub: var(--palette-green-600);      // #16a34a
--risk-safe-header-btn: color-mix(in oklch, var(--palette-green-500) 15%, transparent);

--risk-unknown-header-bg: var(--palette-gray-50);      // #f9fafb
--risk-unknown-header-border: var(--palette-gray-200);  // #e5e7eb
--risk-unknown-header-title: var(--palette-gray-600);  // #4b5563
--risk-unknown-header-sub: var(--palette-gray-500);    // #6b7280
--risk-unknown-header-btn: color-mix(in oklch, var(--palette-gray-400) 15%, transparent);
```

### 暗色模式（.dark-mode 内覆盖）

```scss
.dark-mode {
  --risk-critical-header-bg: var(--palette-red-900);       // #450a0a
  --risk-critical-header-border: var(--palette-red-800);   // #7f1d1d
  --risk-critical-header-title: var(--palette-red-200);   // #fecaca
  --risk-critical-header-sub: var(--palette-red-400);     // #f87171
  --risk-critical-header-btn: color-mix(in oklch, var(--palette-red-400) 20%, transparent);

  --risk-high-header-bg: var(--palette-orange-900);        // #431407
  --risk-high-header-border: var(--palette-orange-800);    // #9a3412
  --risk-high-header-title: var(--palette-orange-200);    // #fed7aa
  --risk-high-header-sub: var(--palette-orange-400);      // #fb923c
  --risk-high-header-btn: color-mix(in oklch, var(--palette-orange-400) 20%, transparent);

  --risk-medium-header-bg: var(--palette-yellow-900);      // #422006
  --risk-medium-header-border: var(--palette-yellow-800); // #713f12
  --risk-medium-header-title: var(--palette-yellow-200);  // #fef08a
  --risk-medium-header-sub: var(--palette-yellow-400);    // #facc15
  --risk-medium-header-btn: color-mix(in oklch, var(--palette-yellow-400) 20%, transparent);

  --risk-low-header-bg: var(--palette-green-950);          // #022c22
  --risk-low-header-border: var(--palette-green-800);     // #14532d
  --risk-low-header-title: var(--palette-green-200);      // #bbf7d0
  --risk-low-header-sub: var(--palette-green-400);        // #4ade80
  --risk-low-header-btn: color-mix(in oklch, var(--palette-green-400) 20%, transparent);

  --risk-safe-header-bg: var(--palette-green-950);         // #022c22
  --risk-safe-header-border: var(--palette-green-700);   // #15803d
  --risk-safe-header-title: var(--palette-green-200);    // #bbf7d0
  --risk-safe-header-sub: var(--palette-green-400);       // #4ade80
  --risk-safe-header-btn: color-mix(in oklch, var(--palette-green-400) 20%, transparent);

  --risk-unknown-header-bg: var(--palette-gray-800);      // #1f2937
  --risk-unknown-header-border: var(--palette-gray-600); // #4b5563
  --risk-unknown-header-title: var(--palette-gray-300);  // #d1d5db
  --risk-unknown-header-sub: var(--palette-gray-500);    // #6b7280
  --risk-unknown-header-btn: color-mix(in oklch, var(--palette-gray-400) 20%, transparent);
}
```

## 4. ThemeStore

```typescript
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
```

## 5. App.vue 改造

```vue
<template>
  <view :class="{ 'dark-mode': themeStore.isDark }">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue"
import { useThemeStore } from "./stores/theme"

const themeStore = useThemeStore()
onMounted(() => themeStore.init())
onUnmounted(() => themeStore.cleanup())
</script>
```

## 6. riskLevel.ts 改造

删除 `RiskLevelConfig` 接口和 `RISK_CONFIG` 对象中所有颜色字段（`headerBgLight` / `headerBgDark` / `headerBorderLight` / `headerBorderDark` / `headerTitleLight` / `headerTitleDark` / `headerSubLight` / `headerSubDark` / `headerBtnLight` / `headerBtnDark` / `badgeBg`）。

保留字段：
- `badge: string`
- `icon: string`
- `subtitleNoProduct: string`
- `needleLeft: string | null`

同时给 `RiskLevelConfig` 新增 `visualKey` 字段，供模板 class 绑定使用：

```typescript
export interface RiskLevelConfig {
  visualKey: VisualKey  // 新增
  badge: string
  icon: string
  subtitleNoProduct: string
  needleLeft: string | null
}
```

## 7. 页面改造

### ingredient-detail/index.vue

删除：
- `ref(false)` 的 `isDark`
- `onMounted`/`onUnmounted` 中的 theme 监听逻辑
- 整块 `pageStyle` computed（~25行）

保留：
- `riskConf` computed（只返回纯数据）
- 业务逻辑 computed（`summary` / `riskFactors` 等）

新增：
- `riskClass` computed：返回 `'risk-critical'` / `'risk-high'` 等 class 名
- `headerStyle` 简化为只包含非颜色相关的样式（如果有）

模板改动：
```vue
<!-- 改造前 -->
<view class="ingredient-detail-page" :style="pageStyle">
  <view class="ing-header" :style="headerStyle">

<!-- 改造后 -->
<view class="ingredient-detail-page">
  <view class="ing-header" :class="riskClass">
```

CSS 样式：
```scss
.ing-header {
  background: var(--risk-critical-header-bg);
  border-bottom: 1px solid var(--risk-critical-header-border);
}
```

> 注意：`--risk-critical-header-*` 中的 `critical` 为占位符，实际使用 `.risk-critical` class 时 CSS 变量会通过 class 选择器指向对应变量，因此需要为每个 risk class 定义对应的 CSS 变量集合。

风险等级 class 与 CSS 变量对应关系：
```scss
.risk-critical { --risk-header-bg: var(--risk-critical-header-bg); --risk-header-border: var(--risk-critical-header-border); /* ... */ }
.risk-high      { --risk-header-bg: var(--risk-high-header-bg); --risk-header-border: var(--risk-high-header-border); /* ... */ }
.risk-medium    { --risk-header-bg: var(--risk-medium-header-bg); --risk-header-border: var(--risk-medium-header-border); /* ... */ }
.risk-low       { --risk-header-bg: var(--risk-low-header-bg); --risk-header-border: var(--risk-low-header-border); /* ... */ }
.risk-safe      { --risk-header-bg: var(--risk-safe-header-bg); --risk-header-border: var(--risk-safe-header-border); /* ... */ }
.risk-unknown   { --risk-header-bg: var(--risk-unknown-header-bg); --risk-header-border: var(--risk-unknown-header-border); /* ... */ }
```

### index/index.vue / search/index.vue / profile/index.vue

删除：
- `ref(false)` 的 `isDark`
- `onMounted`/`onUnmounted` 中的 theme 监听逻辑

新增：
```typescript
import { useThemeStore } from "../../store/theme"
const themeStore = useThemeStore()
// 模板中 isDark.value → themeStore.isDark
// 模板中 statusBarHeight → themeStore.statusBarHeight
```

## 8. 迁移清单

| 文件 | 操作 |
|------|------|
| `src/stores/theme.ts` | 新增 |
| `src/App.vue` | 绑定 dark-mode class |
| `src/styles/design-system.scss` | 新增 risk-header-* semantic tokens |
| `src/utils/riskLevel.ts` | 删除颜色字段，新增 visualKey |
| `src/pages/ingredient-detail/index.vue` | 删除 pageStyle + local isDark，改用 riskClass + CSS 变量 |
| `src/pages/index/index.vue` | 删除 local isDark，改用 themeStore |
| `src/pages/search/index.vue` | 删除 local isDark，改用 themeStore |
| `src/pages/profile/index.vue` | 删除 local isDark，改用 themeStore |

## 9. 设计原则

1. **颜色走 CSS 变量，JS 只管数据** — 颜色变化靠切换 class，不靠 computed 拼接颜色字符串
2. **全局状态集中管理** — `isDark` 和 `statusBarHeight` 只读一次，全局共享
3. **设计体系优先** — 所有颜色必须来自 design-system palette，不允许手写 hex 值（除非 palette 确实没有）
4. **渐进迁移** — 4 个页面逐个改造，不要求一次性全部完成
