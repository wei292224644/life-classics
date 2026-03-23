# UniApp 设计 Token 架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一的 ThemeStore，集中管理 isDark 和 statusBarHeight；将 riskLevel.ts 的颜色配置移入组件 CSS；消除各页面的 pageStyle computed。

**Architecture:**
- 新增 `store/theme.ts` 作为主题状态单一数据源，App.vue 根节点挂载 `.dark-mode` class
- `riskLevel.ts` 剥离颜色字段，仅保留 badge/icon/needleLeft，新增 visualKey 供模板 class 绑定
- ingredient-detail 页面通过 `.risk-critical` 等 class + CSS 变量接管颜色，不再有 pageStyle computed
- 其他三个页面（index/search/profile）统一使用 themeStore，移除 local isDark

**Tech Stack:** Pinia（已有）、Vue 3 Composition API、SCSS、UniApp

---

## File Impact Map

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/store/theme.ts` | 创建 | ThemeStore，isDark + statusBarHeight |
| `src/App.vue` | 修改 | 根节点绑定 dark-mode class |
| `src/utils/riskLevel.ts` | 修改 | 剥离颜色字段，保留纯数据 |
| `src/pages/ingredient-detail/index.vue` | 修改 | 移除 pageStyle，改用 riskClass + CSS |
| `src/pages/index/index.vue` | 修改 | 使用 themeStore |
| `src/pages/search/index.vue` | 修改 | 使用 themeStore |
| `src/pages/profile/index.vue` | 修改 | 使用 themeStore |

---

## Task 1: 创建 ThemeStore

**Files:**
- Create: `src/store/theme.ts`

**Prerequisite:** 无

---

- [ ] **Step 1: 创建 stores 目录并写入 theme.ts**

```bash
mkdir -p src/stores
```

Create `src/store/theme.ts`:

```typescript
// src/store/theme.ts
import { defineStore } from "pinia"
import { ref } from "vue"

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(false)
  const statusBarHeight = ref(0)

  function handleThemeChange({ theme }: { theme: string }) {
    isDark.value = theme === "dark"
  }

  function init() {
    const info = uni.getSystemInfoSync()
    statusBarHeight.value = info.statusBarHeight ?? 0
    isDark.value = info.theme === "dark"
    uni.onThemeChange(handleThemeChange)
  }

  function cleanup() {
    uni.offThemeChange(handleThemeChange)
  }

  return { isDark, statusBarHeight, init, cleanup }
})
```

- [ ] **Step 2: Commit**

```bash
git add src/store/theme.ts
git commit -m "feat(uniapp): add ThemeStore for isDark and statusBarHeight

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 改造 App.vue

**Files:**
- Modify: `src/App.vue:1-16`

**Prerequisite:** Task 1 完成

---

- [ ] **Step 1: 重写 App.vue**

```vue
<script setup lang="ts">
import { onMounted, onUnmounted } from "vue"
import { useThemeStore } from "./stores/theme"

const themeStore = useThemeStore()
onMounted(() => themeStore.init())
onUnmounted(() => themeStore.cleanup())
</script>

<template>
  <view :class="{ 'dark-mode': themeStore.isDark }">
    <slot />
  </view>
</template>

<style lang="scss">
@import 'uview-plus/index.scss';
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/App.vue
git commit -m "feat(uniapp): bind .dark-mode class on App root

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 改造 riskLevel.ts

**Files:**
- Modify: `src/utils/riskLevel.ts`

**Prerequisite:** 无（此文件独立，不依赖其他任务）

---

- [ ] **Step 1: 读取当前 riskLevel.ts 完整内容**

Read `src/utils/riskLevel.ts` — 确认 `RiskLevelConfig` 接口和 `RISK_CONFIG` 对象的当前完整结构。

- [ ] **Step 2: 修改 RiskLevelConfig 接口**

删除所有颜色字段（`headerBgLight` / `headerBgDark` / `headerBorderLight` / `headerBorderDark` / `headerTitleLight` / `headerTitleDark` / `headerSubLight` / `headerSubDark` / `headerBtnLight` / `headerBtnDark` / `badgeBg`）。

新增 `visualKey` 字段：

```typescript
export interface RiskLevelConfig {
  visualKey: VisualKey
  badge: string
  icon: string
  subtitleNoProduct: string
  needleLeft: string | null
}
```

- [ ] **Step 3: 修改 RISK_CONFIG 对象**

每个等级条目删除颜色字段，保留纯数据，新增 `visualKey`：

```typescript
export const RISK_CONFIG: Record<VisualKey, RiskLevelConfig> = {
  critical: {
    visualKey: "critical",
    badge: "极高风险",
    icon: "⛔",
    subtitleNoProduct: "⛔ 极高风险 · 不建议摄入",
    needleLeft: "88%",
  },
  high: {
    visualKey: "high",
    badge: "高风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 高风险 · 谨慎摄入",
    needleLeft: "72%",
  },
  medium: {
    visualKey: "medium",
    badge: "中等风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 中等风险 · 适量摄入",
    needleLeft: "50%",
  },
  low: {
    visualKey: "low",
    badge: "低风险",
    icon: "✓",
    subtitleNoProduct: "✓ 低风险",
    needleLeft: "22%",
  },
  safe: {
    visualKey: "safe",
    badge: "安全",
    icon: "✓",
    subtitleNoProduct: "✓ 安全 · 天然成分",
    needleLeft: "8%",
  },
  unknown: {
    visualKey: "unknown",
    badge: "暂无评级",
    icon: "?",
    subtitleNoProduct: "暂无风险评级数据",
    needleLeft: null,
  },
}
```

- [ ] **Step 4: Commit**

```bash
git add src/utils/riskLevel.ts
git commit -m "refactor(uniapp): remove colors from riskLevel.ts

