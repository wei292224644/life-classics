# UniApp Tailwind 3 样式迁移设计

## 背景

项目 `web/apps/uniapp-tw/` 从头重建，使用 `weapp-vite` + UniApp + Tailwind CSS 3。当前样式大量使用 SCSS + CSS 变量（`design-system.scss`），暗色模式依赖页面级 `dark-mode` class。

## 目标

1. 将所有 SCSS 样式转换为 Tailwind Utility Classes
2. 色彩主题全面使用 Tailwind `theme.extend.colors` + `dark:` 变体
3. 废弃自定义 `dark-mode` class，改用 Tailwind 原生暗色模式（`class="dark"` 在 html/body 或通过 `darkMode: 'class'`）
4. 保留必要 CSS 变量（color-mix 混合、复杂渐变、keyframes）
5. 逐页面、逐组件完成迁移，不破坏现有功能

---

## 色彩系统设计

### Tailwind `theme.extend.colors`

所有语义颜色定义在 `tailwind.config.ts` 的 `theme.extend.colors` 中。

#### 文本色

| Token | Light | Dark |
|-------|-------|------|
| `primary` | #111827 | #f3f4f6 |
| `secondary` | #4b5563 | #9ca3af |
| `muted` | #9ca3af | #6b7280 |

#### 背景色

| Token | Light | Dark |
|-------|-------|------|
| `base` | #f9fafb | #0f0f0f |
| `card` | #ffffff | #1a1a1a |
| `card-hover` | #f9fafb | #222222 |

#### Accent（品牌粉）

| Token | Light | Dark |
|-------|-------|------|
| `accent` | #db2777 | #ec4899 |
| `accent-light` | #ec4899 | #f472b6 |

#### 风险色

| Token | Light | Dark |
|-------|-------|------|
| `risk-t4` (严重) | #dc2626 | #f87171 |
| `risk-t3` (高) | #ea580c | #f97316 |
| `risk-t2` (中) | #ca8a04 | #eab308 |
| `risk-t1` (低) | #22c55e | #4ade80 |
| `risk-t0` (更低) | #16a34a | #22c55e |
| `risk-unknown` | #9ca3af | #6b7280 |

#### 边框/分隔

