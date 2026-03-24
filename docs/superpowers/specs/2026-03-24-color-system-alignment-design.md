# 色彩体系对齐设计方案

## 背景

项目从设计稿迁移到代码实现时，存在色彩体系未完全对齐的问题。设计稿 `homepage-tailwind-v13.html` 中定义了完整的 accent pink 色系，但实现中 CSS 变量缺失，导致 `index.vue` 等文件引用了不存在的 Tailwind 类。

## 问题分析

设计稿中的色彩定义与当前实现对照：

| 设计稿颜色 | CSS 变量 | 状态 |
|---|---|---|
| `#ec4899` (`--accent-pink-light`) | **不存在** | ❌ 缺失 |
| `#db2777` (`--accent-pink`) | `--color-primary: oklch(45% 0.18 330)` | ✅ 值一致，命名不同 |
| 渐变 `from-pink-400 to-pink-500` | `ActionButton` / `BottomBar` | ⚠️ 直接用 Tailwind 内置色 |

`index.vue` 模板中引用了 `from-accent-pink-light to-accent-pink`，该类在 Tailwind 配置中不存在，导致样式失效。

## 设计决策

- 所有颜色以 oklch 值存储，与设计稿精确对应
- `--accent-pink` 与 `--color-primary` 始终保持同值
- 暗色模式下渐变起点变亮、终点跟随主色，保证对比度
- 通过 CSS 变量 + Tailwind 映射双层机制，保证在 Vue 模板和 SCSS 中均可使用

## 修改范围

### 1. `src/style.scss`

在 `:root` 和 `.dark` 中新增 accent pink 色系变量：

```scss
:root {
  --accent-pink-light: oklch(65% 0.2 330);   /* #ec4899，渐变起点 */
  --accent-pink: oklch(45% 0.18 330);          /* #db2777，渐变终点 / 主色 */
}

.dark {
  --accent-pink-light: oklch(75% 0.24 330);   /* 暗色偏亮 */
  --accent-pink: oklch(60% 0.22 330);          /* 与 --color-primary 暗色值一致 */
}
```

### 2. `tailwind.config.ts`

在 `colors` 中新增映射：

```ts
colors: {
  // accent pink 色系
  'accent-pink-light': 'var(--accent-pink-light)',
  'accent-pink': 'var(--accent-pink)',
}
```

### 3. `src/pages/index/index.vue`

`from-accent-pink-light to-accent-pink` 无需改动，Tailwind 配置好后即生效。

### 4. `src/components/ActionButton.vue` / `src/components/BottomBar.vue`

当前使用 `@apply from-pink-400 to-pink-500`，保持在 SCSS 中使用 Tailwind 内置色（不影响暗色切换，如需统一可改为 `from-accent-pink-light to-accent-pink`）。

## 色彩值参考

| 变量名 | 亮色值 | 暗色值 | 用途 |
|---|---|---|---|
| `--accent-pink-light` | `oklch(65% 0.2 330)` | `oklch(75% 0.24 330)` | 渐变起点、图标色 |
| `--accent-pink` | `oklch(45% 0.18 330)` | `oklch(60% 0.22 330)` | 渐变终点、主色 |
| `--color-primary` | `oklch(45% 0.18 330)` | `oklch(60% 0.22 330)` | 与 `--accent-pink` 同步 |
