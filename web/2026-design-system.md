# 产品设计规范 — 2026 Design System

> 本规范基于 product-detail 页面设计总结提炼，适用于 life-classics 全栈应用（UniApp / Console / Web）。
> 所有新增页面和组件须遵循此规范。

---

## 1. 设计原则

1. **功能优先** — 每个视觉决策都服务功能，无纯装饰
2. **一致性** — 全 app 共用同一设计语言，克制个性化表达
3. **可访问** — WCAG 2.1 AA 为最低标准
4. **性能友好** — 动画仅用 `transform` / `opacity`，尊重 `prefers-reduced-motion`

---

## 2. 色彩系统

### 2.1 风险等级色板

| 风险等级 | CSS 变量 (暗) | CSS 变量 (亮) | 语义 |
|---------|--------------|--------------|------|
| 严重 (t4) | `--risk-t4: #ef4444` | `--risk-t4: #dc2626` | 严重风险 |
| 高风险 (t3) | `--risk-t3: #f97316` | `--risk-t3: #ea580c` | 高风险 |
| 中风险 (t2) | `--risk-t2: #eab308` | `--risk-t2: #ca8a04` | 中风险 |
| 低风险 (t0) | `--risk-t0: #22c55e` | `--risk-t0: #16a34a` | 低风险 |
| 未知 (unknown) | `--risk-unknown: #9ca3af` | `--risk-unknown: #9ca3af` | 未检测 |

### 2.2 主题变量

```css
/* 暗色模式 */
--bg-base: #0f0f0f;
--bg-card: #1a1a1a;
--bg-card-hover: #222;
--text-primary: #f5f5f5;
--text-secondary: #a1a1a1;
--text-muted: #6b7280;
--border-color: rgba(255,255,255,0.08);

/* 亮色模式 */
--bg-base: #f5f5f5;
--bg-card: #ffffff;
--bg-card-hover: #f9fafb;
--text-primary: #111;
--text-secondary: #4b5563;
--text-muted: #9ca3af;
--border-color: rgba(0,0,0,0.06);
```

### 2.3 强调色

```css
/* 暗色模式 */
--accent-pink: #ec4899;
--accent-pink-light: #f472b6;

/* 亮色模式 */
--accent-pink: #db2777;
--accent-pink-light: #ec4899;
```

### 2.4 暗色 / 亮色切换

```css
html { color-scheme: dark; }
html:has(.light-mode) { color-scheme: light; }
```

---

## 3. 字体系统

- **主字体**: DM Sans (Google Fonts)，回退 `-apple-system, sans-serif`
- **字号梯度**（设计稿 px，UniApp 对应 rpx 见第 13 节）:
  - 章节标题: 20px / 700 / `letter-spacing: -0.02em`
  - Header 标题: 17px / 600 / `letter-spacing: -0.02em`
  - 配料卡片名称: 13px / 600
  - 正文: 14px / 400 / `line-height: 1.5`
  - 小标签 / 风险徽章: 12px / 600
  - 营养标签 / 单位: 11px / 500 / `uppercase` / `letter-spacing: 0.08em`
  - 营养数值: 32px / 700 / `letter-spacing: -0.03em` / `font-variant-numeric: tabular-nums`

---

## 4. 间距系统

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

圆角：

| 用途 | 设计稿值 |
|------|---------|
| 小按钮 / 图标按钮 | 12px |
| 风险徽章 / 原因标签 | 6–8px |
| 配料卡片 | 16px |
| 风险分组 / 健康卡片 | 20px |
| 营养卡片 | 24px |
| Banner 风险徽章 | 14px |

---

## 5. 阴影系统

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

## 6. 动画规范

### 入场动画原则
- 使用 `transform` + `opacity` 组合（GPU 加速）
- 曲线: `cubic-bezier(0.34, 1.56, 0.64, 1)`（弹入感）
- 避免 `transition: all`

### 标准动画
```css
/* 卡片入场：slideUp */
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
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
```

### 尊重运动偏好
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. 组件规范

### 7.1 按钮

**主按钮 (primary)**
- 背景: 渐变 `linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink))`
- 文字: 白色
- 圆角: 14px
- 内边距: 14px 16px
- 字号: 14px / 600
- Hover: `box-shadow` 增强 + `translateY(-1px)`
- Active: `transform: scale(0.97)`

**次按钮 (secondary)**
- 暗色: `background: rgba(255,255,255,0.06)` + `border: 1px solid rgba(255,255,255,0.1)` + `color: var(--text-primary)`
- 亮色: `background: rgba(0,0,0,0.04)` + `border: 1px solid rgba(0,0,0,0.08)` + `color: #111`
- Hover: 背景加深

**所有按钮必须:**
- 设置 `type="button"`（防默认提交行为）
- 有 `:focus-visible` 样式: `outline: 2px solid var(--accent-pink); outline-offset: 2px`
- icon-only 按钮加 `aria-label`

### 7.2 风险分组卡片

**结构:**
```
.risk-group (t4|t3|t2|t0|unknown)
  .risk-header
    .risk-dot (8px 圆点 + box-shadow glow，暗色专用)
    .risk-badge (文字 + 半透明背景)
    .risk-count ("N 项"，margin-left: auto)
  .ingredient-scroll (横向滚动容器，scroll-snap-type: x mandatory)
    .ingredient-card (每个配料，min-width: 140px)
```

