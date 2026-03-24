# UnoCSS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 1782 lines of SCSS with UnoCSS atomic classes across 21 Vue files in `web/apps/uniapp/src/`, while simplifying the color system.

**Architecture:** Revert broken migration → install `unocss-preset-uni` (rpx support) → simplify `design-system.scss` (remove palette + component layers) → migrate components one-by-one per strict migration guide.

**Tech Stack:** Vue 3, UniApp, UnoCSS, unocss-preset-uni, SCSS

**Spec:** `docs/superpowers/specs/2026-03-24-unocss-migration-design.md`

---

## CRITICAL RULES FOR PHASE 1 WORKERS

1. **Read `web/apps/uniapp/src/migration-guide.md` before touching any file.** It is your only source of truth.
2. **If a CSS pattern is NOT in the guide → keep it in the style block with comment `// kept: not in migration guide`.** Do NOT invent class names.
3. **Never remove a class that is referenced in `:class` binding or `@apply` without adding its UnoCSS equivalent.**
4. **After migrating each file, verify the style block contains ONLY patterns that cannot be expressed atomically.**
5. **Commit after each batch. Do NOT batch multiple batches into one commit.**
6. **Context management:** Each Phase 1 batch must run in a fresh session. At the start of each session, read: `migration-guide.md`, `uno.config.ts`, `design-system.scss`, then the target files.

---

## File Map

**Modified in Phase 0:**
- `web/apps/uniapp/src/styles/design-system.scss` — remove palette+component layers, add missing vars
- `web/apps/uniapp/src/uno.config.ts` — switch to unocss-preset-uni, add shortcuts
- `web/apps/uniapp/vite.config.ts` — configure UnoCSS plugin
- `web/apps/uniapp/src/migration-guide.md` — new file, the bible for Phase 1

**Migrated in Phase 1 (21 files):**
- `src/pages/scan/index.vue`
- `src/components/ListItem.vue`
- `src/components/RiskBadge.vue`
- `src/components/InfoChip.vue`
- `src/components/SectionHeader.vue`
- `src/components/StateView.vue`
- `src/components/RiskTag.vue`
- `src/components/HorizontalScroller.vue`
- `src/components/ActionButton.vue`
- `src/components/InfoCard.vue`
- `src/components/AnalysisCard.vue`
- `src/components/NutritionTable.vue`
- `src/components/IngredientList.vue`
- `src/components/ProductHeader.vue`
- `src/components/BottomBar.vue`
- `src/components/IngredientSection.vue`
- `src/pages/search/index.vue`
- `src/pages/profile/index.vue`
- `src/pages/ingredient-detail/index.vue`
- `src/pages/index/index.vue`
- `src/pages/product/index.vue`

---

## Phase 0: Setup (Claude Opus 4.6 executes this phase)

### Task 0.1: Revert uniapp migration commits, restore pre-migration Vue files

**Files:** All files in `web/apps/uniapp/src/components/` and `web/apps/uniapp/src/pages/`

- [ ] **Step 1: Find pre-migration commit hash**

```bash
cd /Users/wwj/Desktop/self/life-classics
git log --oneline web/apps/uniapp/src/ | grep -v "migrate\|migration\|rpx\|UnoCSS\|design-system\|backward" | head -5
```

The target commit is the one before `ddfa52c` (first migration commit: "migrate product page to UnoCSS layout classes"). Run:

```bash
git log --oneline | grep -A1 "ddfa52c"
```

Note the SHA of the commit AFTER `ddfa52c` in the log (i.e., the parent). Call it `<BASE_SHA>`.

- [ ] **Step 2: Restore component and page files to pre-migration state**

```bash
git checkout <BASE_SHA> -- web/apps/uniapp/src/components/ web/apps/uniapp/src/pages/
```

- [ ] **Step 3: Verify restoration**

```bash
# Should show many modified files (components restored to original)
git status
# Spot check: original files had no UnoCSS classes in template
grep -c "flex items-center" web/apps/uniapp/src/components/ProductHeader.vue
# Should be 1 (only the original one in the header view, not the new ones added by migration)
```

---

### Task 0.2: Install unocss-preset-uni

- [ ] **Step 1: Install the package**

```bash
cd /Users/wwj/Desktop/self/life-classics/web
pnpm add unocss-preset-uni --filter @acme/uniapp
```

- [ ] **Step 2: Verify installation**

```bash
grep "unocss-preset-uni" web/apps/uniapp/package.json
```

---

### Task 0.3: Update uno.config.ts

Replace the entire `web/apps/uniapp/src/uno.config.ts` with:

```ts
import { defineConfig, presetIcons } from 'unocss'
import presetUni from 'unocss-preset-uni'

export default defineConfig({
  presets: [
    presetUni(),
    presetIcons({
      scale: 1.2,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle'
      }
    })
  ],

  theme: {
    colors: {
      // Palette colors (for use as bg-red-500, text-gray-900, etc.)
      gray: { 50:'#f9fafb',100:'#f3f4f6',200:'#e5e7eb',300:'#d1d5db',400:'#9ca3af',500:'#6b7280',600:'#4b5563',700:'#374151',800:'#1f2937',900:'#111827' },
      red: { 50:'#fef2f2',100:'#fee2e2',200:'#fecaca',300:'#fca5a5',400:'#f87171',500:'#dc2626',600:'#b91c1c',700:'#991b1b',800:'#7f1d1d',900:'#450a0a' },
      orange: { 50:'#fff7ed',100:'#ffedd5',200:'#fed7aa',300:'#fdba74',400:'#fb923c',500:'#f97316',600:'#ea580c',700:'#c2410c',800:'#9a3412',900:'#431407' },
      yellow: { 50:'#fefce8',100:'#fef9c3',200:'#fef08a',300:'#fde047',400:'#facc15',500:'#eab308',600:'#ca8a04',700:'#a16207',800:'#713f12',900:'#422006' },
      green: { 50:'#f0fdf4',100:'#dcfce7',200:'#bbf7d0',300:'#86efac',400:'#4ade80',500:'#22c55e',600:'#16a34a',700:'#15803d',800:'#14532d',900:'#052e16',950:'#022c22' },
      purple: { 50:'#f5f3ff',100:'#ede9fe',300:'#c4b5fd',400:'#a78bfa',500:'#8b5cf6',600:'#7c3aed',700:'#6d28d9',800:'#4c1d95' },
      blue: { 50:'#eff6ff',100:'#dbeafe',300:'#93c5fd',400:'#60a5fa',500:'#3b82f6',600:'#2563eb' },
      pink: { 50:'#fdf2f8',100:'#fce7f3',200:'#fbcfe8',300:'#f9a8d4',400:'#f472b6',500:'#ec4899',600:'#db2777' },
    },
  },

  shortcuts: {
    // ── Base components ──────────────────────────────────────
    'card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-sm)]',
    'section-title': 'text-[var(--text-primary)] font-semibold text-lg',
    'icon-wrap': 'w-[40rpx] h-[40rpx] rounded-[var(--radius-sm)] flex items-center justify-center',

    // ── AI label ─────────────────────────────────────────────
    'ai-label': 'text-[20rpx] font-bold px-[12rpx] py-[4rpx] rounded-[24rpx] bg-[var(--ai-label-bg)] text-white',

    // ── Icon backgrounds (SectionHeader) ────────────────────
    'icon-bg-blue':   'bg-[color-mix(in_oklch,#3b82f6_12%,transparent)] text-[#3b82f6]',
    'icon-bg-red':    'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)]',
    'icon-bg-purple': 'bg-[color-mix(in_oklch,#8b5cf6_12%,transparent)] text-[#8b5cf6]',
    'icon-bg-green':  'bg-[color-mix(in_oklch,#22c55e_12%,transparent)] text-[#22c55e]',
    'icon-bg-orange': 'bg-[color-mix(in_oklch,var(--risk-t3)_12%,transparent)] text-[var(--risk-t3)]',

    // ── Info chips (InfoChip.vue) ────────────────────────────
    'chip-risk':    'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)] border border-[color-mix(in_oklch,var(--risk-t4)_20%,transparent)]',
    'chip-warn':    'bg-[color-mix(in_oklch,var(--risk-t2)_10%,transparent)] text-[var(--risk-t2)] border border-[color-mix(in_oklch,var(--risk-t2)_20%,transparent)]',
    'chip-neutral': 'bg-[var(--bg-card-hover)] text-[var(--text-secondary)]',

    // ── Risk tags (RiskTag.vue, AnalysisCard.vue) ────────────
    'risktag-t4':      'bg-[color-mix(in_oklch,var(--risk-t4)_15%,transparent)] text-[var(--risk-t4)]',
    'risktag-t3':      'bg-[color-mix(in_oklch,var(--risk-t3)_15%,transparent)] text-[var(--risk-t3)]',
    'risktag-t2':      'bg-[color-mix(in_oklch,var(--risk-t2)_15%,transparent)] text-[var(--risk-t2)]',
    'risktag-t1':      'bg-[color-mix(in_oklch,var(--risk-t1)_15%,transparent)] text-[var(--risk-t1)]',
    'risktag-t0':      'bg-[color-mix(in_oklch,var(--risk-t0)_15%,transparent)] text-[var(--risk-t0)]',
    'risktag-unknown': 'bg-[color-mix(in_oklch,var(--risk-unknown)_15%,transparent)] text-[var(--risk-unknown)]',

    // ── Risk group containers (IngredientSection.vue) ────────
    'risk-group-t4':      'bg-[color-mix(in_oklch,var(--risk-t4)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t4)_25%,transparent)]',
    'risk-group-t3':      'bg-[color-mix(in_oklch,var(--risk-t3)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t3)_25%,transparent)]',
    'risk-group-t2':      'bg-[color-mix(in_oklch,var(--risk-t2)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t2)_25%,transparent)]',
    'risk-group-t1':      'bg-[color-mix(in_oklch,var(--risk-t1)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t1)_25%,transparent)]',
    'risk-group-t0':      'bg-[color-mix(in_oklch,var(--risk-t0)_8%,transparent)] border border-[color-mix(in_oklch,var(--risk-t0)_25%,transparent)]',
    'risk-group-unknown': 'bg-[var(--bg-card-hover)] border border-[var(--border-color)]',

    // ── Risk reason tags (IngredientSection.vue) ─────────────
    'risk-reason-t4':      'text-[var(--risk-t4)] bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)]',
    'risk-reason-t3':      'text-[var(--risk-t3)] bg-[color-mix(in_oklch,var(--risk-t3)_12%,transparent)]',
    'risk-reason-t2':      'text-[var(--risk-t2)] bg-[color-mix(in_oklch,var(--risk-t2)_12%,transparent)]',
    'risk-reason-t1':      'text-[var(--risk-t1)] bg-[color-mix(in_oklch,var(--risk-t1)_12%,transparent)]',
    'risk-reason-t0':      'text-[var(--risk-t0)] bg-[color-mix(in_oklch,var(--risk-t0)_12%,transparent)]',
    'risk-reason-unknown': 'text-[var(--risk-unknown)] bg-[color-mix(in_oklch,var(--risk-unknown)_12%,transparent)]',

    // ── List item icons (ListItem.vue) ───────────────────────
    'icon-x':            'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)]',
    'icon-check-green':  'bg-[color-mix(in_oklch,var(--risk-t0)_12%,transparent)] text-[var(--risk-t0)]',
    'icon-check-yellow': 'bg-[color-mix(in_oklch,var(--risk-t2)_12%,transparent)] text-[var(--risk-t2)]',

    // ── Transitions ──────────────────────────────────────────
    'transition-spring': 'transition-all duration-200 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
    'transition-spring-slow': 'transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
    'transition-spring-400': 'transition-all duration-400 ease-[cubic-bezier(0.34,1.56,0.64,1)]',

    // ── Buttons ──────────────────────────────────────────────
    'btn-primary':   'bg-gradient-to-br from-[var(--accent-light)] to-[var(--accent)] text-white shadow-[0_4rpx_20rpx_color-mix(in_oklch,var(--accent)_30%,transparent)] active:scale-97 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary': 'bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] active:bg-[var(--bg-card-hover)] disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-ghost':     'bg-transparent text-[var(--text-primary)] active:bg-[color-mix(in_oklch,var(--text-primary)_8%,transparent)] disabled:opacity-50 disabled:cursor-not-allowed',

    // ── Risk badge (RiskBadge.vue) ───────────────────────────
    'risk-badge-critical': 'bg-[color-mix(in_oklch,var(--risk-t4)_15%,transparent)] text-[var(--risk-t4)]',
    'risk-badge-high':     'bg-[color-mix(in_oklch,var(--risk-t3)_15%,transparent)] text-[var(--risk-t3)]',
    'risk-badge-medium':   'bg-[color-mix(in_oklch,var(--risk-t2)_15%,transparent)] text-[var(--risk-t2)]',
    'risk-badge-low':      'bg-[color-mix(in_oklch,var(--risk-t1)_15%,transparent)] text-[var(--risk-t1)]',
    'risk-badge-unknown':  'bg-[color-mix(in_oklch,var(--risk-unknown)_15%,transparent)] text-[var(--risk-unknown)]',

    // ── Index page ───────────────────────────────────────────
    'scan-count-badge': 'bg-[color-mix(in_oklch,var(--risk-t4)_10%,transparent)] text-[var(--risk-t4)] text-[20rpx] font-bold px-[12rpx] py-[4rpx] rounded-full',
  },

  safelist: [
    // Dynamic risk classes (used via template string interpolation)
    'risk-group-t4', 'risk-group-t3', 'risk-group-t2', 'risk-group-t1', 'risk-group-t0', 'risk-group-unknown',
    'risk-reason-t4', 'risk-reason-t3', 'risk-reason-t2', 'risk-reason-t1', 'risk-reason-t0', 'risk-reason-unknown',
    'risktag-t4', 'risktag-t3', 'risktag-t2', 'risktag-t1', 'risktag-t0', 'risktag-unknown',
    'icon-x', 'icon-check-green', 'icon-check-yellow',
    'icon-bg-blue', 'icon-bg-red', 'icon-bg-purple', 'icon-bg-green', 'icon-bg-orange',
    'chip-risk', 'chip-warn', 'chip-neutral',
    'risk-badge-critical', 'risk-badge-high', 'risk-badge-medium', 'risk-badge-low', 'risk-badge-unknown',
    'risk-critical', 'risk-high', 'risk-medium', 'risk-low', 'risk-safe', 'risk-unknown',
    // Level-based classes for ingredient detail
    'level-t4', 'level-t3', 'level-t2', 'level-t1', 'level-t0', 'level-unknown',
  ],
})
```

