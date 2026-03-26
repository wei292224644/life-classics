# 产品设计规范 — 2026 Design System

> 本规范基于 `style.scss` + `tailwind.config.ts` 代码实现总结提炼，适用于 life-classics 全栈应用（UniApp / Console / Web）。
> 所有新增页面和组件须遵循此规范。

---

## 1. 色彩系统

### 1.1 主题变量

#### 亮色模式 (`:root`)

| Token | oklch 值 | hex 近似值 | 用途 |
|-------|----------|------------|------|
| `--background` | `oklch(0.96 0 0)` | `#fafafa` | 页面背景 |
| `--foreground` | `oklch(0.147 0.004 49.3)` | `#111827` | 主文字 |
| `--card` | `oklch(1 0 0)` | `#ffffff` | 卡片背景 |
| `--card-foreground` | `oklch(0.147 0.004 49.3)` | `#111827` | 卡片文字 |
| `--popover` | `oklch(1 0 0)` | `#ffffff` | 浮层背景 |
| `--popover-foreground` | `oklch(0.147 0.004 49.3)` | `#111827` | 浮层文字 |
| `--primary` | `#ec4899` | `#ec4899` | 主题色（固定值） |
| `--primary-foreground` | `oklch(0.971 0.014 343.198)` | `#fff5f7` | 主色上文字 |
| `--secondary` | `oklch(0.967 0.001 286.375)` | `#f3f4f6` | 次要背景 |
| `--secondary-foreground` | `oklch(0.41 0.006 285.885)` | `#6b7280` | 次要文字 |
| `--muted` | `oklch(0.96 0.002 17.2)` | `#f4f4f5` | 弱化背景 |
| `--muted-foreground` | `oklch(0.547 0.021 43.1)` | `#71717a` | 弱化文字 |
| `--accent` | `oklch(0.96 0.002 17.2)` | `#f4f4f5` | 强调背景 |
| `--accent-foreground` | `oklch(0.214 0.009 43.1)` | `#1f2937` | 强调文字 |
| `--destructive` | `oklch(0.577 0.245 27.325)` | `#dc2626` | 危险/错误 |
| `--border` | `oklch(0.922 0.005 34.3)` | `#e5e7eb` | 边框 |
| `--input` | `oklch(0.922 0.005 34.3)` | `#e5e7eb` | 输入框边框 |
| `--ring` | `oklch(0.714 0.014 41.2)` | `#a1a1aa` | 焦点环 |

#### 暗色模式 (`.dark`)

| Token | oklch 值 | hex 近似值 | 用途 |
|-------|----------|------------|------|
| `--background` | `oklch(0.147 0.004 49.3)` | `#111827` | 页面背景 |
| `--foreground` | `oklch(0.986 0.002 67.8)` | `#f4f4f5` | 主文字 |
| `--card` | `oklch(0.214 0.009 43.1)` | `#1f2937` | 卡片背景 |
| `--card-foreground` | `oklch(0.986 0.002 67.8)` | `#f4f4f5` | 卡片文字 |
| `--primary` | `oklch(0.459 0.187 3.815)` | `#be185d` | 主题色（暗） |
| `--primary-foreground` | `oklch(0.971 0.014 343.198)` | `#fff5f7` | 主色上文字 |
| `--secondary` | `oklch(0.274 0.006 286.033)` | `#1f1f1f` | 次要背景 |
| `--secondary-foreground` | `oklch(0.985 0 0)` | `#fafafa` | 次要文字 |
| `--muted` | `oklch(0.268 0.011 36.5)` | `#18181b` | 弱化背景 |
| `--muted-foreground` | `oklch(0.714 0.014 41.2)` | `#a1a1aa` | 弱化文字 |
| `--destructive` | `oklch(0.704 0.191 22.216)` | `#b91c1c` | 危险/错误 |
| `--border` | `oklch(1 0 0 / 10%)` | `rgba(255,255,255,0.1)` | 边框 |
| `--input` | `oklch(1 0 0 / 15%)` | `rgba(255,255,255,0.15)` | 输入框边框 |
| `--ring` | `oklch(0.547 0.021 43.1)` | `#71717a` | 焦点环 |

