# UniApp Tailwind 3 样式迁移设计

> 本文档为最终确认版本，替代旧版 `2026-03-24-uniapp-tw-tailwind-migration-design.md`

## 背景

项目 `web/apps/uniapp-tw/` 使用 `weapp-vite` + UniApp + Tailwind CSS 3 + SCSS。当前样式大量使用 SCSS + CSS 变量（`design-system.scss`），暗色模式依赖页面级 `dark-mode` class，整体样式写法不统一，维护成本高。

**设计参考**：`web/ui/01-index.html`（首页）、`02-product-detail.html`（产品详情）、`03-ingredient-detail.html`（配料详情）

## 目标

1. 采用 **shadcn CSS 变量模式**——所有颜色定义为 CSS 变量，TW config 用 `variable:` 引用
2. `.dark` class 加在根元素时 CSS 变量值自动切换，Tailwind utility 无需任何暗色处理
3. 保留复杂 CSS tokens（color-mix 混合、复杂渐变、keyframes）
4. 动态 inline style JS 对象全部改写为 class 方案
5. 逐页面、逐组件完成迁移，不破坏现有功能

---

## shadcn CSS 变量模式

### 核心理念

同 shadcn/ui，保持 Tailwind 内置语义名（`background`、`foreground`、`border`、`ring` 等），CSS 变量在 `:root`（亮色）和 `.dark`（暗色）下定义不同值，Tailwind 通过 `variable:` 字段关联。

```
design-system.scss
  :root  → --color-background: oklch(...), --color-foreground: oklch(...), ...
  .dark  → --color-background: oklch(...), --color-foreground: oklch(...), ...

tailwind.config.ts
  variable: '--color-background'  →  bg-background = var(--background)

使用
  class="bg-background text-foreground"  ✅ 亮暗自动切换
  class="dark:bg-background"             ❌ 不使用
```

### `tailwind.config.ts` 配置

