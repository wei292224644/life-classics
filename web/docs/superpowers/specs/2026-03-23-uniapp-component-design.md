# UniApp 组件化与 Design System 规范

> 本规范定义 UniApp H5/小程序端的组件化方向与 CSS 变量使用准则。
> 所有数值必须通过 CSS 变量引用，禁止在组件中硬编码。

---

## 一、核心原则

### 1.1 CSS 变量优先

**所有数值必须定义为 CSS 变量，组件中禁止硬编码。**

| 类型 | 示例 | 正确用法 |
|------|------|---------|
| 间距 | `32rpx` | `var(--space-8)` |
| 字体 | `28rpx` | `var(--text-xl)` |
| 圆角 | `40rpx` | `var(--radius-lg)` |
| 图标 | `36rpx` | `var(--icon-lg)` |
| 卡片内边距 | `32rpx` | `var(--card-padding-xl)` |
| 按钮高度 | `88rpx` | `var(--btn-height-xl)` |

**唯一例外**：非设计标的的精确数值（如 scroll-view 固定高度 520rpx）除外。

### 1.2 Color Token 分层（shadcn/ui 风格）

```
PALETTE（调色板）→ 固定纯色值，两模式共用
    ↓ 引用
SEMANTIC（语义色）→ 引用调色板，两模式值不同
    ↓ 引用
COMPONENT（组件色）→ 引用语义色 + color-mix 透明混合
```

**示例**：

```scss
// PALETTE — 固定值，两个模式共用同一套
--palette-red-500: #dc2626;

// SEMANTIC — 引用调色板，亮/暗模式值不同
// 亮: --risk-t4: var(--palette-red-500) → #dc2626
// 暗: --risk-t4: var(--palette-red-400) → #f87171

// COMPONENT — 引用语义色，color-mix 混合透明
--risktag-t4-bg: color-mix(in oklch, var(--risk-t4) 15%, transparent);
// 亮: color-mix(in oklch, #dc2626 15%, transparent)
// 暗: color-mix(in oklch, #f87171 15%, transparent)
```

**规则**：
- Palette 色值**永远不直接在组件中使用**
- 组件色必须通过 `color-mix(in oklch, var(--semantic-color) xx%, transparent)` 生成
- 组件中**禁止出现 `#dc2626` / `#f87171` 等硬编码颜色**

---

## 二、Spacing System（间距系统）

基于 **4px 网格**，所有间距取偶数值：

| Token | Value | 用途 |
|-------|-------|------|
| `--space-1` | `4rpx` | 微间距 |
| `--space-2` | `8rpx` | 紧凑间距 |
| `--space-3` | `12rpx` | 小间距 |
| `--space-4` | `16rpx` | 默认间距 |
| `--space-5` | `20rpx` | 中等间距 |
| `--space-6` | `24rpx` | 区块内间距 |
| `--space-7` | `28rpx` | 区块间距 |
| `--space-8` | `32rpx` | 大区块间距 |
| `--space-10` | `40rpx` | 极大间距 |
| `--space-12` | `48rpx` | 页面级间距 |
| `--space-16` | `64rpx` | 页面级间距 |
| `--space-20` | `80rpx` | 页面顶部间距 |

**Flex Gap 规范**：

| 场景 | Gap 值 |
|------|--------|
| 卡片内元素 | `--space-4` |
| 列表项之间 | `--space-5` |
| 横向滚动项 | `--space-5` |
| 按钮组 | `--space-6` |
| 大区块之间 | `--space-8` |

---

## 三、Typography（字体系统）

| Token | Value | 用途 |
|-------|-------|------|
| `--text-xs` | `18rpx` | 辅助说明 |
| `--text-sm` | `20rpx` | 小标签 |
| `--text-base` | `22rpx` | 基础标签 |
| `--text-md` | `24rpx` | 标签/副标题 |
| `--text-lg` | `26rpx` | 正文/配料名 |
| `--text-xl` | `28rpx` | 正文/描述 |
| `--text-2xl` | `30rpx` | 页面标题 |
| `--text-3xl` | `34rpx` | 大标题 |
| `--text-4xl` | `36rpx` | 极大标题 |
| `--text-5xl` | `40rpx` | 区块标题 |
| `--text-6xl` | `52rpx` | Hero 标题 |

---

## 四、Radius System（圆角系统）

| Token | Value | 用途 |
|-------|-------|------|
| `--radius-sm` | `24rpx` | 小按钮/小标签 |
| `--radius-md` | `32rpx` | 卡片/容器 |
| `--radius-lg` | `40rpx` | 大卡片 |
| `--radius-xl` | `48rpx` | 页面级卡片 |
| `--radius-full` | `9999rpx` | 药丸形标签 |