### 1.2 风险等级色板

后端枚举：`t4 / t3 / t2 / t1 / t0 / unknown`（`server/database/models.py`）。前端保留 5 档独立视觉等级，`unknown` 为特殊回退态。

#### 全局 CSS 变量（`style.scss`）

| level | Token | 亮色 oklch | 暗色 oklch |
|-------|-------|------------|------------|
| `t4` | `--color-risk-t4` | `oklch(50% 0.22 25)` | `oklch(70% 0.22 25)` |
| `t3` | `--color-risk-t3` | `oklch(55% 0.2 50)` | `oklch(70% 0.22 50)` |
| `t2` | `--color-risk-t2` | `oklch(60% 0.18 85)` | `oklch(75% 0.18 85)` |
| `t1` | `--color-risk-t1` | `oklch(65% 0.16 145)` | `oklch(75% 0.16 145)` |
| `t0` | `--color-risk-t0` | `oklch(55% 0.15 145)` | `oklch(65% 0.16 145)` |
| `unknown` | `--color-risk-unknown` | `oklch(60% 0.01 265)` | `oklch(55% 0.01 265)` |

#### Tailwind 扩展色（`tailwind.config.ts`）

```ts
risk: {
  t4: "oklch(50% 0.22 25 / <alpha-value>)",
  t3: "oklch(55% 0.2 50 / <alpha-value>)",
  t2: "oklch(60% 0.18 85 / <alpha-value>)",
  t1: "oklch(65% 0.16 145 / <alpha-value>)",
  t0: "oklch(55% 0.15 145 / <alpha-value>)",
  unknown: "oklch(60% 0.01 265 / <alpha-value>)",
}
```

支持透明度的写法：`bg-risk-t4/20`、`text-risk-t3`、`border-risk-t2/50`

### 1.3 风险分组背景/边框（IngredientSection）

| 等级 | 亮色背景 | 亮色边框 | 暗色背景 | 暗色边框 |
|------|----------|----------|----------|----------|
| `t4` | `oklch(97% 0.02 25 / 4%)` | `oklch(97% 0.02 25 / 10%)` | `oklch(75% 0.12 25 / 8%)` | `oklch(75% 0.12 25 / 15%)` |
| `t3` | `oklch(97% 0.02 50 / 4%)` | `oklch(97% 0.02 50 / 10%)` | `oklch(75% 0.12 50 / 8%)` | `oklch(75% 0.12 50 / 15%)` |
| `t2` | `oklch(97% 0.02 85 / 4%)` | `oklch(97% 0.02 85 / 10%)` | `oklch(75% 0.1 85 / 8%)` | `oklch(75% 0.1 85 / 15%)` |
| `t1` | `oklch(97% 0.02 145 / 4%)` | `oklch(97% 0.02 145 / 10%)` | `oklch(75% 0.1 145 / 8%)` | `oklch(75% 0.1 145 / 15%)` |
| `t0` | `oklch(97% 0.02 145 / 4%)` | `oklch(97% 0.02 145 / 10%)` | `oklch(75% 0.1 145 / 8%)` | `oklch(75% 0.1 145 / 15%)` |
| `unknown` | `oklch(97% 0.01 265 / 4%)` | `oklch(97% 0.01 265 / 10%)` | `oklch(75% 0.01 265 / 8%)` | `oklch(75% 0.01 265 / 15%)` |

### 1.4 调色板色（SectionHeader 图标背景）

| Token | oklch 值 | 用途 |
|-------|----------|------|
| `--palette-blue-500` | `oklch(60% 0.15 250)` | 蓝色图标背景 |
| `--palette-purple-500` | `oklch(55% 0.2 300)` | 紫色图标背景 |
| `--palette-green-500` | `oklch(60% 0.15 145)` | 绿色图标背景 |
| `--palette-orange-500` | `oklch(60% 0.18 50)` | 橙色图标背景 |

### 1.5 强调色（accent pink）

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `--accent-pink-light` | `#ec4899` | `#f472b6` | 浅粉色/hover 态 |
| `--accent-pink` | `#db2777` | `#ec4899` | 主粉色 |

