# Component Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重组 uniapp-tw 组件目录结构，将原子组件、业务组件、图标库分类清晰组织。

**Architecture:** 按照 ui/、icons/、business/ 三层结构重组组件目录，ui/ 存放基础组件，icons/ 存放 Lucide 图标库，business/ 按页面模块分组存放业务组件。

**Tech Stack:** Vue 3, TypeScript, UniApp

---

## File Structure

```
web/apps/uniapp-tw/src/components/
├── ui/                    # 移动：所有原子组件
│   ├── Button.vue
│   ├── Tag.vue
│   ├── Icon.vue
│   ├── card/
│   │   ├── Card.vue
│   │   ├── CardContent.vue
│   │   ├── CardDescription.vue
│   │   ├── CardFooter.vue
│   │   ├── CardHeader.vue
│   │   └── CardTitle.vue
│   ├── ActionButton.vue
│   ├── BottomBar.vue
│   ├── HorizontalScroller.vue
│   ├── InfoCard.vue
│   ├── InfoChip.vue
│   ├── ListItem.vue
│   ├── NutritionTable.vue
│   ├── RiskBadge.vue
│   ├── RiskTag.vue
│   ├── SectionHeader.vue
│   └── StateView.vue
│
├── icons/                 # 不变：Lucide 图标库
│   ├── index.ts
│   ├── types.ts
│   ├── aliases.ts
│   ├── defaultAttributes.ts
│   ├── iconsRegistry.ts
│   ├── createIconComponent.ts
│   └── icons/
│
└── business/              # 移动：业务组件（按页面模块）
    ├── analysis/
    │   └── AnalysisCard.vue
    ├── ingredient/
    │   ├── IngredientList.vue
    │   └── IngredientSection.vue
    └── product/
        └── ProductHeader.vue
```

---

## Task 1: Create directory structure

**Files:**
- Create: `web/apps/uniapp-tw/src/components/ui/`
- Create: `web/apps/uniapp-tw/src/components/business/`
- Create: `web/apps/uniapp-tw/src/components/business/analysis/`
- Create: `web/apps/uniapp-tw/src/components/business/ingredient/`
- Create: `web/apps/uniapp-tw/src/components/business/product/`

- [ ] **Step 1: Create directories**

```bash
mkdir -p web/apps/uniapp-tw/src/components/ui
mkdir -p web/apps/uniapp-tw/src/components/business/analysis
mkdir -p web/apps/uniapp-tw/src/components/business/ingredient
mkdir -p web/apps/uniapp-tw/src/components/business/product
```

---

## Task 2: Move ui components

**Files:**
- Move: `components/Button.vue` → `components/ui/Button.vue`
- Move: `components/Tag.vue` → `components/ui/Tag.vue`
- Move: `components/Icon.vue` → `components/ui/Icon.vue`
- Move: `components/card/` → `components/ui/card/`
- Move: `components/ActionButton.vue` → `components/ui/ActionButton.vue`
- Move: `components/BottomBar.vue` → `components/ui/BottomBar.vue`
- Move: `components/HorizontalScroller.vue` → `components/ui/HorizontalScroller.vue`
- Move: `components/InfoCard.vue` → `components/ui/InfoCard.vue`
- Move: `components/InfoChip.vue` → `components/ui/InfoChip.vue`
- Move: `components/ListItem.vue` → `components/ui/ListItem.vue`
- Move: `components/NutritionTable.vue` → `components/ui/NutritionTable.vue`
- Move: `components/RiskBadge.vue` → `components/ui/RiskBadge.vue`
- Move: `components/RiskTag.vue` → `components/ui/RiskTag.vue`
- Move: `components/SectionHeader.vue` → `components/ui/SectionHeader.vue`
- Move: `components/StateView.vue` → `components/ui/StateView.vue`

- [ ] **Step 1: Move ui components**

```bash
mv web/apps/uniapp-tw/src/components/Button.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/Tag.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/Icon.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/card web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/ActionButton.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/BottomBar.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/HorizontalScroller.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/InfoCard.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/InfoChip.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/ListItem.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/NutritionTable.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/RiskBadge.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/RiskTag.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/SectionHeader.vue web/apps/uniapp-tw/src/components/ui/
mv web/apps/uniapp-tw/src/components/StateView.vue web/apps/uniapp-tw/src/components/ui/
```