RISK_CONFIG now only contains pure data (badge, icon, needleLeft).
Color values moved to component-scoped CSS classes.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 改造 ingredient-detail/index.vue

**Files:**
- Modify: `src/pages/ingredient-detail/index.vue`

**Prerequisite:** Task 2（App.vue）和 Task 3（riskLevel.ts）完成

This is the largest change. Read the file carefully before starting.

---

- [ ] **Step 1: 读取完整文件**

Read `src/pages/ingredient-detail/index.vue` — 记录所有需要删除的代码位置：
- `ref(false)` 的 `isDark` (line ~305)
- theme 监听逻辑 in `onMounted`/`onUnmounted` (~311-320)
- 整块 `pageStyle` computed (~333-357)
- `headerStyle` computed (~359-362)
- `heroCardStyle` / `heroTopStyle` / `badgeStyle` (~364-377)

Also note:
- `riskConf` computed 的引用位置
- 模板中 `:style="pageStyle"` 和 `:style="headerStyle"` 的位置

- [ ] **Step 2: 删除 isDark ref 和 theme 监听**

删除：
```typescript
const isDark = ref(false)
```
删除 `onMounted`/`onUnmounted` 中的 theme 相关逻辑，保留其他初始化逻辑。

- [ ] **Step 3: 删除 pageStyle computed（约 25 行）**

删除整个 `pageStyle` computed 函数。

- [ ] **Step 4: 简化 headerStyle computed**

改造前：
```typescript
const headerStyle = computed(() => ({
  background: "var(--risk-bg)",
  borderBottom: `1px solid var(--risk-border)`,
}))
```

改造后：删除 `headerStyle` computed，`ing-header` 元素改用 `:class="riskClass"`。

- [ ] **Step 5: 新增 riskClass computed**

在原 `riskConf` computed 附近添加：

```typescript
const riskClass = computed(() => `risk-${riskConf.value.visualKey}`)
```

- [ ] **Step 6: 改造模板**

改造前：
```vue
<view class="ingredient-detail-page" :style="pageStyle">
  <view class="ing-header" :style="headerStyle">
```

改造后：
```vue
<view class="ingredient-detail-page">
  <view class="ing-header" :class="riskClass">
```

同样检查 `heroCardStyle` / `heroTopStyle` / `badgeStyle` 是否还有 `:style`，如果它们只引用了 `pageStyle` 里的变量，需要简化或删除。

- [ ] **Step 7: 添加 scoped CSS 风险 class**

在 `<style lang="scss" scoped>` 的 `@import "@/styles/design-system.scss";` 之后、`.ingredient-detail-page` 样式之前，插入：

