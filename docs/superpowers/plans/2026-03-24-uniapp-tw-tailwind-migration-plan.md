# UniApp Tailwind 3 样式迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `web/apps/uniapp-tw/` 所有 SCSS 样式迁移为 Tailwind Utility Classes，采用 shadcn CSS 变量模式，`.dark` class 切换暗色，颜色通过 `var(--color-*)` 自动响应。

**Architecture:** 重构分为 4 个 Phase：
1. Phase 1 — 基础样式层（design-system.scss + tailwind.config.ts + App.vue）
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
| `src/App.vue` | 重写 — 移除 SCSS、`dark-mode` class 绑定，添加 `.dark` 初始化逻辑 |
| `src/store/theme.ts` | 修改 — `init()` 中添加 `document.documentElement.classList.toggle('dark', isDark)` |
| 6 个页面 Vue 文件 | 修改 — SCSS style 块 → TW atomic class |
| 15 个组件 Vue 文件 | 修改 — 同上 |

---

## Phase 1: 基础样式层

### 任务 1: 重写 `design-system.scss`

**文件:** `src/styles/design-system.scss`

**操作:**
- [ ] 用 `@layer base { :root { ... } .dark { ... } }` 替代原有 `page {}` 选择器
- [ ] 所有语义变量改用 `--color-*` 前缀（shadcn 规范）
- [ ] 保留 keyframes 和 `@media (prefers-reduced-motion)`（非原子化，需保留）
- [ ] 亮色 `.dark-mode` 块改为 `.dark`
- [ ] 添加 `accent-glow` token（spec 有，但现有文件缺）