### 1.6 组件级 Token

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `--bottom-bar-bg` | `oklch(100% 0 0 / 95%)` | `oklch(98% 0.003 265 / 95%)` | 底部栏毛玻璃背景 |
| `--bottom-bar-border` | `oklch(14.5% 0.016 265 / 6%)` | `oklch(100% 0 0 / 6%)` | 底部栏边框 |
| `--header-scrolled-bg` | `oklch(100% 0 0 / 90%)` | `oklch(93% 0.005 265 / 88%)` | 滚动后头部背景 |
| `--ai-label-bg` | `linear-gradient(135deg, #8b5cf6, #7c3aed)` | 同左 | AI 标签渐变背景 |
| `--nutrition-bg` | `oklch(65% 0.16 145 / 4%)` | `oklch(75% 0.16 145 / 6%)` | 营养卡片背景 |
| `--nutrition-border` | `oklch(65% 0.16 145 / 12%)` | `oklch(75% 0.16 145 / 10%)` | 营养卡片边框 |
| `--nutrition-glow` | `oklch(65% 0.16 145 / 30%)` | `oklch(75% 0.16 145 / 20%)` | 营养卡片发光线 |
| `--banner-bg` | `linear-gradient(145deg, #fffbeb 0%, #fef3c7 50%, #fde68a 100%)` | `linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%)` | Banner 背景 |
| `--banner-label` | `#713f12` | `oklch(45% 0.012 265)` | Banner 标签文字 |
| `--banner-badge-bg` | `oklch(100% 0 0 / 85%)` | `oklch(12% 0.005 265 / 90%)` | Banner 徽章背景 |
| `--banner-badge-border` | `oklch(100% 0 0 / 20%)` | `oklch(100% 0 0 / 10%)` | Banner 徽章边框 |
| `--banner-badge-shadow` | `0 4px 24px rgba(0, 0, 0, 0.15)` | `0 4px 24px rgba(0, 0, 0, 0.4)` | Banner 徽章阴影 |
| `--accent-glow` | `oklch(45% 0.18 330 / 40%)` | `oklch(70% 0.24 330 / 30%)` | 强调发光效果 |

---

## 2. 字体系统

- **主字体**: DM Sans (Google Fonts)，回退 `-apple-system, sans-serif`
- **图标字体**: Remix Icon（本地加载 `remixicon.css`）

### 字号梯度（设计稿 px，UniApp 对应 rpx 见第 8 节）

| 用途 | 设计稿 | 字重 | 字间距 |
|------|--------|------|--------|
| 章节标题 | 20px | 700 | `-0.02em` |
| Header 标题 | 17px | 600 | `-0.02em` |
| 配料卡片名称 | 13px | 600 | — |
| 正文 | 14px | 400 | `line-height: 1.5` |
| 小标签 / 风险徽章 | 12px | 600 | — |
| 营养标签 / 单位 | 11px | 500 | `uppercase` / `0.08em` |
| 营养数值 | 32px | 700 | `-0.03em` / `tabular-nums` |

---

## 3. 间距系统

基于 4px 网格（设计稿 px）：

| 用途 | 设计稿值 |
|------|---------|
| 图标与文字间隙 | 4px |
| 标签内元素间距 | 8px |
| 按钮内 padding 垂直 | 10–14px |
| 配料卡片间距 | 10px |
| 卡片内 padding | 16–20px |
| 章节间距 | 28px |
| 内容区顶部 padding | 24px |
| 内容区水平 padding | 20px |
| 内容区底部 padding | 40px（滚动内容结束处） |

### 圆角

| 用途 | 设计稿值 |
|------|---------|
| 小按钮 / 图标按钮 | 12px |
| 风险徽章 / 原因标签 | 6–8px |
| 配料卡片 | 16px |
| 风险分组 / 健康卡片 | 20px |
| 营养卡片 | 24px |
| Banner 风险徽章 | 14px |

### CSS / Tailwind Token

```scss
// style.scss
--radius-sm: 0.5rem;  // 7px (14rpx)
--radius-md: 0.625rem; // 10px (20rpx)
--radius-lg: 0.875rem; // 14px (28rpx)
--radius-xl: 1.125rem; // 18px (36rpx)
```