- [ ] **Commit this change**

```bash
git add web/apps/uniapp/src/uno.config.ts web/package.json web/pnpm-lock.yaml
git commit -m "feat(uniapp): install unocss-preset-uni, update uno.config.ts with shortcuts"
```

---

### Task 0.4: Simplify design-system.scss

Replace the entire `web/apps/uniapp/src/styles/design-system.scss` with:

```scss
// ============================================================
// 2026 Design System — CSS Variables (Simplified)
// UniApp + Vue 3 + SCSS
//
// Only semantic and component-specific tokens.
// Palette layer removed — use UnoCSS theme colors (bg-red-500 etc.)
// Component layer removed — use UnoCSS shortcuts in uno.config.ts
// ============================================================

// SCSS compile-time constants (for SCSS functions/mixins only)
$font-family: 'DM Sans', -apple-system, sans-serif;
$ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

page {
  // ── Semantic: Text ──────────────────────────────────────
  --text-primary:   #111827;
  --text-secondary: #4b5563;
  --text-muted:     #9ca3af;

  // ── Semantic: Border ────────────────────────────────────
  --border-color: color-mix(in oklch, #111827 6%, transparent);

  // ── Semantic: Background ────────────────────────────────
  --bg-base:      #f9fafb;
  --bg-card:      #ffffff;
  --bg-card-hover: #f9fafb;

  // ── Semantic: Accent (brand pink) ───────────────────────
  --accent:       #db2777;
  --accent-light: #ec4899;

  // ── Semantic: Risk colors ───────────────────────────────
  --risk-t4:      #dc2626;  // red-600
  --risk-t3:      #ea580c;  // orange-600
  --risk-t2:      #ca8a04;  // yellow-600
  --risk-t1:      #22c55e;  // green-500
  --risk-t0:      #16a34a;  // green-600
  --risk-unknown: #9ca3af;  // gray-400

  // ── Component: layout tokens (used in CSS/JS directly) ──
  --radius-sm: 24rpx;
  --radius-md: 32rpx;
  --radius-lg: 40rpx;
  --radius-xl: 48rpx;
  --shadow-sm: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
  --ease-spring: #{$ease-spring};

  // ── Component: specific tokens ──────────────────────────
  // (kept because used in complex CSS or JS inline styles)
  --bottom-bar-bg:      color-mix(in oklch, #ffffff 95%, transparent);
  --bottom-bar-border:  color-mix(in oklch, #111827 6%, transparent);
  --header-scrolled-bg: color-mix(in oklch, #ffffff 90%, transparent);
  --ai-label-bg:        linear-gradient(135deg, #8b5cf6, #7c3aed);
  --nutrition-bg:       color-mix(in oklch, #22c55e 4%, transparent);
  --nutrition-border:   color-mix(in oklch, #22c55e 12%, transparent);
  --status-bar-bg:      #ffffff;
  --status-bar-text:    #111827;
  --banner-bg:          linear-gradient(145deg, #fefce8 0%, #fef9c3 50%, #fef08a 100%);
  --banner-label:       #713f12;
  // product page specific
  --banner-badge-bg:    color-mix(in oklch, #ffffff 85%, transparent);
  --banner-badge-border: color-mix(in oklch, #ffffff 20%, transparent);
  --banner-badge-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
  --nutrition-glow:     color-mix(in oklch, #22c55e 30%, transparent);
}

// ── Dark Mode ───────────────────────────────────────────────
// NOTE: App.vue injects class "dark-mode" (not "dark"), so use .dark-mode here
.dark-mode {
  --text-primary:   #f3f4f6;
  --text-secondary: #9ca3af;
  --text-muted:     #6b7280;
  --border-color: color-mix(in oklch, #f3f4f6 8%, transparent);
  --bg-base:      #0f0f0f;
  --bg-card:      #1a1a1a;
  --bg-card-hover: #222222;
  --accent:       #ec4899;
  --accent-light: #f472b6;
  --risk-t4:      #f87171;  // red-400
  --risk-t3:      #f97316;  // orange-500
  --risk-t2:      #eab308;  // yellow-500
  --risk-t1:      #4ade80;  // green-400
  --risk-t0:      #22c55e;  // green-500
  --bottom-bar-bg:      color-mix(in oklch, #f9fafb 95%, transparent);
  --bottom-bar-border:  color-mix(in oklch, #ffffff 6%, transparent);
  --header-scrolled-bg: color-mix(in oklch, #f3f4f6 88%, transparent);
  --nutrition-bg:  color-mix(in oklch, #22c55e 6%, transparent);
  --nutrition-border: color-mix(in oklch, #22c55e 10%, transparent);
  --status-bar-bg:  transparent;
  --status-bar-text: #ffffff;
  --banner-bg: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
  --banner-label: #6b7280;
  --banner-badge-bg:    color-mix(in oklch, #1a1a1a 90%, transparent);
  --banner-badge-border: color-mix(in oklch, #ffffff 10%, transparent);
  --banner-badge-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  --nutrition-glow: color-mix(in oklch, #22c55e 20%, transparent);
}

// ── Animation Keyframes ─────────────────────────────────────
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

// ── Reduced Motion ──────────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji,
  .nutrition-card,
  .health-card,
  .advice-card,
  .banner-badge {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

- [ ] **Commit this change**

```bash
git add web/apps/uniapp/src/styles/design-system.scss
git commit -m "feat(uniapp): simplify design-system.scss - remove palette+component layers"
```

---

### Task 0.5: Verify rpx support

- [ ] **Step 1: Add a test class to the simplest component temporarily**

In `web/apps/uniapp/src/pages/scan/index.vue`, temporarily add class `w-[80rpx]` to the view:
```html
<view class="scan-page flex justify-center items-center h-screen w-[80rpx]">
```

- [ ] **Step 2: Build H5**

```bash
cd /Users/wwj/Desktop/self/life-classics/web
pnpm build:uniapp:h5 2>&1 | tail -20
```

- [ ] **Step 3: Check build output**

```bash
grep -r "80rpx\|\.5rem\|80px" web/apps/uniapp/dist/build/h5/static/css/ 2>/dev/null | head -10
```

Expected: `unocss-preset-uni` converts rpx to vw units for H5 (e.g., `w-[80rpx]` → `width: 10.667vw` based on 750rpx base). If output shows `80px` or `5rem`, the preset is not active — check vite.config.ts for correct plugin setup. If output shows vw values (e.g., `10.667vw`), that is correct H5 behavior for rpx.

- [ ] **Step 4: Remove the test class from scan/index.vue**

---

### Task 0.6: Write migration-guide.md

Create `web/apps/uniapp/src/migration-guide.md` with the following content:

```markdown
# UnoCSS Migration Guide

**This file is the ONLY reference for Phase 1 workers.**
**If a pattern is not listed here → keep in style block, add comment `// kept: not in migration guide`**

## Prerequisites

Before migrating any file:
1. Read `uno.config.ts` to understand all available shortcuts
2. Read `styles/design-system.scss` to understand available CSS variables
3. Remove `@import "@/styles/design-system.scss"` from the style block ONLY IF no SCSS variables ($ease-spring etc.) are used in that file's style block

---

## Rule 1: Simple properties → UnoCSS utilities