```scss
// src/styles/design-system.scss
@layer base {
  :root {
    // ── shadcn 语义色 ───────────────────────────────
    --color-background:       oklch(97.5% 0.003 240);
    --color-foreground:       oklch(14.5% 0.016 265);
    --color-primary:          oklch(45% 0.18 330);
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
    --radius-sm:  0.75rem;   // 12px
    --radius-md:  1rem;      // 16px
    --radius-lg:  1.25rem;   // 20px
    --radius-xl:  1.5rem;    // 24px

    // ── 阴影 & 动效 ───────────────────────────────
    --shadow-sm:  0 2rpx 8rpx rgba(0, 0, 0, 0.05);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

    // ── 复杂 component token ───────────────────────
    --bottom-bar-bg:         oklch(100% 0 0 / 95%);
    --bottom-bar-border:     oklch(14.5% 0.016 265 / 6%);
    --header-scrolled-bg:    oklch(100% 0 0 / 90%);
    --ai-label-bg:           linear-gradient(135deg, #8b5cf6, #7c3aed);
    --nutrition-bg:          oklch(65% 0.16 145 / 4%);
    --nutrition-border:      oklch(65% 0.16 145 / 12%);
    --nutrition-glow:        oklch(65% 0.16 145 / 30%);
    --status-bar-bg:         #ffffff;
    --status-bar-text:       #111827;
    --banner-bg:             linear-gradient(145deg, #fefce8 0%, #fef9c3 50%, #fef08a 100%);
    --banner-label:          #713f12;
    --banner-badge-bg:       oklch(100% 0 0 / 85%);
    --banner-badge-border:   oklch(100% 0 0 / 20%);
    --banner-badge-shadow:   0 4px 24px rgba(0, 0, 0, 0.15);
    --accent-glow:           oklch(45% 0.18 330 / 40%);
  }

  .dark {
    --color-background:       oklch(7% 0.006 265);
    --color-foreground:       oklch(93% 0.005 265);
    --color-primary:          oklch(60% 0.22 330);
    --color-primary-foreground: oklch(7% 0.006 265);
    --color-secondary:        oklch(65% 0.015 265);
    --color-secondary-foreground: oklch(93% 0.005 265);
    --color-muted:            oklch(45% 0.012 265);
    --color-muted-foreground: oklch(65% 0.015 265);
    --color-accent:           oklch(70% 0.24 330);
    --color-accent-foreground: oklch(7% 0.006 265);
    --color-card:             oklch(12% 0.005 265);
    --color-card-foreground:  oklch(93% 0.005 265);
    --color-destructive:      oklch(65% 0.22 25);
    --color-destructive-foreground: oklch(7% 0.006 25);
    --color-border:           oklch(93% 0.005 265 / 8%);
    --color-input:            oklch(93% 0.005 265 / 10%);
    --color-ring:             oklch(60% 0.22 330);
    --color-risk-t4:          oklch(70% 0.22 25);
    --color-risk-t3:          oklch(70% 0.22 50);
    --color-risk-t2:          oklch(75% 0.18 85);
    --color-risk-t1:          oklch(75% 0.16 145);
    --color-risk-t0:          oklch(65% 0.16 145);
    --color-risk-unknown:     oklch(55% 0.01 265);
    // 圆角（不变）
    --radius-sm:  0.75rem;
    --radius-md:  1rem;
    --radius-lg:  1.25rem;
    --radius-xl:  1.5rem;
    // 阴影 & 动效
    --shadow-sm:  0 2rpx 8rpx rgba(0, 0, 0, 0.15);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
    // 复杂 token
    --bottom-bar-bg:         oklch(98% 0.003 265 / 95%);
    --bottom-bar-border:     oklch(100% 0 0 / 6%);
    --header-scrolled-bg:    oklch(93% 0.005 265 / 88%);
    --ai-label-bg:           linear-gradient(135deg, #8b5cf6, #7c3aed);
    --nutrition-bg:          oklch(75% 0.16 145 / 6%);
    --nutrition-border:       oklch(75% 0.16 145 / 10%);
    --nutrition-glow:        oklch(75% 0.16 145 / 20%);
    --status-bar-bg:         transparent;
    --status-bar-text:       #ffffff;
    --banner-bg:             linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
    --banner-label:          oklch(45% 0.012 265);
    --banner-badge-bg:       oklch(12% 0.005 265 / 90%);
    --banner-badge-border:   oklch(100% 0 0 / 10%);
    --banner-badge-shadow:   0 4px 24px rgba(0, 0, 0, 0.4);
    --accent-glow:          oklch(70% 0.24 330 / 30%);
  }
}

// ── Keyframes（保留在 SCSS 中）──────────────────────────
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

// ── Reduced Motion ──────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji, .nutrition-card, .health-card,
  .advice-card, .banner-badge {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

### 任务 2: 重写 `tailwind.config.ts`

**文件:** `tailwind.config.ts`

**操作:**
- [ ] 添加 `darkMode: 'class'`
- [ ] 取消注释 `theme.extend`，添加所有 shadcn 语义色（`variable:` 引用）
- [ ] 添加 `borderRadius` 映射到 `--radius-*`
- [ ] 添加 `boxShadow` 映射到 `--shadow-sm`
- [ ] 保留 `cssMacro` 和 `iconsPlugin`

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
        'risk-t4': 'var(--color-risk-t4)',
        'risk-t3': 'var(--color-risk-t3)',
        'risk-t2': 'var(--color-risk-t2)',
        'risk-t1': 'var(--color-risk-t1)',
        'risk-t0': 'var(--color-risk-t0)',
        'risk-unknown': 'var(--color-risk-unknown)',
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

### 任务 3: 重写 `App.vue`

**文件:** `src/App.vue`

**操作:**
- [ ] 移除 `<style lang="scss">` 块（保留 SVG H5 hack）
- [ ] 移除 `dark-mode` class 绑定
- [ ] 添加 `watchEffect` 监听 `themeStore.isDark`，在 `document.documentElement` 上 toggle `.dark`
- [ ] 导入 `@/styles/design-system.scss`（或确保全局注入）

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
/* H5 SVG display fix */
svg {
  display: initial;
}
</style>
```

### 任务 4: 修改 Theme Store

**文件:** `src/store/theme.ts`

**操作:**
- [ ] 移除 `cleanup()` 中的 `offThemeChange`（可选，但保留更完整）
- [ ] 无需添加 class 操作到 store——已在 App.vue 中通过 `watchEffect` 统一处理

> **注意：** App.vue 中已通过 `watchEffect` 处理 `.dark` class，store 保持简单，只负责 `isDark` 状态。

### 任务 5: 确认 SCSS 全局注入

**检查:** `src/main.ts` 是否已导入 `design-system.scss`

- [ ] 若未导入，添加到 `src/main.ts`:
```ts
import '@/styles/design-system.scss'
```

---

## Phase 2: 简单页面

### 任务 6: 迁移 `pages/index/index.vue`

**文件:** `src/pages/index/index.vue`