| Token | Light | Dark |
|-------|-------|------|
| `border` | color-mix(#111827 6%, transparent) | color-mix(#f3f4f6 8%, transparent) |
| `divider` | 同上 | 同上 |

> **注：** 边框色使用 `color-mix()` 无法在 Tailwind 中等价表达，**保留为 CSS 变量 `--tw-border`**（在 `design-system.scss` 的 `:root` 和 `.dark` 下定义，Tailwind 直接引用 CSS 变量值）。

#### 保留 CSS 变量（complex tokens）

以下 tokens 因 `color-mix()` 或复杂 gradient，无法用 Tailwind 等价表达，**保留在 `design-system.scss`** 中：

```
--bottom-bar-bg         color-mix(in oklch, #ffffff 95%, transparent)
--bottom-bar-border     color-mix(in oklch, #111827 6%, transparent)
--bottom-bar-shadow     0 -2rpx 12rpx rgba(0,0,0,0.08)
--header-scrolled-bg    color-mix(in oklch, #ffffff 90%, transparent)
--nutrition-bg          color-mix(in oklch, #22c55e 4%, transparent)
--nutrition-border      color-mix(in oklch, #22c55e 12%, transparent)
--nutrition-glow        color-mix(in oklch, #22c55e 30%, transparent)
--status-bar-bg         #ffffff (dark: transparent)
--status-bar-text       #111827 (dark: #ffffff)
--banner-bg             linear-gradient(...)
--banner-label          #713f12 (dark: #6b7280)
--banner-badge-bg       color-mix(...)
--banner-badge-border   color-mix(...)
--banner-badge-shadow   0 4px 24px rgba(...)
--accent-glow           color-mix(in oklch, var(--accent) 40%, transparent)
```

---

## 暗色模式配置

### `tailwind.config.ts`

```ts
darkMode: 'class',  // 通过 .dark class 切换
```

### 页面级变更

所有页面 `<view class="index-page" :class="{ 'dark-mode': themeStore.isDark }">` 改为：

```vue
<view class="index-page dark:bg-[#0f0f0f]">
```

Theme Store 仍提供 `isDark`，但不再做 class 绑定——由 Tailwind `dark:` 处理。

### 迁移策略

`App.vue` 中初始化时在 `<html>` 或 `<body>` 添加/移除 `.dark` class：

```ts
// main.ts 或 App.vue
import { watch } from 'vue'
import { useThemeStore } from './store/theme'

const theme = useThemeStore()
watch(() => theme.isDark, (dark) => {
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}, { immediate: true })
```

UniApp 各端兼容写法通过 `platform.ts` 判断 H5/小程序分别处理。

---

## 间距 & 字号迁移

当前使用 CSS 变量间距（`var(--space-4)`、`var(--text-xl)` 等），迁移为 Tailwind 对应值：

| CSS var | Tailwind |
|----------|----------|
| `var(--space-1)` | `py-1` / `px-1` |
| `var(--space-2)` | `py-2` |
| `var(--space-3)` | `gap-3` |
| `var(--space-4)` | `gap-4` |
| `var(--space-6)` | `gap-6` |
| `var(--space-7)` | `gap-7` |
| `var(--space-8)` | `gap-8` |
| `var(--space-10)` | `gap-10` |
| `var(--space-12)` | `px-12` |
| `var(--space-14)` | `mt-14` / `mb-14` |
| `var(--space-16)` | `py-16` |
| `var(--space-18)` | `w-18 h-18` (自定义值) |
| `var(--space-20)` | `w-20 h-20` |
| `var(--space-24)` | `gap-24` |

字体大小对应：

| CSS var | Tailwind |
|----------|----------|
| `var(--text-sm)` | `text-sm` |
| `var(--text-base)` | `text-base` |
| `var(--text-md)` | `text-[28rpx]` 或自定义 |
| `var(--text-lg)` | `text-lg` |
| `var(--text-xl)` | `text-xl` |
| `var(--text-2xl)` | `text-2xl` |
| `var(--text-3xl)` | `text-3xl` |
| `var(--text-5xl)` | `text-5xl` |
| `var(--text-6xl)` | `text-6xl` |

> **注：** UniApp 使用 rpx 单位，TW3 通过 `weapp-tailwindcss` 的 `rem2rpx` 转换，部分需要用 arbitrary values `[28rpx]`。

---

## 圆角 & 阴影迁移

| CSS var | Tailwind |
|---------|----------|
| `var(--radius-sm)` (24rpx) | `rounded-3xl` 或 `rounded-[24rpx]` |
| `var(--radius-md)` (32rpx) | `rounded-[32rpx]` |
| `var(--radius-lg)` (40rpx) | `rounded-[40rpx]` |
| `var(--radius-xl)` (48rpx) | `rounded-[48rpx]` |
| `var(--shadow-sm)` | `shadow-sm` |

---

## 页面迁移清单

按依赖顺序迁移：

### Phase 1: 基础样式层
- [ ] `tailwind.config.ts` — 定义所有语义颜色、dark: 变体、自定义 spacing/fontSize
- [ ] `design-system.scss` — 精简为只保留复杂 token（color-mix gradient keyframes）
- [ ] `App.vue` — 添加 dark class 初始化逻辑，清理残留 SCSS
- [ ] Theme Store — 保持 isDark 状态，移除页面 dark-mode class 绑定

### Phase 2: 简单页面
- [ ] `pages/index/index.vue` — 首页（样式相对独立）
- [ ] `pages/search/index.vue`

### Phase 3: 复杂页面
- [ ] `pages/product/index.vue` — 产品详情页
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

### 迁移前（SCSS + CSS 变量）
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

### 迁移后（Tailwind）
```vue
<style lang="scss" scoped>
// 无需 SCSS，移除 scoped style
</style>

<!-- 直接在 template 中 -->
<view class="flex items-center gap-6 rounded-[28rpx] border bg-card p-7 shadow-sm transition-transform active:scale-[0.98] dark:bg-[#1a1a1a] dark:border-[color-mix(in_oklch,#f3f4f6_8%,transparent)]" />
```

> **注意：** `dark:` 变体覆盖颜色时，如果值是 CSS 变量需用完整写法 `dark:bg-[var(--bg-card)]`；如果是 TW 内置色板如 `dark:text-gray-100` 则直接写。

---

## 关键技术点

### 1. `color-mix()` 在 Tailwind 中的使用
```ts
// tailwind.config.ts 中无法直接使用 color-mix，保留 CSS 变量方案
colors: {
  border: 'color-mix(in oklch, #111827 6%, transparent)',
}
// 或在 CSS 中定义后引用
colors: {
  border: 'var(--tw-border)',
}
```

### 2. 动态 rpx 值
TW 默认不处理 rpx，使用 arbitrary values：
```html
<view class="w-[280rpx] h-[280rpx] rounded-full" />
```

**数值就近原则：**
- 优先使用 Tailwind 标准间距（`p-4`=16px, `p-6`=24px, `p-7`=28px 等）
- 若设计值与标准值偏差 ≤ 4px，用标准值；偏差 > 4px，用 arbitrary value 如 `p-[22rpx]`
- rpx 转 px 公式：设计值 ÷ 2 = 目标 px 值（基准屏 375px）

### 3. Dark mode 切换
```ts
// App.vue onMounted
document.documentElement.classList.toggle('dark', themeStore.isDark)
// 监听变化
watch(() => themeStore.isDark, (v) => {
  document.documentElement.classList.toggle('dark', v)
})
```

### 4. Preflight 差异
`tailwind.config.ts` 中 `preflight: !isMp`，H5 开启 Preflight（`box-shadow` 等可能冲突），小程序关闭。小程序若有样式问题，在组件局部重新声明需要重置的属性。

---

## 验收标准

1. 所有页面在亮色/暗色下均正常显示，无样式遗漏
2. `dark:` 变体正确覆盖亮色样式
3. SCSS `<style>` 块仅在有真正 SCSS 逻辑时保留（keyframes、mixin、函数），否则移除
4. `tailwind.config.ts` 中定义的颜色均有完整 dark: 映射
5. `dark-mode` class 从所有页面模板中移除
6. `design-system.scss` 精简至仅含 complex tokens