**风险分组背景色（暗色）:**
```css
.t4: background: rgba(239,68,68,0.08);   border: 1px solid rgba(239,68,68,0.15);
.t3: background: rgba(249,115,22,0.08);  border: 1px solid rgba(249,115,22,0.15);
.t2: background: rgba(234,179,8,0.08);   border: 1px solid rgba(234,179,8,0.15);
.t0: background: rgba(34,197,94,0.08);   border: 1px solid rgba(34,197,94,0.15);
unknown: background: rgba(156,163,175,0.08); border: 1px solid rgba(156,163,175,0.15);
```

**风险分组背景色（亮色）:**
```css
.t4: background: rgba(254,226,226);    border: 1px solid rgba(252,165,165,0.3);
.t3: background: rgba(254,235,200);    border: 1px solid rgba(252,196,110,0.4);
.t2: background: rgba(254,249,195);    border: 1px solid rgba(250,240,137,0.4);
.t0: background: rgba(220,252,231);    border: 1px solid rgba(187,247,208,0.5);
unknown: background: rgba(229,231,235); border: 1px solid rgba(209,213,219,0.5);
```

**配料卡片左侧风险条:**
- 宽度: 3px（`position: absolute; left:0; top:0; bottom:0`）
- 暗色加 `box-shadow: 0 0 8px var(--risk-tN)` glow
- 亮色不加 glow

**配料卡片右上角装饰圆（伪元素）:**
- `position: absolute; top: -15px; right: -15px; width: 50px; height: 50px; border-radius: 50%; opacity: 0.1`
- 颜色为对应风险色

### 7.3 营养卡片

- 圆角: 24px
- 顶部 1px 发光线: `background: linear-gradient(90deg, transparent, var(--nutrition-glow), transparent)`
- 2 列网格，gap: 20px，显示卡路里 / 蛋白质 / 脂肪 / 碳水
- 数值: 32px / 700 / `letter-spacing: -0.03em` / `font-variant-numeric: tabular-nums`
- 展开按钮: `aria-expanded` + `aria-controls`，chevron 旋转 180° 表示展开

### 7.4 健康益处 / 食用建议卡片

**暗色:**
```css
background: rgba(255,255,255,0.02);
border: 1px solid rgba(255,255,255,0.06);
```

**亮色:**
```css
background: #ffffff;
border: 1px solid rgba(0,0,0,0.06);
box-shadow: 0 2px 8px rgba(0,0,0,0.04);
```

- 章节标题（"健康益处" / "食用建议"）位于卡片**外部**，由页面统一管理
- 食用建议卡有内部小标题行（星星图标 + "AI 健康建议"）
- 列表行: 图标左对齐 + 文字 `line-height: 1.5`

### 7.5 Header（导航栏）

- `position: fixed`，`top: statusBarHeight`，`z-index: 50`
- 初始: `background: transparent`
- 滚动后（scrollTop > 60）: `background: var(--header-scrolled-bg)` + `backdrop-filter: saturate(180%) blur(16px)`
- 暗色 scrolled shadow: `0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.06)`
- 亮色 scrolled shadow: `0 4px 24px rgba(0,0,0,0.08), 0 1px 0 rgba(0,0,0,0.04)`
- 图标颜色: 未滚动时白色（含 text-shadow 增强可读性），滚动后 `var(--text-primary)`
- 图标按钮触摸区 40×40px，`border-radius: 12px`

### 7.6 Banner

- 高度: 260px（设计稿）
- 暗色背景: `linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%)`
- 亮色背景: `linear-gradient(145deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%)`
- 有产品图时: `image` 全覆盖，`mode="aspectFill"`
- 无图时: emoji（80px）+ 副标题"产品图片"（居中，vertically centered）
- 右下角风险徽章: `position: absolute; right: 20px; bottom: 20px`，带 slideUpBadge 入场动画

### 7.7 Bottom Bar（底部操作栏）

- `position: fixed`，`bottom: 0`，`z-index: 40`
- `padding: 16px 20px`，`padding-bottom: calc(16px + env(safe-area-inset-bottom))`
- 毛玻璃: `backdrop-filter: saturate(180%) blur(16px)`
- 暗色: `background: rgba(15,15,15,0.95)`，`border-top: 1px solid rgba(255,255,255,0.06)`
- 亮色: `background: rgba(255,255,255,0.95)`，`border-top: 1px solid rgba(0,0,0,0.06)`
- 两按钮各占 `flex: 1`，`gap: 12px`

---

## 8. 无障碍规范

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

## 9. HTML 模板规范

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#0f0f0f">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <!-- 暗色 / 亮色模式容器 -->
</body>
</html>
```

---

## 10. 产品详情页结构（参考实现）

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

**产品详情页组件划分（UniApp）：**

| 文件 | 职责 |
|------|------|
| `pages/product/index.vue` | 页面入口：数据加载、滚动监听、banner、营养成分、健康/建议卡 |
| `components/ProductHeader.vue` | 固定顶部导航，滚动透明度切换 |
| `components/IngredientSection.vue` | 配料区：风险分组 + 横向滚动配料卡片 |
| `components/BottomBar.vue` | 固定底部操作栏 |

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

## 12. UniApp 单位换算规范

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

### SCSS 变量对应

`design-system.scss` 中已有 rpx 变量，使用时优先引用：

```scss
$radius-sm: 24rpx;   // 12px
$radius-md: 32rpx;   // 16px
$radius-lg: 40rpx;   // 20px
$radius-xl: 48rpx;   // 24px
$ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

---

## 13. 设计文件索引

| 文件 | 版本 | 说明 |
|------|------|------|
| `product-detail-v14.html` | v14 | 最终版，含暗色/亮色双模式，位于 `.superpowers/brainstorm/23968-1774164668/` |

> 历史版本 (v1–v13) 存于同一目录下