| CSS | UnoCSS class |
|-----|-------------|
| `display: flex` | `flex` |
| `display: block` | `block` |
| `display: inline-flex` | `inline-flex` |
| `display: inline-block` | `inline-block` |
| `flex-direction: column` | `flex-col` |
| `flex-direction: row` | `flex-row` |
| `align-items: center` | `items-center` |
| `align-items: start` | `items-start` |
| `align-items: flex-start` | `items-start` |
| `justify-content: center` | `justify-center` |
| `justify-content: between` | `justify-between` |
| `justify-content: flex-end` | `justify-end` |
| `flex-wrap: wrap` | `flex-wrap` |
| `flex: 1` | `flex-1` |
| `flex: 0 0 auto` | `flex-none` (or `shrink-0 grow-0`) |
| `flex-shrink: 0` | `shrink-0` |
| `position: relative` | `relative` |
| `position: absolute` | `absolute` |
| `position: fixed` | `fixed` |
| `position: sticky` | `sticky` |
| `top: 0` | `top-0` |
| `left: 0` | `left-0` |
| `right: 0` | `right-0` |
| `bottom: 0` | `bottom-0` |
| `z-index: 40` | `z-40` |
| `z-index: 50` | `z-50` |
| `z-index: 100` | `z-100` |
| `overflow: hidden` | `overflow-hidden` |
| `overflow-x: auto` | `overflow-x-auto` |
| `overflow-y: auto` | `overflow-y-auto` |
| `box-sizing: border-box` | `box-border` |
| `width: 100%` | `w-full` |
| `height: 100%` | `h-full` |
| `min-width: 0` | `min-w-0` |
| `cursor: pointer` | `cursor-pointer` |
| `cursor: not-allowed` | `cursor-not-allowed` |
| `pointer-events: none` | `pointer-events-none` |
| `pointer-events: auto` | `pointer-events-auto` |
| `white-space: nowrap` | `whitespace-nowrap` |
| `text-overflow: ellipsis` | `truncate` (combines overflow-hidden whitespace-nowrap text-ellipsis) |
| `text-align: center` | `text-center` |
| `letter-spacing: -0.02em` | `tracking-[-0.02em]` |
| `letter-spacing: 0.08em` | `tracking-[0.08em]` |
| `line-height: 1` | `leading-none` |
| `line-height: 1.2` | `leading-[1.2]` |
| `line-height: 1.6` | `leading-relaxed` |
| `font-weight: 500` | `font-medium` |
| `font-weight: 600` | `font-semibold` |
| `font-weight: 700` | `font-bold` |
| `opacity: 0.4` | `opacity-40` |
| `opacity: 0.5` | `opacity-50` |

---

## Rule 2: rpx values → arbitrary values

Use `[Nrpx]` syntax for ALL rpx values. Examples:

| CSS | UnoCSS class |
|-----|-------------|
| `width: 80rpx` | `w-[80rpx]` |
| `height: 88rpx` | `h-[88rpx]` |
| `padding: 20rpx 0` | `py-[20rpx] px-0` |
| `padding: 16rpx 32rpx` | `py-[16rpx] px-[32rpx]` |
| `padding: 32rpx 40rpx` | `py-[32rpx] px-[40rpx]` |
| `margin-top: 8rpx` | `mt-[8rpx]` |
| `margin-bottom: 24rpx` | `mb-[24rpx]` |
| `margin-left: auto` | `ml-auto` |
| `font-size: 20rpx` | `text-[20rpx]` |
| `font-size: 24rpx` | `text-[24rpx]` |
| `font-size: 26rpx` | `text-[26rpx]` |
| `font-size: 28rpx` | `text-[28rpx]` |
| `font-size: 30rpx` | `text-[30rpx]` |
| `font-size: 32rpx` | `text-[32rpx]` |
| `font-size: 34rpx` | `text-[34rpx]` |
| `font-size: 36rpx` | `text-[36rpx]` |
| `font-size: 52rpx` | `text-[52rpx]` |
| `border-radius: 8rpx` | `rounded-[8rpx]` |
| `border-radius: 12rpx` | `rounded-[12rpx]` |
| `border-radius: 16rpx` | `rounded-[16rpx]` |
| `border-radius: 24rpx` | `rounded-[24rpx]` |
| `border-radius: 28rpx` | `rounded-[28rpx]` |
| `border-radius: 32rpx` | `rounded-[32rpx]` |
| `border-radius: 40rpx` | `rounded-[40rpx]` |
| `border-radius: 48rpx` | `rounded-[48rpx]` |
| `border-radius: 50%` | `rounded-full` |
| `border-radius: 9999rpx` | `rounded-full` |
| `gap: 4rpx` | `gap-[4rpx]` |
| `gap: 8rpx` | `gap-[8rpx]` |
| `gap: 12rpx` | `gap-[12rpx]` |
| `gap: 16rpx` | `gap-[16rpx]` |
| `gap: 20rpx` | `gap-[20rpx]` |
| `gap: 24rpx` | `gap-[24rpx]` |
| `gap: 32rpx` | `gap-[32rpx]` |
| `h-screen` = `height: 100vh` | `h-screen` |
| `min-height: 100vh` or `min-h-screen` | `min-h-screen` |

---

## Rule 3: CSS variables → arbitrary value syntax

| CSS | UnoCSS class |
|-----|-------------|
| `color: var(--text-primary)` | `text-[var(--text-primary)]` |
| `color: var(--text-secondary)` | `text-[var(--text-secondary)]` |
| `color: var(--text-muted)` | `text-[var(--text-muted)]` |
| `color: #ffffff` or `color: white` | `text-white` |
| `background: var(--bg-card)` | `bg-[var(--bg-card)]` |
| `background: var(--bg-base)` | `bg-[var(--bg-base)]` |
| `background: var(--bg-card-hover)` | `bg-[var(--bg-card-hover)]` |
| `background: transparent` | `bg-transparent` |
| `border: 1px solid var(--border-color)` | `border border-[var(--border-color)]` |
| `border-bottom: 1px solid var(--border-color)` | `border-b border-[var(--border-color)]` |
| `border-top: 1px solid var(--border-color)` | `border-t border-[var(--border-color)]` |
| `border: none` | `border-none` |
| `border-radius: var(--radius-lg)` | `rounded-[var(--radius-lg)]` |
| `border-radius: var(--radius-xl)` | `rounded-[var(--radius-xl)]` |
| `box-shadow: var(--shadow-sm)` | `shadow-[var(--shadow-sm)]` |
| `color: var(--risk-t4)` | `text-[var(--risk-t4)]` |
| `color: var(--accent)` | `text-[var(--accent)]` |

---

## Rule 4: Pseudo-classes

| CSS | UnoCSS class |
|-----|-------------|
| `&:active { transform: scale(0.97) }` | `active:scale-97` |
| `&:active { transform: scale(0.96) }` | `active:scale-[0.96]` |
| `&:active { transform: scale(0.95) }` | `active:scale-95` |
| `&:active { transform: scale(0.92) }` | `active:scale-[0.92]` |
| `&:active { transform: scale(0.98) }` | `active:scale-[0.98]` |
| `&:active { background: var(--bg-card-hover) }` | `active:bg-[var(--bg-card-hover)]` |
| `&:disabled { opacity: 0.5 }` | `disabled:opacity-50` |
| `&:disabled { cursor: not-allowed }` | `disabled:cursor-not-allowed` |
| `&:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }` | `focus-visible:outline-2 focus-visible:outline-[var(--accent)] focus-visible:outline-offset-2` |
| `&:last-child { border-bottom: none }` | `last:border-b-0` |

---

## Rule 5: Transitions

| CSS | UnoCSS shortcut |
|-----|----------------|
| `transition: all 0.2s $ease-spring` | `transition-spring` |
| `transition: all 0.3s $ease-spring` | `transition-spring-slow` |
| `transition: all 0.4s $ease-spring` | `transition-spring-400` |
| `transition: transform 0.15s ease` | `transition-transform duration-150 ease-in-out` |
| `transition: background 0.15s ease` | `transition-colors duration-150 ease-in-out` |
| `transition: background 0.4s $ease-spring, box-shadow 0.4s $ease-spring` | keep in style block: `// kept: multiple property transition` |

---

## Rule 6: UnoCSS shortcuts (defined in uno.config.ts)

These are compound shortcuts. Use them as single class names:

| Shortcut class | What it applies |
|---------------|----------------|
| `card` | bg-card + border + rounded-xl + shadow |
| `icon-bg-blue` | blue tinted background + blue text |
| `icon-bg-red` | risk-t4 tinted background + risk-t4 text |
| `icon-bg-purple` | purple tinted background + purple text |
| `icon-bg-green` | green tinted background + green text |
| `icon-bg-orange` | risk-t3 tinted background + risk-t3 text |
| `ai-label` | gradient background + white text + padding + rounded |
| `chip-risk` | red background + red text + red border |
| `chip-warn` | yellow background + yellow text + yellow border |
| `chip-neutral` | gray background + secondary text |
| `risktag-t4` through `risktag-unknown` | risk-level background + matching text color |
| `risk-group-t4` through `risk-group-unknown` | risk group container bg + border |
| `risk-reason-t4` through `risk-reason-unknown` | risk reason tag bg + text |
| `icon-x` | red circle bg + red text |
| `icon-check-green` | green circle bg + green text |
| `icon-check-yellow` | yellow circle bg + yellow text |
| `transition-spring` | 200ms spring transition |
| `transition-spring-slow` | 300ms spring transition |
| `btn-primary` | gradient bg + white text + shadow + active/disabled states |
| `btn-secondary` | card bg + border + active/disabled states |
| `btn-ghost` | transparent + active/disabled states |
| `risk-badge-critical` through `risk-badge-unknown` | for RiskBadge component levels |
| `scan-count-badge` | red tinted badge for scan count |

---

## Rule 7: Gradient backgrounds

| CSS | UnoCSS class |
|-----|-------------|
| `background: linear-gradient(135deg, var(--accent-light), var(--accent))` | `bg-gradient-to-br from-[var(--accent-light)] to-[var(--accent)]` |
| `background: linear-gradient(135deg, var(--palette-pink-400), var(--palette-pink-500))` | `bg-gradient-to-br from-pink-400 to-pink-500` |
| Complex gradients with more than 2 stops | **keep in style block**: `// kept: complex gradient` |

---

## Rule 8: SVG dimensions

For SVG elements inside style blocks:
```scss
svg { width: 36rpx; height: 36rpx; }
```
→ Add to the SVG element in template: `class="w-[36rpx] h-[36rpx]"`

---

## ⛔ KEEP IN STYLE BLOCK — These CANNOT be atomic

These patterns must always stay in `<style>`:

1. **`::before` / `::after` pseudo-elements** — keep with comment `// kept: pseudo-element`
2. **`@keyframes`** — keep with comment `// kept: keyframes`
3. **`backdrop-filter`** — keep with comment `// kept: backdrop-filter`
4. **`:deep(...)` selectors** — keep with comment `// kept: :deep selector for UniApp scroll wrapper`
5. **`::-webkit-scrollbar`** — keep with comment `// kept: scrollbar hide`
6. **CSS custom property definitions** (e.g., `.risk-critical { --risk-header-bg: ... }`) — keep with comment `// kept: CSS custom property definition`
7. **Parent context selectors** like `.header--scrolled & { ... }` — keep with comment `// kept: parent context selector`
8. **`env(safe-area-inset-bottom)`** — keep with comment `// kept: safe area env()`
9. **Multiple-property transitions on same element** — keep with comment `// kept: multi-prop transition`
10. **Nested SCSS that creates compound selectors** that cannot be expressed in UnoCSS — keep with comment

