# 色彩体系对齐实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `style.scss` 补全 `--accent-pink-light` / `--accent-pink` CSS 变量，并在 `tailwind.config.ts` 中映射到 Tailwind 类，使 `index.vue` 中的 `from-accent-pink-light to-accent-pink` 渐变生效。

**Architecture:** 通过 CSS 变量定义完整色彩值，再由 Tailwind 配置映射为原子类。`:root` 定义亮色值，`.dark` 定义暗色值，一步完成亮暗切换。

**Tech Stack:** Tailwind CSS v3, SCSS

---

## 文件修改映射

| 文件 | 修改位置 | 职责 |
|---|---|---|
| `web/apps/uniapp-tw/src/style.scss` | `:root` 和 `.dark` 块 | 定义 `--accent-pink-light` 和 `--accent-pink` CSS 变量 |
| `web/apps/uniapp-tw/tailwind.config.ts` | `colors` 对象 | 映射 `accent-pink-light` / `accent-pink` → 对应变量 |

---

### Task 1: 在 `style.scss` 中补全 CSS 变量

**文件:** `web/apps/uniapp-tw/src/style.scss`

- [ ] **Step 1: 在 `:root` 中添加 accent-pink 变量**

在 `--color-ring` 行之后插入：

```scss
  // accent pink 色系（与设计稿一致）
  --accent-pink-light: oklch(65% 0.2 330);   /* #ec4899，渐变起点 */
  --accent-pink: oklch(45% 0.18 330);          /* #db2777，渐变终点 / 主色 */
```

- [ ] **Step 2: 在 `.dark` 中添加对应变量**

在 `.dark` 块的 `--color-ring` 行之后插入：

```scss
  // accent pink 色系
  --accent-pink-light: oklch(75% 0.24 330);   /* 暗色偏亮 */
  --accent-pink: oklch(60% 0.22 330);          /* 与 --color-primary 暗色值一致 */
```

- [ ] **Step 3: 提交**

```bash
git add web/apps/uniapp-tw/src/style.scss
git commit -m "feat(uniapp-tw): add accent-pink CSS variables for gradient colors"
```

---

### Task 2: 在 `tailwind.config.ts` 中映射到 Tailwind 类

**文件:** `web/apps/uniapp-tw/tailwind.config.ts`

- [ ] **Step 1: 在 `colors` 对象中添加 accent-pink 映射**

在 `// 调色板色` 注释块之前添加：

```ts
        // accent pink 色系
        'accent-pink-light': 'var(--accent-pink-light)',
        'accent-pink': 'var(--accent-pink)',
```

- [ ] **Step 2: 验证 index.vue 引用**

确认 `src/pages/index/index.vue:128` 中的写法：

```html
class="scan-cta ... bg-gradient-to-br from-accent-pink-light to-accent-pink ..."
```

无需修改，Tailwind 配置好后即生效。

- [ ] **Step 3: 提交**

```bash
git add web/apps/uniapp-tw/tailwind.config.ts
git commit -m "feat(uniapp-tw): map accent-pink CSS vars to Tailwind classes"
```

---

### Task 3: 验证

**验证方式:** 启动 H5 开发服务器，肉眼确认首页扫一扫按钮渐变正确显示：

```bash
cd web && pnpm dev:uniapp:h5
```

预期：
- 亮色：`from-accent-pink-light (#ec4899)` → `to-accent-pink (#db2777)` 渐变生效
- 暗色：渐变跟随 `.dark` class 自动切换
