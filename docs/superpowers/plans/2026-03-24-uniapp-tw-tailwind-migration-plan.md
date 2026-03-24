# UniApp Tailwind 3 样式迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `web/apps/uniapp-tw/` 所有 SCSS 样式迁移为 Tailwind Utility Classes，采用 shadcn CSS 变量模式，`.dark` class 切换暗色，颜色通过 `var(--color-*)` 自动响应。

**Architecture:** 重构分为 4 个 Phase：
1. Phase 1 — 基础样式层（design-system.scss + tailwind.config.ts + main.ts + App.vue）
2. Phase 2 — 简单页面（index 首页、search 搜索）
3. Phase 3 — 复杂页面（product 产品、ingredient-detail 配料详情、scan 扫描、profile 个人）
4. Phase 4 — 公共组件（BottomBar、ProductHeader 等 15 个组件）

**Tech Stack:** Tailwind CSS 3, weapp-tailwindcss (rem2rpx), UniApp (Vue 3), SCSS, oklch 颜色格式

---

## 文件变更总览

| 文件 | 操作 |
|------|------|
| `src/styles/design-system.scss` | 重写 — `@layer base :root / .dark` 模式，所有 `--color-*` 变量 |
| `tailwind.config.ts` | 重写 — `darkMode: 'class'`、完整 `theme.extend.colors`、`borderRadius`、`boxShadow` |
| `src/main.ts` | 修改 — 添加 `import '@/styles/design-system.scss'` 全局导入 |
| `src/App.vue` | 修改 — 添加 `watchEffect` 监听 `themeStore.isDark`，在 `document.documentElement` 上 toggle `.dark` |
| 6 个页面 Vue 文件 | 修改 — SCSS style 块 → TW atomic class |
| 15 个组件 Vue 文件 | 修改 — 同上 |

---

## Phase 1: 基础样式层

### 任务 1: 重写 `design-system.scss`

**文件:** `src/styles/design-system.scss`

用 `@layer base { :root { } .dark { } }` 替代原有 `page {}` 选择器。所有颜色改用 `--color-*` 前缀（shadcn 规范）。保留 keyframes 和 `@media (prefers-reduced-motion)`。`.dark-mode` 块改为 `.dark`。

- [ ] **Step 1: 备份并重写 `design-system.scss`**

完整内容如下（覆盖整个文件）：