---

## Template Class Replacement Pattern

When an old CSS class (e.g., `.foo`) has ALL its properties convertible:
1. On the element: add the UnoCSS classes to the `class` attribute
2. Remove the old class name from the `class` attribute
3. Delete the `.foo { ... }` rule from the style block

When an old CSS class has SOME properties convertible (mixed):
1. Keep the old class name on the element (it still has styles in the style block)
2. Add the newly atomic UnoCSS classes alongside it
3. In the style block, keep only the non-atomic properties for that class

When an old CSS class is used dynamically (`:class="['foo', varName]"`):
- The class name must exist in uno.config.ts shortcuts OR style block
- Do NOT remove the class name from `:class` bindings without verifying its new home
```

- [ ] **Commit migration guide**

```bash
git add web/apps/uniapp/src/migration-guide.md
git commit -m "docs(uniapp): add migration-guide.md for Phase 1"
```

---

### Task 0.7: Phase 0 validation commit

- [ ] **Build H5 to check no regressions**

```bash
cd /Users/wwj/Desktop/self/life-classics/web
pnpm build:uniapp:h5 2>&1 | grep -E "error|Error|warn|built" | tail -20
```

Build should succeed. If it fails due to missing CSS variables, add them to design-system.scss.

- [ ] **Final Phase 0 commit**

```bash
git add -A
git commit -m "feat(uniapp): Phase 0 complete - reverted migration, unocss-preset-uni setup, simplified design-system"
```

---

## Phase 1: Component Migration (Junior Model)

> **START OF EACH SESSION:** Read `migration-guide.md`, `uno.config.ts`, `design-system.scss` BEFORE any edits.
> **END OF EACH SESSION:** Commit and close.

---

### Task 1.1: Batch 1 — Trivial files

**Files:** `pages/scan/index.vue`, `components/ListItem.vue`, `components/RiskBadge.vue`, `components/InfoChip.vue`

#### File: `pages/scan/index.vue`

The current style block is:
```scss
.hint { color: #888; font-size: 28rpx; }
```

**Migration:**
- Replace `.hint` with atomic classes on the `<text>` element
- Delete entire `<style>` block

Final template `<text>` line:
```html
<text class="text-[#888] text-[28rpx]">正在启动扫码...</text>
```

Final file has **no `<style>` block**.

---

#### File: `components/ListItem.vue`

Current `<template>` root view: `class="flex items-start gap-4"` — already has atomic classes, keep.

Current style block contains `.list-item-icon` and `.list-item-text`.

**`.list-item-text` — fully atomic:**
```scss
font-size: 26rpx;       → text-[26rpx]
color: var(--text-secondary); → text-[var(--text-secondary)]
line-height: 1.6;       → leading-relaxed
```

Add to the `<text class="list-item-text flex-1">` element: `text-[26rpx] text-[var(--text-secondary)] leading-relaxed`
Remove `.list-item-text` class name from element, delete rule from style.

**`.list-item-icon` — partially atomic:**
```scss
width: 36rpx; height: 36rpx; → w-[36rpx] h-[36rpx]
border-radius: 50%;           → rounded-full
font-size: 20rpx;             → text-[20rpx]
font-weight: 700;             → font-bold
```
The variant classes `&.icon-x { ... }` etc. are now shortcuts in uno.config.ts (`icon-x`, `icon-check-green`, `icon-check-yellow`). These are already in the safelist.

SVG inside: `svg { width: 24rpx; height: 24rpx; }` → add `class="w-[24rpx] h-[24rpx]"` to both SVG elements in template.

Final template:
```html
<template>
  <view class="flex items-start gap-4">
    <view :class="['w-[36rpx] h-[36rpx] rounded-full text-[20rpx] font-bold flex items-center justify-center shrink-0 mt-1', `icon-${icon}`]">
      <svg v-if="icon === 'x'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="w-[24rpx] h-[24rpx]" aria-hidden="true">
        <path d="M18 6L6 18M6 6l12 12"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="w-[24rpx] h-[24rpx]" aria-hidden="true">
        <path d="M20 6L9 17l-5-5"/>
      </svg>
    </view>
    <text class="flex-1 text-[26rpx] text-[var(--text-secondary)] leading-relaxed">{{ text }}</text>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/RiskBadge.vue`

Current style block:
```scss
.risk-badge {
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  font-size: 28rpx;
  &--critical { background: ...; color: ...; }
  ...
}
```

The `whoLevel` → `level` computed returns: `'critical'`, `'high'`, `'medium'`, `'low'`, `'unknown'`.

In uno.config.ts there are shortcuts: `risk-badge-critical`, `risk-badge-high`, etc.

Final template:
```html
<template>
  <view :class="['inline-flex items-center py-[4rpx] px-[12rpx] rounded-[8rpx] text-[28rpx]', `risk-badge-${level}`]">
    <text>{{ label }}</text>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/InfoChip.vue`

Current style block:
```scss
.info-chip {
  font-size: 20rpx; padding: 4rpx 16rpx; border-radius: 24rpx;
  font-weight: 500; box-sizing: border-box; white-space: nowrap;
  &.chip-risk { ... }
  &.chip-warn { ... }
  &.chip-neutral { ... }
}
```

The `chip-risk`, `chip-warn`, `chip-neutral` shortcuts are defined in uno.config.ts.

Final template:
```html
<template>
  <text :class="['inline-flex items-center text-[20rpx] py-[4rpx] px-[16rpx] rounded-[24rpx] font-medium box-border whitespace-nowrap', `chip-${variant}`]">{{ text }}</text>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

- [ ] **Verify: all 4 files have no `<style>` block or only empty one**
- [ ] **Build H5**

```bash
cd /Users/wwj/Desktop/self/life-classics/web
pnpm build:uniapp:h5 2>&1 | grep -E "error|Error" | head -10
```

- [ ] **Commit**

```bash
git add web/apps/uniapp/src/pages/scan/index.vue \
        web/apps/uniapp/src/components/ListItem.vue \
        web/apps/uniapp/src/components/RiskBadge.vue \
        web/apps/uniapp/src/components/InfoChip.vue
git commit -m "feat(uniapp): Batch 1 - migrate scan, ListItem, RiskBadge, InfoChip to UnoCSS"
```

---

### Task 1.2: Batch 2 — Simple components

**Files:** `components/SectionHeader.vue`, `components/StateView.vue`, `components/RiskTag.vue`, `components/HorizontalScroller.vue`

#### File: `components/SectionHeader.vue`

The current template has: `class="section-header flex items-center gap-4 mb-5 pb-4"` and `class="section-title flex-1"`.

Current style block:
- `.section-header { border-bottom: 1px solid var(--border-color); }` → add `border-b border-[var(--border-color)]` to template
- `.section-icon-wrap` + icon-bg variants → use `icon-bg-*` shortcuts from uno.config.ts
- `.section-title` → `text-[26rpx] font-bold text-[var(--text-primary)]`
- `.ai-label` → use `ai-label` shortcut

Final template:
```html
<template>
  <view class="flex items-center gap-4 mb-5 pb-4 border-b border-[var(--border-color)]">
    <view :class="['w-[36rpx] h-[36rpx] rounded-[24rpx] flex items-center justify-center shrink-0', `icon-bg-${icon}`]">
      <slot name="icon" />
    </view>
    <text class="flex-1 text-[26rpx] font-bold text-[var(--text-primary)]">{{ title }}</text>
    <view v-if="showAiBadge" class="ai-label">AI</view>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/StateView.vue`

Current style block:
- `.state-view__message`: `font-size: 26rpx; color: var(--text-muted); text-align: center;`
- `.state-view__action`: complex with padding, border-radius, font-size, background, border, color, cursor + `:active`

Final template:
```html
<template>
  <view :class="['flex flex-col items-center justify-center gap-8', `state-view--${state}`]">
    <template v-if="state === 'loading'">
      <up-loading-icon mode="circle" />
      <text class="text-[26rpx] text-[var(--text-muted)] text-center">{{ message || "加载中..." }}</text>
    </template>
    <template v-else-if="state === 'empty'">
      <text class="text-[26rpx] text-[var(--text-muted)] text-center">{{ message || "暂无数据" }}</text>
    </template>
    <template v-else-if="state === 'error'">
      <text class="text-[26rpx] text-[var(--text-muted)] text-center">{{ message || "请求失败" }}</text>
      <button
        v-if="actionLabel"
        class="py-[12rpx] px-[32rpx] rounded-[32rpx] text-[26rpx] font-medium bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] cursor-pointer active:bg-[var(--bg-card-hover)]"
        @click="$emit('retry')"
      >
        {{ actionLabel }}
      </button>
    </template>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/RiskTag.vue`

The `level` computed returns: `'t4'`, `'t3'`, `'t2'`, `'t1'`, `'t0'`, `'unknown'`.
Shortcuts `risktag-t4` through `risktag-unknown` are in uno.config.ts.

The `--sm` variant only changes font-size and padding. Handle via conditional classes.

Final template:
```html
<template>
  <view :class="[
    'inline-flex items-center rounded-full font-semibold text-[20rpx] py-[4rpx]',
    size === 'sm' ? 'px-[12rpx]' : 'px-[16rpx]',
    `risktag-${level}`
  ]">
    <text>{{ config.badge }}</text>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/HorizontalScroller.vue`

Current style block:
```scss
.horizontal-scroller {
  :deep(.uni-scroll-view:first-child) { overflow: hidden; }
  &::-webkit-scrollbar { display: none; }
}
```

Both rules CANNOT be expressed atomically:
- `:deep(...)` → must stay
- `::-webkit-scrollbar` → must stay

The `scroll-x` attribute is already on the element. The class `horizontal-scroller` is needed for these style rules.

Final `<style>` block:
```scss
.horizontal-scroller {
  // kept: :deep selector for UniApp scroll wrapper
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  // kept: scrollbar hide
  &::-webkit-scrollbar { display: none; }
}
```

Template: unchanged (no atomic changes needed for the template).

---

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/components/SectionHeader.vue \
        web/apps/uniapp/src/components/StateView.vue \
        web/apps/uniapp/src/components/RiskTag.vue \
        web/apps/uniapp/src/components/HorizontalScroller.vue
git commit -m "feat(uniapp): Batch 2 - migrate SectionHeader, StateView, RiskTag, HorizontalScroller"
```

---

### Task 1.3: Batch 3 — Medium components

**Files:** `components/ActionButton.vue`, `components/InfoCard.vue`, `components/AnalysisCard.vue`, `components/NutritionTable.vue`

#### File: `components/ActionButton.vue`

The `btn-primary`, `btn-secondary`, `btn-ghost` shortcuts are in uno.config.ts.
Size variants (`--lg` and `--md`) need per-variant classes.

Final template:
```html
<template>
  <button
    :class="[
      'w-full border-none font-semibold cursor-pointer inline-flex items-center justify-center gap-2 transition-spring',
      variant === 'primary'   ? 'btn-primary'   : '',
      variant === 'secondary' ? 'btn-secondary' : '',
      variant === 'ghost'     ? 'btn-ghost'     : '',
      size === 'lg' ? 'h-[88rpx] px-[32rpx] text-[28rpx] rounded-[28rpx]' : '',
      size === 'md' ? 'h-[72rpx] px-[24rpx] text-[26rpx] rounded-[32rpx]' : '',
    ]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <up-loading-icon v-if="loading" class="w-[28rpx] h-[28rpx]" />
    <svg v-else-if="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-[28rpx] h-[28rpx]" aria-hidden="true">
      <path :d="icon" />
    </svg>
    <text>{{ label }}</text>
  </button>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/InfoCard.vue`

The `paddingMap` uses `--card-padding-*` CSS vars that no longer exist. Change to rpx values directly.

Update the script `paddingMap`:
```ts
const paddingMap: Record<PaddingLevel, string> = {
  sm:  '24rpx',
  md:  '32rpx',
  lg:  '40rpx',
  xl:  '48rpx',
  '2xl': '56rpx',
  '3xl': '64rpx',
}
```

The radiusMap already uses CSS vars that exist (`--radius-lg`, `--radius-xl`). Keep as-is.

Current style block:
```scss
.info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;
}
```
All atomic.

Final template:
```html
<template>
  <view class="bg-[var(--bg-card)] border border-[var(--border-color)] box-border w-full overflow-hidden" :style="cardStyle">
    <slot />
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

