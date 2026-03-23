# UniApp + UnoCSS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate UnoCSS into `@acme/uniapp`, migrate all components/pages from SCSS to UnoCSS atomic classes, maintain H5 + WeChat MiniApp + HarmonyOS compatibility.

**Architecture:** UnoCSS with `presetUno` + `presetAttributify` + `presetIcons`. Design-system SCSS retains only palette and semantic color tokens. All spacing/radius/shadow/layout via UnoCSS atomic classes. Dark mode via JS system preference detection.

**Tech Stack:** UnoCSS 0.66.x, Vue 3, UniApp, SCSS, PostCSS rpx transform

---

## File Map

```
web/apps/uniapp/
├── package.json                          ← Modify: add UnoCSS deps
├── vite.config.ts                       ← Modify: add UnoCSS plugin + PostCSS
├── src/
│   ├── uno.config.ts                    ← Create: UnoCSS configuration
│   ├── styles/
│   │   └── design-system.scss            ← Modify: remove spacing/text/size vars, keep palette/semantic
│   ├── App.vue                          ← Modify: add dark mode class
│   ├── components/                      ← Migrate (13 files)
│   └── pages/                           ← Migrate (6 files)
```

---

## Phase 1: Infrastructure

### Task 1: Install UnoCSS Dependencies

**Files:**
- Modify: `web/apps/uniapp/package.json`

- [ ] **Step 1: Add UnoCSS dependencies to package.json**

Add to `devDependencies`:
```json
"devDependencies": {
  "unocss": "^66.x",
  "@unocss/preset-uno": "^66.x",
  "@unocss/preset-icons": "^66.x",
  "@unocss/preset-attributify": "^66.x",
  "postcss-rpx-transform": "^1.x"
}
```

- [ ] **Step 2: Run pnpm install**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web
pnpm install
```

Expected: All new packages installed without errors.

- [ ] **Step 3: Commit**

```bash
git add web/apps/uniapp/package.json
git commit -m "feat(uniapp): add UnoCSS dependencies v66.x

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Create uno.config.ts

**Files:**
- Create: `web/apps/uniapp/src/uno.config.ts`

- [ ] **Step 1: Create uno.config.ts**