```scss
// ============================================================
// 2026 Design System — CSS Variables (shadcn Mode)
// UniApp + Vue 3 + Tailwind CSS 3
//
// 所有颜色通过 CSS 变量定义，.dark class 切换暗色。
// Tailwind config 通过 variable: 引用，无需 dark: 前缀。
// ============================================================

@layer base {
  :root {
    // ── shadcn 语义色 ───────────────────────────────
    --color-background:        oklch(97.5% 0.003 240);
    --color-foreground:        oklch(14.5% 0.016 265);
    --color-primary:           oklch(45% 0.18 330);         // #db2777
    --color-primary-foreground: oklch(98% 0.002 240);
    --color-secondary:        oklch(55% 0.02 265);
    --color-secondary-foreground: oklch(14.5% 0.016 265);
    --color-muted:            oklch(70% 0.015 265);
    --color-muted-foreground: oklch(50% 0.015 265);
    --color-accent:           oklch(55% 0.22 330);
    --color-accent-foreground: oklch(14.5% 0.016 265);
    --color-card:             oklch(100% 0 0);
    --color-card-foreground:  oklch(14.5% 0.016 265);
    --color-destructive:      oklch(50% 0.22 25);
    --color-destructive-foreground: oklch(98% 0.002 25);
    --color-border:           oklch(14.5% 0.016 265 / 6%);
    --color-input:            oklch(14.5% 0.016 265 / 10%);
    --color-ring:             oklch(45% 0.18 330);

    // ── 风险色 ───────────────────────────────────
    --color-risk-t4:          oklch(50% 0.22 25);
    --color-risk-t3:          oklch(55% 0.20 50);
    --color-risk-t2:          oklch(60% 0.18 85);
    --color-risk-t1:          oklch(65% 0.16 145);
    --color-risk-t0:          oklch(55% 0.15 145);
    --color-risk-unknown:     oklch(60% 0.01 265);

    // ── 圆角 ───────────────────────────────────
    --radius-sm:  0.75rem;   // 12px (24rpx)
    --radius-md:  1rem;      // 16px (32rpx)
    --radius-lg:  1.25rem;   // 20px (40rpx)
    --radius-xl:  1.5rem;    // 24px (48rpx)

    // ── 阴影 & 动效 ───────────────────────────────
    --shadow-sm:  0 2rpx 8rpx rgba(0, 0, 0, 0.05);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

    // ── 复杂 component token ───────────────────────
    --bottom-bar-bg:         oklch(100% 0 0 / 95%);
    --bottom-bar-border:     oklch(14.5% 0.016 265 / 6%);
    --header-scrolled-bg:    oklch(100% 0 0 / 90%);
    --ai-label-bg:           linear-gradient(135deg, #8b5cf6, #7c3aed);
    --nutrition-bg:           oklch(65% 0.16 145 / 4%);
    --nutrition-border:        oklch(65% 0.16 145 / 12%);
    --nutrition-glow:         oklch(65% 0.16 145 / 30%);
    --status-bar-bg:          #ffffff;
    --status-bar-text:         #111827;
    --banner-bg:             linear-gradient(145deg, #fefce8 0%, #fef9c3 50%, #fef08a 100%);
    --banner-label:          #713f12;
    --banner-badge-bg:       oklch(100% 0 0 / 85%);
    --banner-badge-border:    oklch(100% 0 0 / 20%);
    --banner-badge-shadow:    0 4px 24px rgba(0, 0, 0, 0.15);
    --accent-glow:            oklch(45% 0.18 330 / 40%);
  }

  .dark {
    --color-background:        oklch(7% 0.006 265);
    --color-foreground:        oklch(93% 0.005 265);
    --color-primary:           oklch(60% 0.22 330);
    --color-primary-foreground: oklch(7% 0.006 265);
    --color-secondary:        oklch(65% 0.015 265);
    --color-secondary-foreground: oklch(93% 0.005 265);
    --color-muted:            oklch(45% 0.012 265);
    --color-muted-foreground: oklch(65% 0.015 265);
    --color-accent:           oklch(70% 0.24 330);
    --color-accent-foreground: oklch(7% 0.006 265);
    --color-card:              oklch(12% 0.005 265);
    --color-card-foreground:   oklch(93% 0.005 265);
    --color-destructive:       oklch(65% 0.22 25);
    --color-destructive-foreground: oklch(7% 0.006 25);
    --color-border:            oklch(93% 0.005 265 / 8%);
    --color-input:             oklch(93% 0.005 265 / 10%);
    --color-ring:              oklch(60% 0.22 330);
    --color-risk-t4:           oklch(70% 0.22 25);
    --color-risk-t3:           oklch(70% 0.22 50);
    --color-risk-t2:           oklch(75% 0.18 85);
    --color-risk-t1:           oklch(75% 0.16 145);
    --color-risk-t0:           oklch(65% 0.16 145);
    --color-risk-unknown:      oklch(55% 0.01 265);
    --radius-sm:  0.75rem;
    --radius-md:  1rem;
    --radius-lg:  1.25rem;
    --radius-xl:  1.5rem;
    --shadow-sm:  0 2rpx 8rpx rgba(0, 0, 0, 0.15);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
    --bottom-bar-bg:          oklch(98% 0.003 265 / 95%);
    --bottom-bar-border:       oklch(100% 0 0 / 6%);
    --header-scrolled-bg:     oklch(93% 0.005 265 / 88%);
    --ai-label-bg:            linear-gradient(135deg, #8b5cf6, #7c3aed);
    --nutrition-bg:            oklch(75% 0.16 145 / 6%);
    --nutrition-border:         oklch(75% 0.16 145 / 10%);
    --nutrition-glow:          oklch(75% 0.16 145 / 20%);
    --status-bar-bg:          transparent;
    --status-bar-text:         #ffffff;
    --banner-bg:               linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
    --banner-label:           oklch(45% 0.012 265);
    --banner-badge-bg:        oklch(12% 0.005 265 / 90%);
    --banner-badge-border:      oklch(100% 0 0 / 10%);
    --banner-badge-shadow:      0 4px 24px rgba(0, 0, 0, 0.4);
    --accent-glow:             oklch(70% 0.24 330 / 30%);
  }
}

// ── Keyframes ───────────────────────────────────────────────
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16rpx); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes floatIn {
  from { opacity: 0; transform: scale(0.8); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes slideUpBadge {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-ring {
  0%   { transform: scale(1); opacity: 0.6; }
  70%  { transform: scale(1.15); opacity: 0; }
  100% { transform: scale(1.15); opacity: 0; }
}

// ── Reduced Motion ───────────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji, .nutrition-card, .health-card,
  .advice-card, .banner-badge {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

- [ ] **Step 2: 验证文件写入成功**

Run: `wc -l src/styles/design-system.scss`
Expected: 约 150 行

- [ ] **Step 3: Commit**

```bash
git add src/styles/design-system.scss
git commit -m "feat(uniapp-tw): rewrite design-system.scss with shadcn CSS variable mode

