# Web Monorepo Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 T3 Turbo monorepo 迁移到纯 pnpm workspace，删除所有不再需要的 packages 和 apps，为 uni-app 接入做好工程准备。

**Architecture:** 保留 `apps/`（console + uniapp）和 `tooling/`（eslint/prettier/typescript），删除 `packages/`（db/api/auth/ui/validators/db-seed）、`apps/nextjs`、Turborepo 配置和 `tooling/tailwind`。console 已直接依赖 Radix UI，不依赖 `@acme/ui`，无需 UI 层面的重构。

**Tech Stack:** pnpm workspace、pnpm-workspace.yaml

---

## 文件结构变更

```
删除：
  web/apps/nextjs/               整个目录
  web/packages/                  整个目录（db/api/auth/ui/validators/db-seed）
  web/tooling/tailwind/          不再需要
  web/tooling/github/            CI/CD 配置随 turbo 一起废弃
  web/turbo.json

修改：
  web/package.json               移除 turbo 脚本和依赖，简化为 pnpm workspace 脚本
  web/pnpm-workspace.yaml        移除 packages/*，清理不再需要的 catalog 条目
  web/tooling/eslint/base.ts     移除 turbo eslint 插件引用

保留：
  web/apps/console/              不变
  web/tooling/eslint/
  web/tooling/prettier/
  web/tooling/typescript/
```

---

### Task 1: 删除 apps/nextjs

**Files:**
- Delete: `web/apps/nextjs/`（整个目录）

- [ ] **Step 1: 删除 nextjs 应用目录**

```bash
rm -rf web/apps/nextjs
```

- [ ] **Step 2: 验证 console 仍可正常启动**

```bash
cd web
pnpm --filter @acme/console dev
```

预期：Vite 启动，无报错（Ctrl+C 退出即可）

- [ ] **Step 3: Commit**

```bash
git add -A web/apps/nextjs
git commit -m "chore: remove nextjs app"
```

---

### Task 2: 删除 packages/

**Files:**
- Delete: `web/packages/` （db / api / auth / ui / validators / db-seed）

- [ ] **Step 1: 删除整个 packages 目录**

```bash
rm -rf web/packages
```

- [ ] **Step 2: 验证 console 仍可构建**

```bash
cd web
pnpm install
pnpm build:console
```

预期：`web/apps/console/dist/` 生成成功，无依赖找不到的报错

- [ ] **Step 3: Commit**

```bash
git add -A web/packages
git commit -m "chore: remove all shared packages (db/api/auth/ui/validators/db-seed)"
```

---

### Task 3: 删除 tooling/tailwind 和 tooling/github

**Files:**
- Delete: `web/tooling/tailwind/`
- Delete: `web/tooling/github/`

- [ ] **Step 1: 删除两个目录**

```bash
rm -rf web/tooling/tailwind web/tooling/github
```

- [ ] **Step 2: Commit**

```bash
git add -A web/tooling/tailwind web/tooling/github
git commit -m "chore: remove tailwind and github tooling packages"
```

---

### Task 4: 移除 Turborepo

**Files:**
- Delete: `web/turbo.json`
- Modify: `web/package.json`

- [ ] **Step 1: 删除 turbo.json**

```bash
rm web/turbo.json
```

- [ ] **Step 2: 更新 `web/package.json`**

将整个文件替换为（保留必要的 workspace 脚本，移除 turbo）：

```json
{
  "name": "life-classics-web",
  "private": true,
  "engines": {
    "node": "^22.21.0",
    "pnpm": "^10.19.0"
  },
  "packageManager": "pnpm@10.19.0",
  "scripts": {
    "dev:console": "pnpm --filter @acme/console dev",
    "build:console": "pnpm --filter @acme/console build",
    "dev:uniapp:weapp": "pnpm --filter @acme/uniapp dev:mp-weixin",
    "dev:uniapp:alipay": "pnpm --filter @acme/uniapp dev:mp-alipay",
    "dev:uniapp:tt": "pnpm --filter @acme/uniapp dev:mp-toutiao",
    "dev:uniapp:h5": "pnpm --filter @acme/uniapp dev:h5",
    "build:uniapp:weapp": "pnpm --filter @acme/uniapp build:mp-weixin",
    "lint": "pnpm -r run lint",
    "format": "pnpm -r run format",
    "typecheck": "pnpm -r run typecheck"
  },
  "devDependencies": {
    "prettier": "catalog:",
    "typescript": "catalog:"
  },
  "prettier": "@acme/prettier-config"
}
```

- [ ] **Step 3: 运行 pnpm install 验证**

```bash
cd web
pnpm install
```