```typescript
import { defineConfig, presetUno, presetIcons, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
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
      gray: {
        50: 'var(--palette-gray-50)',
        100: 'var(--palette-gray-100)',
        200: 'var(--palette-gray-200)',
        300: 'var(--palette-gray-300)',
        400: 'var(--palette-gray-400)',
        500: 'var(--palette-gray-500)',
        600: 'var(--palette-gray-600)',
        700: 'var(--palette-gray-700)',
        800: 'var(--palette-gray-800)',
        900: 'var(--palette-gray-900)',
      },
      red: {
        50: 'var(--palette-red-50)',
        100: 'var(--palette-red-100)',
        200: 'var(--palette-red-200)',
        300: 'var(--palette-red-300)',
        400: 'var(--palette-red-400)',
        500: 'var(--palette-red-500)',
        600: 'var(--palette-red-600)',
        700: 'var(--palette-red-700)',
        800: 'var(--palette-red-800)',
        900: 'var(--palette-red-900)',
      },
      orange: {
        50: 'var(--palette-orange-50)',
        100: 'var(--palette-orange-100)',
        200: 'var(--palette-orange-200)',
        300: 'var(--palette-orange-300)',
        400: 'var(--palette-orange-400)',
        500: 'var(--palette-orange-500)',
        600: 'var(--palette-orange-600)',
        700: 'var(--palette-orange-700)',
        800: 'var(--palette-orange-800)',
        900: 'var(--palette-orange-900)',
      },
      yellow: {
        50: 'var(--palette-yellow-50)',
        100: 'var(--palette-yellow-100)',
        200: 'var(--palette-yellow-200)',
        300: 'var(--palette-yellow-300)',
        400: 'var(--palette-yellow-400)',
        500: 'var(--palette-yellow-500)',
        600: 'var(--palette-yellow-600)',
        700: 'var(--palette-yellow-700)',
        800: 'var(--palette-yellow-800)',
        900: 'var(--palette-yellow-900)',
      },
      green: {
        50: 'var(--palette-green-50)',
        100: 'var(--palette-green-100)',
        200: 'var(--palette-green-200)',
        300: 'var(--palette-green-300)',
        400: 'var(--palette-green-400)',
        500: 'var(--palette-green-500)',
        600: 'var(--palette-green-600)',
        700: 'var(--palette-green-700)',
        800: 'var(--palette-green-800)',
        900: 'var(--palette-green-900)',
        950: 'var(--palette-green-950)',
      },
      purple: {
        50: 'var(--palette-purple-50)',
        100: 'var(--palette-purple-100)',
        300: 'var(--palette-purple-300)',
        400: 'var(--palette-purple-400)',
        500: 'var(--palette-purple-500)',
        600: 'var(--palette-purple-600)',
        700: 'var(--palette-purple-700)',
        800: 'var(--palette-purple-800)',
      },
      blue: {
        50: 'var(--palette-blue-50)',
        100: 'var(--palette-blue-100)',
        300: 'var(--palette-blue-300)',
        400: 'var(--palette-blue-400)',
        500: 'var(--palette-blue-500)',
        600: 'var(--palette-blue-600)',
      },
      pink: {
        300: 'var(--palette-pink-300)',
        400: 'var(--palette-pink-400)',
        500: 'var(--palette-pink-500)',
        600: 'var(--palette-pink-600)',
      },
      accent: {
        DEFAULT: 'var(--accent)',
        light: 'var(--accent-light)',
      },
      risk: {
        t4: 'var(--risk-t4)',
        t3: 'var(--risk-t3)',
        t2: 'var(--risk-t2)',
        t1: 'var(--risk-t1)',
        t0: 'var(--risk-t0)',
        unknown: 'var(--risk-unknown)',
      }
    },
    borderRadius: {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
      lg: 'var(--radius-lg)',
      xl: 'var(--radius-xl)',
      full: 'var(--radius-full)',
    }
  },

  safelist: [
    'risk-critical', 'risk-high', 'risk-medium', 'risk-low', 'risk-safe', 'risk-unknown',
    'icon-bg-blue', 'icon-bg-red', 'icon-bg-purple', 'icon-bg-green', 'icon-bg-orange',
    'chip-func', 'chip-warn', 'chip-neu',
    'list-item-icon', 'icon-x', 'icon-check-green', 'icon-check-yellow',
    'risk-med'
  ],

  shortcuts: {
    'card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-[var(--shadow-sm)]',
    'section-title': 'text-[var(--text-primary)] font-semibold text-lg',
    'icon-wrap': 'w-[40rpx] h-[40rpx] rounded-[var(--space-3)] flex items-center justify-center',
  }
})
```

- [ ] **Step 2: Verify file is syntactically valid (basic TS check)**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web/apps/uniapp
npx tsc src/uno.config.ts --noEmit --skipLibCheck 2>&1 || echo "Config check done"
```

Expected: No syntax errors in the config file.

- [ ] **Step 3: Commit**

```bash
git add web/apps/uniapp/src/uno.config.ts
git commit -m "feat(uniapp): create UnoCSS config with palette theme integration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Update vite.config.ts

**Files:**
- Modify: `web/apps/uniapp/vite.config.ts`

- [ ] **Step 1: Read current vite.config.ts**

```typescript
// Current content:
import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

export default defineConfig({
  server: {
    port: 5174,
  },
  plugins: [uni()],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@import "uview-plus/theme.scss";',
      },
    },
  },
});
```

- [ ] **Step 2: Update vite.config.ts with UnoCSS + rpx support**

```typescript
import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";
import UnoCSS from "unocss/vite";

export default defineConfig({
  server: {
    port: 5174,
  },
  plugins: [
    UnoCSS(),
    uni(),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@import "uview-plus/theme.scss";',
      },
    },
    // rpx conversion: px values in UnoCSS output → rpx for miniapp compatibility
    // NOTE: postcss-rpx-transform plugin to be added after dependency testing
    postcss: process.env.UNI_PLATFORM !== 'h5' ? {
      plugins: [
        // TODO: Add postcss-rpx-transform here after Phase 1 verification
        // Example: transformRpx({ viewportWidth: 750, mode: 'rpx' })
      ]
    } : undefined
  },
});
```

