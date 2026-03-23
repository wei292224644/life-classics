# UniApp 组件化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 8 个通用组件（RiskTag、ActionButton、HorizontalScroller、StateView、SectionHeader、InfoChip、ListItem、InfoCard），并将现有页面的硬编码样式迁移至 CSS 变量。

**Architecture:**
- 所有组件放在 `web/apps/uniapp/src/components/` 下
- 每个组件独立，样式全部引用 `design-system.scss` 中的 CSS 变量
- 颜色遵循 Palette → Semantic → Component 三层架构，禁止硬编码
- 迁移时保持现有功能不变，只改样式引用方式

**Tech Stack:** Vue 3 Composition API + UniApp + SCSS

---

## 文件结构

```
web/apps/uniapp/src/
├── components/
│   ├── RiskTag.vue              # 新增：统一风险标签
│   ├── ActionButton.vue         # 新增：统一按钮
│   ├── HorizontalScroller.vue   # 新增：横向滚动容器
│   ├── StateView.vue            # 新增：loading/error/empty 状态
│   ├── SectionHeader.vue        # 新增：icon + title + AI badge
│   ├── InfoChip.vue             # 新增：信息小标签
│   ├── ListItem.vue             # 新增：列表项
│   ├── InfoCard.vue             # 新增：通用卡片容器
│   ├── BottomBar.vue            # 修改：迁移至 ActionButton + CSS 变量
│   ├── IngredientSection.vue    # 修改：迁移至 HorizontalScroller + CSS 变量
│   ├── AnalysisCard.vue         # 修改：迁移至 InfoCard + RiskTag + ListItem
│   ├── IngredientList.vue       # 修改：RiskBadge → RiskTag
│   └── RiskBadge.vue           # 删除：由 RiskTag 替代
└── pages/
    ├── product/index.vue         # 修改：CSS 变量迁移
    └── ingredient-detail/index.vue  # 修改：CSS 变量迁移
```

---

## Part 1：创建基础组件

### Task 1: RiskTag — 风险标签

**Files:**
- Create: `web/apps/uniapp/src/components/RiskTag.vue`

- [ ] **Step 1: 创建 RiskTag.vue**

```vue
<template>
  <view :class="['risk-tag', `level-${level}`, size === 'sm' && 'risk-tag--sm']">
    <text>{{ config.badge }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { getRiskConfig } from "../utils/riskLevel";
import type { RiskLevel } from "../utils/riskLevel";

const props = withDefaults(
  defineProps<{
    level: RiskLevel;
    size?: "sm" | "md";
  }>(),
  { size: "md" }
);

const config = computed(() => getRiskConfig(props.level));
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.risk-tag {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;

  &--sm {
    font-size: var(--text-xs);
    padding: var(--space-1) var(--space-3);
  }

  // 颜色引用 CSS 变量，亮/暗模式自动切换
  &.level-t4 { background: var(--risktag-t4-bg); color: var(--risktag-t4-text); }
  &.level-t3 { background: var(--risktag-t3-bg); color: var(--risktag-t3-text); }
  &.level-t2 { background: var(--risktag-t2-bg); color: var(--risktag-t2-text); }
  &.level-t1 { background: var(--risktag-t1-bg); color: var(--risktag-t1-text); }
  &.level-t0 { background: var(--risktag-t0-bg); color: var(--risktag-t0-text); }
  &.level-unknown { background: var(--risktag-unknown-bg); color: var(--risktag-unknown-text); }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/RiskTag.vue
git commit -m "feat(uniapp): add RiskTag component

- Props: level (t0-t4|unknown), size (sm|md)
- Uses getRiskConfig() for badge text
- All colors reference CSS vars, auto dark mode
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: ActionButton — 按钮

**Files:**
- Create: `web/apps/uniapp/src/components/ActionButton.vue`

- [ ] **Step 1: 创建 ActionButton.vue**

```vue
<template>
  <button
    :class="['action-btn', `action-btn--${variant}`, `action-btn--${size}`]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <up-loading-icon v-if="loading" class="action-btn__loading" />
    <svg v-else-if="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="action-btn__icon" aria-hidden="true">
      <path :d="icon" />
    </svg>
    <text>{{ label }}</text>
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string;
    variant?: "primary" | "secondary" | "ghost";
    size?: "md" | "lg";
    disabled?: boolean;
    loading?: boolean;
    icon?: string; // SVG path, optional
  }>(),
  { variant: "primary", size: "lg", disabled: false, loading: false, icon: undefined }
);