```scss
// Risk level color classes — scoped to this component
// Generic header vars consumed by .ing-header
@mixin risk-header-vars {
  background: var(--risk-header-bg);
  border-bottom: 1px solid var(--risk-header-border);
}

// Light mode risk classes
.risk-critical { --risk-header-bg: var(--palette-red-50); --risk-header-border: var(--palette-red-200); }
.risk-high      { --risk-header-bg: var(--palette-orange-50); --risk-header-border: var(--palette-orange-200); }
.risk-medium    { --risk-header-bg: var(--palette-yellow-50); --risk-header-border: var(--palette-yellow-200); }
.risk-low       { --risk-header-bg: var(--palette-green-50); --risk-header-border: var(--palette-green-200); }
.risk-safe      { --risk-header-bg: var(--palette-green-50); --risk-header-border: var(--palette-green-200); }
.risk-unknown   { --risk-header-bg: var(--palette-gray-50); --risk-header-border: var(--palette-gray-200); }

// Dark mode risk classes
.dark-mode {
  .risk-critical { --risk-header-bg: var(--palette-red-900); --risk-header-border: var(--palette-red-800); }
  .risk-high      { --risk-header-bg: var(--palette-orange-900); --risk-header-border: var(--palette-orange-800); }
  .risk-medium    { --risk-header-bg: var(--palette-yellow-900); --risk-header-border: var(--palette-yellow-800); }
  .risk-low       { --risk-header-bg: var(--palette-green-950); --risk-header-border: var(--palette-green-800); }
  .risk-safe      { --risk-header-bg: var(--palette-green-950); --risk-header-border: var(--palette-green-700); }
  .risk-unknown   { --risk-header-bg: var(--palette-gray-800); --risk-header-border: var(--palette-gray-600); }
}

// Ing-header uses the generic vars
.ing-header {
  background: var(--risk-header-bg);
  border-bottom: 1px solid var(--risk-header-border);
}
```

- [ ] **Step 8: 验证页面仍可正常渲染**

启动 H5 开发服务器：
```bash
pnpm dev:uniapp:h5
```
访问 ingredient-detail 页面，切换暗色模式，确认风险 Header 颜色正确变化。

- [ ] **Step 9: Commit**

```bash
git add src/pages/ingredient-detail/index.vue
git commit -m "refactor(uniapp): remove pageStyle computed, use riskClass + CSS vars

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 改造 index/index.vue

**Files:**
- Modify: `src/pages/index/index.vue`

**Prerequisite:** Task 2 完成（App.vue 已有 themeStore）

---

- [ ] **Step 1: 读取 JS 部分，确认 isDark 和 statusBarHeight 位置**

- [ ] **Step 2: 替换 import**

删除：`import { ref } from "vue"`
添加：`import { useThemeStore } from "../../store/theme"`
添加 store 实例（文件顶部）：`const themeStore = useThemeStore()`

- [ ] **Step 3: 删除 local isDark ref 和 theme 监听**

删除：
```typescript
const isDark = ref(false)
const statusBarHeight = ref(0)
```
删除 `onMounted` 中的 `statusBarHeight` 赋值和 `isDark` 赋值及 `uni.onThemeChange` 监听。
删除 `onUnmounted` 中的 `uni.offThemeChange`。
保留 `loadRecentScans()` 相关逻辑不变。

- [ ] **Step 4: 替换模板中的引用**

`:class="{ 'dark-mode': isDark }"` → `:class="{ 'dark-mode': themeStore.isDark }"`
`statusBarHeight + 'px'` → `themeStore.statusBarHeight + 'px'`

- [ ] **Step 5: 验证**

```bash
pnpm dev:uniapp:h5
```
访问首页，切换暗色模式，确认背景色正确变化。

- [ ] **Step 6: Commit**

```bash
git add src/pages/index/index.vue
git commit -m "refactor(uniapp): use ThemeStore in index page

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 改造 search/index.vue

**Files:**
- Modify: `src/pages/search/index.vue`

**Prerequisite:** Task 2 完成

---

- [ ] **Step 1: 读取 JS 部分**

- [ ] **Step 2: 替换 import**

删除：`import { ref, computed } from "vue"`
添加：`import { useThemeStore } from "../../store/theme"`
添加 store 实例：`const themeStore = useThemeStore()`

- [ ] **Step 3: 删除 local isDark ref 和 theme 监听**

删除 `isDark` 和 `statusBarHeight` 的 local ref 定义。
删除 `handleThemeChange` 函数。
删除 `onMounted` 中的 theme 监听初始化。
删除 `onUnmounted` 中的 `offThemeChange`。