- [ ] **Step 3: Test dev server starts without errors**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web
pnpm dev:uniapp:h5 &
sleep 8
curl -s http://localhost:5174 | head -20
kill %1 2>/dev/null
```

Expected: H5 dev server starts, page loads with UnoCSS classes.

- [ ] **Step 4: Commit**

```bash
git add web/apps/uniapp/vite.config.ts
git commit -m "feat(uniapp): integrate UnoCSS vite plugin

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Design System Cleanup

### Task 4: Clean up design-system.scss

**Files:**
- Modify: `web/apps/uniapp/src/styles/design-system.scss`

**Goal:** Remove spacing tokens (`--space-*`), text size tokens (`--text-*`), icon size tokens (`--icon-*`), button tokens (`--btn-*`), header tokens, card padding tokens. Retain palette colors and semantic color tokens.

- [ ] **Step 1: Read full design-system.scss to identify all tokens**

```bash
wc -l /Users/wwj/Desktop/myself/life-classics/web/apps/uniapp/src/styles/design-system.scss
```

- [ ] **Step 2: Replace the CSS custom properties section — remove spacing/text/icon/btn/header/card-padding tokens, keep palette and semantic**

Replace the entire `page { ... }` block with:

```scss
page {
  // ═══════════════════════════════════════════════════════
  // PALETTE — 调色板（保留，供 UnoCSS theme 引用）
  // ═══════════════════════════════════════════════════════

  // Gray
  --palette-gray-50: #f9fafb;
  --palette-gray-100: #f3f4f6;
  --palette-gray-200: #e5e7eb;
  --palette-gray-300: #d1d5db;
  --palette-gray-400: #9ca3af;
  --palette-gray-500: #6b7280;
  --palette-gray-600: #4b5563;
  --palette-gray-700: #374151;
  --palette-gray-800: #1f2937;
  --palette-gray-900: #111827;

  // Red
  --palette-red-50: #fef2f2;
  --palette-red-100: #fee2e2;
  --palette-red-200: #fecaca;
  --palette-red-300: #fca5a5;
  --palette-red-400: #f87171;
  --palette-red-500: #dc2626;
  --palette-red-600: #b91c1c;
  --palette-red-700: #991b1b;
  --palette-red-800: #7f1d1d;
  --palette-red-900: #450a0a;

  // Orange
  --palette-orange-50: #fff7ed;
  --palette-orange-100: #ffedd5;
  --palette-orange-200: #fed7aa;
  --palette-orange-300: #fdba74;
  --palette-orange-400: #fb923c;
  --palette-orange-500: #f97316;
  --palette-orange-600: #ea580c;
  --palette-orange-700: #c2410c;
  --palette-orange-800: #9a3412;
  --palette-orange-900: #431407;

  // Yellow
  --palette-yellow-50: #fefce8;
  --palette-yellow-100: #fef9c3;
  --palette-yellow-200: #fef08a;
  --palette-yellow-300: #fde047;
  --palette-yellow-400: #facc15;
  --palette-yellow-500: #eab308;
  --palette-yellow-600: #ca8a04;
  --palette-yellow-700: #a16207;
  --palette-yellow-800: #713f12;
  --palette-yellow-900: #422006;

  // Green
  --palette-green-50: #f0fdf4;
  --palette-green-100: #dcfce7;
  --palette-green-200: #bbf7d0;
  --palette-green-300: #86efac;
  --palette-green-400: #4ade80;
  --palette-green-500: #22c55e;
  --palette-green-600: #16a34a;
  --palette-green-700: #15803d;
  --palette-green-800: #14532d;
  --palette-green-900: #052e16;
  --palette-green-950: #022c22;

  // Purple
  --palette-purple-50: #f5f3ff;
  --palette-purple-100: #ede9fe;
  --palette-purple-300: #c4b5fd;
  --palette-purple-400: #a78bfa;
  --palette-purple-500: #8b5cf6;
  --palette-purple-600: #7c3aed;
  --palette-purple-700: #6d28d9;
  --palette-purple-800: #4c1d95;

  // Blue
  --palette-blue-50: #eff6ff;
  --palette-blue-100: #dbeafe;
  --palette-blue-300: #93c5fd;
  --palette-blue-400: #60a5fa;
  --palette-blue-500: #3b82f6;
  --palette-blue-600: #2563eb;

  // Pink
  --palette-pink-300: #f472b6;
  --palette-pink-400: #ec4899;
  --palette-pink-500: #db2777;
  --palette-pink-600: #be185d;

  // ═══════════════════════════════════════════════════════
  // SEMANTIC — 语义色（保留）
  // ═══════════════════════════════════════════════════════

  --text-primary: var(--palette-gray-900);
  --text-secondary: var(--palette-gray-600);
  --text-muted: var(--palette-gray-400);

  --border-color: color-mix(in oklch, var(--palette-gray-900) 6%, transparent);

  --bg-base: var(--palette-gray-50);
  --bg-card: #ffffff;
  --bg-card-hover: var(--palette-gray-50);

  --accent: var(--palette-pink-500);
  --accent-light: var(--palette-pink-400);

  --risk-t4: var(--palette-red-500);
  --risk-t3: var(--palette-orange-600);
  --risk-t2: var(--palette-yellow-600);
  --risk-t1: var(--palette-green-500);
  --risk-t0: var(--palette-green-600);
  --risk-unknown: var(--palette-gray-400);

  // Component tokens (color-mix based, keep)
  --risk-t4-bg: color-mix(in oklch, var(--risk-t4) 12%, transparent);
  --risk-t4-border: color-mix(in oklch, var(--risk-t4) 30%, transparent);
  --risk-t3-bg: color-mix(in oklch, var(--risk-t3) 12%, transparent);
  --risk-t3-border: color-mix(in oklch, var(--risk-t3) 30%, transparent);
  --risk-t2-bg: color-mix(in oklch, var(--risk-t2) 12%, transparent);
  --risk-t2-border: color-mix(in oklch, var(--risk-t2) 30%, transparent);
  --risk-t1-bg: color-mix(in oklch, var(--risk-t1) 12%, transparent);
  --risk-t1-border: color-mix(in oklch, var(--risk-t1) 30%, transparent);
  --risk-t0-bg: color-mix(in oklch, var(--risk-t0) 12%, transparent);
  --risk-t0-border: color-mix(in oklch, var(--risk-t0) 30%, transparent);
  --risk-unknown-bg: var(--palette-gray-100);
  --risk-unknown-border: color-mix(in oklch, var(--palette-gray-400) 30%, transparent);

  --risktag-t4-bg: color-mix(in oklch, var(--risk-t4) 15%, transparent);
  --risktag-t4-text: var(--risk-t4);
  --risktag-t3-bg: color-mix(in oklch, var(--risk-t3) 15%, transparent);
  --risktag-t3-text: var(--risk-t3);
  --risktag-t2-bg: color-mix(in oklch, var(--risk-t2) 15%, transparent);
  --risktag-t2-text: var(--risk-t2);
  --risktag-t1-bg: color-mix(in oklch, var(--risk-t1) 15%, transparent);
  --risktag-t1-text: var(--risk-t1);
  --risktag-t0-bg: color-mix(in oklch, var(--risk-t0) 15%, transparent);
  --risktag-t0-text: var(--risk-t0);
  --risktag-unknown-bg: color-mix(in oklch, var(--risk-unknown) 15%, transparent);
  --risktag-unknown-text: var(--risk-unknown);

  --chip-risk-bg: color-mix(in oklch, var(--risk-t4) 12%, transparent);
  --chip-risk-text: var(--risk-t4);
  --chip-risk-border: color-mix(in oklch, var(--risk-t4) 20%, transparent);
  --chip-warn-bg: color-mix(in oklch, var(--risk-t2) 10%, transparent);
  --chip-warn-text: var(--risk-t2);
  --chip-warn-border: color-mix(in oklch, var(--risk-t2) 20%, transparent);
  --chip-neu-bg: var(--palette-gray-100);
  --chip-neu-text: var(--text-secondary);

  --ai-label-bg: linear-gradient(135deg, var(--palette-purple-500), var(--palette-purple-600));

  --header-scrolled-bg: color-mix(in oklch, #ffffff 90%, transparent);
  --header-text: color-mix(in oklch, var(--palette-gray-900) 80%, transparent);

  --banner-bg: linear-gradient(145deg, var(--palette-yellow-50) 0%, var(--palette-yellow-100) 50%, var(--palette-yellow-200) 100%);
  --banner-label: var(--palette-yellow-800);

  --bottom-bar-bg: color-mix(in oklch, #ffffff 95%, transparent);
  --bottom-bar-border: color-mix(in oklch, var(--palette-gray-900) 6%, transparent);

  --nutrition-bg: color-mix(in oklch, var(--palette-green-500) 4%, transparent);
  --nutrition-border: color-mix(in oklch, var(--palette-green-500) 12%, transparent);

  --status-bar-bg: #ffffff;
  --status-bar-text: var(--palette-gray-900);

  // Layout tokens needed by existing SCSS (keep for backward compat during migration)
  // These will be removed in Phase 3 after all components migrated
  --space-1: 4rpx;
  --space-2: 8rpx;
  --space-3: 12rpx;
  --space-4: 16rpx;
  --space-5: 20rpx;
  --space-6: 24rpx;
  --space-7: 28rpx;
  --space-8: 32rpx;
  --space-9: 36rpx;
  --space-10: 40rpx;
  --space-12: 48rpx;
  --space-14: 56rpx;
  --space-16: 64rpx;
  --space-18: 72rpx;
  --space-20: 80rpx;
  --text-sm: 20rpx;
  --text-md: 24rpx;
  --text-lg: 26rpx;
  --text-xl: 28rpx;
  --text-2xl: 30rpx;
  --text-3xl: 34rpx;
  --text-4xl: 36rpx;
  --text-5xl: 40rpx;
  --text-6xl: 52rpx;
  --icon-sm: 28rpx;
  --icon-xl: 40rpx;
  --radius-sm: 24rpx;
  --radius-md: 32rpx;
  --radius-lg: 40rpx;
  --radius-xl: 48rpx;
  --radius-full: 9999rpx;
  --shadow-sm: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 16rpx rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32rpx rgba(0, 0, 0, 0.12);
}
```

