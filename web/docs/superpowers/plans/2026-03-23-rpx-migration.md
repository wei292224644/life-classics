# Rpx 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** 将 UniApp 组件中硬编码的 width/height/padding/margin rpx 值替换为 `--space-*` CSS 变量，超出 space 范围的保持硬编码 rpx。

**架构：** 纯 CSS 迁移，无架构变更。逐文件扫描替换。

**涉及文件（共 13 个）：**

| 文件 | rpx 出现次数 | 需要迁移的属性 |
|------|------------|--------------|
| `pages/index/index.vue` | 39 | padding, margin, width, height, gap |
| `pages/search/index.vue` | 23 | padding, margin, width, height, gap |
| `pages/profile/index.vue` | 18 | padding, margin, width, height, gap |
| `pages/ingredient-detail/index.vue` | 15 | padding, margin, width, height, gap |
| `components/ProductHeader.vue` | 8 | padding, margin, width, height, gap |
| `components/IngredientSection.vue` | 11 | padding, margin, width, height, gap |
| `components/NutritionTable.vue` | 8 | padding, margin, width, height, gap |
| `pages/product/index.vue` | 3 | padding, margin, width, height, gap |
| `components/BottomBar.vue` | 2 | padding, margin, width, height, gap |
| `components/AnalysisCard.vue` | 1 | padding, margin |
| `components/ActionButton.vue` | 1 | padding, margin |
| `pages/scan/index.vue` | 1 | - |
| `components/IngredientList.vue` | 1 | padding, margin |

**迁移规则（按属性）：**

| 属性 | 规则 |
|------|------|
| `padding`, `margin` | 用 `--space-*` |
| `width`, `height` | 用 `--space-*` |
| `gap` | 用 `--space-*` |
| `font-size` | 不迁移（已在 --text-* 体系） |
| `border-radius` | 不迁移（已在 --radius-* 体系） |
| `box-shadow` 值 | 不迁移 |
| `border: N rpx` | 不迁移（border-width 用 1px） |

**可替换的 space 映射（Tailwind CSS Spacing Scale × 2 = rpx）：**

```
0      → var(--space-0)     2rpx   → var(--space-px)
4rpx   → var(--space-1/0-5)  8rpx   → var(--space-2/1-5)
12rpx  → var(--space-3/2-5)  16rpx  → var(--space-4/3-5)
20rpx  → var(--space-5/4-5)  24rpx  → var(--space-6/5-5)
28rpx  → var(--space-7/6-5)  32rpx  → var(--space-8/7-5)
36rpx  → var(--space-9/8-5)  40rpx  → var(--space-10/9-5)
44rpx  → var(--space-11/10-5) 48rpx → var(--space-12/11-5)
52rpx  → var(--space-13/12-5) 56rpx → var(--space-14/13-5)
60rpx  → var(--space-15/14-5) 64rpx → var(--space-16/15-5)
72rpx  → var(--space-18/16-5) 80rpx → var(--space-20/18-5)
88rpx  → var(--space-22/20-5) 96rpx → var(--space-24/22-5)
112rpx → var(--space-28)   128rpx → var(--space-32)
144rpx → var(--space-36)   160rpx → var(--space-40)
192rpx → var(--space-48)   224rpx → var(--space-56)
256rpx → var(--space-64)   288rpx → var(--space-72)
320rpx → var(--space-80)   384rpx → var(--space-96)
```

**超出 Tailwind scale 范围、保持硬编码 rpx：**
- `280rpx`、`260rpx`、`371rpx`、`520rpx` 等
- `border: 4rpx solid` 中的 4rpx 保持不变

---

## 实施任务

### Task 1: pages/index/index.vue

**文件：** `web/apps/uniapp/src/pages/index/index.vue`

**迁移步骤：**

- [ ] **Step 1: 替换 padding 值**

```scss
// 替换 (行号基于当前文件)
padding-bottom: calc(80rpx + env(safe-area-inset-bottom));
→ padding-bottom: calc(var(--space-20) + env(safe-area-inset-bottom));

padding: 80rpx 48rpx 64rpx;
→ padding: var(--space-20) var(--space-12) var(--space-16);

padding: 80rpx 0 64rpx;
→ padding: var(--space-20) 0 var(--space-16);

padding: 0 48rpx 24rpx;
→ padding: 0 var(--space-12) var(--space-6);

padding: 0 48rpx 40rpx;
→ padding: 0 var(--space-12) var(--space-10);

padding: 28rpx 32rpx;
→ padding: var(--space-7) var(--space-8);

padding: 4rpx 12rpx;
→ padding: var(--space-1) var(--space-3);

padding: 48rpx 0;
→ padding: var(--space-12) 0;
```