#### File: `components/AnalysisCard.vue`

Current style block classes: `.analysis-card`, `.card-title`, `.level-badge`, `.card-content`.

`.analysis-card`:
- `background: var(--bg-card)` → `bg-[var(--bg-card)]`
- `border-radius: 16rpx` → `rounded-[16rpx]`
- `padding: 28rpx` → `p-[28rpx]`
- `margin-bottom: 20rpx` → `mb-[20rpx]`
- `border-left: 6rpx solid var(--border-color)` → keep in style (no `border-l-[6rpx]` with arbitrary color in standard UnoCSS — use style block)

Actually `border-l-[6rpx] border-l-[var(--border-color)]` — check if this works. Use style block to be safe.

For `.analysis-card--t4`, `--t3`, etc. (changes only `border-left-color`):
These are dynamic classes. Use style block for border-left-color overrides.

`.card-title`: `font-size: 30rpx; font-weight: 600; color: var(--text-primary);` → all atomic
`.card-content`: `font-size: 28rpx; color: var(--text-secondary); line-height: 1.6;` → all atomic

`.level-badge`: `padding: 4rpx 16rpx; border-radius: 9999rpx; font-size: 28rpx;` → atomic; color variants use `risktag-*` shortcuts.

Final template:
```html
<template>
  <view :class="['bg-[var(--bg-card)] rounded-[16rpx] p-[28rpx] mb-[20rpx] analysis-card', `analysis-card--${item.level}`]">
    <view class="flex justify-between items-center mb-4">
      <text class="text-[30rpx] font-semibold text-[var(--text-primary)]">{{ ANALYSIS_LABELS[item.analysis_type] ?? item.analysis_type }}</text>
      <view :class="['py-[4rpx] px-[16rpx] rounded-full text-[28rpx]', `risktag-${item.level}`]">
        <text>{{ LEVEL_LABELS[item.level] ?? item.level }}</text>
      </view>
    </view>
    <text class="text-[28rpx] text-[var(--text-secondary)] leading-relaxed">{{ extractSummary(item.results) }}</text>
  </view>
</template>
```

Final `<style>` block (keep only border-left rules):
```scss
@import "@/styles/design-system.scss";

.analysis-card {
  // kept: border-left with arbitrary rpx width — cannot combine width+color atomically
  border-left: 6rpx solid var(--border-color);

  &--t4 { border-left-color: var(--risk-t4); }
  &--t3 { border-left-color: var(--risk-t3); }
  &--t2 { border-left-color: var(--risk-t2); }
  &--t1 { border-left-color: var(--risk-t1); }
  &--t0 { border-left-color: var(--risk-t0); }
}
```

> **Bug fix note:** Original code had `&--t0 { background: var(--risktag-t1-bg); color: var(--risk-t1); }` — this was a copy-paste bug using t1 values for t0. The migrated `risktag-t0` shortcut correctly uses `var(--risk-t0)`. This is an intentional fix.

---

#### File: `components/NutritionTable.vue`

