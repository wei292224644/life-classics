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
| 状态嵌套 `.header--scrolled &` | UnoCSS custom variant；若涉及父级 `.dark &` 且组件为 scoped，需改用 `:deep()` 或将该块移入独立非 scoped `<style>` 块 |
| `$ease-spring`（SCSS 变量） | 迁移为 CSS 变量 `--ease-spring`，uno.config.ts 引用 |
| `@keyframes` 动画块 | 保留在各组件 style 块，`animation:` 属性用 `animation-[...]` 任意值写法；Phase 0 migration-guide 中列出所有动画名 |
| `backdrop-filter`、`radial-gradient` 等复合属性 | 保留在 style 块，注明"无法原子化" |

**原则**：能用原子类就用，无法表达的用 shortcut/custom rule 封装，实在不行保留在 style 块并注明原因。

**scoped 与 `.dark &` 冲突说明**：`<style scoped>` 下 Vue 会为所有选择器注入 `[data-v-xxx]`，导致 `.dark &` 父选择器失效（`.dark` 在 `page` 元素上，不含 scoped 属性）。解法：将依赖 `.dark &` 的样式块改为 `:deep()` 写法，或单独用一个非 scoped `<style>` 块承载。

---

## 迁移流水线

### Phase 0：准备（1 个 session）

1. 回滚 uniapp 迁移 commit，保留 server/api commit
2. 安装 `unocss-preset-uni`，更新 `uno.config.ts`
3. **rpx 支持验证**：用最简单的组件（ListItem）写一个包含 `w-[80rpx]` 的测试类，执行 H5 构建，检查产物 CSS 中 rpx 是否原样保留；验证通过再进入后续步骤
4. 精简 `design-system.scss`（删 Palette + Component 层）
5. 编写 `migration-guide.md`（所有 CSS 模式 → UnoCSS 映射，包含所有 @keyframes 名称列表，后续所有 session 的唯一参考）

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

- [ ] 所有 21 个 Vue 文件的 style 块行数总计 < 200 行（当前 1782 行；允许保留 @keyframes、backdrop-filter、radial-gradient 等无法原子化的内容，但必须注明原因）
- [ ] 视觉效果与迁移前一致（亮色 + 暗色模式）
- [ ] H5 构建无报错
- [ ] 每个保留的 style 块注明保留原因