---

## 五、组件设计

### 5.1 RiskTag — 风险标签

统一风险等级徽章，替代现有 4 处散落实现。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `level` | `RiskLevel` | 必填 | `t0 \| t1 \| t2 \| t3 \| t4 \| unknown` |
| `size` | `'sm' \| 'md'` | `'md'` | 尺寸变体 |

**样式规则**：

```scss
// 颜色通过 CSS 变量按等级引用
// 亮/暗模式由 --risktag-t4-bg / --risktag-t4-text 等变量自动切换

.risk-tag {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;

  &.level-t4 { background: var(--risktag-t4-bg); color: var(--risktag-t4-text); }
  &.level-t3 { background: var(--risktag-t3-bg); color: var(--risktag-t3-text); }
  &.level-t2 { background: var(--risktag-t2-bg); color: var(--risktag-t2-text); }
  &.level-t1 { background: var(--risktag-t1-bg); color: var(--risktag-t1-text); }
  &.level-t0 { background: var(--risktag-t0-bg); color: var(--risktag-t0-text); }
  &.level-unknown { background: var(--risktag-unknown-bg); color: var(--risktag-unknown-text); }
}
```

**使用 `getRiskConfig(level)` 获取 badge 文案和图标**。

---

### 5.2 ActionButton — 按钮

统一按钮样式，覆盖 primary / secondary / ghost 三种变体。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `variant` | `'primary' \| 'secondary' \| 'ghost'` | `'primary'` | 变体 |
| `size` | `'md' \| 'lg'` | `'lg'` | 尺寸 |
| `icon` | `string` | `undefined` | SVG icon path（可选） |
| `loading` | `boolean` | `false` | 加载态 |

**样式规则**：

```scss
.action-btn {
  height: var(--btn-height-lg);
  padding: 0 var(--btn-padding-x);
  border-radius: var(--btn-radius);
  font-size: var(--text-xl);
  font-weight: 600;
  transition: all 0.2s $ease-spring;

  &--primary {
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    color: #fff;
    box-shadow: 0 4rpx 20rpx rgba(236, 72, 153, 0.3);
  }

  &--secondary {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
  }

  &--ghost {
    background: transparent;
    color: var(--text-primary);
  }
}
```

---

### 5.3 HorizontalScroller — 横向滚动容器

封装 clip + scroll-view + gap 逻辑。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `gap` | `number` | `20` | 滚动项间距（rpx） |
| `itemWidth` | `number` | `undefined` | 固定项宽度（可选） |

**样式规则**：

```scss
.horizontal-scroller {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar { display: none; }
}

.horizontal-scroller-inner {
  display: flex;
  flex-direction: row;
  gap: var(--space-5); // 20rpx
  width: max-content;
  padding-bottom: var(--space-2);
}
```

---

### 5.4 StateView — 状态视图

统一 loading / error / empty 三种状态。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `state` | `'loading' \| 'error' \| 'empty'` | 必填 | 状态类型 |
| `message` | `string` | 见默认 | 显示文案 |
| `actionLabel` | `string` | `undefined` | 显示重试/返回按钮 |

---

### 5.5 SectionHeader — 区块头部

统一 icon + title + AI badge 的组合。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `icon` | `'blue' \| 'red' \| 'purple' \| 'green' \| 'orange'` | 必填 | 图标颜色主题 |
| `title` | `string` | 必填 | 标题文案 |
| `showAiBadge` | `boolean` | `false` | 是否显示 AI 标签 |

**样式规则**：

```scss
.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-color);
}

.section-icon-wrap {
  width: var(--icon-lg);
  height: var(--icon-lg);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;

  // 图标颜色引用 palette + color-mix，组件中禁止写死 rgba
  &.icon-bg-blue { background: color-mix(in oklch, var(--palette-blue-500) 12%, transparent); }
  &.icon-bg-red { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); }
  &.icon-bg-purple { background: color-mix(in oklch, var(--palette-purple-500) 12%, transparent); }
  &.icon-bg-green { background: color-mix(in oklch, var(--palette-green-500) 12%, transparent); }
  &.icon-bg-orange { background: color-mix(in oklch, var(--risk-t3) 12%, transparent); }
}

.section-icon {
  width: var(--icon-sm);
  height: var(--icon-sm);
  fill: currentColor;
}

.ai-label {
  font-size: var(--text-xs);
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--ai-label-bg);
  color: #fff;
}
```

---

### 5.6 InfoChip — 信息小标签

统一风险/警告/中性三种 chip。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `variant` | `'risk' \| 'warn' \| 'neutral'` | 必填 | 变体 |
| `text` | `string` | 必填 | 标签文案 |

**样式规则**：