This file does NOT import design-system.scss and uses hardcoded colors (#888, #333, #555, #aaa).

All properties are atomic. No dark mode handling (hardcoded colors stay hardcoded).

Final template (remove all CSS class names, inline everything):
```html
<template>
  <view class="w-full">
    <view v-for="group in grouped" :key="group.label" class="mb-[32rpx]">
      <text class="block text-[26rpx] text-[#888] mb-2">{{ group.label }}</text>
      <view class="flex justify-between py-[16rpx] border-b border-[#f0f0f0] font-bold">
        <text class="text-[28rpx] text-[#333]">营养成分</text>
        <text class="text-[28rpx] text-[#333]">每{{ group.referenceUnit }}</text>
      </view>
      <view v-for="item in group.items" :key="item.name" class="flex justify-between py-[16rpx] border-b border-[#f0f0f0]">
        <text class="text-[28rpx] text-[#333]">{{ item.name }}</text>
        <text class="text-[28rpx] text-[#555]">{{ item.value }} {{ item.value_unit }}</text>
      </view>
    </view>
    <text v-if="nutritions.length === 0" class="text-[#aaa] text-[28rpx]">暂无营养成分数据</text>
  </view>
</template>
```

Final `<style>` block: **empty, delete it entirely.**

---

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/components/ActionButton.vue \
        web/apps/uniapp/src/components/InfoCard.vue \
        web/apps/uniapp/src/components/AnalysisCard.vue \
        web/apps/uniapp/src/components/NutritionTable.vue
git commit -m "feat(uniapp): Batch 3 - migrate ActionButton, InfoCard, AnalysisCard, NutritionTable"
```

---

### Task 1.4: Batch 4 — Complex components

**Files:** `components/IngredientList.vue`, `components/ProductHeader.vue`, `components/BottomBar.vue`

#### File: `components/IngredientList.vue`

Current style rules:
- `.ingredient-list { width: 100%; }` → `w-full` on root element
- `.ingredient-item { padding: 20rpx 0; border-bottom: 1rpx solid var(--border-color); }` → `py-[20rpx] border-b border-[var(--border-color)]`
- `.ingredient-item--risk { background: color-mix(...); border-radius: 8rpx; padding: 16rpx; }` → keep in style (color-mix on bg)
- `.ingredient-name { font-size: 30rpx; color: var(--text-primary); }` → atomic
- `.ingredient-meta { display: block; font-size: 24rpx; color: var(--text-muted); margin-top: 8rpx; }` → atomic
- `.ingredient-allergen { display: block; font-size: 24rpx; color: var(--risk-t4); margin-top: 8rpx; }` → atomic
- `.empty { color: var(--text-muted); font-size: 28rpx; }` → atomic

Final template:
```html
<template>
  <view class="w-full">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['py-[20rpx] border-b border-[var(--border-color)]', isHighRisk(item.who_level) && 'ingredient-item--risk']"
    >
      <view class="flex items-center justify-between">
        <text class="text-[30rpx] text-[var(--text-primary)]">{{ item.name }}</text>
        <RiskBadge :who-level="item.who_level" />
      </view>
      <text v-if="item.function_type" class="block text-[24rpx] text-[var(--text-muted)] mt-[8rpx]">
        {{ item.function_type }}
      </text>
      <text v-if="item.allergen_info" class="block text-[24rpx] text-[var(--risk-t4)] mt-[8rpx]">
        过敏提示：{{ item.allergen_info }}
      </text>
    </view>
    <text v-if="ingredients.length === 0" class="text-[var(--text-muted)] text-[28rpx]">暂无配料数据</text>
  </view>
</template>
```

Final `<style>` block:
```scss
@import "@/styles/design-system.scss";

.ingredient-item--risk {
  // kept: color-mix not expressible atomically with arbitrary percentage
  background: color-mix(in oklch, var(--risk-t4) 4%, transparent);
  border-radius: 8rpx;
  padding: 16rpx;
}
```

---

#### File: `components/ProductHeader.vue`

This component has complex scroll-dependent state transitions that must largely stay in the style block.

Properties that CAN be moved to template:
- `.product-header`: `position: fixed; top: 0; left: 0; right: 0; z-index: 50; pointer-events: none;`
  → `fixed top-0 left-0 right-0 z-50 pointer-events-none`
- `.header`: `position: fixed; left: 0; right: 0;` → `fixed left-0 right-0`
  `padding: 16rpx 32rpx` → `py-[16rpx] px-[32rpx]`
  `background: transparent` → `bg-transparent`
  But the `transition` and `&--scrolled` state → keep in style

`.header-btn`:
- `width: 80rpx; height: 80rpx;` → `w-[80rpx] h-[80rpx]`
- `border-radius: 24rpx;` → `rounded-[24rpx]`
- `background: transparent; border: none;` → `bg-transparent border-none`
- `-webkit-appearance: none; appearance: none;` → keep in style
- `&:active { transform: scale(0.92); background: ... }` → `active:scale-[0.92]`
- `color: #ffffff;` → `text-white` (initial state)
- The `.header--scrolled &` nested rule → keep in style

`.header-title`: `font-size: 34rpx; font-weight: 600; letter-spacing: -0.02em; color: #ffffff;`
→ `text-[34rpx] font-semibold tracking-[-0.02em] text-white`
But the `.header--scrolled &` override → keep in style

SVG: `width: 36rpx; height: 36rpx;` → add `class="w-[36rpx] h-[36rpx]"` to both SVGs

Final template:
```html
<template>
  <view class="fixed top-0 left-0 right-0 z-50 pointer-events-none">
    <view
      class="header fixed left-0 right-0 py-[16rpx] px-[32rpx] flex items-center gap-6 bg-transparent pointer-events-auto"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: statusBarHeight + 'px' }"
    >
      <button type="button" class="header-btn w-[80rpx] h-[80rpx] rounded-[24rpx] bg-transparent border-none flex items-center justify-center shrink-0 active:scale-[0.92] text-white" aria-label="返回" @click="handleBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-[36rpx] h-[36rpx]" aria-hidden="true">
          <path d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <text class="header-title flex-1 text-[34rpx] font-semibold tracking-[-0.02em] text-white">{{ name }}</text>
      <button type="button" class="header-btn w-[80rpx] h-[80rpx] rounded-[24rpx] bg-transparent border-none flex items-center justify-center shrink-0 active:scale-[0.92] text-white" aria-label="分享" @click="handleShare">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-[36rpx] h-[36rpx]" aria-hidden="true">
          <path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
        </svg>
      </button>
    </view>
  </view>
</template>
```

Final `<style>` block:
```scss
@import "@/styles/design-system.scss";

.header {
  // kept: multi-prop transition
  transition: background 0.4s $ease-spring, box-shadow 0.4s $ease-spring;

  &--scrolled {
    background: var(--header-scrolled-bg);
    // kept: backdrop-filter
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 1px 0 rgba(255, 255, 255, 0.06);
    // kept: parent context selector for light mode box-shadow override
    .product-page:not(.dark-mode) & {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 0 rgba(0, 0, 0, 0.04);
    }
  }
}

.header-btn {
  // kept: appearance reset
  -webkit-appearance: none;
  appearance: none;
  outline: none;
  cursor: pointer;
  // kept: parent context selector
  .header--scrolled & {
    color: var(--text-primary);
  }
  &:active {
    // kept: rgba background on active (complements active:scale-[0.92] in template)
    background: rgba(128, 128, 128, 0.15);
  }
  &:focus-visible {
    // Note: original used var(--accent-pink) which was removed; var(--accent) is equivalent
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.header-title {
  // kept: parent context selector
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  transition: color 0.3s $ease-spring, text-shadow 0.3s $ease-spring;
  .header--scrolled & {
    color: var(--text-primary);
    text-shadow: none;
  }
}
```

---

#### File: `components/BottomBar.vue`

The `.bottom-bar` container has complex styles (fixed, padding with safe-area, backdrop-filter).
The `.action-btn` has gradient, box-shadow, transitions, and a parent context selector `.product-page:not(.dark-mode) &`.

Properties that CAN be moved:
- `.bottom-bar`: `position: fixed; bottom: 0; left: 0; right: 0; z-index: 40;` → `fixed bottom-0 left-0 right-0 z-40`
- `.action-btn` common: `flex: 1; border-radius: 28rpx; font-size: 28rpx; font-weight: 600; font-family: inherit; cursor: pointer; border: none; appearance: none; line-height: 1.2; box-sizing: border-box; padding: 28rpx 32rpx;`
  → `flex-1 rounded-[28rpx] text-[28rpx] font-semibold cursor-pointer border-none box-border leading-[1.2] py-[28rpx] px-[32rpx]`

Properties that CANNOT be moved:
- `backdrop-filter`, `padding-bottom: calc(32rpx + env(...))`, parent context selector, box-shadow on `:active`

Final template:
```html
<template>
  <view class="bottom-bar fixed bottom-0 left-0 right-0 z-40 flex gap-6">
    <button type="button" class="action-btn action-btn--secondary flex-1 rounded-[28rpx] text-[28rpx] font-semibold cursor-pointer border-none box-border leading-[1.2] py-[28rpx] px-[32rpx]" @click="emit('add-record')">
      添加到记录
    </button>
    <button type="button" class="action-btn action-btn--primary flex-1 rounded-[28rpx] text-[28rpx] font-semibold cursor-pointer border-none box-border leading-[1.2] py-[28rpx] px-[32rpx]" @click="emit('chat')">
      咨询 AI 助手
    </button>
  </view>
</template>
```

Final `<style>` block:
```scss
@import "@/styles/design-system.scss";

.bottom-bar {
  // kept: safe-area env()
  padding: 32rpx 40rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  background: var(--bottom-bar-bg);
  // kept: backdrop-filter
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-top: 1px solid var(--bottom-bar-border);
}

.action-btn {
  -webkit-appearance: none;
  appearance: none;
  min-height: 0;
  // kept: multi-prop transition
  transition: all 0.2s $ease-spring;

  &:active { transform: scale(0.97); }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  &--primary {
    color: #fff;
    background: linear-gradient(135deg, var(--accent-light), var(--accent));
    // kept: complex box-shadow with color-mix
    box-shadow: 0 4px 20rpx color-mix(in oklch, var(--accent) 30%, transparent);
    &:active {
      box-shadow: 0 6px 28rpx color-mix(in oklch, var(--accent) 40%, transparent);
    }
  }

  &--secondary {
    background: color-mix(in oklch, #ffffff 6%, transparent);
    border: 1px solid color-mix(in oklch, #ffffff 10%, transparent);
    color: var(--text-primary);
    // kept: parent context selector
    .product-page:not(.dark-mode) & {
      background: color-mix(in oklch, var(--palette-gray-900) 4%, transparent);
      border-color: color-mix(in oklch, var(--palette-gray-900) 8%, transparent);
    }
  }
}
```

> **Note:** `.product-page:not(.dark-mode) &` references `--palette-gray-900`. Since we removed the palette CSS vars, replace `var(--palette-gray-900)` with `#111827` (the hex value).

---

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/components/IngredientList.vue \
        web/apps/uniapp/src/components/ProductHeader.vue \
        web/apps/uniapp/src/components/BottomBar.vue
git commit -m "feat(uniapp): Batch 4 - migrate IngredientList, ProductHeader, BottomBar"
```

---

### Task 1.5: Batch 5 — IngredientSection component

**Files:** `components/IngredientSection.vue` (complex, gets its own batch)

This component has 179 lines of SCSS and uses many dynamic class patterns.

**Key changes required:**

1. **`.risk-group` + level variant** — use `risk-group-*` shortcuts:
   Change `:class="['risk-group', levelKey]"` → `:class="['rounded-[40rpx] p-[32rpx] mb-[24rpx] relative overflow-hidden', `risk-group-${levelKey}`]"`

2. **`.risk-dot`** — use dynamic color:
   Change `:class="['risk-dot', levelKey]"` → keep `.risk-dot` + level class, keep style rules (box-shadow with CSS var can't be atomic)

3. **`.risk-badge`** inside the group header — uses parent context `.t4 &`:
   The current code is: `:class="['risk-badge', levelKey]"` where level is the OUTER group's level.
   Actually looking at the template: `<view :class="['risk-badge', levelKey]">` where `levelKey` is the group level.
   These can use `risktag-*` shortcuts: change to `:class="['text-[24rpx] font-semibold py-[8rpx] px-[20rpx] rounded-[24rpx]', `risktag-${levelKey}`]"`

4. **`.risk-count`** → atomic: `text-[28rpx] text-[var(--text-muted)] ml-auto`

5. **`.ingredient-scroll`** → keep `:deep` and scrollbar rules in style

6. **`.ingredient-card`** + level variants — card styling + active state:
   Base: `flex-none w-[280rpx] rounded-[32rpx] p-[28rpx] relative overflow-hidden cursor-pointer bg-[var(--bg-card)] border border-[var(--border-color)] active:scale-[0.96] box-border`
   Border color variant: keep as style rules since it's a border-color-only override

7. **`.risk-bar`** — absolute positioned with box-shadow → keep in style (::before/absolute with box-shadow)

8. **`.ingredient-arrow`** → atomic: `absolute right-[12rpx] top-[12rpx] w-[28rpx] h-[28rpx] opacity-40 text-[var(--text-muted)]`

9. **`.ingredient-content`** → already has atomic classes in template

10. **`.ingredient-name-text`** → `text-[26rpx] font-semibold text-[var(--text-primary)]`

11. **`.ingredient-reason`** + level → use `risk-reason-*` shortcuts

12. **`.ingredient-card::before`** → keep in style (pseudo-element)

13. **`.icon` inside ingredient-name** → `w-[28rpx] h-[28rpx] shrink-0`

Final `<style>` block (what remains):
```scss
@import "@/styles/design-system.scss";

// ── Scroll wrapper ─────────────────────────────────────────
.ingredient-scroll {
  // kept: :deep selector for UniApp scroll wrapper
  :deep(.uni-scroll-view:first-child) { overflow: hidden; }
  // kept: scrollbar hide
  &::-webkit-scrollbar { display: none; }
}

// ── Risk dot (glow box-shadow can't be atomic) ─────────────
.risk-dot {
  &.t4 { background: var(--risk-t4); box-shadow: 0 0 8px var(--risk-t4); }
  &.t3 { background: var(--risk-t3); box-shadow: 0 0 8px var(--risk-t3); }
  &.t2 { background: var(--risk-t2); box-shadow: 0 0 8px var(--risk-t2); }
  &.t1 { background: var(--risk-t1); box-shadow: 0 0 8px var(--risk-t1); }
  &.t0 { background: var(--risk-t0); box-shadow: 0 0 8px var(--risk-t0); }
  &.unknown { background: var(--risk-unknown); }
}

// ── Card border color variants ─────────────────────────────
.ingredient-card {
  // kept: multi-prop transition
  transition: transform 0.2s $ease-spring;

  &.t4 { border-color: color-mix(in oklch, var(--risk-t4) 25%, transparent); }
  &.t3 { border-color: color-mix(in oklch, var(--risk-t3) 25%, transparent); }
  &.t2 { border-color: color-mix(in oklch, var(--risk-t2) 25%, transparent); }
  &.t1 { border-color: color-mix(in oklch, var(--risk-t1) 25%, transparent); }
  &.t0 { border-color: color-mix(in oklch, var(--risk-t0) 25%, transparent); }
  &.unknown { border-color: var(--border-color); }

  // kept: pseudo-element
  &::before {
    content: "";
    position: absolute;
    top: -30rpx; right: -30rpx;
    width: 100rpx; height: 100rpx;
    border-radius: 50%;
    opacity: 0.1;
  }
  &.t4::before { background: var(--risk-t4); }
  &.t3::before { background: var(--risk-t3); }
  &.t2::before { background: var(--risk-t2); }
  &.t1::before { background: var(--risk-t1); }
  &.t0::before { background: var(--risk-t0); }
  &.unknown::before { background: var(--risk-unknown); }
}

// ── Risk bar (absolute + glow) ─────────────────────────────
.risk-bar {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6rpx;
  // kept: parent context selectors with box-shadow
  .t4 & { background: var(--risk-t4); box-shadow: 0 0 16rpx var(--risk-t4); }
  .t3 & { background: var(--risk-t3); box-shadow: 0 0 16rpx var(--risk-t3); }
  .t2 & { background: var(--risk-t2); box-shadow: 0 0 16rpx var(--risk-t2); }
  .t1 & { background: var(--risk-t1); box-shadow: 0 0 16rpx var(--risk-t1); }
  .t0 & { background: var(--risk-t0); box-shadow: 0 0 16rpx var(--risk-t0); }
  .unknown & { background: var(--risk-unknown); }
}

// ── Icon color variants ────────────────────────────────────
.ingredient-name {
  .icon { width: 28rpx; height: 28rpx; flex-shrink: 0; }
  // kept: parent context selectors for icon fill/stroke
  .t4 & .icon { fill: var(--risk-t4); }
  .t3 & .icon { fill: var(--risk-t3); }
  .t2 & .icon { fill: var(--risk-t2); }
  .t1 & .icon { stroke: var(--risk-t1); fill: none; }
  .t0 & .icon { stroke: var(--risk-t0); fill: none; }
  .unknown & .icon { fill: var(--risk-unknown); }
}

// ── Ingredient reason (overflow) ───────────────────────────
.ingredient-reason {
  // kept: text-overflow pattern (truncate class doesn't apply to inline-block in UniApp)
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  align-self: flex-start;
}
```

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/components/IngredientSection.vue
git commit -m "feat(uniapp): Batch 5 - migrate IngredientSection"
```

---

### Task 1.6: Batch 6 — Simple pages

**Files:** `pages/search/index.vue`, `pages/profile/index.vue`

#### File: `pages/search/index.vue`

This page already has many UnoCSS classes in the template from previous work. The style block has many empty class rules and a few with actual styles.

**Main changes:**

1. Update `typeTagStyle()` function (references removed CSS vars):
   ```ts
   function typeTagStyle(type: string) {
     if (type === 'product') {
       return { background: 'color-mix(in oklch, var(--risk-t2) 10%, transparent)', color: 'var(--risk-t2)' }
     }
     return { background: 'color-mix(in oklch, var(--risk-t4) 12%, transparent)', color: 'var(--risk-t4)' }
   }
   ```

2. Remove ALL empty style rules (classes with empty bodies like `.header-spacer {}`, `.content-scroll {}`, etc.)

3. For classes with actual styles, convert to atomic where possible:
   - `.search-page { background: var(--bg-base) }` → already has `bg-[var(--bg-base)]` in template? Check. If not, add to root `<view>` element.
   - `.search-header { background: var(--bg-base); border-bottom: 1px solid var(--border-color); }` → add `bg-[var(--bg-base)] border-b border-[var(--border-color)]` to `.search-header` element
   - `.header-btn { background: transparent; border: none; padding: 0; border-radius: 32rpx; }` + `svg` → atomic
   - `.header-title { font-size: 24rpx; font-weight: 600; color: var(--text-primary); letter-spacing: -0.02em; margin-right: 120rpx; }` → atomic
   - `.search-input-wrap { background: var(--bg-base) }` → `bg-[var(--bg-base)]` on element
   - `.search-input-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 48rpx; }` → atomic on element
   - `.search-input { font-size: 28rpx; color: var(--text-primary); background: transparent; border: none; outline: none; }` → atomic; `&::placeholder { color: var(--text-muted); }` → keep in style
   - `.result-item { ... box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.05); }` → add `shadow-[0_2rpx_8rpx_rgba(0,0,0,0.05)]` to element
   - `.result-type-tag { display: inline-block; font-size: 20rpx; padding: 0 24rpx; border-radius: 9999rpx; }` → atomic (colors come from inline style via typeTagStyle)
   - `.history-tag { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 9999rpx; font-size: 20rpx; color: var(--text-secondary); }` → atomic

Final `<style>` block (what remains):
```scss
@import '@/styles/design-system.scss';

.search-input {
  // kept: placeholder pseudo-element
  &::placeholder {
    color: var(--text-muted);
  }
}
```

---

#### File: `pages/profile/index.vue`

Main issue: `.dark .login-card` uses `background: linear-gradient(...)` and `border-color` override. This is a parent context selector that works with non-scoped `<style>`.

Since the style is `<style lang="scss" scoped>`, `.dark .login-card` won't match (scoped adds `[data-v-xxx]` which `.dark` doesn't have). This is a **pre-existing bug** — note it but don't fix the scoping issue in this task; just keep the dark mode override as-is.