- [ ] **Step 4: 替换模板引用**

`:class="{ 'dark-mode': isDark }"` → `:class="{ 'dark-mode': themeStore.isDark }"`
`statusBarHeight + 'px'` → `themeStore.statusBarHeight + 'px'"`
`headerStyle` computed 中的 `isDark.value` → `themeStore.isDark`

**注意：** `typeTagStyle` 函数里也有 `isDark.value` 判断，需要改为 `themeStore.isDark`。

- [ ] **Step 5: 验证**

```bash
pnpm dev:uniapp:h5
```
访问搜索页，切换暗色模式，确认样式正确。

- [ ] **Step 6: Commit**

```bash
git add src/pages/search/index.vue
git commit -m "refactor(uniapp): use ThemeStore in search page

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 改造 profile/index.vue

**Files:**
- Modify: `src/pages/profile/index.vue`

**Prerequisite:** Task 2 完成

---

- [ ] **Step 1: 读取 JS 部分**

- [ ] **Step 2: 替换 import**

删除：`import { ref, computed } from 'vue'`
添加：`import { useThemeStore } from "../../store/theme"`
添加 store 实例：`const themeStore = useThemeStore()`

- [ ] **Step 3: 删除 local isDark ref 和 theme 监听**

删除 `isDark` 和 `statusBarHeight` local ref。
删除 `handleThemeChange` 函数。
删除 `onMounted` 中的 theme 监听初始化。
删除 `onUnmounted` 中的 `offThemeChange`。

- [ ] **Step 4: 简化 headerStyle computed**

改造前：
```typescript
const headerStyle = computed(() => ({
  '--header-bg': isDark.value ? 'var(--bg-card)' : 'var(--bg-base)',
}))
```

改造后：删除 `headerStyle` computed。模板中的 `:style="headerStyle"` 改为直接用 CSS class（`.profile-header` 在 scoped style 里已有 `background: var(--bg-base)` 定义）。

- [ ] **Step 5: 替换模板引用**

`:class="{ 'dark-mode': isDark }"` → `:class="{ 'dark-mode': themeStore.isDark }"`
`statusBarHeight + 'px'` → `themeStore.statusBarHeight + 'px'"`
删除 `:style="headerStyle"` 绑定（Header 样式已在 scoped CSS 中定义）。

- [ ] **Step 6: 验证**

```bash
pnpm dev:uniapp:h5
```
访问个人页，切换暗色模式，确认样式正确。

- [ ] **Step 7: Commit**

```bash
git add src/pages/profile/index.vue
git commit -m "refactor(uniapp): use ThemeStore in profile page

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 补充 palette-green-950（设计系统缺失）

**Files:**
- Modify: `src/styles/design-system.scss`

**Prerequisite:** 无（独立修复）

> ⚠️ Task 4 的 scoped CSS 引用了 `--palette-green-950`，但 design-system.scss 只定义了 green-900。需要在 palette 段补充 green-950。

- [ ] **Step 1: 确认 green palette 末尾位置**

在 design-system.scss 中找到 green palette 末尾（`--palette-green-900: #052e16;` 之后）。

- [ ] **Step 2: 添加 green-950**

在 green palette 末尾添加：

```scss
--palette-green-950: #022c22;
```

- [ ] **Step 3: Commit**

```bash
git add src/styles/design-system.scss
git commit -m "fix(uniapp): add palette-green-950 to design-system

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 修复记录

- [x] Import path 修正 + 目录名统一：`../../stores/theme` → `../../store/theme`（Tasks 5/6/7）；创建时目录 `stores/` → `store/`（Task 1）
- [x] palette-green-950 缺失：已补充为 Task 8

---

## Verification Checklist

All tasks完成后，执行以下验证：

1. **App.vue** — 检查根 view 有 `:class="{ 'dark-mode': themeStore.isDark }"`
2. **ThemeStore** — `isDark` 和 `statusBarHeight` 正确初始化和监听
3. **riskLevel.ts** — 所有颜色字段已删除，`visualKey` 已添加
4. **ingredient-detail** — 无 `pageStyle` computed，无 local `isDark`，风险 Header 颜色通过 CSS class 切换
5. **3 个子页面** — 全部使用 `themeStore.isDark` 和 `themeStore.statusBarHeight`
6. **暗色模式** — H5 切换系统主题，所有页面正确响应
