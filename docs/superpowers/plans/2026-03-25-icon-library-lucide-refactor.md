# Icon Library Lucide-Style Refactor Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 uniapp-tw 的 icon 系统重构为 Lucide 风格，支持 tree-shaking、按需导入、别名、完整类型安全。

**Architecture:**
- 每个 icon 独立文件（`icons/arrow-left.ts`），而非集中在一个大文件
- 工厂函数 `createIconComponent` 生成 Vue 组件
- 统一 `defaultAttributes` 管理 SVG 默认属性
- `aliases.ts` 管理图标别名（如 `left` → `arrow-left`）
- 双导出：命名导出（支持 tree-shaking）+ 命名空间导出

**Tech Stack:** TypeScript, Vue 3 (Script Setup), Vite

---

## File Structure

```
web/apps/uniapp-tw/src/components/
├── Icon.vue                      # 主入口组件（重写）
└── icons/
    ├── index.ts                  # 统一导出
    ├── types.ts                  # IconName 类型 + IconProps
    ├── defaultAttributes.ts      # SVG 默认属性
    ├── aliases.ts                # 别名映射
    ├── createIconComponent.ts    # 工厂函数
    └── icons/
        ├── arrow-left.ts
        ├── arrow-right.ts
        ├── x.ts
        ├── check.ts
        ├── chevron-down.ts
        ├── share.ts
        ├── star.ts
        ├── badge-check.ts
        ├── leaf.ts
        ├── help-circle.ts
        ├── alert-triangle.ts
        ├── info.ts
        ├── alert-circle.ts
        ├── shopping-cart.ts
        ├── scan.ts
        ├── user.ts
        ├── menu.ts
        ├── users.ts
        ├── bookmark.ts
        ├── settings.ts
        ├── search.ts
        ├── message-circle.ts
        └── loader.ts
```

---

## Task 1: Create `icons/types.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/types.ts`

- [ ] **Step 1: Write types.ts**

```typescript
/**
 * Icon Types — Lucide-style type definitions
 */

export interface IconAttributes {
  xmlns?: string;
  viewBox: string;
  fill?: 'none' | 'currentColor' | string;
  stroke?: 'none' | 'currentColor' | string;
  strokeWidth?: number | string;
  strokeLinecap?: 'butt' | 'round' | 'square';
  strokeLinejoin?: 'arcs' | 'bevel' | 'miter' | 'round';
  strokeDasharray?: number | string;
  strokeDashoffset?: number | string;
  strokeMiterlimit?: number | string;
}

export interface IconEntry {
  name: string;
  aliases?: string[];
  tags?: string[];
  contents: string;  // SVG path(s) as string
}

export interface IconProps {
  size?: number | string;
  strokeWidth?: number | string;
  absoluteStrokeWidth?: boolean;
  spin?: boolean;
}
```

---

## Task 2: Create `icons/defaultAttributes.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/defaultAttributes.ts`

- [ ] **Step 1: Write defaultAttributes.ts**

```typescript
/**
 * Default SVG Attributes — Lucide-style shared attributes
 */

import type { IconAttributes } from './types';

export const defaultAttributes: IconAttributes = {
  xmlns: 'http://www.w3.org/2000/svg',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};
```

---

## Task 3: Create `icons/icons/arrow-left.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/icons/arrow-left.ts`

- [ ] **Step 1: Write arrow-left.ts icon**

```typescript
import type { IconEntry } from '../types';

export const arrowLeft: IconEntry = {
  name: 'arrow-left',
  tags: ['arrow', 'direction', 'left', 'previous', 'back'],
  contents: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
};
```

---

## Task 4: Create remaining icon files

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/icons/arrow-right.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/x.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/check.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/chevron-down.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/share.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/star.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/badge-check.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/leaf.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/help-circle.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/alert-triangle.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/info.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/alert-circle.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/shopping-cart.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/scan.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/user.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/menu.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/users.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/bookmark.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/settings.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/search.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/message-circle.ts`
- Create: `web/apps/uniapp-tw/src/components/icons/icons/loader.ts`

- [ ] **Step 1: Write all icon files**

```typescript
// arrow-right.ts
import type { IconEntry } from '../types';

export const arrowRight: IconEntry = {
  name: 'arrow-right',
  tags: ['arrow', 'direction', 'right', 'next'],
  contents: '<path d="M5 12h14M12 5l7 7-7 7"/>',
};

// x.ts (filled variant - uses different path)
import type { IconEntry } from '../types';

export const x: IconEntry = {
  name: 'x',
  tags: ['close', 'delete', 'remove', 'cancel'],
  contents: '<path d="M18 6L6 18M6 6l12 12"/>',
};