- Add @layer base with :root and .dark CSS variable definitions
- All colors use --color-* prefix (shadcn naming)
- oklch color format for all semantic colors
- Risk colors, radius, shadow, component tokens all migrated
- Keyframes (slideUp, floatIn, slideUpBadge, pulse-ring) preserved
- Reduced motion media query preserved

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 2: 重写 `tailwind.config.ts`

**文件:** `tailwind.config.ts`

- [ ] **Step 1: 重写 `tailwind.config.ts`**

```ts
import type { Config } from 'tailwindcss'
import { getIconCollections, iconsPlugin } from '@egoist/tailwindcss-icons'
import cssMacro from 'weapp-tailwindcss/css-macro'
import { isMp } from './platform'

export default <Config>{
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{html,js,ts,jsx,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        // shadcn 语义变量命名
        background: 'var(--color-background)',
        foreground: 'var(--color-foreground)',
        card: 'var(--color-card)',
        'card-foreground': 'var(--color-card-foreground)',
        primary: 'var(--color-primary)',
        'primary-foreground': 'var(--color-primary-foreground)',
        secondary: 'var(--color-secondary)',
        'secondary-foreground': 'var(--color-secondary-foreground)',
        muted: 'var(--color-muted)',
        'muted-foreground': 'var(--color-muted-foreground)',
        accent: 'var(--color-accent)',
        'accent-foreground': 'var(--color-accent-foreground)',
        destructive: 'var(--color-destructive)',
        'destructive-foreground': 'var(--color-destructive-foreground)',
        border: 'var(--color-border)',
        input: 'var(--color-input)',
        ring: 'var(--color-ring)',

        // 风险色
        'risk-t4': 'var(--color-risk-t4)',
        'risk-t3': 'var(--color-risk-t3)',
        'risk-t2': 'var(--color-risk-t2)',
        'risk-t1': 'var(--color-risk-t1)',
        'risk-t0': 'var(--color-risk-t0)',
        'risk-unknown': 'var(--color-risk-unknown)',

        // 复杂 component token
        'bottom-bar-bg': 'var(--bottom-bar-bg)',
        'bottom-bar-border': 'var(--bottom-bar-border)',
        'header-scrolled-bg': 'var(--header-scrolled-bg)',
        'ai-label-bg': 'var(--ai-label-bg)',
        'nutrition-bg': 'var(--nutrition-bg)',
        'nutrition-border': 'var(--nutrition-border)',
        'nutrition-glow': 'var(--nutrition-glow)',
        'status-bar-bg': 'var(--status-bar-bg)',
        'status-bar-text': 'var(--status-bar-text)',
        'banner-bg': 'var(--banner-bg)',
        'banner-label': 'var(--banner-label)',
        'banner-badge-bg': 'var(--banner-badge-bg)',
        'banner-badge-border': 'var(--banner-badge-border)',
        'banner-badge-shadow': 'var(--banner-badge-shadow)',
        'accent-glow': 'var(--accent-glow)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
      },
    },
  },
  plugins: [
    cssMacro({
      variantsMap: {
        'wx': 'MP-WEIXIN',
        '-wx': { value: 'MP-WEIXIN', negative: true },
      },
    }),
    iconsPlugin({
      collections: getIconCollections(['svg-spinners', 'mdi']),
    }),
  ],
  corePlugins: {
    preflight: !isMp,
    container: !isMp,
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add tailwind.config.ts
git commit -m "feat(uniapp-tw): rewrite tailwind.config.ts with shadcn variable mode

- Add darkMode: 'class'
- All colors reference CSS variables via variable: syntax
- borderRadius and boxShadow map to CSS token variables
- Keep existing cssMacro and iconsPlugin configuration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 3: 修改 `main.ts` 添加全局 SCSS 导入

**文件:** `src/main.ts`

- [ ] **Step 1: 修改 `main.ts`，在顶部添加 design-system.scss 导入**

```ts
import '@dcloudio/uni-app'
import * as Pinia from 'pinia'
import { createSSRApp } from 'vue'
import App from './App.vue'
import '@/styles/design-system.scss'