**操作:**
- [ ] 移除 `<style lang="scss" scoped>` 块
- [ ] 将所有 SCSS 规则转为 TW atomic class
- [ ] 移除 `:class="{ 'dark-mode': themeStore.isDark }"`（由 App.vue 全局处理）
- [ ] 引用设计稿值：`scan-cta` 140×140px → `w-[140px] h-[140px]`、`scan-item` radius 14px → `rounded-[14px]`

**关键转换对照:**

| 原有 SCSS | TW class |
|-----------|----------|
| `class="index-page"` | `class="index-page"` (保留) |
| `class="hero"` | `class="bg-card pb-12 px-12 pt-20 flex flex-col items-center border-b border-border"` |
| `class="logo-emoji"` | `class="text-[3rem] leading-none"` |
| `class="logo-title"` | `class="text-[1.875rem] font-bold text-foreground tracking-tight"` |
| `class="scan-cta"` | `class="w-[140px] h-[140px] bg-gradient-to-br from-primary/80 to-primary rounded-full shadow-lg ..."` |
| `class="scan-item"` | `class="flex items-center gap-6 bg-card border border-border rounded-[14px] p-7 shadow-sm ..."` |

### 任务 7: 迁移 `pages/search/index.vue`

**文件:** `src/pages/search/index.vue`

**操作:**
- [ ] 同上，移除 SCSS style 块
- [ ] `typeTagStyle()` 函数中的 `var(--chip-warn-bg)` 等引用需替换为 `bg-*` token
  - 但 `typeTagStyle` 是 JS 函数返回 inline style 对象，保留（因为是动态颜色计算）
  - 静态样式全部迁移到 class

---

## Phase 3: 复杂页面

### 任务 8: 迁移 `pages/product/index.vue`

**文件:** `src/pages/product/index.vue`

**操作:**
- [ ] 移除 SCSS style 块
- [ ] 逐个 section 迁移（banner、nutrition-card、ingredient-card 等）
- [ ] 参照设计稿 `product-detail-v14.html` 逐区块转换

### 任务 9: 迁移 `pages/ingredient-detail/index.vue`

**文件:** `src/pages/ingredient-detail/index.vue`

### 任务 10: 迁移 `pages/scan/index.vue`

**文件:** `src/pages/scan/index.vue`

### 任务 11: 迁移 `pages/profile/index.vue`

**文件:** `src/pages/profile/index.vue`

---

## Phase 4: 公共组件

### 任务 12: 迁移 BottomBar

**文件:** `src/components/BottomBar.vue`

### 任务 13: 迁移 ProductHeader

**文件:** `src/components/ProductHeader.vue`

### 任务 14: 迁移 IngredientSection

**文件:** `src/components/IngredientSection.vue`

### 任务 15: 迁移 RiskBadge

**文件:** `src/components/RiskBadge.vue`

### 任务 16: 迁移 RiskTag

**文件:** `src/components/RiskTag.vue`

### 任务 17: 迁移 InfoCard

**文件:** `src/components/InfoCard.vue`

### 任务 18: 迁移 InfoChip

**文件:** `src/components/InfoChip.vue`

### 任务 19: 迁移 ActionButton

**文件:** `src/components/ActionButton.vue`

### 任务 20: 迁移 AnalysisCard

**文件:** `src/components/AnalysisCard.vue`

### 任务 21: 迁移 ListItem

**文件:** `src/components/ListItem.vue`

### 任务 22: 迁移 NutritionTable

**文件:** `src/components/NutritionTable.vue`

### 任务 23: 迁移 SectionHeader

**文件:** `src/components/SectionHeader.vue`

### 任务 24: 迁移 StateView

**文件:** `src/components/StateView.vue`

### 任务 25: 迁移 HorizontalScroller

**文件:** `src/components/HorizontalScroller.vue`

### 任务 26: 迁移 IngredientList

**文件:** `src/components/IngredientList.vue`

---

## 验收标准

- [ ] 所有页面在亮色/暗色下均正常显示，无样式遗漏
- [ ] 颜色通过 CSS 变量自动切换，**不使用** `dark:` TW 前缀
- [ ] `tailwind.config.ts` 中所有颜色通过 `var(--color-*)` 引用
- [ ] CSS 变量定义在 `@layer base` 的 `:root` 和 `.dark` 下
- [ ] SCSS `<style>` 块仅在有 keyframes/mixin 时保留，否则移除
- [ ] `.dark-mode` class 全面替换为 `.dark`，从所有模板中清除
- [ ] `design-system.scss` 中所有原有 CSS 变量均已在 spec 中定义