// check.ts (filled icon)
import type { IconEntry } from '../types';

export const check: IconEntry = {
  name: 'check',
  tags: ['done', 'complete', 'tick'],
  contents: '<path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" fill="currentColor"/>',
};

// chevron-down.ts
import type { IconEntry } from '../types';

export const chevronDown: IconEntry = {
  name: 'chevron-down',
  tags: ['arrow', 'direction', 'down', 'expand'],
  contents: '<path d="M6 9l6 6 6-6"/>',
};

// share.ts
import type { IconEntry } from '../types';

export const share: IconEntry = {
  name: 'share',
  tags: ['share', 'social', 'send'],
  contents: '<path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>',
};

// star.ts (filled)
import type { IconEntry } from '../types';

export const star: IconEntry = {
  name: 'star',
  tags: ['star', 'rating', 'favorite'],
  contents: '<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" fill="currentColor"/>',
};

// badge-check.ts (filled)
import type { IconEntry } from '../types';

export const badgeCheck: IconEntry = {
  name: 'badge-check',
  tags: ['badge', 'verified', 'success'],
  contents: '<path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" fill="currentColor"/>',
};

// leaf.ts
import type { IconEntry } from '../types';

export const leaf: IconEntry = {
  name: 'leaf',
  tags: ['leaf', 'nature', 'safe', 'low-risk'],
  contents: '<path d="M6.5 21C3 17.5 3 12 6 8c2-2.5 5-4 8.5-4C18 4 21 7 21 10c0 2.5-1.5 4.5-3.5 5.5M12 22V12"/>',
};

// help-circle.ts (filled)
import type { IconEntry } from '../types';

export const helpCircle: IconEntry = {
  name: 'help-circle',
  tags: ['help', 'question', 'unknown'],
  contents: '<path d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" fill="currentColor"/>',
};

// alert-triangle.ts (filled)
import type { IconEntry } from '../types';

export const alertTriangle: IconEntry = {
  name: 'alert-triangle',
  tags: ['warning', 'alert', 'danger'],
  contents: '<path d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" fill="currentColor"/>',
};

// info.ts (filled)
import type { IconEntry } from '../types';

export const info: IconEntry = {
  name: 'info',
  tags: ['info', 'description'],
  contents: '<path d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" fill="currentColor"/>',
};

// alert-circle.ts (filled)
import type { IconEntry } from '../types';

export const alertCircle: IconEntry = {
  name: 'alert-circle',
  tags: ['alert', 'warning', 'error'],
  contents: '<path d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" fill="currentColor"/>',
};

// shopping-cart.ts (filled)
import type { IconEntry } from '../types';

export const shoppingCart: IconEntry = {
  name: 'shopping-cart',
  tags: ['cart', 'shop', 'product'],
  contents: '<path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3z" fill="currentColor"/>',
};

// scan.ts
import type { IconEntry } from '../types';

export const scan: IconEntry = {
  name: 'scan',
  tags: ['scan', 'barcode', 'qr'],
  contents: '<path d="M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2M7 12h10" stroke-width="2.5"/>',
};

// user.ts
import type { IconEntry } from '../types';

export const user: IconEntry = {
  name: 'user',
  tags: ['user', 'person', 'account'],
  contents: '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z"/>',
};

// menu.ts
import type { IconEntry } from '../types';

export const menu: IconEntry = {
  name: 'menu',
  tags: ['menu', 'hamburger', 'bars'],
  contents: '<path d="M4 6h16M4 12h16M4 18h16"/>',
};

// users.ts
import type { IconEntry } from '../types';

export const users: IconEntry = {
  name: 'users',
  tags: ['users', 'group', 'family'],
  contents: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>',
};

// bookmark.ts
import type { IconEntry } from '../types';

export const bookmark: IconEntry = {
  name: 'bookmark',
  tags: ['bookmark', 'favorite', 'save'],
  contents: '<path d="M5 3h14a1 1 0 011 1v18l-7-3-7 3V4a1 1 0 011-1z"/>',
};

// settings.ts
import type { IconEntry } from '../types';

export const settings: IconEntry = {
  name: 'settings',
  tags: ['settings', 'gear', 'cog'],
  contents: '<path d="M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>',
};

// search.ts
import type { IconEntry } from '../types';

export const search: IconEntry = {
  name: 'search',
  tags: ['search', 'find', 'magnifier'],
  contents: '<path d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>',
};

// message-circle.ts (filled)
import type { IconEntry } from '../types';