- [ ] **Step 2: 替换 margin 值**

```scss
margin-bottom: 8rpx;  → margin-bottom: var(--space-2);
margin-bottom: 4rpx;  → margin-bottom: var(--space-1);
```

- [ ] **Step 3: 替换 width/height 值**

```scss
width: 280rpx; height: 280rpx;  → 硬编码（280rpx 不在 space 列表）
width: 72rpx; height: 72rpx;    → 硬编码（72rpx 不在 space 列表）
width: 80rpx; height: 80rpx;     → width: var(--space-20); height: var(--space-20);
width: 32rpx; height: 32rpx;    → 硬编码（32rpx 不在 space 列表）
```

- [ ] **Step 4: 验证并运行**

启动 H5 开发服务器确认无报错：`pnpm dev:uniapp:h5`

---

### Task 2: pages/search/index.vue

**文件：** `web/apps/uniapp/src/pages/search/index.vue`

- [ ] **Step 1: 扫描并替换** — 检查所有 rpx 值，替换 padding/margin/gap/width/height 中可用 --space-* 的项

**典型替换：**
```scss
padding: 0 var(--space-4);           // var(--space-4) = 16rpx
padding: var(--space-4) var(--space-6); // 16rpx 24rpx
padding: var(--space-16) 0;           // 64rpx 0
gap: var(--space-3);                  // 12rpx
gap: var(--space-4);                  // 16rpx
margin-bottom: var(--space-4);        // 16rpx
```

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 3: pages/profile/index.vue

**文件：** `web/apps/uniapp/src/pages/profile/index.vue`

- [ ] **Step 1: 扫描并替换** — 重点处理 `height: 88rpx`（不在 space → 硬编码）、`width: 60rpx`（不在 space → 硬编码）等

**典型替换：**
```scss
height: 88rpx;  → 硬编码（88rpx 不在 space 列表）
width: 60rpx;   → 硬编码（60rpx 不在 space 列表）
padding: 0 var(--space-4); → var(--space-4) = 16rpx
gap: var(--space-3);       → var(--space-3) = 12rpx
```

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 4: pages/ingredient-detail/index.vue

**文件：** `web/apps/uniapp/src/pages/ingredient-detail/index.vue`

- [ ] **Step 1: 扫描并替换** — 检查 padding/margin/gap/width/height

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 5: components/ProductHeader.vue

**文件：** `web/apps/uniapp/src/components/ProductHeader.vue`

- [ ] **Step 1: 扫描并替换** — 重点处理 padding 值

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 6: components/IngredientSection.vue

**文件：** `web/apps/uniapp/src/components/IngredientSection.vue`

- [ ] **Step 1: 扫描并替换**

**典型替换：**
```scss
padding: var(--space-8);        // 32rpx
margin-bottom: var(--space-6);   // 24rpx
gap: var(--space-4);             // 16rpx
width: var(--space-4);          // 16rpx
height: var(--space-4);          // 16rpx
padding: var(--space-2) var(--space-5);  // 8rpx 20rpx
width: var(--space-7);          // 28rpx
height: var(--space-7);          // 28rpx
padding-left: var(--space-4);    // 16rpx
```

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 7: components/NutritionTable.vue

**文件：** `web/apps/uniapp/src/components/NutritionTable.vue`

- [ ] **Step 1: 扫描并替换**

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

### Task 8: pages/product/index.vue + BottomBar.vue + AnalysisCard.vue + ActionButton.vue + IngredientList.vue + scan/index.vue

**文件：** 其余 6 个文件（共约 8 处 rpx）

- [ ] **Step 1: 扫描并替换** — 每个文件逐个检查

- [ ] **Step 2: 验证** — `pnpm dev:uniapp:h5`

---

## 验收标准

1. 所有 `padding`、`margin`、`gap`、`width`、`height` 中涉及 4/8/12/16/20/24/28/32/40/48/56/64/80rpx 的值均已替换为 `--space-*` 变量
2. `font-size`、`border-radius`、`box-shadow` 中的 rpx **不迁移**（已在各自体系）
3. 超出 space 列表的值保持硬编码 rpx
4. H5 开发服务器启动无报错
