# uniapp-tw Component Organization Design

> **Date:** 2026-03-25
> **Status:** Approved

## Goal

整理 `web/apps/uniapp-tw/src/components/` 目录，将原子性组件、业务组件、图标库分类清晰组织，符合 shadcn/ui 风格。

## Target Structure

```
components/
├── ui/                    # 基础UI组件 (shadcn风格)
│   ├── Button.vue
│   ├── Tag.vue
│   ├── Icon.vue
│   ├── card/              # Card 组件系列
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
├── icons/                 # Lucide图标库
│   ├── index.ts
│   ├── types.ts
│   ├── aliases.ts
│   ├── defaultAttributes.ts
│   ├── iconsRegistry.ts
│   ├── createIconComponent.ts
│   ├── icons/             # 23个独立图标文件
│   │   ├── arrow-left.ts
│   │   ├── arrow-right.ts
│   │   ├── check.ts
│   │   └── ... (共23个)
│   └── __tests__/
│       └── icons.test.ts
│
└── business/              # 业务组件 (按页面模块分组)
    ├── analysis/
    │   └── AnalysisCard.vue
    ├── ingredient/
    │   ├── IngredientList.vue
    │   └── IngredientSection.vue
    └── product/
        └── ProductHeader.vue
```

## File Movements

| 文件 | 原位置 | 新位置 |
|------|--------|--------|
| Button.vue | `components/Button.vue` | `components/ui/Button.vue` |
| Tag.vue | `components/Tag.vue` | `components/ui/Tag.vue` |
| Icon.vue | `components/Icon.vue` | `components/ui/Icon.vue` |
| card/ | `components/card/` | `components/ui/card/` |
| ActionButton.vue | `components/ActionButton.vue` | `components/ui/ActionButton.vue` |
| BottomBar.vue | `components/BottomBar.vue` | `components/ui/BottomBar.vue` |
| HorizontalScroller.vue | `components/HorizontalScroller.vue` | `components/ui/HorizontalScroller.vue` |
| InfoCard.vue | `components/InfoCard.vue` | `components/ui/InfoCard.vue` |
| InfoChip.vue | `components/InfoChip.vue` | `components/ui/InfoChip.vue` |
| ListItem.vue | `components/ListItem.vue` | `components/ui/ListItem.vue` |
| NutritionTable.vue | `components/NutritionTable.vue` | `components/ui/NutritionTable.vue` |
| RiskBadge.vue | `components/RiskBadge.vue` | `components/ui/RiskBadge.vue` |
| RiskTag.vue | `components/RiskTag.vue` | `components/ui/RiskTag.vue` |
| SectionHeader.vue | `components/SectionHeader.vue` | `components/ui/SectionHeader.vue` |
| StateView.vue | `components/StateView.vue` | `components/ui/StateView.vue` |
| icons/ | `components/icons/` | `components/icons/` (不变) |
| AnalysisCard.vue | `components/AnalysisCard.vue` | `components/business/analysis/AnalysisCard.vue` |
| IngredientList.vue | `components/IngredientList.vue` | `components/business/ingredient/IngredientList.vue` |
| IngredientSection.vue | `components/IngredientSection.vue` | `components/business/ingredient/IngredientSection.vue` |
| ProductHeader.vue | `components/ProductHeader.vue` | `components/business/product/ProductHeader.vue` |

## Import Path Updates

需要更新引用的文件：
- `pages/index/` - 引用 AnalysisCard, Icon
- `pages/profile/` - 引用 Icon
- `pages/search/` - 引用 Icon
- `pages/ingredient-detail/` - 引用 Icon, IngredientList, IngredientSection
- `pages/product/` - 引用 Icon, ProductHeader
- `components/Tag.vue` - 引用 Icon, IconName
- `components/Button.vue` - 引用 Icon, IconName
- `components/business/` - 内部相互引用

## Principles

1. **ui/** - 可复用的基础UI组件，无业务逻辑
2. **icons/** - Lucide风格图标库，独立管理
3. **business/** - 业务组件，按页面模块分组，便于查找和维护
