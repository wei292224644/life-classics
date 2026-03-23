# UniApp + UnoCSS 全端迁移设计

**日期**: 2026-03-23
**状态**: 已批准
**目标**: 将 `@acme/uniapp` 项目从 SCSS + CSS 变量迁移到 UnoCSS 原子化样式，保持 H5 + 微信小程序 + HarmonyOS 等全端支持。

---

## 1. 背景与目标

**现状**:
- `@acme/uniapp` 使用 Vue 3 + SCSS
- `design-system.scss` 定义了完整的 CSS 变量系统（spacing、colors、typography）
- 组件中大量使用 `var(--space-*)`、`var(--text-*)` 等 CSS 变量
- 未配置任何原子化 CSS 框架

**目标**:
- 引入 UnoCSS，享受 Tailwind CSS 风格的原子化开发体验
- 全端兼容：H5 + 微信小程序 + HarmonyOS + 其他小程序
- 深色模式：基于系统偏好 `prefers-color-scheme`
- rpx 单位：PostCSS 构建时转换（设计稿 750）

---

## 2. 架构设计

```
web/apps/uniapp/
├── src/
│   ├── styles/
│   │   ├── design-system.scss    ← 保留：仅语义化颜色变量（text-*, bg-*, border-*）
│   │   ├── uno.config.ts         ← 新增：UnoCSS 配置
│   │   └── shortcuts/           ← 新增：组件级 shortcuts
│   ├── pages/...                 ← 逐步迁移：SCSS → 原子类
│   └── components/...            ← 逐步迁移：SCSS → 原子类
├── vite.config.ts                ← 修改：集成 UnoCSS + PostCSS rpx 转换
└── package.json                  ← 修改：添加 UnoCSS 依赖
```

**核心原则**:
- `design-system.scss` 中的 **palette（调色板）和 semantic tokens（语义色）保留为 CSS 变量**，因为这些是品牌核心
- **spacing、radius、shadow 等 layout token 在 UnoCSS 中直接用原子类**（`gap-2`、`rounded-xl`、`shadow-md`），不再引用 CSS 变量
- 所有 SCSS mixin、变量运算逐步移除

---

## 3. UnoCSS 配置（`uno.config.ts`）

```typescript
import { defineConfig, presetUno, presetIcons, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),           // Tailwind CSS 兼容原子类
    presetAttributify(),   // 支持 <view flex /> 写法
    presetIcons({
      scale: 1.2,
      extraProperties: { 'display': 'inline-block', 'vertical-align': 'middle' }
    })
  ],

  theme: {
    colors: {
      // 接入 design-system.scss 的 palette
      gray: {
        50: 'var(--palette-gray-50)',
        100: 'var(--palette-gray-100)',
        200: 'var(--palette-gray-200)',
        300: 'var(--palette-gray-300)',
        400: 'var(--palette-gray-400)',
        500: 'var(--palette-gray-500)',
        600: 'var(--palette-gray-600)',
        700: 'var(--palette-gray-700)',
        800: 'var(--palette-gray-800)',
        900: 'var(--palette-gray-900)',
      },
      red: {
        50: 'var(--palette-red-50)',
        100: 'var(--palette-red-100)',
        200: 'var(--palette-red-200)',
        300: 'var(--palette-red-300)',
        400: 'var(--palette-red-400)',
        500: 'var(--palette-red-500)',
        600: 'var(--palette-red-600)',
        700: 'var(--palette-red-700)',
        800: 'var(--palette-red-800)',
        900: 'var(--palette-red-900)',
      },
      orange: { /* 同上 */ },
      yellow: { /* 同上 */ },
      green: { /* 同上 */ },
      purple: { /* 同上 */ },
      blue: { /* 同上 */ },
      pink: { /* 同上 */ },
      accent: { DEFAULT: 'var(--accent)', light: 'var(--accent-light)' },
      risk: {
        t4: 'var(--risk-t4)', t3: 'var(--risk-t3)',
        t2: 'var(--risk-t2)', t1: 'var(--risk-t1)',
        t0: 'var(--risk-t0)', unknown: 'var(--risk-unknown)',
      }
    },
    borderRadius: {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
      lg: 'var(--radius-lg)',
      xl: 'var(--radius-xl)',
      full: 'var(--radius-full)',
    }
  },

  safelist: [
    // 小程序动态 class 需要显式声明
    'risk-critical', 'risk-high', 'risk-medium', 'risk-low', 'risk-safe', 'risk-unknown',
    'icon-bg-blue', 'icon-bg-red', 'icon-bg-purple', 'icon-bg-green', 'icon-bg-orange',
    'chip-func', 'chip-warn', 'chip-neu',
    'list-item-icon', 'icon-x', 'icon-check-green', 'icon-check-yellow',
    'risk-high', 'risk-med'
  ],

  shortcuts: {
    // 组件级快捷类
    'card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-sm)]',
    'section-title': 'text-[var(--text-primary)] font-semibold text-lg',
    'icon-wrap': 'w-[var(--icon-xl)] h-[var(--icon-xl)] rounded-[var(--space-3)] flex items-center justify-center',
  }
})
```

