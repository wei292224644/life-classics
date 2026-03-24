# UniApp Tailwind 3 样式迁移设计

## 背景

项目 `web/apps/uniapp-tw/` 从头重建，使用 `weapp-vite` + UniApp + Tailwind CSS 3。当前样式大量使用 SCSS + CSS 变量（`design-system.scss`），暗色模式依赖页面级 `dark-mode` class。

## 目标

1. 将所有 SCSS 样式转换为 Tailwind Utility Classes
2. 采用 **shadcn CSS 变量模式**——所有颜色在 CSS 中定义为 CSS 变量，TW config 用 `variable:` 引用
3. `.dark` class 加在根元素时 CSS 变量值自动切换，Tailwind utility 无需任何暗色处理
4. 保留复杂 CSS tokens（color-mix 混合、复杂渐变、keyframes）
5. 逐页面、逐组件完成迁移，不破坏现有功能

---

## shadcn CSS 变量模式

### 核心理念

同 shadcn/ui，保持 Tailwind 内置语义名（`background`、`foreground`、`border`、`ring` 等），CSS 变量在 `:root`（亮色）和 `.dark`（暗色）下定义不同值，Tailwind 通过 `variable:` 字段关联。

```
globals.css / design-system.scss
  :root  → --background: oklch(...), --foreground: oklch(...), ...
  .dark  → --background: oklch(...), --foreground: oklch(...), ...

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

export default <Config>{
  darkMode: 'class',  // 用于切换 .dark class，但颜色不依赖 dark: 前缀
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

        // 风险色（不在 shadcn 标准语义中，用 --color-* 自定义名）
        'risk-t4': 'var(--color-risk-t4)',
        'risk-t3': 'var(--color-risk-t3)',
        'risk-t2': 'var(--color-risk-t2)',
        'risk-t1': 'var(--color-risk-t1)',
        'risk-t0': 'var(--color-risk-t0)',
        'risk-unknown': 'var(--color-risk-unknown)',

        // 复杂 token（直接引用 CSS 变量）
        'bottom-bar-bg': 'var(--bottom-bar-bg)',
        'bottom-bar-border': 'var(--bottom-bar-border)',
        'nutrition-bg': 'var(--nutrition-bg)',
        'nutrition-border': 'var(--nutrition-border)',
        'banner-bg': 'var(--banner-bg)',
        'banner-label': 'var(--banner-label)',
      },
      borderRadius: {
        lg: 'var(--radius-lg)',
        md: 'var(--radius-md)',
        sm: 'var(--radius-sm)',
      },
    },
  },
}
```

### CSS 变量定义（`design-system.scss`）

#### 基础色板（oklch，接近原设计）

```scss
@layer base {
  :root {
    // ── 亮色模式 ───────────────────────────────
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

    --color-border:           oklch(14.5% 0.016 265 / 6%);  // color-mix 近似
    --color-input:            oklch(14.5% 0.016 265 / 10%);
    --color-ring:             oklch(45% 0.18 330);

    // 风险色
    --color-risk-t4:          oklch(50% 0.22 25);          // #dc2626
    --color-risk-t3:          oklch(55% 0.20 50);          // #ea580c
    --color-risk-t2:          oklch(60% 0.18 85);          // #ca8a04
    --color-risk-t1:          oklch(65% 0.16 145);         // #22c55e
    --color-risk-t0:          oklch(55% 0.15 145);         // #16a34a
    --color-risk-unknown:     oklch(60% 0.01 265);        // #9ca3af

    // 圆角
    --radius-sm:              0.75rem;   // 12px (24rpx)
    --radius-md:              1rem;      // 16px (32rpx)
    --radius-lg:              1.25rem;   // 20px (40rpx)

    // 复杂 token
    --bottom-bar-bg:          oklch(100% 0 0 / 95%);
    --bottom-bar-border:      oklch(14.5% 0.016 265 / 6%);
    --header-scrolled-bg:     oklch(100% 0 0 / 90%);
    --nutrition-bg:           oklch(65% 0.16 145 / 4%);
    --nutrition-border:        oklch(65% 0.16 145 / 12%);
    --nutrition-glow:         oklch(65% 0.16 145 / 30%);
    --banner-bg:              linear-gradient(145deg, oklch(99% 0.005 95) 0%, oklch(98% 0.01 95) 50%, oklch(96% 0.02 85) 100%);
    --banner-label:           oklch(40% 0.12 60);          // #713f12
    --accent-glow:           oklch(45% 0.18 330 / 40%);
  }

  .dark {
    // ── 暗色模式 ───────────────────────────────
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

    // 风险色
    --color-risk-t4:          oklch(70% 0.22 25);          // #f87171
    --color-risk-t3:          oklch(70% 0.22 50);          // #f97316
    --color-risk-t2:          oklch(75% 0.18 85);          // #eab308
    --color-risk-t1:          oklch(75% 0.16 145);         // #4ade80
    --color-risk-t0:          oklch(65% 0.16 145);         // #22c55e
    --color-risk-unknown:     oklch(55% 0.01 265);        // #6b7280

    // 圆角（不变）
    --radius-sm:              0.75rem;
    --radius-md:              1rem;
    --radius-lg:              1.25rem;

    // 复杂 token
    --bottom-bar-bg:          oklch(98% 0.003 265 / 95%);
    --bottom-bar-border:      oklch(100% 0 0 / 6%);
    --header-scrolled-bg:     oklch(93% 0.005 265 / 88%);
    --nutrition-bg:           oklch(75% 0.16 145 / 6%);
    --nutrition-border:       oklch(75% 0.16 145 / 10%);
    --nutrition-glow:         oklch(75% 0.16 145 / 20%);
    --banner-bg:              linear-gradient(145deg, oklch(10% 0.005 265) 0%, oklch(6% 0.004 265) 50%, oklch(9% 0.005 265) 100%);
    --banner-label:           oklch(45% 0.012 265);        // #6b7280
    --accent-glow:            oklch(70% 0.24 330 / 30%);
  }
}
```