---

## Task 3: Move business components

**Files:**
- Move: `components/AnalysisCard.vue` → `components/business/analysis/AnalysisCard.vue`
- Move: `components/IngredientList.vue` → `components/business/ingredient/IngredientList.vue`
- Move: `components/IngredientSection.vue` → `components/business/ingredient/IngredientSection.vue`
- Move: `components/ProductHeader.vue` → `components/business/product/ProductHeader.vue`

- [ ] **Step 1: Move business components**

```bash
mv web/apps/uniapp-tw/src/components/AnalysisCard.vue web/apps/uniapp-tw/src/components/business/analysis/
mv web/apps/uniapp-tw/src/components/IngredientList.vue web/apps/uniapp-tw/src/components/business/ingredient/
mv web/apps/uniapp-tw/src/components/IngredientSection.vue web/apps/uniapp-tw/src/components/business/ingredient/
mv web/apps/uniapp-tw/src/components/ProductHeader.vue web/apps/uniapp-tw/src/components/business/product/
```

---

## Task 4: Update import paths in Tag.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/components/ui/Tag.vue`

- [ ] **Step 1: Update import path**

```typescript
// Change from:
import Icon from './Icon.vue'
import type { IconName } from './icons/iconsRegistry'

// Change to:
import Icon from './Icon.vue'
import type { IconName } from '../icons/iconsRegistry'
```

---

## Task 5: Update import paths in Button.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/components/ui/Button.vue`

- [ ] **Step 1: Update import path**

```typescript
// Change from:
import Icon from './Icon.vue'
import type { IconName } from './icons/iconsRegistry'

// Change to:
import Icon from './Icon.vue'
import type { IconName } from '../icons/iconsRegistry'
```

---

## Task 6: Update import paths in pages/index/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/index/index.vue`

- [ ] **Step 1: Update import paths**

```typescript
// Change from:
import Icon from "../../components/Icon.vue"

// Change to:
import Icon from "@/components/ui/Icon.vue"
```

---

## Task 7: Update import paths in pages/profile/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/profile/index.vue`

- [ ] **Step 1: Update import paths**

```typescript
// Change from:
import Icon from '@/components/Icon.vue'

// Change to:
import Icon from '@/components/ui/Icon.vue'
```

---

## Task 8: Update import paths in pages/search/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/search/index.vue`

- [ ] **Step 1: Update import paths**

```typescript
// Change from:
import Icon from '@/components/Icon.vue'

// Change to:
import Icon from '@/components/ui/Icon.vue'
```

---

## Task 9: Update import paths in pages/ingredient-detail/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue`

- [ ] **Step 1: Update import paths**

```typescript
// Change from:
import Icon from '../../components/Icon.vue'

// Change to:
import Icon from "@/components/ui/Icon.vue"
```

---

## Task 10: Update import paths in pages/product/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/product/index.vue`

- [ ] **Step 1: Update import paths**

```typescript
// Change from:
import ProductHeader from "../../components/ProductHeader.vue";
import IngredientSection from "../../components/IngredientSection.vue";
import BottomBar from "../../components/BottomBar.vue";
import Icon from "../../components/Icon.vue";

// Change to:
import ProductHeader from "@/components/business/product/ProductHeader.vue";
import IngredientSection from "@/components/business/ingredient/IngredientSection.vue";
import BottomBar from "@/components/ui/BottomBar.vue";
import Icon from "@/components/ui/Icon.vue";
```

---

## Task 11: Verify build

**Files:**
- Verify: `web/apps/uniapp-tw/src/`

- [ ] **Step 1: Run type check**

```bash
cd web/apps/uniapp-tw
pnpm typecheck 2>&1 || vue-tsc --noEmit 2>&1
```

- [ ] **Step 2: Try build (if available)**

```bash
cd web/apps/uniapp-tw
pnpm build 2>&1
```

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