```ts
// tailwind.config.ts
borderRadius: {
  sm: "var(--radius-sm)",
  md: "var(--radius-md)",
  lg: "var(--radius-lg)",
  xl: "var(--radius-xl)",
},
```

---

## 4. 阴影系统

### 暗色模式
```css
/* 滚动后 header */
box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.06);

/* 底部栏 */
box-shadow: 0 -8px 32px rgba(0,0,0,0.4);

/* 主按钮 */
box-shadow: 0 4px 20px rgba(236,72,153,0.3);

/* 风险色条 glow（暗色专用） */
box-shadow: 0 0 8px var(--risk-tN);
```

### 亮色模式
```css
/* 滚动后 header */
box-shadow: 0 4px 24px rgba(0,0,0,0.08), 0 1px 0 rgba(0,0,0,0.04);

/* 底部栏 */
box-shadow: 0 -8px 32px rgba(0,0,0,0.06);

/* 白色卡片（健康/建议卡） */
box-shadow: 0 2px 8px rgba(0,0,0,0.04);

/* 主按钮 */
box-shadow: 0 4px 20px rgba(236,72,153,0.3);
```

---

## 5. 动画规范

### 入场动画原则
- 使用 `transform` + `opacity` 组合（GPU 加速）
- 曲线: `cubic-bezier(0.34, 1.56, 0.64, 1)`（弹入感）
- 避免 `transition: all`

### 标准动画

```css
/* 卡片入场：slideUp */
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16rpx); }
  to   { opacity: 1; transform: translateY(0); }
}
/* 使用：animation: slideUp 0.5s 0.1s cubic-bezier(0.34, 1.56, 0.64, 1) forwards */

/* Banner emoji：floatIn */
@keyframes floatIn {
  from { opacity: 0; transform: scale(0.8); }
  to   { opacity: 1; transform: scale(1); }
}
/* 使用：animation: floatIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards */

/* Banner 徽章：slideUpBadge */
@keyframes slideUpBadge {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* 使用：animation: slideUpBadge 0.6s 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards */

/* Toast 进度条：shrink */
@keyframes shrink {
  from { width: 100%; }
  to   { width: 0%; }
}
/* 使用：animation: shrink linear forwards */
```

### 尊重运动偏好
```css
@media (prefers-reduced-motion: reduce) {
  .banner-emoji, .nutrition-card, .health-card, .advice-card, .banner-badge {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
  .animate-shrink {
    animation: none !important;
  }
}
```

---

## 6. 组件规范

### 6.1 DButton

**文件**: `components/ui/DButton.vue`

**Variants**:

| variant | 说明 | 样式 |
|---------|------|------|
| `default` | 渐变粉色主按钮 | `bg-[linear-gradient(135deg,var(--accent-pink-light),var(--accent-pink))]` + 粉色阴影 |
| `secondary` | 次要按钮 | `bg-secondary border-border` |
| `outline` | 描边按钮 | `border-border bg-transparent` |
| `ghost` | 幽灵按钮 | `bg-transparent border-transparent` |
| `destructive` | 危险按钮 | `bg-destructive text-white` |

**Sizes**:

| size | 高度 | padding | 字号 | 圆角 | 用途 |
|------|------|---------|------|------|------|
| `sm` | 32px | `px-3` | 12px | `rounded-md` | 小按钮 |
| `md` | 40px | `px-4` | 14px | `rounded-lg` | 默认 |
| `lg` | 48px | `px-6` | 16px | `rounded-xl` | 大按钮 |
| `icon` | 40px | `p-0` | — | `rounded-lg` | 图标按钮 |

**Props**:

```ts
interface Props {
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  disabled?: boolean;
  loading?: boolean;
  iconLeft?: IconName;   // 左侧图标
  iconRight?: IconName;  // 右侧图标
  icon?: IconName;       // iconLeft 的别名
  dclass?: string;       // 自定义 tailwind class
}
```

**Events**:
- `click(event: Event)` — 点击事件