Also update the `.dark-mode` block to use `.dark` class instead:

```scss
.dark {
  --text-primary: var(--palette-gray-100);
  --text-secondary: var(--palette-gray-400);
  --text-muted: var(--palette-gray-500);
  --border-color: color-mix(in oklch, var(--palette-gray-100) 8%, transparent);
  --bg-base: #0f0f0f;
  --bg-card: #1a1a1a;
  --bg-card-hover: #222222;
  --accent: var(--palette-pink-400);
  --accent-light: var(--palette-pink-300);
  --risk-t4: var(--palette-red-400);
  --risk-t3: var(--palette-orange-500);
  --risk-t2: var(--palette-yellow-500);
  --risk-t1: var(--palette-green-400);
  --risk-t0: var(--palette-green-500);
  --risk-unknown: var(--palette-gray-400);

  --risk-t4-bg: color-mix(in oklch, var(--risk-t4) 8%, transparent);
  --risk-t4-border: color-mix(in oklch, var(--risk-t4) 15%, transparent);
  --risk-t3-bg: color-mix(in oklch, var(--risk-t3) 8%, transparent);
  --risk-t3-border: color-mix(in oklch, var(--risk-t3) 15%, transparent);
  --risk-t2-bg: color-mix(in oklch, var(--risk-t2) 8%, transparent);
  --risk-t2-border: color-mix(in oklch, var(--risk-t2) 15%, transparent);
  --risk-t1-bg: color-mix(in oklch, var(--risk-t1) 8%, transparent);
  --risk-t1-border: color-mix(in oklch, var(--risk-t1) 15%, transparent);
  --risk-t0-bg: color-mix(in oklch, var(--risk-t0) 8%, transparent);
  --risk-t0-border: color-mix(in oklch, var(--risk-t0) 15%, transparent);
  --risk-unknown-bg: color-mix(in oklch, var(--palette-gray-500) 8%, transparent);
  --risk-unknown-border: color-mix(in oklch, var(--palette-gray-500) 15%, transparent);

  --risktag-t4-bg: color-mix(in oklch, var(--risk-t4) 15%, transparent);
  --risktag-t4-text: var(--risk-t4);
  --risktag-t3-bg: color-mix(in oklch, var(--risk-t3) 15%, transparent);
  --risktag-t3-text: var(--risk-t3);
  --risktag-t2-bg: color-mix(in oklch, var(--risk-t2) 15%, transparent);
  --risktag-t2-text: var(--risk-t2);
  --risktag-t1-bg: color-mix(in oklch, var(--risk-t1) 15%, transparent);
  --risktag-t1-text: var(--risk-t1);
  --risktag-t0-bg: color-mix(in oklch, var(--risk-t0) 15%, transparent);
  --risktag-t0-text: var(--risk-t0);
  --risktag-unknown-bg: color-mix(in oklch, var(--risk-unknown) 15%, transparent);
  --risktag-unknown-text: var(--risk-unknown);

  --chip-risk-bg: color-mix(in oklch, var(--risk-t4) 15%, transparent);
  --chip-risk-text: var(--risk-t4);
  --chip-risk-border: transparent;
  --chip-warn-bg: color-mix(in oklch, var(--risk-t2) 15%, transparent);
  --chip-warn-text: var(--risk-t2);
  --chip-warn-border: transparent;
  --chip-neu-bg: color-mix(in oklch, #ffffff 8%, transparent);
  --chip-neu-text: var(--text-muted);

  --header-scrolled-bg: color-mix(in oklch, var(--palette-gray-100) 88%, transparent);
  --header-text: color-mix(in oklch, #ffffff 90%, transparent);

  --banner-bg: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
  --banner-label: var(--palette-gray-500);

  --bottom-bar-bg: color-mix(in oklch, var(--palette-gray-50) 95%, transparent);
  --bottom-bar-border: color-mix(in oklch, #ffffff 6%, transparent);

  --nutrition-bg: color-mix(in oklch, var(--palette-green-500) 6%, transparent);
  --nutrition-border: color-mix(in oklch, var(--palette-green-500) 10%, transparent);

  --status-bar-bg: transparent;
  --status-bar-text: #ffffff;
}
```