---

## 4. 深色模式方案

**使用 `prefers-color-scheme` 媒体查询 + JS 降级：**

```typescript
// uno.config.ts
dark: 'html:not(.light-mode)'
```

**页面根节点设置类：**

```typescript
// App.vue 或页面入口
import { ref, onMounted } from 'vue'

const isDark = ref(false)

onMounted(() => {
  // 小程序
  const systemInfo = uni.getSystemInfoSync()
  isDark.value = systemInfo.theme === 'dark'

  // H5
  if (typeof window !== 'undefined') {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    isDark.value = mq.matches
    mq.addEventListener('change', (e) => { isDark.value = e.matches })
  }
})
```

```vue
<template>
  <view :class="isDark ? 'dark' : 'light'">
    <!-- 页面内容 -->
  </view>
</template>
```

**CSS 变量.dark 覆盖：**

```scss
// design-system.scss
html.dark {
  --text-primary: var(--palette-gray-100);
  --text-secondary: var(--palette-gray-400);
  --bg-base: #0f0f0f;
  --bg-card: #1a1a1a;
  // ... 其他语义色
}
```

---

## 5. Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  plugins: [
    UnoCSS(),
    uni(),
  ],
  css: {
    postcss: {
      plugins: [
        // postcss-rpx-transform 或 autoprefixer + postcss-rpx-transform
        // viewportWidth: 750 匹配设计稿
      ]
    }
  }
})
```

**rpx 转换**：通过 `postcss-rpx-transform` 插件实现，UnoCSS 写 px 值（如 `p-4` = 16px），构建时自动转为 `32rpx`。

---

## 6. 迁移策略

### Phase 1 — 基础设施

1. 安装依赖：
   ```
   pnpm add -w unocss @unocss/preset-uno @unocss/preset-icons @unocss/preset-attributify postcss-rpx-transform
   ```

2. 创建 `uno.config.ts`

3. 改造 `vite.config.ts`

4. 保留 `design-system.scss`，删除已废弃的 spacing/text/size 变量

### Phase 2 — 逐组件迁移

每页/每组件单独迁移：

- **`<style lang="scss">`** 中的 `display`/`flex`/`gap`/`padding`/`margin` → UnoCSS 原子类
- **保留** `color`、`background`、`border` 中对 CSS 变量的引用（`var(--accent)` 等）
- **动画关键帧**保留在 SCSS 中（UnoCSS `@apply` 在小程序有限制）
- **BEM 类名结构**：工具类直接用原子类替代 SCSS 变量引用

迁移示例：

```vue
<!-- Before -->
<view class="scan-item" style="display: flex; align-items: center; gap: var(--space-6);">
  <style lang="scss">
  .scan-item {
    display: flex;
    align-items: center;
    gap: var(--space-6);
    padding: var(--space-7) var(--space-8);
  }
  </style>

<!-- After -->
<view class="flex items-center gap-6 px-8 py-7 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl shadow-[var(--shadow-sm)]">
```

### Phase 3 — 清理

- 删除不再使用的 SCSS 变量和 mixin
- `design-system.scss` 仅保留语义化 token（颜色）
- 全局搜索 `var(--space-` / `var(--text-` 等，确保无遗漏

---

## 7. 关键风险与应对

| 风险 | 应对 |
|------|------|
| 小程序动态 class 不生成 | `safelist` 显式声明 |
| 小程序不支持 `@apply` | 动画、复杂选择器仍用 SCSS |
| UniApp 组件样式隔离（`scoped`） | UnoCSS 的 shortcuts 生成静态类，scoped 不影响 |
| rpx 转换精度 | viewportWidth: 750 匹配设计稿，UnoCSS 写 px 值 |
| `color-mix()` 小程序兼容性 | 已在 design-system.scss 中验证支持；必要时降级为纯色 |

---

## 8. 依赖清单

```json
{
  "unocss": "^0.x",
  "@unocss/preset-uno": "^0.x",
  "@unocss/preset-icons": "^0.x",
  "@unocss/preset-attributify": "^0.x",
  "postcss-rpx-transform": "^0.x"
}
```