export const messageCircle: IconEntry = {
  name: 'message-circle',
  tags: ['message', 'chat', 'ai'],
  contents: '<path d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" fill="currentColor"/>',
};

// loader.ts
import type { IconEntry } from '../types';

export const loader: IconEntry = {
  name: 'loader',
  tags: ['loader', 'loading', 'spinner'],
  contents: '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>',
};
```

---

## Task 5: Create `icons/aliases.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/aliases.ts`

- [ ] **Step 1: Write aliases.ts**

```typescript
/**
 * Icon Aliases — Lucide-style backward compatibility aliases
 */

export const aliases: Record<string, string> = {
  // Direction
  left: 'arrow-left',
  right: 'arrow-right',
  'chevron-up': 'chevron-down', // inverse for some cases
  'chevron-left': 'arrow-left',

  // Close
  close: 'x',
  delete: 'x',
  remove: 'x',

  // Common
  home: 'arrow-left', // mapped to back for now
  back: 'arrow-left',

  // Social
  chat: 'message-circle',
  ai: 'message-circle',

  // Misc
  cart: 'shopping-cart',
  shop: 'shopping-cart',
};
```

---

## Task 6: Create `icons/createIconComponent.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/createIconComponent.ts`

- [ ] **Step 1: Write createIconComponent.ts**

```typescript
/**
 * Create Icon Component — Lucide-style factory function
 */

import { defaultAttributes } from './defaultAttributes';
import type { IconEntry, IconProps } from './types';

interface ComponentOptions {
  name: string;
  entry: IconEntry;
}

export function createIconComponent({ name, entry }: ComponentOptions) {
  return {
    name: `Icon${pascalCase(name)}`,
    props: {
      size: {
        type: [Number, String],
        default: 24,
      },
      strokeWidth: {
        type: [Number, String],
        default: 2,
      },
      absoluteStrokeWidth: {
        type: Boolean,
        default: false,
      },
      spin: {
        type: Boolean,
        default: false,
      },
    },
    setup(props: IconProps, { slots }: any) {
      const strokeWidth = () => {
        if (props.absoluteStrokeWidth) {
          return Number(props.strokeWidth) * (24 / Number(props.size));
        }
        return props.strokeWidth;
      };

      const renderedContent = () => {
        let content = entry.contents;
        // If filled icon, ensure fill="currentColor" is set
        if (content.includes('fill="currentColor"')) {
          return content;
        }
        // For stroke icons, add stroke attributes
        return content;
      };

      return () => ({
        type: 'svg',
        props: {
          xmlns: defaultAttributes.xmlns,
          viewBox: defaultAttributes.viewBox,
          width: props.size,
          height: props.size,
          fill: content.includes('fill="currentColor"') ? 'currentColor' : 'none',
          stroke: content.includes('fill="currentColor"') ? undefined : 'currentColor',
          strokeWidth: content.includes('fill="currentColor"') ? undefined : strokeWidth(),
          strokeLinecap: content.includes('fill="currentColor"') ? undefined : defaultAttributes.strokeLinecap,
          strokeLinejoin: content.includes('fill="currentColor"') ? undefined : defaultAttributes.strokeLinejoin,
          class: ['icon', { 'icon--spin': props.spin }],
          'aria-hidden': true,
        },
        children: content,
      });
    },
  };
}

function pascalCase(str: string): string {
  return str
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('');
}
```

---

## Task 7: Create `icons/index.ts`

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/index.ts`

- [ ] **Step 1: Write index.ts with all exports**

```typescript
/**
 * Icon Library — Lucide-style unified exports
 */

// Types
export type { IconName, IconProps, IconEntry, IconAttributes } from './types';

// Default attributes
export { defaultAttributes } from './defaultAttributes';

// Aliases
export { aliases } from './aliases';

// Individual icon exports (for tree-shaking)
export {
  arrowLeft,
  arrowRight,
  x,
  check,
  chevronDown,
  share,
  star,
  badgeCheck,
  leaf,
  helpCircle,
  alertTriangle,
  info,
  alertCircle,
  shoppingCart,
  scan,
  user,
  menu,
  users,
  bookmark,
  settings,
  search,
  messageCircle,
  loader,
} from './icons/arrow-left';
// ... re-export all icons individually

// Namespace export (for dynamic access)
export { icons } from './icons';

// Create icon component factory
export { createIconComponent } from './createIconComponent';
```

---

## Task 8: Rewrite `Icon.vue`

**Files:**
- Modify: `web/apps/uniapp-tw/src/components/Icon.vue`

- [ ] **Step 1: Rewrite Icon.vue to use new system**