**行为**:
- `disabled || loading` 时添加 `opacity-50 pointer-events-none`
- `loading` 态显示旋转 loader 图标
- Active 态：`active:scale-[0.97]`
- Focus 态：`focus-visible:ring-accent-pink`

---

### 6.2 DIcon

**文件**: `components/ui/DIcon.vue`

Remix Icon 的 Vue 封装，支持 `line`（描边）和 `fill`（填充）两种类型。

**Props**:

```ts
interface Props {
  name: string;                    // 图标名称（camelCase，自动转 kebab-case）
  type?: 'line' | 'fill';         // 图标类型，默认 'line'
  dclass?: string;                // 自定义 tailwind class
}
```

**图标名称**（`iconsRegistry.ts`）:

```ts
arrowLeft, arrowRight, x, check, chevronDown, share, star, badgeCheck,
leaf, helpCircle, alertTriangle, info, alertCircle, shoppingCart, scan,
user, menu, users, bookmark, settings, search, messageCircle, loader,
riskT0, riskT1, riskT2, riskT3, riskT4, riskUnknown, checkCircle, xCircle
```

**使用示例**:
```vue
<DIcon name="arrowLeft" />
<DIcon name="check" type="fill" />
<DIcon name="riskT4" dclass="text-risk-t4" />
```

---

### 6.3 AITag

**文件**: `components/ui/AITag.vue`

AI 标签组件，显示"AI"渐变文字。

**样式**:
- 字号：9.5px / 700
- 背景：`linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink))`
- 文字：`-webkit-background-clip: text` + `-webkit-text-fill-color: transparent`

---

### 6.4 TopBar

**文件**: `components/ui/TopBar.vue`

状态栏占位组件，用于适配不同设备的刘海屏高度。

**实现**: 读取系统 `statusBarHeight`，渲染对应高度的占位 view。

---

### 6.5 Screen

**文件**: `components/ui/Screen.vue`

页面布局容器，提供 header / content / footer 三插槽结构。

**Slots**:
- `header` — 顶部区域（固定）
- `content` — 滚动内容区（`<scroll-view>`）
- `footer` — 底部区域（固定）

**Events**:
- `scroll(event)` — 滚动事件，参数 `{ detail: { scrollTop: number } }`

**Props**:
```ts
interface Props {
  header?: VNode;
  content?: VNode;
  footer?: VNode;
}
```

---

### 6.6 BottomBar

**文件**: `components/ui/BottomBar.vue`

固定底部操作栏，与 design system 规范一致。

**Props**:

| prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `primaryLabel` | `string` | `"咨询 AI 助手"` | 主按钮文字 |
| `secondaryLabel` | `string` | `"添加到记录"` | 次按钮文字 |

**Events**:

| event | 说明 |
|-------|------|
| `primary` | 主按钮点击 |
| `secondary` | 次按钮点击 |

**样式**:
- 毛玻璃：`backdrop-saturate-[180%] backdrop-blur-[16px]`
- 亮色：`bg-white/95 border-t border-border shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.06)]`
- 暗色：`bg-black/95 border-t border-border shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.4)]`

---

### 6.7 RiskBadge

**文件**: `components/ui/RiskBadge.vue`

风险等级徽章组件，显示等级文字 + 对应颜色。

| 视觉 key | 文案 | 图标 |
|---------|------|------|
| `critical` | 极高风险 | ⛔ |
| `high` | 高风险 | ⚠ |
| `medium` | 中等风险 | ⚠ |
| `low` | 低风险 | ✓ |
| `safe` | 安全 | ✓ |
| `unknown` | 暂无评级 | ? |

---

### 6.8 SectionHeader

**文件**: `components/ui/SectionHeader.vue`

章节标题组件。

**Props**:
```ts
interface Props {
  title: string;           // 标题文字
  icon?: IconName;         // 左侧图标
  iconBg?: string;          // 图标背景色（palette-*）
  aiLabel?: boolean;       // 是否显示 AI 标签
}
```

---

### 6.9 RiskTag

**文件**: `components/ui/RiskTag.vue`

风险标签组件（与 RiskBadge 不同，RiskTag 是小标签样式）。

---

### 6.10 Tag