预期：安装成功，无依赖找不到的报错

- [ ] **Step 4: Commit**

```bash
git add web/turbo.json web/package.json
git commit -m "chore: remove turborepo, replace with plain pnpm workspace scripts"
```

---

### Task 5: 更新 pnpm-workspace.yaml

**Files:**
- Modify: `web/pnpm-workspace.yaml`

- [ ] **Step 1: 替换 pnpm-workspace.yaml**

```yaml
packages:
  - apps/*
  - tooling/*

catalog:
  "@types/node": ^22.18.12
  "@vitejs/plugin-react": 5.1.0
  eslint: ^9.38.0
  prettier: ^3.6.2
  tailwindcss: ^4.1.16
  typescript: ^5.9.3
  vite: 7.1.12

catalogs:
  react19:
    "@types/react": ~19.1.0
    "@types/react-dom": ~19.1.0
    react: 19.1.2
    react-dom: 19.1.2

linkWorkspacePackages: true

onlyBuiltDependencies:
  - "@tailwindcss/oxide"
  - esbuild

overrides:
  lightningcss: 1.30.1
  vite: 7.1.12

publicHoistPattern:
  - "@ianvs/prettier-plugin-sort-imports"
  - prettier-plugin-tailwindcss
```

- [ ] **Step 2: 运行 pnpm install 验证**

```bash
cd web
pnpm install
```

预期：安装成功，catalog 解析无报错

- [ ] **Step 3: Commit**

```bash
git add web/pnpm-workspace.yaml
git commit -m "chore: simplify pnpm-workspace.yaml, remove packages/* and unused catalogs"
```

---

### Task 6: 清理 ESLint tooling

**Files:**
- Modify: `web/tooling/eslint/base.ts`
- Modify: `web/tooling/eslint/package.json`

`base.ts` 当前引用了 `eslint-plugin-turbo`，需要移除。

- [ ] **Step 1: 更新 `web/tooling/eslint/base.ts`**

移除 turbo plugin 相关代码，将文件更新为：

```typescript
import * as path from "node:path";
import { includeIgnoreFile } from "@eslint/compat";
import eslint from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";

export const restrictEnvAccess = defineConfig(
  { ignores: ["**/env.ts"] },
  {
    files: ["**/*.js", "**/*.ts", "**/*.tsx"],
    rules: {
      "no-restricted-properties": [
        "error",
        {
          object: "process",
          property: "env",
          message: "Use typed env config instead of process.env directly.",
        },
      ],
    },
  },
);

export const baseConfig = defineConfig(
  includeIgnoreFile(path.join(import.meta.dirname, "../../.gitignore")),
  { ignores: ["**/*.config.*"] },
  {
    files: ["**/*.js", "**/*.ts", "**/*.tsx"],
    plugins: {
      import: importPlugin,
    },
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.recommended,
      ...tseslint.configs.recommendedTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
    ],
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/consistent-type-imports": [
        "warn",
        { prefer: "type-imports", fixStyle: "separate-type-imports" },
      ],
      "@typescript-eslint/no-misused-promises": [
        2,
        { checksVoidReturn: { attributes: false } },
      ],
      "@typescript-eslint/no-unnecessary-condition": [
        "error",
        { allowConstantLoopConditions: true },
      ],
      "@typescript-eslint/no-non-null-assertion": "error",
      "import/consistent-type-specifier-style": ["error", "prefer-top-level"],
    },
  },
  {
    linterOptions: { reportUnusedDisableDirectives: true },
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
);
```

- [ ] **Step 2: 从 `web/tooling/eslint/package.json` 移除 turbo 依赖**

打开 `web/tooling/eslint/package.json`，删除 `eslint-plugin-turbo` 相关条目。

- [ ] **Step 3: 运行 pnpm install**

```bash
cd web
pnpm install
```

- [ ] **Step 4: 验证 console lint 仍然通过**

```bash
cd web
pnpm --filter @acme/console lint
```

预期：lint 通过或只有已知警告（无 import 报错）

- [ ] **Step 5: Commit**

```bash
git add web/tooling/eslint/
git commit -m "chore: remove eslint-plugin-turbo from tooling"
```

---

### Task 7: 最终验证

- [ ] **Step 1: 完整安装**

```bash
cd web
pnpm install
```

- [ ] **Step 2: 验证 console 构建**

```bash
cd web
pnpm build:console
```

预期：`web/apps/console/dist/` 生成成功

- [ ] **Step 3: 确认 workspace 结构**

```bash
cd web
pnpm list -r --depth 0
```

预期：只列出 console、tooling 下的包，无 packages/ 下的包

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify web monorepo restructure complete"
```
