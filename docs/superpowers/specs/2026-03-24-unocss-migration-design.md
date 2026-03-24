# UnoCSS 迁移设计文档

**日期**：2026-03-24
**范围**：`web/apps/uniapp/src/` 所有组件和页面（21 个 Vue 文件）
**目标**：用 UnoCSS 原子类替代手写 CSS，style 块接近空

---

## 背景

昨天的自动化迁移结果不满意：
- UI 视觉偏离原始设计
- 1782 行 CSS 未被清除，仍大量残留
- 模板混入了 UnoCSS 类，但原 CSS class 也还在

根本原因：没有明确的映射规则，Claude 自行发挥；rpx 单位未处理；颜色体系未整理。

---

## 决策

### 1. 先回滚

回滚 uniapp 相关迁移 commit，保留 server/api commit（`0fb299f`、`dd9a8a7`、`bd8dbc9`、`eae429b`、`336fe93`）。
**策略**：对 uniapp 文件做定点还原（`git checkout <pre-migration-sha> -- src/`），而非 `git reset`。

### 2. 使用 unocss-preset-uni

安装 `unocss-preset-uni`，原生支持 rpx 单位，替换现有 `presetUno()`。

### 3. 颜色体系精简

**删除**：design-system.scss 中的 Palette 层（已在 uno.config.ts theme.colors 重复定义）和 Component 层。
**保留**：Semantic 层（约 20 个变量：`--text-primary`、`--bg-card`、`--risk-t4` 等）及暗色模式覆盖。
**新增**：Component 层迁移为 uno.config.ts shortcuts：

```ts
shortcuts: {
  'risk-t4-bg': 'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)]',
  'risk-t4-border': 'border-[color-mix(in_oklch,var(--risk-t4)_30%,transparent)]',
  'chip-risk': 'bg-[color-mix(in_oklch,var(--risk-t4)_12%,transparent)] text-[var(--risk-t4)]',
  // 其余 risk 等级同理
}
```

### 4. 迁移原则

| CSS 模式 | UnoCSS 写法 |
|---------|------------|
| `width: 80rpx` | `w-[80rpx]`（unocss-preset-uni 支持） |
| `display: flex; align-items: center` | `flex items-center` |
| `color: var(--text-primary)` | `text-[var(--text-primary)]` |
| `border-radius: var(--radius-md)` | `rounded-[var(--radius-md)]` |
| `transition: all 0.2s $ease-spring` | UnoCSS shortcut `transition-spring` |
| `color-mix(in oklch, var(--risk-t4) 12%, transparent)` | shortcut `risk-t4-bg` |
| `&:active { transform: scale(0.92) }` | `active:scale-92` |
| 状态嵌套 `.header--scrolled &` | UnoCSS custom variant 或保留极少量 style 并注明原因 |
| `$ease-spring`（SCSS 变量） | 迁移为 CSS 变量 `--ease-spring`，uno.config.ts 引用 |

**原则**：能用原子类就用，无法表达的用 shortcut/custom rule 封装，实在不行保留在 style 块并注明原因（预计极少数）。

---

## 迁移流水线

### Phase 0：准备（1 个 session）

1. 回滚 uniapp 迁移 commit，保留 server/api commit
2. 安装 `unocss-preset-uni`，更新 `uno.config.ts`
3. 精简 `design-system.scss`（删 Palette + Component 层）
4. 编写 `migration-guide.md`（所有 CSS 模式 → UnoCSS 映射，后续所有 session 的唯一参考）

### Phase 1：组件迁移（多个 session，每 session 处理 3-4 个组件）

每批：新 session → 读 migration-guide → 逐组件迁移 → 自检 → commit → 结束 session

| 批次 | 文件 | 复杂度 |
|------|------|--------|
| 批次 1 | ListItem、RiskBadge、InfoChip、SectionHeader | 低 |
| 批次 2 | RiskTag、StateView、ActionButton、HorizontalScroller | 低-中 |
| 批次 3 | AnalysisCard、InfoCard、IngredientList、NutritionTable | 中 |
| 批次 4 | ProductHeader、BottomBar、IngredientSection | 中-高 |
| 批次 5 | scan、profile、search、ingredient-detail 页面 | 中-高 |
| 批次 6 | product 页面（289 行 style）、index 页面 | 高 |

### Phase 2：验证（1 个 session）

- H5 构建，列出所有剩余 style 块及保留原因
- 修复明显视觉偏差

---

## 成功标准

- [ ] 所有 21 个 Vue 文件的 style 块行数总计 < 100 行（当前 1782 行）
- [ ] 视觉效果与迁移前一致（亮色 + 暗色模式）
- [ ] H5 构建无报错
- [ ] 每个保留的 style 块注明保留原因