```vue
<script setup lang="ts">
/**
 * Icon — Lucide-style icon component
 */
import { computed, useSlots } from 'vue';
import { defaultAttributes, aliases } from './icons';

interface Props {
  name: string;
  size?: number | string;
  strokeWidth?: number | string;
  absoluteStrokeWidth?: boolean;
  spin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  strokeWidth: 2,
  absoluteStrokeWidth: false,
  spin: false,
});

const slots = useSlots();

// Resolve icon name (handle aliases)
const resolvedName = computed(() => {
  const baseName = props.name.replace(/([A-Z])/g, '-$1').toLowerCase();
  return aliases[baseName] || baseName;
});

// Dynamic import of icon
const iconModule = computed(() => {
  try {
    return import(`./icons/icons/${resolvedName.value}.ts`);
  } catch {
    return null;
  }
});
</script>

<template>
  <svg
    class="icon"
    :class="{ 'icon--spin': spin }"
    :viewBox="defaultAttributes.viewBox"
    :width="size"
    :height="size"
    :fill="filled ? 'currentColor' : 'none'"
    :stroke="filled ? undefined : 'currentColor'"
    :stroke-width="filled ? undefined : effectiveStrokeWidth"
    :stroke-linecap="filled ? undefined : 'round'"
    :stroke-linejoin="filled ? undefined : 'round'"
    aria-hidden="true"
    v-if="iconModule"
  >
    <!-- Content rendered via innerHTML or dynamic component -->
  </svg>
  <span v-else class="icon-placeholder">{{ name }}</span>
</template>

<style lang="scss" scoped>
.icon {
  display: inline-block;
  flex-shrink: 0;
  vertical-align: middle;
  color: currentColor;

  &--spin {
    animation: spin 1.2s linear infinite;
  }
}

.icon-placeholder {
  font-size: 0.75em;
  opacity: 0.5;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
```

---

## Task 9: Create test file

**Files:**
- Create: `web/apps/uniapp-tw/src/components/icons/__tests__/icons.test.ts`

- [ ] **Step 1: Write test file**

```typescript
import { describe, it, expect } from 'vitest';
import { aliases, defaultAttributes } from '../';

describe('Icon Library', () => {
  describe('aliases', () => {
    it('should resolve left to arrow-left', () => {
      expect(aliases['left']).toBe('arrow-left');
    });

    it('should resolve close to x', () => {
      expect(aliases['close']).toBe('x');
    });
  });

  describe('defaultAttributes', () => {
    it('should have correct viewBox', () => {
      expect(defaultAttributes.viewBox).toBe('0 0 24 24');
    });

    it('should use currentColor for stroke', () => {
      expect(defaultAttributes.stroke).toBe('currentColor');
    });

    it('should have round linecap and linejoin', () => {
      expect(defaultAttributes.strokeLinecap).toBe('round');
      expect(defaultAttributes.strokeLinejoin).toBe('round');
    });
  });
});
```

---

## Task 10: Update import paths in consuming components

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/index/index.vue:204`
- Modify: `web/apps/uniapp-tw/src/pages/profile/index.vue` (multiple)
- Modify: `web/apps/uniapp-tw/src/pages/search/index.vue` (multiple)
- Modify: `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` (multiple)
- Modify: `web/apps/uniapp-tw/src/pages/product/index.vue` (multiple)
- Modify: `web/apps/uniapp-tw/src/components/Tag.vue:43`
- Modify: `web/apps/uniapp-tw/src/components/IngredientSection.vue:34`
- Modify: `web/apps/uniapp-tw/src/components/Button.vue:64`
- Modify: `web/apps/uniapp-tw/src/components/ProductHeader.vue:39,43`

- [ ] **Step 1: Update Icon import in all files**

```typescript
// Change from:
import { icons, type IconName } from "../utils/icons";

// Change to:
// For static imports (named exports)
import { Icon } from '@/components/Icon';

// For dynamic usage, icons can still be accessed via namespace
import { icons } from '@/components/icons';
```

---

## Task 11: Delete old icons.ts

**Files:**
- Delete: `web/apps/uniapp-tw/src/utils/icons.ts`

- [ ] **Step 1: Delete old icons.ts**

```bash
rm web/apps/uniapp-tw/src/utils/icons.ts
```

---

## Task 12: Run tests and verify

- [ ] **Step 1: Run tests**

```bash
cd web/apps/uniapp-tw
pnpm test --run
```

- [ ] **Step 2: Verify build**

```bash
cd web/apps/uniapp-tw
pnpm build
```

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
