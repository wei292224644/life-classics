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
- **字号梯度**:
  - 页面标题: 20px / 700 / letter-spacing: -0.02em
  - 卡片标题: 17px / 600 / letter-spacing: -0.02em
  - 正文: 14px / 400
  - 标签/单位: 11px / 500 / uppercase / letter-spacing: 0.08em
- **数字**: 营养数值使用 `font-variant-numeric: tabular-nums` 保证对齐

---

## 4. 间距系统

基于 4px 网格:
- `4px` — 紧凑间距（图标与文字间隙）
- `8px` — 小间距（标签内元素）
- `12px` — 中间距（按钮内 padding）
- `16px` — 标准间距（卡片 padding、section gap）
- `20px` — 大间距（section 间）
- `24px` — 容器内大间距
- `28px` — 卡片间大间距

圆角:
- 按钮/小卡片: 12px
- 中卡片: 16px
- 大卡片/风险组: 20px
- 营养卡片: 24px
- 手机框架: 44px

---

## 5. 阴影系统

### 暗色模式
```css
/* 手机框架 */
box-shadow: 0 0 0 1px rgba(255,255,255,0.06), 0 40px 80px rgba(0,0,0,0.6);

/* 滚动后 header */
box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.06);

/* 底部栏 */
box-shadow: 0 -8px 32px rgba(0,0,0,0.4);

/* 主按钮 */
box-shadow: 0 4px 20px rgba(236,72,153,0.3);
```

### 亮色模式
```css
/* 手机框架 */
box-shadow: 0 0 0 1px rgba(0,0,0,0.06), 0 40px 80px rgba(0,0,0,0.12);

/* 滚动后 header */
box-shadow: 0 4px 24px rgba(0,0,0,0.08), 0 1px 0 rgba(0,0,0,0.04);

/* 底部栏 */
box-shadow: 0 -8px 32px rgba(0,0,0,0.06);

/* 白色卡片 */
box-shadow: 0 2px 8px rgba(0,0,0,0.04);
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
  to { opacity: 1; transform: translateY(0); }
}
/* 使用：animation: slideUp 0.5s 0.1s cubic-bezier(0.34, 1.56, 0.64, 1) forwards */

/* Banner emoji：floatIn */
@keyframes floatIn {
  to { opacity: 1; transform: scale(1); }
}
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
- 暗色: `background: rgba(255,255,255,0.06)` + `border: 1px solid rgba(255,255,255,0.1)`
- 亮色: `background: rgba(0,0,0,0.04)` + `border: 1px solid rgba(0,0,0,0.08)`
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
    .risk-dot (8px 圆点 + box-shadow glow)
    .risk-badge (文字 + 半透明背景)
    .risk-count ("N 项")
  .ingredient-scroll (横向滚动容器)
    .ingredient-card (每个配料)
```

**背景色规则（暗色）:**
```css
.t4: background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.15);
.t3: background: rgba(249,115,22,0.08); border: 1px solid rgba(249,115,22,0.15);
.t2: background: rgba(234,179,8,0.08);  border: 1px solid rgba(234,179,8,0.15);
.t0: background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.15);
unknown: background: rgba(156,163,175,0.08); border: 1px solid rgba(156,163,175,0.15);
```

**配料卡片左侧风险条:**
- 宽度: 3px
- 暗色模式加 `box-shadow: 0 0 8px var(--risk-tN)` glow 效果
- 亮色模式不加 glow（颜色本身够用）

### 7.3 营养卡片

- 24px 圆角
- 顶部 1px 发光分隔线（暗色用 `var(--nutrition-glow)`）
- 2 列网格布局（卡路里、蛋白质、脂肪、碳水）
- 数值: 32px / 700 / `letter-spacing: -0.03em`
- 展开按钮: `aria-expanded` + `aria-controls` 配套使用

### 7.4 Header（导航栏）

- 透明背景，滚动后 `backdrop-filter: blur(16px) saturate(180%)`
- 高度 44px（iOS 标准，含 status bar）
- 按钮 40px 触摸区域
- 滚动状态: `.header.scrolled` class 切换

### 7.5 Bottom Bar（底部操作栏）

- 固定底部，`z-index: 40`
- 高度 88px（含 safe-area）
- 毛玻璃效果: `backdrop-filter: blur(16px) saturate(180%)`
- 两按钮水平排列，gap 12px

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
  /* 透明去除点击高亮，保留语义 */
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
  <!-- Google Fonts: DM Sans -->
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap" rel="stylesheet">
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
│  status-bar (44px)          │
├─────────────────────────────┤
│  header (透明→毛玻璃)        │
│  [←返回] [标题] [分享]       │
├─────────────────────────────┤
│  banner (260px, 产品图/Emoji) │
│         [低风险徽章]         │
├─────────────────────────────┤
│  scroll-area                │
│  ├─ 营养成分 (2×2网格+展开)   │
│  ├─ 配料信息                 │
│  │  ├─ 严重风险组            │
│  │  ├─ 高风险组              │
│  │  ├─ 低风险组 ← 叶子图标    │
│  │  └─ 未知组                │
│  ├─ 健康益处                 │
│  └─ AI 建议                  │
├─────────────────────────────┤
│  bottom-bar (88px, 毛玻璃)   │
│  [添加到记录] [咨询 AI 助手]   │
└─────────────────────────────┘
```

---

## 11. 图标规范

| 用途 | 图标类型 | 备注 |
|------|---------|------|
| 严重/高/中风险 | 警告三角形 `fill` | `fill: var(--risk-tN)` |
| 低风险 | 叶子 `stroke` | `stroke: var(--risk-t0)` |
| 未知 | 问号圆 `fill` | `fill: var(--risk-unknown)` |
| 健康益处 | 绿色对勾 | `fill: var(--risk-t0)` |
| AI 建议 | 金色星星 | `fill: #f59e0b` |
| 返回/分享 | 箭头/网格 | `stroke: currentColor` |
| 展开箭头 | chevron | `stroke` |

---

## 12. 设计文件索引

| 文件 | 版本 | 说明 |
|------|------|------|
| `product-detail-v14.html` | v14 | 最终版，含暗色/亮色双模式 |

> 历史版本 (v1–v13) 存于 `.superpowers/brainstorm/23968-1774164668/`