**文件**: `components/ui/Tag.vue`

通用标签组件。

---

### 6.11 StateView

**文件**: `components/ui/StateView.vue`

加载/错误状态视图组件。

---

### 6.12 Toast / ToastContainer

**文件**: `components/ui/Toast.vue`, `ToastContainer.vue`

轻提示组件。`ToastContainer` 是容器，`Toast` 是单个提示。

---

### 6.13 HorizontalScroller

**文件**: `components/ui/HorizontalScroller.vue`

横向滚动容器组件。

---

### 6.14 InfoCard / InfoChip

**文件**: `components/ui/InfoCard.vue`, `InfoChip.vue`

信息卡片和信息标签组件。

---

### 6.15 NutritionTable

**文件**: `components/ui/NutritionTable.vue`

营养成分表格组件。

---

### 6.16 Cell / ListItem / Separator

**文件**: `components/ui/Cell.vue`, `ListItem.vue`, `Separator.vue`

列表相关基础组件。

---

---

## 7. Card 组件

**文件**: `components/ui/card/`

基于 shadcn/card 模式的卡片组件系列。

### Card

**Props**:

| prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'default' \| 'elevated' \| 'outlined'` | `'default'` | 卡片变体 |
| `hoverable` | `boolean` | `false` | 是否可 hover（带悬停动效） |
| `dclass` | `string` | `''` | 自定义 tailwind class |

**Variant 样式**:

| variant | 样式 |
|---------|------|
| `default` | `bg-card border border-border shadow-sm` |
| `elevated` | `bg-card border border-transparent shadow-[0_4rpx_12rpx_rgba(0,0,0,0.08),0_8rpx_24rpx_rgba(0,0,0,0.06)]` |
| `outlined` | `bg-card border border-border shadow-none` |

**hoverable 动效**:
- `hover:-translate-y-[2rpx] hover:shadow-[...]`
- `active:translate-y-0`
- 曲线：`cubic-bezier(0.34, 1.56, 0.64, 1)`

### CardHeader / CardTitle / CardDescription / CardContent / CardFooter

子组件，用于构建完整卡片结构：

```vue
<Card>
  <CardHeader>
    <CardTitle>标题</CardTitle>
    <CardDescription>描述文字</CardDescription>
  </CardHeader>
  <CardContent>
    内容区
  </CardContent>
  <CardFooter>
    页脚
  </CardFooter>
</Card>
```

---

## 8. 工具函数

### cn()

**文件**: `utils/cn.ts`

Tailwind class 合并工具，基于 `tailwind-merge`。

```ts
import { cn } from '@/utils/cn'

// 合并多个 class，解决同组属性冲突（如 py-3 py-0 → py-0）
// 后面的 class 优先级更高
cn('px-4 py-2', isActive && 'bg-primary', 'px-4 py-0')
// → "py-0 bg-primary"（如果 isActive 为 true）
```

**签名**:
```ts
function cn(...inputs: (string | undefined | null | false)[]): string
```

---

### riskCls() / getRiskConfig()

**文件**: `utils/riskLevel.ts`

风险等级工具函数集。

**RiskLevel 类型**:
```ts
type RiskLevel = "t4" | "t3" | "t2" | "t1" | "t0" | "unknown";
type VisualKey = "critical" | "high" | "medium" | "low" | "safe" | "unknown";
```

**getRiskConfig(level)** — 获取风险等级完整配置：

```ts
interface RiskLevelConfig {
  visualKey: VisualKey;
  badge: string;           // 风险徽章文案
  icon: string;            // 风险徽章图标名
  subtitleNoProduct: string; // 无产品上下文时 Header 副标题
  needleLeft: string | null; // 谱条指针 left%，null 表示隐藏
}

getRiskConfig('t2')
// → { visualKey: 'medium', badge: '中等风险', icon: 'riskT2', subtitleNoProduct: '⚠ 中等风险 · 适量摄入', needleLeft: '50%' }
```

**riskCls(level, recipe)** — 动态生成风险色 Tailwind class：

```ts
// recipe 中使用 risk 色前缀（bg/10 border 等），自动替换为对应风险色
riskCls('t2', 'bg/10 border')
// → 'bg-risk-t2/10 border-risk-t2'

