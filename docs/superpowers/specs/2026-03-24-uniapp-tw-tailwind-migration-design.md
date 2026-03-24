# UniApp Tailwind 3 样式迁移设计

## 背景

项目 `web/apps/uniapp-tw/` 从头重建，使用 `weapp-vite` + UniApp + Tailwind CSS 3。当前样式大量使用 SCSS + CSS 变量（`design-system.scss`），暗色模式依赖页面级 `dark-mode` class。

## 目标

1. 将所有 SCSS 样式转换为 Tailwind Utility Classes
2. **废弃 `dark:` 变体**，所有亮暗颜色通过 CSS 变量值切换（`.dark` class 在根元素）
3. Tailwind 的 `theme.extend.colors` 引用 CSS 变量，同一 utility class 在亮/暗下自动对应正确颜色
4. 保留复杂 CSS 变量（color-mix 混合、复杂渐变、keyframes）
5. 逐页面、逐组件完成迁移，不破坏现有功能

---

## 色彩系统设计

### 核心原则

所有语义颜色定义为 CSS 变量，**不**使用 Tailwind `dark:` 变体。`.dark` class 加在根元素时，CSS 变量自动切换颜色值，Tailwind utility class 无需任何变动。

### 架构

```
tailwind.config.ts
  theme.extend.colors → 引用 CSS 变量值 (var(--color-primary))

design-system.scss
  :root           → 亮色 CSS 变量值
  .dark           → 暗色 CSS 变量值（覆盖）
  其他 complex    → 保留（gradient, color-mix, keyframes）
```

### 语义颜色变量定义（`design-system.scss`）

#### 文本色

```scss
:root {
  --color-primary:   #111827;
  --color-secondary: #4b5563;
  --color-muted:     #9ca3af;
}
.dark {
  --color-primary:   #f3f4f6;
  --color-secondary: #9ca3af;
  --color-muted:     #6b7280;
}
```

#### 背景色

```scss
:root {
  --color-base:      #f9fafb;
  --color-card:      #ffffff;
  --color-card-hover: #f9fafb;
}
.dark {
  --color-base:      #0f0f0f;
  --color-card:      #1a1a1a;
  --color-card-hover: #222222;
}
```

#### Accent（品牌粉）

```scss
:root {
  --color-accent:       #db2777;
  --color-accent-light: #ec4899;
}
.dark {
  --color-accent:       #ec4899;
  --color-accent-light: #f472b6;
}
```

#### 风险色

```scss
:root {
  --color-risk-t4:      #dc2626;
  --color-risk-t3:      #ea580c;
  --color-risk-t2:      #ca8a04;
  --color-risk-t1:      #22c55e;
  --color-risk-t0:      #16a34a;
  --color-risk-unknown: #9ca3af;
}
.dark {
  --color-risk-t4:      #f87171;
  --color-risk-t3:      #f97316;
  --color-risk-t2:      #eab308;
  --color-risk-t1:      #4ade80;
  --color-risk-t0:      #22c55e;
  --color-risk-unknown: #6b7280;
}
```

#### 边框色

```scss
:root {
  --color-border: color-mix(in oklch, #111827 6%, transparent);
}
.dark {
  --color-border: color-mix(in oklch, #f3f4f6 8%, transparent);
}
```

### Tailwind `theme.extend.colors` 配置

```ts
// tailwind.config.ts
colors: {
  primary: 'var(--color-primary)',
  secondary: 'var(--color-secondary)',
  muted: 'var(--color-muted)',
  base: 'var(--color-base)',
  card: 'var(--color-card)',
  'card-hover': 'var(--color-card-hover)',
  accent: 'var(--color-accent)',
  'accent-light': 'var(--color-accent-light)',
  'risk-t4': 'var(--color-risk-t4)',
  'risk-t3': 'var(--color-risk-t3)',
  'risk-t2': 'var(--color-risk-t2)',
  'risk-t1': 'var(--color-risk-t1)',
  'risk-t0': 'var(--color-risk-t0)',
  'risk-unknown': 'var(--color-risk-unknown)',
  border: 'var(--color-border)',
}
```

> **注意：** TW 的 `darkMode: 'class'` 仍然配置，但**不使用** `dark:` 变体写法。`.dark` class 只用来触发 CSS 变量值切换。

### 保留 CSS 变量（complex tokens）

以下 tokens 保留在 `design-system.scss`（不在 TW colors 中定义），在需要时直接引用：

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
--accent-glow           color-mix(in oklch, var(--color-accent) 40%, transparent)
```

---

## 暗色模式切换机制

### App.vue

```ts
// App.vue
import { watch } from 'vue'
import { useThemeStore } from './store/theme'