**Changes:**

1. Remove empty rules (`.header-spacer {}`, `.content-scroll {}`, `.content {}`, `.menu-item-left {}`, `.header-spacer {}`)

2. `.profile-page { background: var(--bg-base); }` → add `bg-[var(--bg-base)]` to root view (already has it via class attribute? Check — root has `class="profile-page flex flex-col min-h-screen"`. Add `bg-[var(--bg-base)]` to that.)

3. `.profile-header { background: var(--bg-base); border-bottom: 1px solid var(--border-color); }` → add `bg-[var(--bg-base)] border-b border-[var(--border-color)]` to `.profile-header` element

4. `.header-btn` → atomic (transparent bg, no border, rounded): `bg-transparent border-none p-0 rounded-[32rpx]` + `svg { width: 36rpx; height: 36rpx; color: var(--text-primary); }` → add to SVG element

5. `.header-title { font-size: 24rpx; font-weight: 600; color: var(--text-primary); letter-spacing: -0.02em; margin-right: 120rpx; }` → atomic

6. `.login-card { background: linear-gradient(135deg, ...); border-radius: 40rpx; margin-bottom: 48rpx; border: 1px solid color-mix(...); }` → gradient and color-mix in style block

7. `.login-avatar { border-radius: 50%; background: var(--bg-card); box-shadow: ...; }` → `rounded-full bg-[var(--bg-card)] shadow-[0_2rpx_8rpx_rgba(0,0,0,0.05)]`; svg → add dims to element

8. `.login-text { font-size: 28rpx; color: var(--text-muted); }` → atomic

9. `.menu-list { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 40rpx; }` → atomic

10. `.menu-item { border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.15s ease; &:last-child { border-bottom: none; } &:active { background: var(--bg-card-hover); } &.disabled { opacity: 0.5; pointer-events: none; } }` → keep transition + `:last-child` (complex), but `:active` and `.disabled` can be atomic

11. `.menu-icon { width: 80rpx; height: 80rpx; color: var(--text-secondary); }` → atomic via class on SVG elements

12. `.menu-text { font-size: 28rpx; color: var(--text-primary); }` → atomic

13. `.menu-arrow { width: 64rpx; height: 64rpx; color: var(--text-muted); opacity: 0.4; }` → atomic

Final `<style>` block:
```scss
@import '@/styles/design-system.scss';

.login-card {
  // kept: linear-gradient background
  background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
  border: 1px solid color-mix(in oklch, #fbcfe8 50%, transparent);
}

// kept: parent context selector (pre-existing dark mode pattern)
.dark .login-card {
  background: linear-gradient(135deg, #1a1018 0%, #1a1a1a 100%);
  border-color: var(--border-color);
}

.menu-item {
  // kept: transition
  transition: background 0.15s ease;
  // kept: :last-child pseudo-class (last:border-b-0 not reliable in UniApp scoped)
  &:last-child { border-bottom: none; }
}
```

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/pages/search/index.vue \
        web/apps/uniapp/src/pages/profile/index.vue
git commit -m "feat(uniapp): Batch 6 - migrate search and profile pages"
```

---

### Task 1.7: Batch 7 — ingredient-detail and index pages

**Files:** `pages/ingredient-detail/index.vue`, `pages/index/index.vue`

#### File: `pages/ingredient-detail/index.vue`

This page has CSS custom property definitions (`.risk-critical { --risk-header-bg: ...; }`) that MUST stay in the style block (they define local CSS variables used via `var(--risk-header-bg)` in other rules).

Since `--palette-*` CSS vars were removed, replace all `var(--palette-*)` references in the style block with their hex values:
- `var(--palette-red-50)` → `#fef2f2`
- `var(--palette-red-200)` → `#fecaca`
- `var(--palette-red-500)` → `#dc2626`
- `var(--palette-red-800)` → `#7f1d1d`
- `var(--palette-orange-50)` → `#fff7ed`
- `var(--palette-orange-200)` → `#fed7aa`
- `var(--palette-orange-500)` → `#f97316`
- `var(--palette-orange-800)` → `#9a3412`
- `var(--palette-yellow-50)` → `#fefce8`
- `var(--palette-yellow-200)` → `#fef08a`
- `var(--palette-yellow-500)` → `#eab308`
- `var(--palette-yellow-800)` → `#713f12`
- `var(--palette-green-50)` → `#f0fdf4`
- `var(--palette-green-200)` → `#bbf7d0`
- `var(--palette-green-500)` → `#22c55e`
- `var(--palette-green-800)` → `#14532d`
- `var(--palette-gray-50)` → `#f9fafb`
- `var(--palette-gray-200)` → `#e5e7eb`
- `var(--palette-gray-500)` → `#6b7280`
- `var(--palette-gray-600)` → `#4b5563`

The `.risk-critical`, `.risk-high`, etc. class rules stay entirely in the style block — they define CSS custom properties.

For the rest of the style block: read the current file starting at line 490 and apply atomic class migrations per migration-guide.md. Most simple properties (font-size, color, padding, display, flex) can be moved to template. Complex ones (backdrop-filter, transitions with multiple props, ::before) stay.

Key rule: the `--bottom-bar-shadow` CSS custom property set in `.header-content` must stay:
```scss
.header-content {
  // kept: local CSS custom property definition
  --bottom-bar-shadow: 0 -8rpx 32rpx rgba(0, 0, 0, 0.06);
}
```

The `.chip-func`, `.chip-warn`, `.chip-neu` classes used in the chips row are in uno.config.ts as shortcuts (`chip-risk` maps to what was `chip-func` — check the actual class names used in template).

**Important:** The template uses `class="chip chip-func"`, `class="chip chip-warn"`, `class="chip chip-neu"`. The `chip` class itself and `chip-func` are NOT in shortcuts. Looking at the ingredient-detail template, chips use:
- `.chip-func` → this should be `chip-neutral` (functional/neutral chip)
- `.chip-warn` → `chip-warn` (already a shortcut)
- `.chip-neu` → `chip-neutral` (already a shortcut)

The `.chip` base class: `padding: 8rpx 20rpx; border-radius: 24rpx; font-size: 24rpx;` — move to template as atomic; rename `chip` usage to inline classes.

For the list item icons (`list-item-icon`, `icon-x`, `icon-check-green`, `icon-check-yellow`): these are shortcuts in uno.config.ts. The style block may define them separately — remove those definitions since shortcuts now handle them.

---

#### File: `pages/index/index.vue`

Key items to handle:

1. **`@keyframes pulse-ring`** → keep in style block
2. **`@media (prefers-reduced-motion)`** → keep in style block
3. **`.dark-mode .scan-count`** — parent context selector → keep in style block
4. **`.scan-cta`** → most can be atomic except `box-shadow` and `transition`:
   - `width: 280rpx; height: 280rpx;` → `w-[280rpx] h-[280rpx]`
   - `background: linear-gradient(135deg, ...)` → `bg-gradient-to-br from-pink-400 to-pink-500`
   - `border-radius: 50%;` → `rounded-full`
   - `display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12rpx;` → `flex flex-col items-center justify-center gap-[12rpx]`
   - `cursor: pointer; position: relative;` → `cursor-pointer relative`
   - `&:active { transform: scale(0.95); }` → `active:scale-95`
   - `box-shadow: 0 16rpx 80rpx rgba(236, 72, 153, 0.4);` → keep in style
   - `transition: transform 0.25s ..., box-shadow 0.2s ease;` → keep in style (multi-prop)
5. **`.scan-cta-ring`** → keep in style (absolute + animation + `border: 4rpx solid`)
6. **`.scan-count`** → use `scan-count-badge` shortcut
7. **`.scan-item { &:active { transform: scale(0.98); } box-shadow: ...; transition: ... }`** → `active:scale-[0.98]` in template; box-shadow and transition keep in style
8. All other simple classes → atomic