riskCls('t4', 'bg/30')
// → 'bg-risk-t4/30'

// 支持 variant 前缀
riskCls('t1', 'dark:bg/5 dark:border hover:bg/20')
// → 'dark:bg-risk-t1/5 dark:border-risk-t1 hover:bg-risk-t1/20'
```

**LEVEL → VISUALKEY 映射**:

| Level | VisualKey |
|-------|-----------|
| t4 | critical |
| t3 | high |
| t2 | medium |
| t1 | low |
| t0 | safe |
| unknown | unknown |

**谱条指针位置**:

| VisualKey | needleLeft |
|-----------|------------|
| safe | `8%` |
| low | `22%` |
| medium | `50%` |
| high | `72%` |
| critical | `88%` |
| unknown | `null`（隐藏） |

---

## 9. UniApp 单位换算规范

> UniApp 以 **750rpx** 为设计基准宽度（等同 375px 的物理像素宽度手机）。
> 本设计规范基于 **375px** 宽手机设计稿，因此换算关系为：
>
> **设计稿 1px = UniApp 2rpx**

### 换算表（常用值）

| 设计稿 (px) | UniApp (rpx) | 用途 |
|------------|-------------|------|
| 4 | 8rpx | 最小间距 |
| 8 | 16rpx | 小间距 |
| 10 | 20rpx | 配料卡间距 |
| 12 | 24rpx | 中间距 |
| 14 | 28rpx | 正文字号 |
| 16 | 32rpx | 标准间距 |
| 17 | 34rpx | Header 标题字号 |
| 18 | 36rpx | 卡片内边距 |
| 20 | 40rpx | 章节标题字号 / 水平 padding |
| 24 | 48rpx | 内容区顶部 padding |
| 28 | 56rpx | 卡片下边距 |
| 32 | 64rpx | 营养数值字号 |
| 40 | 80rpx | 内容区底部 padding（非安全区） |
| 260 | 520rpx | Banner 高度 |
| 80 | 160rpx | 占位 Emoji 字号 |
| 140 | 280rpx | 配料卡片最小宽度 |

### 使用规则

1. **所有尺寸、间距、字号使用 `rpx`**，不使用 `px`（`px` 在小程序中是固定像素，不随屏幕缩放）
2. **例外：`border` 宽度用 `1px`**，不用 `2rpx`，避免高清屏上边框过粗
3. **`env(safe-area-inset-bottom)` 保持原样**，这是浏览器/系统变量，不转换
4. **动画 `transform` 中的 `px` 值**（如 `translateY(16px)`）可保留，动画偏移量不影响响应式布局

---

## 10. 无障碍规范

### 必须项
- 所有 icon-only 按钮: `aria-label`
- 装饰性 SVG: `aria-hidden="true"`
- 交互状态按钮: `aria-expanded`（展开类）、`aria-pressed`（切换类）
- `prefers-reduced-motion` 支持

### 触摸优化
```css
* {
  -webkit-tap-highlight-color: rgba(0,0,0,0);
}
body {
  touch-action: manipulation; /* 消除双击缩放延迟 */
}
```

### 焦点管理
- `:focus-visible` 替代 `:focus`（避免点击时出现焦点圈）
- 焦点样式: `outline: 2px solid var(--accent-pink); outline-offset: 2px`

---

## 11. 图标规范

| 用途 | 图标类型 | 样式 |
|------|---------|------|
| 严重/高/中风险 | 警告三角形（filled） | `fill: var(--risk-tN)` |
| 低风险 | 叶子（stroke） | `stroke: var(--risk-t0)` |
| 未知 | 问号圆（filled） | `fill: var(--risk-unknown)` |
| 健康益处 | 绿色对勾圆 | `fill: var(--risk-t0)` |
| AI 建议标题 | 金色星星 | `fill: #f59e0b` |
| 返回 | 左箭头 chevron | `stroke: currentColor` |
| 分享 | 分享图标 | `stroke: currentColor` |
| 展开/收起 | 下/上 chevron | `stroke: currentColor`，旋转动画 |
| 配料卡片导航 | 右箭头 chevron | `stroke: currentColor`，opacity 0.4 |

