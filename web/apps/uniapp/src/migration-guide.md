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

Use `[Nrpx]` syntax for ALL rpx values. `unocss-preset-uni` converts rpx to rem units in H5 (e.g., `w-[80rpx]` → `width: 2.5rem`). Examples:

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