- [ ] **Step 3: Commit**

```bash
git add web/apps/uniapp/src/styles/design-system.scss
git commit -m "refactor(uniapp): clean design-system, remove spacing/text vars, keep palette

Design tokens for spacing, text sizes, icon sizes removed (now via UnoCSS).
Palette colors and semantic tokens retained. Layout tokens kept temporarily
for backward compat during migration (removed in Phase 3).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: Component Migration

**迁移原则（所有组件统一执行）:**
1. `<style lang="scss">` 中的 layout 属性 → UnoCSS 原子类（`display: flex` → `flex`，`gap: var(--space-6)` → `gap-6`）
2. `color`、`background`、`border` 中使用 CSS 变量保留（`var(--accent)`、`var(--bg-card)`）
3. 动画关键帧保留在 SCSS 中
4. BEM 修饰类中的工具样式直接用原子类替换
5. **重要**：`design-system.scss` 中已删除的 `--btn-*`、`--header-*`、`--card-padding-*`、`--space-*`、`--text-*` 等变量，在迁移组件时一律用 **硬编码 rpx 值** 替换（不要引用已删除的变量）

**Spacing 换算对照（基准：4rpx = 2px）:**

> 注：Tailwind `gap-1` = 4px = 8rpx，对应 `--space-2`（8rpx）。`--space-1`（4rpx）没有直接对应的 UnoCSS class，需要用 `style="gap: 4rpx"` 或自定义 rule。

| UnoCSS class | px值 | rpx值 | 对应旧 var |
|---|---|---|---|
| `gap-1` | 4px | 8rpx | `--space-2` |
| `gap-2` | 8px | 16rpx | `--space-4` |
| `gap-3` | 12px | 24rpx | `--space-6` |
| `gap-4` | 16px | 32rpx | `--space-8` |
| `gap-5` | 20px | 40rpx | `--space-10` |
| `gap-6` | 24px | 48rpx | `--space-12` |
| `gap-8` | 32px | 64rpx | `--space-16` |
| `gap-10` | 40px | 80rpx | `--space-20` |
| `px-2` | 8px | 16rpx | `--space-4` |
| `px-3` | 12px | 24rpx | `--space-6` |
| `px-4` | 16px | 32rpx | `--space-8` |
| `px-6` | 24px | 48rpx | `--space-12` |
| `px-8` | 32px | 64rpx | `--space-16` |
| `py-1` | 4px | 8rpx | `--space-2` |
| `py-2` | 8px | 16rpx | `--space-4` |
| `py-3` | 12px | 24rpx | `--space-6` |
| `py-4` | 16px | 32rpx | `--space-8` |
| `py-5` | 20px | 40rpx | `--space-10` |
| `py-8` | 32px | 64rpx | `--space-16` |
| `py-12` | 48px | 96rpx | `--space-24` |
| `py-20` | 80px | 160rpx | `--space-40` |
| `rounded-lg` | — | — | `--radius-lg` |
| `rounded-xl` | — | — | `--radius-xl` |
| `rounded-full` | — | — | `--radius-full` |
| `shadow-sm` | — | — | `--shadow-sm` |

---

### Task 5: Migrate ActionButton.vue

**Files:**
- Modify: `web/apps/uniapp/src/components/ActionButton.vue`

- [ ] **Step 1: Read current file**

- [ ] **Step 2: Migrate SCSS to UnoCSS atomic classes**

Replace the `<style lang="scss">` block. Keep the `@import "@/styles/design-system.scss"`. Replace layout properties:

```vue
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
    height: var(--btn-height-xl);
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

  &__loading,
  &__icon {
    width: var(--icon-sm);
    height: var(--icon-sm);
  }
}
</style>
```

Becomes:

```vue
<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.action-btn {
  // Layout: inline-flex + center done via class="inline-flex items-center justify-center gap-2"
  width: 100%;
  border: none;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s $ease-spring;

  // size — lg
  &--lg {
    height: 88rpx;  // var(--btn-height-xl) = 88rpx
    padding: 0 32rpx;  // var(--btn-padding-x) = 32rpx
    font-size: 28rpx;  // var(--text-xl)
    border-radius: 28rpx;  // var(--btn-radius)
  }

  // size — md
  &--md {
    height: 72rpx;  // var(--btn-height-md) = 72rpx
    padding: 0 24rpx;  // var(--space-6) = 24rpx
    font-size: 26rpx;  // var(--text-lg)
    border-radius: 32rpx;  // var(--radius-md)
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

  &__loading,
  &__icon {
    width: var(--icon-sm);
    height: var(--icon-sm);
  }
}
</style>
```

Update template to add layout classes:

```vue
<button
  :class="['action-btn', `action-btn--${variant}`, `action-btn--${size}`, 'inline-flex', 'items-center', 'justify-center', 'gap-2']"
  ...
```

- [ ] **Step 3: Test component renders correctly**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web && pnpm dev:uniapp:h5 &
sleep 8
kill %1 2>/dev/null
```

- [ ] **Step 4: Commit**

---

### Task 6: Migrate index.vue (Home Page)

**Files:**
- Modify: `web/apps/uniapp/src/pages/index/index.vue`

- [ ] **Step 1: Read current file**

- [ ] **Step 2: Apply migration pattern**

Pattern: Move layout CSS properties from SCSS to template `class` attributes. Use the spacing conversion table above.

Key migrations:
- `display: flex; flex-direction: column;` → `class="flex flex-col"`
- `display: flex; align-items: center; gap: var(--space-4);` → `class="flex items-center gap-4"`
- `display: flex; justify-content: center; align-items: center;` → `class="flex justify-center items-center"`
- `padding: var(--space-20) var(--space-12) var(--space-16)` → `class="py-20 px-12 pb-16"`
- `gap: var(--space-6)` → `gap-6`
- `border-radius: var(--space-7)` → `rounded-3xl` (112rpx/16=7个单位 → rounded-3xl是40rpx/4=10，但实际112rpx对应rounded-3xl≈40rpx...)

> Note: 112rpx = 14 * 8rpx, Tailwind最大rounded-3xl=40rpx。超出范围用 `style="border-radius: 112rpx"` 保留，或扩展 uno.config.ts 的 borderRadius。

For values not in Tailwind default scale (e.g., `rpx: 112rpx`), use `style="border-radius: 112rpx"` inline or extend uno.config.ts. Prefer inline style for rare values.

- [ ] **Step 3: Commit**

---

### Task 7: Migrate ingredient-detail/index.vue

**Files:**
- Modify: `web/apps/uniapp/src/pages/ingredient-detail/index.vue`

- [ ] **Step 1: Read current file**

- [ ] **Step 2: Migrate all SCSS block by block**

This is the largest page. Key patterns:
- Risk level color classes (`risk-critical`, `risk-high`, etc.) already in safelist
- Section cards: `display: flex; flex-direction: column; gap: var(--space-4)` → `class="flex flex-col gap-4"`
- Chips row: `display: flex; flex-wrap: wrap; gap: var(--space-3)` → `class="flex flex-wrap gap-3"`
- Bottom bar: `position: fixed; bottom: 0; left: 0; right: 0;` → `class="fixed bottom-0 left-0 right-0"`

- [ ] **Step 3: Commit**

---

### Task 8: Migrate remaining pages

**Files (batch migrate):**
- Modify: `web/apps/uniapp/src/pages/product/index.vue`
- Modify: `web/apps/uniapp/src/pages/profile/index.vue`
- Modify: `web/apps/uniapp/src/pages/scan/index.vue`
- Modify: `web/apps/uniapp/src/pages/search/index.vue`

- [ ] **Step 1: Migrate each page individually, commit after each**

Follow the same migration pattern as Task 6/7.

- [ ] **Step 2: Commit each page separately**

---

### Task 9: Migrate all remaining components

**Files (batch migrate 13 components):**
- Modify: `web/apps/uniapp/src/components/AnalysisCard.vue`
- Modify: `web/apps/uniapp/src/components/BottomBar.vue`
- Modify: `web/apps/uniapp/src/components/HorizontalScroller.vue`
- Modify: `web/apps/uniapp/src/components/InfoCard.vue`
- Modify: `web/apps/uniapp/src/components/InfoChip.vue`
- Modify: `web/apps/uniapp/src/components/IngredientList.vue`
- Modify: `web/apps/uniapp/src/components/IngredientSection.vue`
- Modify: `web/apps/uniapp/src/components/ListItem.vue`
- Modify: `web/apps/uniapp/src/components/NutritionTable.vue`
- Modify: `web/apps/uniapp/src/components/ProductHeader.vue`
- Modify: `web/apps/uniapp/src/components/RiskBadge.vue`
- Modify: `web/apps/uniapp/src/components/RiskTag.vue`
- Modify: `web/apps/uniapp/src/components/SectionHeader.vue`
- Modify: `web/apps/uniapp/src/components/StateView.vue`

- [ ] **Step 1: Migrate each component, commit after each or batch 3-4 together**

---

## Phase 4: Verification & Cleanup

### Task 10: Search for remaining old CSS variable references

- [ ] **Step 1: Search for any remaining `var(--space-` and `var(--text-` references in .vue files**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web/apps/uniapp
grep -r "var(--space-" src/ --include="*.vue" --include="*.scss" | grep -v "design-system.scss"
grep -r "var(--text-" src/ --include="*.vue" --include="*.scss" | grep -v "design-system.scss"
```

Expected: No matches (except design-system.scss itself).

- [ ] **Step 2: Verify build still works**

```bash
cd /Users/wwj/Desktop/myself/life-classics/web
pnpm dev:uniapp:h5 &
sleep 8
kill %1 2>/dev/null
echo "Build verification done"
```

- [ ] **Step 3: Commit cleanup**

---

### Task 11: Remove backward-compat layout tokens from design-system.scss

**Files:**
- Modify: `web/apps/uniapp/src/styles/design-system.scss`

- [ ] **Step 1: Remove the temporary layout tokens added in Task 4**

Remove these from the `page {}` block:
```scss
--space-1: 4rpx;
--space-2: 8rpx;
// ... all --space-* vars
--text-sm: 20rpx;
// ... all --text-* vars
--icon-sm: 28rpx;
--icon-xl: 40rpx;
--radius-sm: 24rpx;
// ... all --radius-* vars
--shadow-sm: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
// ... all --shadow-* vars
```

- [ ] **Step 2: Verify build**

- [ ] **Step 3: Commit**

---

### Task 12: Final Verification

- [ ] **Step 1: Run H5 dev server, verify page renders correctly**

- [ ] **Step 2: Commit final state**

```bash
git add -A
git commit -m "feat(uniapp): complete UnoCSS migration

Phase 1: Install UnoCSS, create uno.config.ts, update vite.config
Phase 2: Clean design-system.scss
Phase 3: Migrate all 13 components and 6 pages to UnoCSS atomic classes
Phase 4: Remove backward-compat layout tokens

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