---

## 12. 暗色 / 亮色切换

```css
html { color-scheme: dark; }
html:has(.light-mode) { color-scheme: light; }
```

初始化：`uni.getSystemInfoSync().theme`
运行时监听：`uni.onThemeChange()` + `onUnmounted` 调用 `uni.offThemeChange()`

---

## 13. Tailwind Safelist

风险色动态 class 的 safelist 配置（`tailwind.config.ts`）：

```ts
safelist: [
  {
    pattern: /^(bg|text|border|shadow|ring|outline|fill|stroke|from|to|via)-risk-(t0|t1|t2|t3|t4|unknown)(\/([0-9]|[1-9][0-9]|100))?$/,
    variants: ['hover', 'active', 'focus', 'dark', 'group-hover', 'group-active'],
  },
],
```

这确保了动态拼接的风险 class（如 `bg-risk-t4/20`）不会被 Tailwind  purge。

---

## 14. 设计文件索引

| 文件 | 版本 | 说明 |
|------|------|------|
| `web/apps/uniapp-tw/src/style.scss` | — | CSS 变量定义（源码） |
| `web/apps/uniapp-tw/tailwind.config.ts` | — | Tailwind 配置（源码） |
| `web/apps/uniapp-tw/src/components/ui/*.vue` | — | UI 组件实现 |
| `web/apps/uniapp-tw/src/utils/cn.ts` | — | class 合并工具 |
| `web/apps/uniapp-tw/src/components/icons/iconsRegistry.ts` | — | 图标注册表 |

---

## 15. 页面结构参考

### 产品详情页

```
┌─────────────────────────────┐
│  status-bar (native)        │
├─────────────────────────────┤
│  header (透明→毛玻璃)        │
│  [←返回] [标题] [分享]       │
├─────────────────────────────┤
│  scroll-area (全屏，z:1)     │
│  ├─ banner (260px)           │
│  │   emoji/图片 + 风险徽章   │
│  └─ content (pad 24 20 40)  │
│      ├─ 章节标题"营养成分"   │
│      ├─ 营养卡片             │
│      ├─ 章节标题"配料信息"   │
│      ├─ IngredientSection   │
│      │   ├─ 严重风险组       │
│      │   ├─ 高风险组         │
│      │   ├─ 低风险组         │
│      │   └─ 未知组           │
│      ├─ 章节标题"健康益处"   │
│      ├─ 健康益处卡           │
│      ├─ 章节标题"食用建议"   │
│      └─ 食用建议卡           │
├─────────────────────────────┤
│  bottom-bar (fixed, z:40)   │
│  [添加到记录] [咨询 AI 助手] │
└─────────────────────────────┘
```

### ingredient-detail 页面

**页面路径：** `pages/ingredient-detail/index.vue`

**信息流：** Identity（Hero 风险卡）→ Risk（AI 风险分析）→ Detail（风险管理信息 + AI 建议）→ Related（含此配料的产品）

**入口与路由参数：**

| 入口 | 路由参数 | Header 副标题 |
|------|----------|--------------|
| 产品详情页配料列表点入 | `ingredientId` + `fromProductName` | "来自：{fromProductName}" |
| 独立搜索 / AI 对话跳转 | `ingredientId` 只 | 按视觉 key 动态渲染 |

**Hero 风险卡结构：**
```
.hero-card
  .hero-top（risk-bg 背景，risk-border 底边）
    成分名称（20px / 800）+ 风险徽章（右对齐）
    风险谱条（8px 高，渐变色 + 指示针）
    谱条标签（低风险 / 中等 / 高风险，10px）
  .chips（10px 12px 内边距）
    功能 chip（function_type，红色）
    来源 chip（灰色中性）
    警告 chip（孕妇禁用等，黄色）
    别名 chips（alias[]，灰色中性）
```

**底部 sticky bar：**
- 与 BottomBar 组件规范相同
- 左按钮：咨询 AI 助手 → `/pages/chat/index?context={name}`
- 右按钮：查看相关食品 → `/pages/search/index?ingredientId={id}`