defineEmits<{ (e: "click"): void }>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  border: none;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s $ease-spring;

  // size
  &--lg {
    height: var(--btn-height-lg);
    padding: 0 var(--btn-padding-x);
    font-size: var(--text-xl);
    border-radius: var(--btn-radius);
  }
  &--md {
    height: var(--btn-height-md);
    padding: 0 var(--space-6);
    font-size: var(--text-lg);
    border-radius: var(--radius-md);
  }

  // primary
  &--primary {
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    color: #fff;
    box-shadow: 0 4rpx 20rpx color-mix(in oklch, var(--accent-pink) 30%, transparent);

    &:active { transform: scale(0.97); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  }

  // secondary
  &--secondary {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);

    &:active { background: var(--bg-card-hover); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  // ghost
  &--ghost {
    background: transparent;
    color: var(--text-primary);

    &:active { background: color-mix(in oklch, var(--text-primary) 8%, transparent); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  &__loading {
    width: var(--icon-sm);
    height: var(--icon-sm);
  }

  &__icon {
    width: var(--icon-sm);
    height: var(--icon-sm);
    stroke-width: 2;
  }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/ActionButton.vue
git commit -m "feat(uniapp): add ActionButton component

- Props: label, variant (primary|secondary|ghost), size (md|lg), disabled, loading
- All colors reference CSS vars, dark mode auto
- Gradient shadow uses color-mix
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: HorizontalScroller — 横向滚动容器

**Files:**
- Create: `web/apps/uniapp/src/components/HorizontalScroller.vue`

- [ ] **Step 1: 创建 HorizontalScroller.vue**

```vue
<template>
  <scroll-view scroll-x class="horizontal-scroller" :enhanced="true">
    <view class="horizontal-scroller-inner" :style="{ gap: `${gap}rpx` }">
      <slot />
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    gap?: number;
  }>(),
  { gap: 20 }
);
</script>

<style lang="scss" scoped>
.horizontal-scroller {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar { display: none; }
}

.horizontal-scroller-inner {
  display: flex;
  flex-direction: row;
  width: max-content;
  padding-bottom: var(--space-2);
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/HorizontalScroller.vue
git commit -m "feat(uniapp): add HorizontalScroller component

- Props: gap (default 20rpx)
- Encapsulates UniApp scroll-view clip hack + hide scrollbar
- Exposes default slot
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: StateView — 状态视图

**Files:**
- Create: `web/apps/uniapp/src/components/StateView.vue`

- [ ] **Step 1: 创建 StateView.vue**

```vue
<template>
  <view :class="['state-view', `state-view--${state}`]">
    <template v-if="state === 'loading'">
      <up-loading-icon mode="circle" />
      <text class="state-view__message">{{ message || "加载中..." }}</text>
    </template>
    <template v-else-if="state === 'empty'">
      <text class="state-view__message">{{ message || "暂无数据" }}</text>
    </template>
    <template v-else-if="state === 'error'">
      <text class="state-view__message">{{ message || "请求失败" }}</text>
      <button
        v-if="actionLabel"
        class="state-view__action"
        @click="$emit('retry')"
      >
        {{ actionLabel }}
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    state: "loading" | "error" | "empty";
    message?: string;
    actionLabel?: string;
  }>(),
  { message: undefined, actionLabel: undefined }
);

defineEmits<{ (e: "retry"): void }>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);

  &__message {
    font-size: var(--text-lg);
    color: var(--text-muted);
    text-align: center;
  }

  &__action {
    padding: var(--space-3) var(--space-8);
    border-radius: var(--radius-md);
    font-size: var(--text-lg);
    font-weight: 500;
    font-family: inherit;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    cursor: pointer;

    &:active { background: var(--bg-card-hover); }
  }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/StateView.vue
git commit -m "feat(uniapp): add StateView component

- Props: state (loading|error|empty), message, actionLabel
- loading shows spinner, empty/error show message + optional retry button
- All colors reference CSS vars
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: SectionHeader — 区块头部

**Files:**
- Create: `web/apps/uniapp/src/components/SectionHeader.vue`

- [ ] **Step 1: 创建 SectionHeader.vue**

```vue
<template>
  <view class="section-header">
    <view :class="['section-icon-wrap', `icon-bg-${icon}`]">
      <slot name="icon" />
    </view>
    <text class="section-title">{{ title }}</text>
    <view v-if="showAiBadge" class="ai-label">AI</view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  icon: "blue" | "red" | "purple" | "green" | "orange";
  title: string;
  showAiBadge?: boolean;
}>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

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
  flex-shrink: 0;

  &.icon-bg-blue { background: color-mix(in oklch, var(--palette-blue-500) 12%, transparent); }
  &.icon-bg-red { background: color-mix(in oklch, var(--risk-t4) 12%, transparent); }
  &.icon-bg-purple { background: color-mix(in oklch, var(--palette-purple-500) 12%, transparent); }
  &.icon-bg-green { background: color-mix(in oklch, var(--palette-green-500) 12%, transparent); }
  &.icon-bg-orange { background: color-mix(in oklch, var(--risk-t3) 12%, transparent); }
}

.section-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}

.ai-label {
  font-size: var(--text-xs);
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--ai-label-bg);
  color: #fff;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/SectionHeader.vue
git commit -m "feat(uniapp): add SectionHeader component

- Props: icon (blue|red|purple|green|orange), title, showAiBadge
- Icon colors use color-mix referencing palette/semantic tokens
- Exposes icon slot for custom SVG content
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: InfoChip — 信息小标签

**Files:**
- Create: `web/apps/uniapp/src/components/InfoChip.vue`

- [ ] **Step 1: 创建 InfoChip.vue**

```vue
<template>
  <text :class="['info-chip', `chip-${variant}`]">{{ text }}</text>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
  variant: "risk" | "warn" | "neutral";
}>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.info-chip {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-sm);
  font-weight: 500;
  box-sizing: border-box;
  white-space: nowrap;

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
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/InfoChip.vue
git commit -m "feat(uniapp): add InfoChip component