Final `<style>` block keeps:
- `.scan-cta` (box-shadow + multi-prop transition)
- `.scan-cta-ring` (absolute positioning, animation, border with rpx)
- `@keyframes pulse-ring`
- `@media (prefers-reduced-motion)`
- `.dark-mode .scan-count` (parent context selector)
- `.scan-item` (box-shadow + transition)
- `.divider-line` (`flex: 1; height: 1px; background:` — these CAN be atomic: `flex-1 h-[1px] bg-[var(--border-color)]`, so remove from style)

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/pages/ingredient-detail/index.vue \
        web/apps/uniapp/src/pages/index/index.vue
git commit -m "feat(uniapp): Batch 7 - migrate ingredient-detail and index pages"
```

---

### Task 1.8: Batch 8 — product page (most complex)

**File:** `pages/product/index.vue` (289 lines of style)

> **This batch is for the product page only. Start a fresh session.**

- [ ] **Step 1: Read `pages/product/index.vue` and `migration-guide.md` completely**

- [ ] **Step 2: Apply template atomic classes per the table below**

| Element | CSS class to remove | Atomic classes to add to template |
|---------|--------------------|------------------------------------|
| `<view class="product-page ...">` | `.product-page` | `bg-[var(--bg-base)]` |
| `<scroll-view class="scroll-area ...">` | `.scroll-area` | `bg-[var(--bg-base)]` |
| `<text class="status-text">` | `.status-text` | `text-[30rpx] text-[var(--text-muted)]` |
| `<button class="retry-btn" ...>` | `.retry-btn` | `py-[24rpx] px-[64rpx] rounded-[24rpx] text-[28rpx] font-medium bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)]` |
| `<text class="banner-emoji">` | — | `text-[160rpx]` (keep `.banner-emoji` for animation) |
| `<text class="banner-label">` | `.banner-label` | `text-[26rpx] text-[var(--banner-label)] tracking-[0.1em]` |
| `<view class="banner-badge ...">` | — | `rounded-[24rpx] py-[20rpx] px-[32rpx] flex items-center gap-[16rpx]` (KEEP `.banner-badge` — child selectors depend on it) |
| `<svg class="badge-icon" ...>` | — | `w-[28rpx] h-[28rpx] flex-shrink-0` (KEEP `.badge-icon` — parent context fill selectors depend on it) |
| `<text class="badge-text">` | — | `text-[24rpx] font-semibold` (KEEP `.badge-text` — parent context color selectors depend on it) |
| `<view class="bottom-spacer" />` | `.bottom-spacer` | `h-[180rpx]` |
| `<text class="section-title ...">` | `.section-title` | `text-[40rpx] font-bold tracking-[-0.02em] text-[var(--text-primary)]` |
| `<view class="nutrition-card ...">` | — | `p-[80rpx] bg-[var(--nutrition-bg)] border border-[var(--nutrition-border)]` (KEEP `.nutrition-card` for `::before` + animation) |
| `<text class="nutrition-label">` | `.nutrition-label` | `text-[28rpx] uppercase tracking-[0.08em] mb-[8rpx] text-[var(--text-muted)]` |
| `<text class="nutrition-value">` | `.nutrition-value` | `text-[40rpx] font-bold tracking-[-0.03em] tabular-nums leading-none text-[var(--text-primary)] mt-[8rpx]` |
| `<text class="nutrition-unit">` | `.nutrition-unit` | `text-[28rpx] mt-[8rpx] text-[var(--text-muted)]` |
| `<button class="nutrition-toggle ...">` | — | (KEEP `.nutrition-toggle` — complex nested + pseudo selectors) |
| `<view class="nutrition-details ...">` | `.nutrition-details` | `border-t border-[var(--border-color)] pt-[64rpx] mt-[16rpx]` |
| `<view class="nutrition-row ...">` | — | `py-[40rpx] border-b border-[var(--border-color)] text-[28rpx]` (KEEP `.nutrition-row` — `:last-child` + nested child selectors) |
| `<text class="row-label">` | — | (stays inside `.nutrition-row` nested selector in style block) |
| `<text class="row-value">` | — | (stays inside `.nutrition-row` nested selector in style block) |
| `<view class="analysis-card ...">` | — | (KEEP `.analysis-card` for animation + parent-context selector in non-scoped block) |
| `<view class="advice-header ...">` | `.advice-header` | `flex items-center gap-[16rpx] mb-[56rpx] text-[30rpx] font-semibold text-[var(--text-primary)]` |
| `<svg class="star-icon" ...>` | `.star-icon` | `w-[36rpx] h-[36rpx] flex-shrink-0` (fill applied inline: `style="fill: #eab308"`) |
| `<svg class="item-icon item-icon--check" ...>` | — | `w-[36rpx] h-[36rpx] flex-shrink-0 mt-[8rpx]` (KEEP both classes for `&--check`/`&--dot` fill selectors) |
| `<text class="item-text">` | `.item-text` | `text-[28rpx] leading-[1.5] text-[var(--text-secondary)] flex-1` |
| `<text class="empty-text">` | `.empty-text` | `text-[28rpx] text-[var(--text-muted)]` |

> **Note on `.star-icon`**: `var(--palette-yellow-500)` no longer exists after design-system.scss simplification. Replace with hardcoded `#eab308` (the yellow-500 value) via inline `style="fill: #eab308"`. Remove `.star-icon` CSS class entirely.

> **Note on `.analysis-card` dark/light mode**: The original `.product-page:not(.dark) &` selector is broken — `.dark-mode` is on `page`, not `.product-page`. Fix: add a **separate non-scoped `<style>` block** (no `scoped` attribute) at the bottom of the file to handle this.

- [ ] **Step 3: Replace the `<style lang="scss" scoped>` block with the following**

```scss
<style lang="scss" scoped>
// @import removed — all CSS vars are global, no SCSS vars used

// ── Banner ────────────────────────────────────────────
.banner {
  // kept: ::before pseudo-element cannot be atomized
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 1;
  }
}

.banner-emoji {
  // kept: CSS filter + animation with initial opacity/transform state
  filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.3));
  animation: floatIn 0.8s var(--ease-spring) forwards;
  opacity: 0;
  transform: scale(0.8);
  transform-origin: center;
}

.banner-badge {
  // kept: backdrop-filter cannot be atomized; CSS-var bg/border/shadow; animation initial state
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: var(--banner-badge-bg);
  border: 1px solid var(--banner-badge-border);
  box-shadow: var(--banner-badge-shadow);
  animation: slideUpBadge 0.6s 0.2s var(--ease-spring) forwards;
  opacity: 0;
  transform: translateY(10px);
}

.badge-icon {
  // kept: parent context selectors (sibling class on parent, not root — these work in scoped)
  .banner-badge.t4 & { fill: var(--risk-t4); }
  .banner-badge.t3 & { fill: var(--risk-t3); }
  .banner-badge.t2 & { fill: var(--risk-t2); }
  .banner-badge.t0 & { fill: var(--risk-t0); }
  .banner-badge.unknown & { fill: var(--risk-unknown); }
}

.badge-text {
  // kept: parent context selectors
  .banner-badge.t4 & { color: var(--risk-t4); }
  .banner-badge.t3 & { color: var(--risk-t3); }
  .banner-badge.t2 & { color: var(--risk-t2); }
  .banner-badge.t0 & { color: var(--risk-t0); }
  .banner-badge.unknown & { color: var(--risk-unknown); }
}

// ── 营养卡片 ──────────────────────────────────────────
.nutrition-card {
  // kept: ::before linear-gradient + animation with initial opacity/transform state
  animation: slideUp 0.5s 0.1s var(--ease-spring) forwards;
  opacity: 0;
  transform: translateY(16px);

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--nutrition-glow), transparent);
  }
}

.nutrition-toggle {
  // kept: :active color-mix pseudo + :focus-visible + nested chevron transition + &.expanded
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;

  &:active { background: color-mix(in oklch, var(--palette-gray-500) 10%, transparent); }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .chevron {
    transition: transform 0.3s ease;
    stroke: var(--text-muted);
  }

  &.expanded .chevron { transform: rotate(180deg); }
}

.nutrition-row {
  // kept: :last-child pseudo-class + nested child selectors
  &:last-child { border-bottom: none; }
  .row-label { color: var(--text-secondary); }
  .row-value { color: var(--text-primary); font-weight: 500; font-variant-numeric: tabular-nums; }
}

// ── 健康益处 / 食用建议 ────────────────────────────────
.analysis-card {
  // kept: animation with initial opacity/transform state
  // light/dark mode styles are in the non-scoped <style> block below
  animation: slideUp 0.5s 0.3s var(--ease-spring) forwards;
  opacity: 0;
  transform: translateY(16px);
}

.analysis-item {
  // kept: BEM modifier nested selectors
  .item-icon {
    &--check { fill: var(--risk-t0); }
    &--dot { fill: var(--text-muted); }
  }
}

// ── Reduced Motion ────────────────────────────────────
@media (prefers-reduced-motion: reduce) {
  .banner-emoji,
  .banner-badge,
  .nutrition-card,
  .analysis-card {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>
```

- [ ] **Step 4: Add a non-scoped `<style>` block after the scoped one (for parent-context selectors that break under scoped)**

```scss
<style lang="scss">
// kept: .dark-mode is on page element (not inside this component) so scoped CSS cannot target it
.dark-mode .banner::before {
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, color-mix(in oklch, var(--risk-t0) 8%, transparent) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 80%, color-mix(in oklch, var(--accent) 5%, transparent) 0%, transparent 50%);
}

// kept: light mode analysis card appearance (dark mode default is set in scoped block)
page:not(.dark-mode) .analysis-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
}

// dark mode analysis card default
.dark-mode .analysis-card {
  background: color-mix(in oklch, var(--bg-card) 2%, transparent);
  border: 1px solid color-mix(in oklch, #ffffff 6%, transparent);
}
</style>
```

- [ ] **Build H5 and verify no errors**
- [ ] **Commit**

```bash
git add web/apps/uniapp/src/pages/product/index.vue
git commit -m "feat(uniapp): Batch 8 - migrate product page"
```

---

## Phase 2: Validation

### Task 2.1: Count remaining style block lines and verify success criteria

- [ ] **Count remaining lines**

```bash
for f in web/apps/uniapp/src/components/*.vue web/apps/uniapp/src/pages/**/*.vue; do
  lines=$(awk '/<style/,/<\/style>/' "$f" | wc -l)
  if [ "$lines" -gt 3 ]; then
    echo "$lines $f"
  fi
done | sort -rn
```

Target: total < 200 lines across all files.

- [ ] **Final H5 build**

```bash
cd /Users/wwj/Desktop/self/life-classics/web
pnpm build:uniapp:h5 2>&1 | tail -10
```

Build must succeed with no errors.

- [ ] **List all remaining style block content with reasons**

For each file that still has style content, verify every remaining rule has a `// kept:` comment explaining why it cannot be atomic.

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat(uniapp): Phase 1+2 complete - UnoCSS migration done, < 200 lines CSS remaining"
```