> **注：** 为与 shadcn 一致，颜色使用 oklch 格式（现代色域，更广的 P3 色彩空间）。若设计稿色值用 hex/rgb，可转换后填入 oklch，oklch( lightness chroma hue )。

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

**数值就近原则：**
- 优先使用 Tailwind 标准间距（`p-4`=16px, `p-6`=24px, `p-7`=28px 等）
- 若设计值与 TW 标准值偏差 ≤ 4px，用标准值；偏差 > 4px，用 arbitrary value `p-[18px]`
- rpx 转 rem：设计值(rpx) ÷ 2 ÷ 16 = 目标 rem

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
- [ ] `tailwind.config.ts` — `theme.extend.colors` 用 `variable:` 引用 `--color-*`，`borderRadius` 引用 `--radius-*`
- [ ] `App.vue` — 添加 `.dark` class 初始化逻辑，清理残留 SCSS
- [ ] Theme Store — 保持 isDark，移除页面 dark-mode class 绑定

### Phase 2: 简单页面
- [ ] `pages/index/index.vue`
- [ ] `pages/search/index.vue`

### Phase 3: 复杂页面
- [ ] `pages/product/index.vue`
- [ ] `pages/ingredient-detail/index.vue`
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
- [ ] 其他组件

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

### 1. oklch 颜色格式

shadcn 使用 oklch，比传统 hex/rgb 更适合现代显示。转换方式：

```ts
// 使用在线工具或：
// oklch(L% C H)
// L: 明度 0-100 或 0-1（0.97 = 97%）
// C: 色度 0-0.4
// H: 色相 0-360
```

设计稿色值（hex）转换参考：
- `#111827` → `oklch(14.5% 0.016 265)`
- `#f3f4f6` → `oklch(93% 0.005 265)`
- `#db2777` → `oklch(45% 0.18 330)`
- `#ec4899` → `oklch(55% 0.22 330)`

> 可使用 Chrome DevTools 的 color picker 直接复制 oklch 值。

### 2. 复杂 token 处理

color-mix、gradient 等无法用 oklch 表示的，仍保留 CSS 变量：
```scss
--nutrition-bg: oklch(65% 0.16 145 / 4%);   // oklch 支持 alpha: /
--banner-bg: linear-gradient(...);
```
TW config 引用：
```ts
'nutrition-bg': 'var(--nutrition-bg)',
```

### 3. Dark mode 切换

```ts
// App.vue
watch(() => theme.isDark, (dark) => {
  document.documentElement.classList.toggle('dark', dark)
}, { immediate: true })
```

`.dark` class 在 `<html>` 或 `<body>` 上，CSS 变量在 `.dark` 下的定义自动生效。

### 4. Preflight 差异

`preflight: !isMp`，H5 开启，小程序关闭。如有冲突在组件局部重新声明。

---

## 验收标准

1. 所有页面在亮色/暗色下均正常显示，无样式遗漏
2. 颜色通过 CSS 变量自动切换，**不使用** `dark:` TW 前缀
3. `tailwind.config.ts` 中所有颜色通过 `var(--color-*)` 引用
4. CSS 变量定义在 `@layer base` 的 `:root` 和 `.dark` 下（shadcn 模式）
5. SCSS `<style>` 块仅在有 SCSS 逻辑时保留，否则移除
6. `dark-mode` class 从所有页面模板中移除