- Props: text, variant (risk|warn|neutral)
- All colors reference CSS vars (chip-*/risktag-* tokens)
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: ListItem — 列表项

**Files:**
- Create: `web/apps/uniapp/src/components/ListItem.vue`

- [ ] **Step 1: 创建 ListItem.vue**

```vue
<template>
  <view class="list-item">
    <view :class="['list-item-icon', `icon-${icon}`]">
      <text>{{ iconSymbol }}</text>
    </view>
    <text class="list-item-text">{{ text }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  icon: "x" | "check-green" | "check-yellow";
  text: string;
}>();

const iconSymbol = computed(() => {
  if (props.icon === "x") return "✕";
  return "✓";
});
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

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

  &.icon-x {
    background: color-mix(in oklch, var(--risk-t4) 12%, transparent);
    color: var(--risk-t4);
  }
  &.icon-check-green {
    background: color-mix(in oklch, var(--risk-t0) 12%, transparent);
    color: var(--risk-t0);
  }
  &.icon-check-yellow {
    background: color-mix(in oklch, var(--risk-t2) 12%, transparent);
    color: var(--risk-t2);
  }
}

.list-item-text {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  line-height: 1.6;
  flex: 1;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/ListItem.vue
git commit -m "feat(uniapp): add ListItem component

- Props: icon (x|check-green|check-yellow), text
- Colors use color-mix referencing risk semantic tokens
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 8: InfoCard — 通用卡片容器

**Files:**
- Create: `web/apps/uniapp/src/components/InfoCard.vue`

- [ ] **Step 1: 创建 InfoCard.vue**

```vue
<template>
  <view :class="['info-card', `info-card--${radius}`]">
    <slot />
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    radius?: "lg" | "xl";
  }>(),
  { radius: "lg" }
);
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.info-card {
  background: var(--bg-card);
  padding: var(--card-padding-xl);
  border: 1px solid var(--border-color);
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;

  &--lg { border-radius: var(--radius-lg); }
  &--xl { border-radius: var(--radius-xl); }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/InfoCard.vue
git commit -m "feat(uniapp): add InfoCard component

- Props: radius (lg|xl, default lg)
- Unifies card background/border/padding/radius
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Part 2：迁移现有组件

### Task 9: 迁移 BottomBar.vue → ActionButton

**Files:**
- Modify: `web/apps/uniapp/src/components/BottomBar.vue`

- [ ] **Step 1: 将 BottomBar 的按钮样式迁移至 CSS 变量**

将 BottomBar.vue 中的：
- `.action-btn` height `88rpx` → `var(--btn-height-xl)`
- `.action-btn` padding `28rpx 32rpx` → `var(--space-7) var(--btn-padding-x)`
- `.action-btn` border-radius `28rpx` → `var(--btn-radius)`
- `.action-btn` font-size `28rpx` → `var(--text-xl)`
- 颜色 `linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink))` → 已引用 `var(--accent-pink-light)` / `var(--accent-pink)`

**注**：BottomBar 保持按钮功能不变，只将硬编码数值替换为 CSS 变量引用。

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/BottomBar.vue
git commit -m "refactor(uniapp): migrate BottomBar styles to CSS vars

- Replace hardcoded rpx values with design-system tokens
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 10: 迁移 IngredientSection.vue → HorizontalScroller + InfoChip

**Files:**
- Modify: `web/apps/uniapp/src/components/IngredientSection.vue`

- [ ] **Step 1: 将 IngredientSection 的横向滚动和配料卡片迁移至新组件**

替换 `.ingredient-scroll` 和 `.ingredient-scroll-inner` 为 `<HorizontalScroller>`：
```html
<HorizontalScroller :gap="20">
  <view v-for="item in groupedIngredients[levelKey]" ... />
</HorizontalScroller>
```

替换 `.ingredient-reason` chip 样式中的硬编码值：
- `font-size: 20rpx` → `var(--text-sm)`
- `padding: 8rpx 16rpx` → `var(--space-1) var(--space-4)`
- 颜色 `#dc2626` 等 → 引用 `var(--risk-t4)` 等语义变量

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/IngredientSection.vue
git commit -m "refactor(uniapp): migrate IngredientSection to HorizontalScroller + CSS vars

- Replace scroll-view wrapper with HorizontalScroller component
- Replace hardcoded colors with semantic tokens
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 11: 迁移 AnalysisCard.vue → InfoCard + RiskTag + ListItem

**Files:**
- Modify: `web/apps/uniapp/src/components/AnalysisCard.vue`

- [ ] **Step 1: 将 AnalysisCard 重构为使用新组件**

替换：
- 最外层 `.analysis-card` → `<InfoCard>`
- 内部 `.level-badge` → `<RiskTag :level="item.level" size="sm">`
- `.analysis-item` → `<ListItem :icon="..." :text="...">`

同时将硬编码颜色替换：
- `#fff` → `var(--bg-card)`
- `#e5e7eb` → `var(--border-color)`
- `#1a1a1a` → `var(--text-primary)`
- `#555` → `var(--text-secondary)`

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/AnalysisCard.vue
git commit -m "refactor(uniapp): migrate AnalysisCard to new components

- Replace card container with InfoCard
- Replace level badge with RiskTag
- Replace list items with ListItem
- Replace hardcoded colors with CSS vars
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 12: 迁移 RiskBadge.vue → RiskTag

**Files:**
- Modify: `web/apps/uniapp/src/components/RiskBadge.vue`
- Modify: `web/apps/uniapp/src/components/IngredientList.vue`（引用 RiskBadge）

- [ ] **Step 1: RiskBadge.vue 改为引用 RiskTag**

将 RiskBadge.vue 的样式全部替换为引用 RiskTag，或直接让 RiskBadge 作为 RiskTag 的别名（wrapper）。

IngredientList.vue 中的 `<RiskBadge :who-level="...">` 改为 `<RiskTag :level="...">`，需要添加 `level` prop 到 RiskTag 并处理 whoLevel → RiskLevel 的映射逻辑。

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/components/RiskBadge.vue web/apps/uniapp/src/components/IngredientList.vue
git commit -m "refactor(uniapp): replace RiskBadge with RiskTag

- RiskBadge becomes alias of RiskTag with whoLevel→level mapping
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 13: 迁移 product/index.vue CSS 变量

**Files:**
- Modify: `web/apps/uniapp/src/pages/product/index.vue`

- [ ] **Step 1: 将 product/index.vue 中所有硬编码数值替换为 CSS 变量**

逐块迁移（保持 JS 逻辑不变，只改 SCSS）：

| 硬编码 | CSS 变量 |
|--------|---------|
| `font-size: 30rpx` | `var(--text-xl)` |
| `font-size: 40rpx` | `var(--text-5xl)` |
| `font-size: 64rpx` | 大号数值保留，但通过 `font-variant-numeric: tabular-nums` |
| `padding: 40rpx` | `var(--card-padding-3xl)` |
| `padding: 36rpx` | `var(--card-padding-2xl)` |
| `padding: 20rpx` | `var(--space-5)` |
| `border-radius: 40rpx` | `var(--radius-lg)` |
| `border-radius: 32rpx` | `var(--radius-md)` |
| `gap: 16rpx` | `var(--space-4)` |
| `gap: 28rpx` | `var(--space-7)` |
| `gap: 48rpx` | `var(--space-12)` |
| `width: 36rpx; height: 36rpx` | `var(--icon-lg)` |
| `width: 32rpx; height: 32rpx` | `var(--icon-md)` |
| `background: rgba(34, 197, 94, 0.04)` | `var(--nutrition-bg)` |
| `background: rgba(239, 68, 68, 0.15)` | `color-mix(in oklch, var(--risk-t4) 15%, transparent)` |
| `#dc2626` | `var(--risk-t4)` |

**注意**：`banner-bg` 是 linear-gradient，引用 `var(--banner-bg)` 而非硬编码。

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/pages/product/index.vue
git commit -m "refactor(uniapp): migrate product page styles to CSS vars

- Replace all hardcoded rpx values with design-system tokens
- Replace hardcoded colors with semantic tokens
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 14: 迁移 ingredient-detail/index.vue CSS 变量

**Files:**
- Modify: `web/apps/uniapp/src/pages/ingredient-detail/index.vue`

- [ ] **Step 1: 将 ingredient-detail/index.vue 中所有硬编码数值替换为 CSS 变量**

同上，逐块迁移：

| 硬编码 | CSS 变量 |
|--------|---------|
| `width: 60rpx; height: 60rpx` | `var(--header-btn-size)` |
| `border-radius: 18rpx` | `var(--radius-sm)` |
| `padding: 20rpx 24rpx 24rpx` | `var(--header-padding-y) var(--header-padding-x)` |
| `gap: 16rpx` | `var(--space-4)` |
| `font-size: 34rpx` | `var(--text-3xl)` |
| `font-size: 24rpx` | `var(--text-md)` |
| `padding: 32rpx` | `var(--card-padding-xl)` |
| `margin-bottom: 24rpx` | `var(--space-6)` |
| `padding: 24rpx 24rpx 0` | `var(--space-6) var(--space-6) 0` |
| `width: 40rpx; height: 40rpx` | `var(--icon-lg)` |
| `width: 24rpx; height: 24rpx` | `var(--icon-md)` |
| `border-radius: 12rpx` | `var(--radius-sm)` |
| `background: linear-gradient(135deg, #6366f1, #8b5cf6)` | `var(--ai-label-bg)` |
| `#ef4444` | `var(--risk-t4)` |
| `#f87171` | `var(--risk-t4)` (暗色调整后对应值) |
| `box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.04)` | `var(--shadow-sm)` |
| `width: 172rpx` | 固定宽度保留（设计决策，非 token） |
| `height: 172rpx` | 固定高度保留 |
| `width: 200rpx` | 固定宽度保留 |
| `padding-bottom: max(48rpx, env(safe-area-inset-bottom))` | safe-area 逻辑不变 |

**注意**：`ingredient-detail` 使用 inline style 计算动态颜色（`pageStyle` computed），这些保持不变，因为它们引用 `riskConf` 的动态值。

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp/src/pages/ingredient-detail/index.vue
git commit -m "refactor(uniapp): migrate ingredient-detail page styles to CSS vars

- Replace all hardcoded rpx values with design-system tokens
- Replace hardcoded colors with semantic tokens
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验证清单

迁移前，确保 `design-system.scss` 已包含所有 plan 引用的 token：
- `--risktag-t4/t3/t2/t1/t0/unknown-bg` / `--risktag-t4/t3/t2/t1/t0/unknown-text`
- `--chip-risk/warn/neu-bg` / `--chip-risk/warn-text` / `--chip-neu-text`
- `--icon-xs/sm/md/lg`（已在 design-system.scss 中）
- `--card-padding-xl/2xl/3xl`（已在 design-system.scss 中）

迁移完成后，确保：

- [ ] 所有 `.vue` 文件导入 `@/styles/design-system.scss`
- [ ] 组件中无 `#dc2626` / `#f87171` / `#fee2e2` 等硬编码颜色（搜索确认）
- [ ] 组件中无 `xxrpx` 硬编码间距（搜索确认）
- [ ] 暗色模式切换正常（通过 `.dark-mode` class 覆盖）
- [ ] UniApp H5 构建无报错：`pnpm build:uniapp:h5`