const theme = useThemeStore()
watch(() => theme.isDark, (dark) => {
  // H5
  document.documentElement.classList.toggle('dark', dark)
}, { immediate: true })
```

### 页面模板变更

**移除**所有页面中的 `:class="{ 'dark-mode': themeStore.isDark }"` 绑定。

```vue
<!-- 迁移前 -->
<view class="index-page" :class="{ 'dark-mode': themeStore.isDark }">

<!-- 迁移后 -->
<view class="index-page">
```

颜色完全由 utility class 引用 CSS 变量，无需任何动态 class：
```vue
<view class="index-page bg-base text-primary">
  <view class="hero bg-card border border-border">
```

---

## 间距 & 字号迁移

`weapp-tailwindcss` 的 `rem2rpx` 已自动转换，直接使用 Tailwind 标准值。

**数值就近原则：**
- 优先使用 Tailwind 标准间距（`p-4`=16px, `p-6`=24px, `p-7`=28px 等）
- 若设计值与 TW 标准值偏差 ≤ 4px，用标准值；偏差 > 4px，用 arbitrary value `p-[18px]`
- rpx 转 rem 公式：设计值(rpx) ÷ 2 ÷ 16 = 目标 rem（基准屏 2x）

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

| CSS var (设计值) | Tailwind |
|---------|----------|
| `var(--radius-sm)` (24rpx=12px) | `rounded-xl` |
| `var(--radius-md)` (32rpx=16px) | `rounded-2xl` |
| `var(--radius-lg)` (40rpx=20px) | `rounded-[20px]` |
| `var(--radius-xl)` (48rpx=24px) | `rounded-3xl` |
| `var(--shadow-sm)` | `shadow-sm` |

---

## 页面迁移清单

### Phase 1: 基础样式层
- [ ] `tailwind.config.ts` — `theme.extend.colors` 引用 CSS 变量，`darkMode: 'class'` 保留但不写 `dark:` 用法
- [ ] `design-system.scss` — 整理为 `:root` 和 `.dark` 两套 CSS 变量，移除 TW 已覆盖的简单颜色
- [ ] `App.vue` — 添加 `.dark` class 初始化逻辑，清理残留 SCSS
- [ ] Theme Store — 保持 isDark，移除页面 dark-mode class 绑定

### Phase 2: 简单页面
- [ ] `pages/index/index.vue` — 首页
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
<!-- 移除 <style>，直接写在 template class 中 -->
<view class="flex items-center gap-6 rounded-xl border bg-card p-7 shadow-sm transition-transform active:scale-[0.98] border-border" />
```

**说明：**
- `bg-card` → `var(--color-card)` → 亮色 `#ffffff` / 暗色 `#1a1a1a`（自动）
- `border-border` → `var(--color-border)` → 亮色 `color-mix()` / 暗色 `color-mix()`
- `rounded-xl` → 12px，接近原 24rpx（12px）
- 无需任何 `dark:` 前缀

---

## 关键技术点

### 1. CSS 变量与 Tailwind 颜色联动

所有 `theme.extend.colors` 引用 CSS 变量：
```ts
colors: {
  primary: 'var(--color-primary)',
  card: 'var(--color-card)',
  border: 'var(--color-border)',
}
```

`design-system.scss` 中 `:root` 定义亮色，`.dark` 覆盖：
```scss
:root { --color-primary: #111827; }
.dark { --color-primary: #f3f4f6; }
```

使用时 `text-primary` 即可，亮暗自动切换。

### 2. 复杂 tokens 保留 CSS 变量写法

对于 `color-mix()`、gradient 等无法用 TW 表达的，仍直接引用：
```vue
<view style="background: var(--nutrition-bg); border-color: var(--nutrition-border);" />
```
或通过 `theme.extend` 在 tailwind config 中映射：
```ts
colors: {
  nutritionBg: 'var(--nutrition-bg)',
}
```

### 3. Dark mode 切换

```ts
// App.vue
watch(() => theme.isDark, (dark) => {
  document.documentElement.classList.toggle('dark', dark)
}, { immediate: true })
```

UniApp 各端兼容写法（H5 / 小程序）通过 `platform.ts` 判断。

### 4. Preflight 差异

`tailwind.config.ts` 中 `preflight: !isMp`，H5 开启 Preflight（可能与组件样式冲突），小程序关闭。如有冲突在组件局部重新声明。

---

## 验收标准

1. 所有页面在亮色/暗色下均正常显示，无样式遗漏
2. 颜色通过 CSS 变量自动切换，**不使用** `dark:` 变体
3. SCSS `<style>` 块仅在有 SCSS 逻辑时保留（keyframes、mixin、函数），否则移除
4. `tailwind.config.ts` 中所有颜色引用 CSS 变量，亮暗两套值定义在 `design-system.scss`
5. `dark-mode` class 从所有页面模板中移除
6. `design-system.scss` 保留 complex tokens（color-mix、gradient、keyframes），清理已迁移的简单 tokens