```ts
// tailwind.config.ts
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

        // 复杂 component token（直接引用 CSS 变量）
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

### CSS 变量定义（`design-system.scss`）

#### 基础色板（oklch）

```scss
@layer base {
  :root {
    // ── shadcn 语义色 ───────────────────────────────
    --color-background:       oklch(97.5% 0.003 240);
    --color-foreground:       oklch(14.5% 0.016 265);   // #111827
    --color-primary:          oklch(45% 0.18 330);        // #db2777
    --color-primary-foreground: oklch(98% 0.002 240);    // white
    --color-secondary:        oklch(55% 0.02 265);       // #4b5563
    --color-secondary-foreground: oklch(14.5% 0.016 265);
    --color-muted:            oklch(70% 0.015 265);       // #9ca3af
    --color-muted-foreground: oklch(50% 0.015 265);      // #6b7280
    --color-accent:           oklch(55% 0.22 330);        // #ec4899
    --color-accent-foreground: oklch(14.5% 0.016 265);
    --color-card:             oklch(100% 0 0);            // #ffffff
    --color-card-foreground:  oklch(14.5% 0.016 265);
    --color-destructive:      oklch(50% 0.22 25);         // #dc2626
    --color-destructive-foreground: oklch(98% 0.002 25);
    --color-border:           oklch(14.5% 0.016 265 / 6%);
    --color-input:            oklch(14.5% 0.016 265 / 10%);
    --color-ring:             oklch(45% 0.18 330);

    // ── 风险色 ───────────────────────────────────
    --color-risk-t4:          oklch(50% 0.22 25);          // #dc2626
    --color-risk-t3:          oklch(55% 0.20 50);          // #ea580c
    --color-risk-t2:          oklch(60% 0.18 85);          // #ca8a04
    --color-risk-t1:          oklch(65% 0.16 145);         // #22c55e
    --color-risk-t0:          oklch(55% 0.15 145);         // #16a34a
    --color-risk-unknown:     oklch(60% 0.01 265);        // #9ca3af

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
    --nutrition-bg:          oklch(65% 0.16 145 / 4%);
    --nutrition-border:       oklch(65% 0.16 145 / 12%);
    --nutrition-glow:        oklch(65% 0.16 145 / 30%);
    --status-bar-bg:         #ffffff;
    --status-bar-text:        #111827;
    --banner-bg:             linear-gradient(145deg, #fefce8 0%, #fef9c3 50%, #fef08a 100%);
    --banner-label:          #713f12;
    --banner-badge-bg:       oklch(100% 0 0 / 85%);
    --banner-badge-border:   oklch(100% 0 0 / 20%);
    --banner-badge-shadow:   0 4px 24px rgba(0, 0, 0, 0.15);
    --accent-glow:           oklch(45% 0.18 330 / 40%);
  }

  .dark {
    --color-background:       oklch(7% 0.006 265);        // #0f0f0f
    --color-foreground:       oklch(93% 0.005 265);       // #f3f4f6
    --color-primary:          oklch(60% 0.22 330);         // #ec4899
    --color-primary-foreground: oklch(7% 0.006 265);
    --color-secondary:        oklch(65% 0.015 265);       // #9ca3af
    --color-secondary-foreground: oklch(93% 0.005 265);
    --color-muted:            oklch(45% 0.012 265);        // #6b7280
    --color-muted-foreground: oklch(65% 0.015 265);
    --color-accent:           oklch(70% 0.24 330);         // #f472b6
    --color-accent-foreground: oklch(7% 0.006 265);
    --color-card:             oklch(12% 0.005 265);         // #1a1a1a
    --color-card-foreground:  oklch(93% 0.005 265);
    --color-destructive:      oklch(65% 0.22 25);          // #f87171
    --color-destructive-foreground: oklch(7% 0.006 25);
    --color-border:           oklch(93% 0.005 265 / 8%);
    --color-input:            oklch(93% 0.005 265 / 10%);
    --color-ring:             oklch(60% 0.22 330);
    --color-risk-t4:          oklch(70% 0.22 25);          // #f87171
    --color-risk-t3:          oklch(70% 0.22 50);          // #f97316
    --color-risk-t2:          oklch(75% 0.18 85);          // #eab308
    --color-risk-t1:          oklch(75% 0.16 145);         // #4ade80
    --color-risk-t0:          oklch(65% 0.16 145);         // #22c55e
    --color-risk-unknown:     oklch(55% 0.01 265);        // #6b7280
    --radius-sm:  0.75rem;
    --radius-md:  1rem;
    --radius-lg:  1.25rem;
    --radius-xl:  1.5rem;
    --shadow-sm:  0 2rpx 8rpx rgba(0, 0, 0, 0.15);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
    --bottom-bar-bg:         oklch(98% 0.003 265 / 95%);
    --bottom-bar-border:     oklch(100% 0 0 / 6%);
    --header-scrolled-bg:    oklch(93% 0.005 265 / 88%);
    --ai-label-bg:           linear-gradient(135deg, #8b5cf6, #7c3aed);
    --nutrition-bg:          oklch(75% 0.16 145 / 6%);
    --nutrition-border:       oklch(75% 0.16 145 / 10%);
    --nutrition-glow:        oklch(75% 0.16 145 / 20%);
    --status-bar-bg:         transparent;
    --status-bar-text:        #ffffff;
    --banner-bg:             linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
    --banner-label:          oklch(45% 0.012 265);
    --banner-badge-bg:       oklch(12% 0.005 265 / 90%);
    --banner-badge-border:   oklch(100% 0 0 / 10%);
    --banner-badge-shadow:   0 4px 24px rgba(0, 0, 0, 0.4);
    --accent-glow:          oklch(70% 0.24 330 / 30%);
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

---

## 迁移后的使用方式

```vue
<!-- 亮暗自动切换，无任何 dark: 前缀 -->
<view class="bg-background text-foreground">
  <view class="bg-card text-card-foreground border border-border rounded-lg p-6">
    <text class="text-primary">品牌色文字</text>
    <text class="text-muted-foreground">次要文字</text>
  </view>
</view>
```

复杂 token 直接引用：
```vue
<view class="bg-nutrition-bg border border-nutrition-border rounded-xl">
```

---

## 间距 & 字号迁移

`weapp-tailwindcss` 的 `rem2rpx` 已自动转换，直接使用 Tailwind 标准值。

| CSS var (设计值) | Tailwind | 备注 |
|----------|----------|------|
| `var(--space-1)` | `py-1 px-1` | 4px |
| `var(--space-2)` | `py-2 px-2` | 8px |
| `var(--space-3)` | `gap-3` | 12px |
| `var(--space-4)` | `gap-4` | 16px |
| `var(--space-6)` | `gap-6` | 24px |
| `var(--space-7)` | `gap-7` | 28px |
| `var(--space-8)` | `gap-8` | 32px |
| `var(--space-10)` | `gap-10` | 40px |
| `var(--space-12)` | `px-12` | 48px |
| `var(--space-14)` | `mt-14 mb-14` | 56px |
| `var(--space-16)` | `py-16` | 64px |
| `var(--space-20)` | `w-20 h-20` | 80px |
| `var(--space-24)` | `gap-24` | 96px |

字体大小：

| CSS var | Tailwind |
|----------|----------|
| `var(--text-sm)` | `text-sm` |
| `var(--text-base)` | `text-base` |
| `var(--text-md)` | `text-base` |
| `var(--text-lg)` | `text-lg` |
| `var(--text-xl)` | `text-xl` |
| `var(--text-2xl)` | `text-2xl` |
| `var(--text-3xl)` | `text-3xl` |
| `var(--text-5xl)` | `text-5xl` |
| `var(--text-6xl)` | `text-6xl` |

---

## 圆角 & 阴影迁移

| CSS var | Tailwind |
|---------|----------|
| `var(--radius-sm)` | `rounded-sm` |
| `var(--radius-md)` | `rounded-md` |
| `var(--radius-lg)` | `rounded-lg` |
| `var(--shadow-sm)` | `shadow-sm` |

---

## 页面迁移清单

### Phase 1: 基础样式层
- [ ] `design-system.scss` — 整理为 shadcn `@layer base` 模式，`:root` 和 `.dark` 下定义所有 `--color-*` 变量（oklch 格式）
- [ ] `tailwind.config.ts` — `darkMode: 'class'`、完整 `theme.extend.colors`、`borderRadius`、`boxShadow`
- [ ] `main.ts` — 添加 `import '@/styles/design-system.scss'` 全局导入，移除各页面重复 import
- [ ] Theme Store — `.dark` class 由 App.vue 统一管理（通过 `watchEffect`），store 只负责 `isDark` 状态
- [ ] 全局清理 `.dark-mode` 选择器 — `design-system.scss`、各页面 SCSS 块、各组件 SCSS 块中的 `.dark-mode` 全部替换为 `.dark`

### Phase 2: 简单页面
- [ ] `pages/index/index.vue` — SCSS → TW class，移除 `:class="{ 'dark-mode': ... }"`
- [ ] `pages/search/index.vue` — 同上，**动态 JS style 对象全部改写为 class 方案**

### Phase 3: 复杂页面
- [ ] `pages/product/index.vue` — 参照设计稿 `02-product-detail.html`
- [ ] `pages/ingredient-detail/index.vue` — 参照设计稿 `03-ingredient-detail.html`
- [ ] `pages/scan/index.vue`
- [ ] `pages/profile/index.vue`

### Phase 4: 公共组件
- [ ] `BottomBar.vue`
- [ ] `ProductHeader.vue`
- [ ] `IngredientSection.vue`
- [ ] `RiskBadge.vue`
- [ ] `RiskTag.vue`
- [ ] `InfoCard.vue`
- [ ] `InfoChip.vue`
- [ ] `ActionButton.vue`
- [ ] `AnalysisCard.vue`
- [ ] `ListItem.vue`
- [ ] `NutritionTable.vue`
- [ ] `SectionHeader.vue`
- [ ] `StateView.vue`
- [ ] `HorizontalScroller.vue`
- [ ] `IngredientList.vue`

---

## 组件迁移对照（示例）

### 迁移前

```vue
<style lang="scss" scoped>
.scan-item {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--space-7);
  padding: var(--space-7) var(--space-8);
  display: flex;
  align-items: center;
  gap: var(--space-6);
  box-shadow: var(--shadow-sm);
  transition: transform 0.15s ease;
  &:active { transform: scale(0.98); }
}
</style>
```

### 迁移后

```vue
<!-- 直接在 template class 中 -->
<view class="flex items-center gap-6 rounded-md border bg-card p-7 shadow-sm transition-transform active:scale-[0.98] border-border" />
```

- `bg-card` → `var(--color-card)` → 亮 `#ffffff` / 暗 `#1a1a1a`
- `border-border` → `var(--color-border)` → 亮 `oklch(...)` / 暗 `oklch(...)`
- `rounded-md` → `var(--radius-md)` = 16px ≈ 原 24rpx
- 无 `dark:` 前缀，无 SCSS

---

## 关键技术点

### 1. `.dark-mode` 散落清理

现有项目使用 `.dark-mode` class 的位置（全部改为 `.dark`）：

| 文件 | 位置 |
|------|------|
| `design-system.scss` | `.dark-mode {}` 块 |
| `pages/index/index.vue` | 根元素 `:class` + SCSS `.dark-mode .scan-count` |
| `pages/search/index.vue` | 根元素 `:class` |
| `pages/profile/index.vue` | 根元素 `:class` + SCSS `.dark-mode .login-card` |
| `pages/product/index.vue` | SCSS `.dark-mode &::before`、`.product-page:not(.dark-mode) &` |
| `pages/ingredient-detail/index.vue` | SCSS `.dark-mode &` |
| `components/BottomBar.vue` | SCSS `.product-page:not(.dark-mode) &` |
| `components/ProductHeader.vue` | SCSS `.product-page:not(.dark-mode) &` |

### 2. 动态 JS style 对象改写

**错误做法（不保留）：**
```ts
function typeTagStyle(isActive: boolean) {
  return {
    color: 'var(--text-primary)',
    background: 'var(--bg-card)',
  }
}
```

**正确做法（class 方案）：**
```vue
<text :class="[tagBaseClass, isActive && 'font-semibold']">
```

```ts
function getTagClass(isActive: boolean) {
  return isActive
    ? 'bg-accent text-accent-foreground rounded-full px-3 py-1 text-sm font-semibold'
    : 'bg-muted text-muted-foreground rounded-full px-3 py-1 text-sm font-medium'
}
```

JS 只控制业务状态（激活/非激活、展开/收起），颜色全部由 CSS 变量通过 Tailwind class 决定，`dark` 切换时自动响应。

### 3. oklch 颜色格式

shadcn 使用 oklch，比传统 hex/rgb 更适合现代显示。

设计稿色值（hex）转换参考：
- `#111827` → `oklch(14.5% 0.016 265)`
- `#f3f4f6` → `oklch(93% 0.005 265)`
- `#db2777` → `oklch(45% 0.18 330)`
- `#ec4899` → `oklch(55% 0.22 330)`

> 可使用 Chrome DevTools 的 color picker 直接复制 oklch 值。

### 4. 复杂 token 处理

color-mix、gradient 等无法用 oklch 表示的，仍保留 CSS 变量：
```scss
--nutrition-bg: oklch(65% 0.16 145 / 4%);
--banner-bg: linear-gradient(...);
```
TW config 引用：
```ts
'nutrition-bg': 'var(--nutrition-bg)',
```

### 5. 动画 Keyframes

以下 keyframes 保留在 `design-system.scss` 中（不在 TW config 中定义）：

```scss
@keyframes slideUp { ... }
@keyframes floatIn { ... }
@keyframes slideUpBadge { ... }

@media (prefers-reduced-motion: reduce) {
  .banner-emoji, .nutrition-card, .health-card,
  .advice-card, .banner-badge {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

### 6. App.vue 保持不变

现有 `@use 'tailwindcss/*'` 和 `@layer components { .raw-btn .btn }` **暂不处理**，不影响本次迁移。

---

## 验收标准

1. 所有页面在亮色/暗色下均正常显示，无样式遗漏
2. 颜色通过 CSS 变量自动切换，**不使用** `dark:` TW 前缀
3. `tailwind.config.ts` 中所有颜色通过 `var(--color-*)` 引用
4. CSS 变量定义在 `@layer base` 的 `:root` 和 `.dark` 下（shadcn 模式）
5. SCSS `<style>` 块仅在有 keyframes/mixin/color-mix 时保留，否则移除
6. `.dark-mode` class 全面替换为 `.dark`，从所有模板和 SCSS 中清除
7. 动态 JS style 对象中涉及颜色的全部改写为 class 方案
8. `design-system.scss` 中所有原有 CSS 变量均已在 spec 中定义，无遗漏