```scss
.info-chip {
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-sm);
  font-weight: 500;

  &.chip-risk {
    color: var(--chip-risk-text);
    background: var(--chip-risk-bg);
    border: 1px solid var(--chip-risk-border);
  }

  &.chip-warn {
    color: var(--chip-warn-text);
    background: var(--chip-warn-bg);
    border: 1px solid var(--chip-warn-border);
  }

  &.chip-neutral {
    color: var(--chip-neu-text);
    background: var(--chip-neu-bg);
  }
}
```

---

### 5.7 ListItem — 列表项

统一带图标 + 文案的列表项。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `icon` | `'x' \| 'check-green' \| 'check-yellow'` | 必填 | 图标类型 |
| `text` | `string` | 必填 | 列表文案 |

**样式规则**：

```scss
.list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.list-item-icon {
  width: var(--icon-lg);
  height: var(--icon-lg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 700;
  flex-shrink: 0;
  margin-top: var(--space-1);

  // 禁止硬编码 rgba，统一用 color-mix 引用语义色
  &.icon-x { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); color: var(--risk-t4); }
  &.icon-check-green { background: color-mix(in oklch, var(--risk-t0) 12%, transparent); color: var(--risk-t0); }
  &.icon-check-yellow { background: color-mix(in oklch, var(--risk-t2) 12%, transparent); color: var(--risk-t2); }
}

.list-item-text {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  line-height: 1.6;
  flex: 1;
}
```

---

### 5.8 InfoCard — 通用卡片容器

统一卡片背景/边框/圆角/内边距。

**Props**：

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `padding` | `string` | `'xl'` | 内边距级别 |
| `radius` | `'lg' \| 'xl'` | `'lg'` | 圆角级别 |

**样式规则**：

```scss
.info-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: var(--card-padding-xl);
  border: 1px solid var(--border-color);
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;

  // 可选：顶部渐变装饰线
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-color, transparent), transparent);
  }
}
```

---

## 六、迁移检查清单

组件抽取时，**必须确保**：

- [ ] 所有 `xxrpx` 数值替换为 CSS 变量
- [ ] 引用 `riskLevel.ts` 的 `getRiskConfig()` 获取风险配置
- [ ] 暗色模式通过 CSS 变量自动切换，无需 media query
- [ ] 组件导入 `@/styles/design-system.scss`

**CSS 变量速查表**：

```scss
// ── Palette（固定纯色，不直接在组件中使用）─────────────
var(--palette-gray-50 ~ --palette-gray-900)
var(--palette-red-50 ~ --palette-red-900)
var(--palette-orange-50 ~ --palette-orange-900)
var(--palette-yellow-50 ~ --palette-yellow-900)
var(--palette-green-50 ~ --palette-green-900)
var(--palette-purple-50/100/300/400/500/600/700/800)
var(--palette-blue-50/100/300/400/500/600)
var(--palette-pink-300/400/500/600)

// ── Semantic（引用 Palette，两个模式值不同）────────────
var(--text-primary/secondary/muted)
var(--border-color)
var(--bg-base/card/card-hover)
var(--accent/accent-light)
var(--risk-t0/t1/t2/t3/t4/unknown)

// ── Component（引用 Semantic，用 color-mix 混合）────────
var(--risk-t0-bg/border ~ --risk-t4-bg/border)
var(--risktag-t0-bg/t0-text ~ --risktag-t4-bg/t4-text)
var(--chip-risk-bg/text/border)
var(--chip-warn-bg/text/border)
var(--chip-neu-bg/text)
var(--ai-label-bg)
var(--header-scrolled-bg/text)
var(--bottom-bar-bg/border)
var(--nutrition-bg/border)

// ── Layout / Typography ─────────────────────────────────
var(--space-1 ~ --space-20)
var(--text-xs ~ --text-6xl)
var(--radius-sm/md/lg/xl/full)
var(--icon-xs/sm/md/lg/xl)
var(--card-padding-sm/md/lg/xl/2xl/3xl)
var(--btn-height-sm/md/lg/xl)
var(--btn-padding-x)
var(--btn-radius)
var(--header-btn-size/icon-size/padding-x/padding-y)
var(--shadow-sm/md/lg)
```

---

## 七、文件结构

```
web/apps/uniapp/src/
├── components/
│   ├── RiskTag.vue          # 新增
│   ├── ActionButton.vue     # 新增
│   ├── HorizontalScroller.vue  # 新增
│   ├── StateView.vue        # 新增
│   ├── SectionHeader.vue    # 新增
│   ├── InfoChip.vue         # 新增
│   ├── ListItem.vue         # 新增
│   └── InfoCard.vue         # 新增
└── styles/
    └── design-system.scss   # 已完善
```