export function createApp() {
  const app = createSSRApp(App)
  app.use(Pinia.createPinia())
  return {
    app,
    Pinia,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/main.ts
git commit -m "feat(uniapp-tw): import design-system.scss globally in main.ts

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 4: 修改 `App.vue` 添加 `.dark` class 切换

**文件:** `src/App.vue`

- [ ] **Step 1: 修改 `App.vue`，添加 `watchEffect` 监听暗色切换**

```vue
<script setup lang="ts">
import { watchEffect } from 'vue'
import { useThemeStore } from './store/theme'

const themeStore = useThemeStore()

// 初始化主题 class 到 html 元素
themeStore.init()
watchEffect(() => {
  document.documentElement.classList.toggle('dark', themeStore.isDark)
})

onLaunch(() => {
  console.log('App Launch')
})
onShow(() => {
  console.log('App Show')
})
onHide(() => {
  console.log('App Hide')
})
</script>

<style lang="scss">
@use 'tailwindcss/base';
@use 'tailwindcss/components';
@use 'tailwindcss/utilities';

/*  #ifdef  H5  */
svg {
  display: initial;
}

/*  #endif  */

@layer components {
  .raw-btn {
    @apply after:border-none inline-flex items-center gap-2 rounded text-sm font-semibold transition-all;
  }

  .btn {
    @apply raw-btn bg-gradient-to-r from-[#9e58e9] to-blue-500 px-2 py-1 text-white;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/App.vue
git commit -m "feat(uniapp-tw): add watchEffect in App.vue to toggle .dark class

- themeStore.init() called at startup
- watchEffect toggles .dark class on documentElement based on isDark
- Remove: old dark-mode class binding (no longer needed)
- Keep: existing @use tailwindcss/* and @layer components (per spec decision)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 5: 全局清理 `.dark-mode` 选择器

**文件:** 多个 SCSS 文件

使用 `grep` 找到所有包含 `.dark-mode` 的文件，然后用 `Edit` 替换。

- [ ] **Step 1: 查找所有包含 `.dark-mode` 的文件**

Run: `grep -r "\.dark-mode" --include="*.vue" --include="*.scss" src/ -l`

预期输出文件列表（可能包括）：
```
src/pages/index/index.vue
src/pages/search/index.vue
src/pages/profile/index.vue
src/pages/product/index.vue
src/pages/ingredient-detail/index.vue
src/components/BottomBar.vue
src/components/ProductHeader.vue
```

- [ ] **Step 2: 替换所有文件中的 `.dark-mode` 为 `.dark`**

对每个文件执行替换（使用 `replace_all: true`）：

| 文件 | 替换 |
|------|------|
| `src/pages/index/index.vue` | `.dark-mode` → `.dark` |
| `src/pages/search/index.vue` | `.dark-mode` → `.dark` |
| `src/pages/profile/index.vue` | `.dark-mode` → `.dark` |
| `src/pages/product/index.vue` | `.dark-mode` → `.dark`；`.product-page:not(.dark-mode) &` → `.product-page:not(.dark) &` |
| `src/pages/ingredient-detail/index.vue` | `.dark-mode` → `.dark` |
| `src/components/BottomBar.vue` | `.product-page:not(.dark-mode) &` → `.product-page:not(.dark) &` |
| `src/components/ProductHeader.vue` | `.product-page:not(.dark-mode) &` → `.product-page:not(.dark) &` |

- [ ] **Step 3: 验证没有遗漏**

Run: `grep -r "\.dark-mode" --include="*.vue" --include="*.scss" src/`
Expected: 无输出

- [ ] **Step 4: Commit**

```bash
git add src/
git commit -m "refactor(uniapp-tw): replace all .dark-mode with .dark

- Replace .dark-mode class selector with .dark in all Vue/SCSS files
- Fix compound selectors like .product-page:not(.dark-mode) &
- No .dark-mode references should remain in src/

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: 简单页面

### 任务 6: 迁移 `pages/index/index.vue`

**文件:** `src/pages/index/index.vue`

**设计参考:** `web/ui/01-index.html`

- [ ] **Step 1: 读取当前文件，确认需要修改的内容**

读取文件，列出所有需要迁移的 SCSS 块和 `:class` 绑定。

- [ ] **Step 2: 移除 SCSS style 块，全部转为 TW class**

移除 `<style lang="scss" scoped>` 整块，将所有样式迁移到 template 的 class 属性中。

**迁移对照：**

| 原有 SCSS | TW class |
|-----------|----------|
| `height: 100vh; background: var(--bg-base)` | `h-screen bg-background` |
| `background: var(--bg-card)` | `bg-card` |
| `border-bottom: 1px solid var(--border-color)` | `border-b border-border` |
| `padding: var(--space-20) var(--space-12) var(--space-16)` | `px-12 pt-20 pb-16` |
| `display: flex; flex-direction: column; align-items: center` | `flex flex-col items-center` |
| `gap: var(--space-4)` | `gap-4` |
| `font-size: var(--text-6xl); line-height: 1` | `text-[3rem] leading-none` |
| `font-size: var(--text-3xl); font-weight: 700` | `text-3xl font-bold` |
| `color: var(--text-primary)` | `text-foreground` |
| `color: var(--text-muted)` | `text-muted-foreground` |
| `width: 280rpx; height: 280rpx` | `w-[140px] h-[140px]` |
| `background: linear-gradient(135deg, var(--palette-pink-400), var(--palette-pink-500))` | `bg-gradient-to-br from-primary/80 to-primary` |
| `border-radius: 50%` | `rounded-full` |
| `box-shadow: 0 16rpx 80rpx rgba(236, 72, 153, 0.4)` | `shadow-[0_16rpx_80rpx_rgba(236,72,153,0.4)]` |
| `border-radius: var(--space-7)` | `rounded-[14px]`（TW 无精确对应，用 arbitrary） |
| `padding: var(--space-7) var(--space-8)` | `p-7 gap-6` |
| `display: flex; align-items: center; gap: var(--space-6)` | `flex items-center gap-6` |
| `box-shadow: var(--shadow-sm)` | `shadow-sm` |
| `transition: transform 0.15s ease` | `transition-transform duration-150` |
| `&:active { transform: scale(0.98); }` | `active:scale-[0.98]` |

- [ ] **Step 3: 移除根元素 `:class="{ 'dark-mode': themeStore.isDark }"`**

移除 `:class="{ 'dark-mode': themeStore.isDark }"`（App.vue 统一管理 `.dark` class）。

- [ ] **Step 4: 移除 `<style lang="scss" scoped>` 和 `@import`**

- [ ] **Step 5: 验证暗色/亮色显示正确**

Build H5 或小程序，确认样式无遗漏。

- [ ] **Step 6: Commit**

```bash
git add src/pages/index/index.vue
git commit -m "feat(uniapp-tw): migrate pages/index/index.vue to Tailwind

- Remove <style lang="scss" scoped>, all styles converted to TW classes
- Remove :class dark-mode binding (now global via App.vue)
- All colors use CSS variable tokens (bg-card, text-foreground, etc.)
- Animated pulse-ring defined in design-system.scss keyframes

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 7: 迁移 `pages/search/index.vue`

**文件:** `src/pages/search/index.vue`

- [ ] **Step 1: 读取当前文件，分析所有 SCSS 块和动态 style 函数**

- [ ] **Step 2: 迁移 SCSS style 块到 TW class（与任务 6 相同方式）**

- [ ] **Step 3: 移除根元素 `:class="{ 'dark-mode': ... }"`**

- [ ] **Step 4: 重写所有动态 JS style 对象为 class 方案**

**关键函数处理：**

找到所有返回 inline style 对象的 JS 函数（如 `typeTagStyle`、`headerTextStyle` 等），改写为返回 class 字符串的函数。

例如：
```ts
// 旧（错误）
function typeTagStyle(isActive: boolean) {
  return {
    color: 'var(--text-primary)',
    background: 'var(--bg-card)',
  }
}

// 新（正确）
function getTagClass(isActive: boolean) {
  return isActive
    ? 'bg-accent text-accent-foreground rounded-full px-3 py-1 text-sm font-semibold'
    : 'bg-muted text-muted-foreground rounded-full px-3 py-1 text-sm font-medium'
}
```

对应的 template 变化：
```vue
<!-- 旧 -->
<view :style="typeTagStyle(isActive)">

<!-- 新 -->
<view :class="getTagClass(isActive)">
```

- [ ] **Step 5: 验证编译通过，暗色切换正常**

- [ ] **Step 6: Commit**

```bash
git add src/pages/search/index.vue
git commit -m "feat(uniapp-tw): migrate pages/search/index.vue to Tailwind

- Convert all SCSS to TW utility classes
- Remove dark-mode class binding (global via App.vue)
- Rewrite dynamic JS style objects to class-based approach
- All colors now use CSS variable tokens

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: 复杂页面

### 任务 8: 迁移 `pages/product/index.vue`

**文件:** `src/pages/product/index.vue`

**设计参考:** `web/ui/02-product-detail.html`

- [ ] **Step 1: 读取当前文件和设计稿 `02-product-detail.html`**

- [ ] **Step 2: 迁移 SCSS style 块**

逐区块迁移：banner、nutrition-card、risk-group、ingredient-card、health-card、advice-card、bottom-bar。

- [ ] **Step 3: 移除所有 `.dark-mode` 相关 SCSS 选择器（Phase 1 任务 5 应已处理）**

- [ ] **Step 4: 处理 JS style 对象（如有）**

- [ ] **Step 5: Commit**

```bash
git add src/pages/product/index.vue
git commit -m "feat(uniapp-tw): migrate pages/product/index.vue to Tailwind

- All SCSS blocks converted to TW utility classes
- Reference: 02-product-detail.html design
- Banner, nutrition card, risk groups, ingredient cards migrated

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### 任务 9: 迁移 `pages/ingredient-detail/index.vue`

**文件:** `src/pages/ingredient-detail/index.vue`

**设计参考:** `web/ui/03-ingredient-detail.html`

- [ ] **Step 1-5: 同任务 8，参照设计稿 `03-ingredient-detail.html`**

- [ ] **Step 6: Commit**

---

### 任务 10: 迁移 `pages/scan/index.vue`

**文件:** `src/pages/scan/index.vue`

- [ ] **Step 1-5: 同上处理**

- [ ] **Step 6: Commit**

---

### 任务 11: 迁移 `pages/profile/index.vue`

**文件:** `src/pages/profile/index.vue`

- [ ] **Step 1-5: 同上处理，注意 `.dark-mode .login-card` 等已改为 `.dark .login-card`**

- [ ] **Step 6: Commit**

---

## Phase 4: 公共组件

### 任务 12-26: 迁移各组件

按以下顺序迁移，**每个组件单独一个 commit**：

| 任务 | 文件 | 备注 |
|------|------|------|
| 12 | `src/components/BottomBar.vue` | 注意 `.product-page:not(.dark) &` 选择器 |
| 13 | `src/components/ProductHeader.vue` | 同上 |
| 14 | `src/components/IngredientSection.vue` | |
| 15 | `src/components/RiskBadge.vue` | |
| 16 | `src/components/RiskTag.vue` | |
| 17 | `src/components/InfoCard.vue` | |
| 18 | `src/components/InfoChip.vue` | |
| 19 | `src/components/ActionButton.vue` | 保留 `color-mix()` 用法（在 SCSS 中） |
| 20 | `src/components/AnalysisCard.vue` | |
| 21 | `src/components/ListItem.vue` | |
| 22 | `src/components/NutritionTable.vue` | |
| 23 | `src/components/SectionHeader.vue` | |
| 24 | `src/components/StateView.vue` | |
| 25 | `src/components/HorizontalScroller.vue` | |
| 26 | `src/components/IngredientList.vue` | |

**每个组件迁移标准步骤：**
- [ ] 读取组件文件
- [ ] 迁移 SCSS style 块到 TW class（或保留 color-mix/mixin 等复杂逻辑）
- [ ] 清理 `.dark-mode` 选择器
- [ ] 处理 JS style 对象
- [ ] 验证编译通过
- [ ] Commit

---

## 验收标准

- [ ] 所有页面在亮色/暗色下均正常显示，无样式遗漏
- [ ] 颜色通过 CSS 变量自动切换，**不使用** `dark:` TW 前缀
- [ ] `tailwind.config.ts` 中所有颜色通过 `var(--color-*)` 引用
- [ ] CSS 变量定义在 `@layer base` 的 `:root` 和 `.dark` 下（shadcn 模式）
- [ ] SCSS `<style>` 块仅在有 keyframes/mixin/color-mix 时保留，否则移除
- [ ] `.dark-mode` class 全面替换为 `.dark`，从所有模板和 SCSS 中清除
- [ ] 动态 JS style 对象中涉及颜色的全部改写为 class 方案
- [ ] `design-system.scss` 中所有原有 CSS 变量均已在 spec 中定义，无遗漏
