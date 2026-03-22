# life-classics-web

本目录为 **pnpm workspace** 前端，包含知识库管理台与 UniApp 客户端。后端 API 由仓库根目录下的 `server/`（FastAPI，默认 `http://localhost:9999`）提供。

## 包与目录

| 包名 | 路径 | 说明 |
|------|------|------|
| `@acme/console` | `apps/console` | React 18 + Vite 5 + Tailwind：文档上传、Chunk 列表/编辑、对话等 |
| `@acme/uniapp` | `apps/uniapp` | UniApp（Vue 3）：H5 与各小程序端 |
| `@acme/eslint-config` 等 | `tooling/*` | 共享 ESLint、Prettier、TSConfig |

`ui/` 为设计稿与静态 HTML 原型，**不是** workspace 包；说明见 `web/ui/README.md`。

## 环境要求

见根目录 [package.json](./package.json) 的 `engines`：当前使用 **Node 22** 与 **pnpm 10**。

```bash
node -v
pnpm -v
```

## 安装

在 **`web/`** 目录执行：

```bash
pnpm install
```

## 常用脚本

在 `web/` 根目录执行：

| 命令 | 说明 |
|------|------|
| `pnpm dev:console` | 启动管理台，默认 <http://localhost:5173> |
| `pnpm build:console` | 构建管理台；产物可被 FastAPI 挂载到 `/admin` |
| `pnpm dev:uniapp:h5` | UniApp H5，默认 <http://localhost:5174> |
| `pnpm dev:uniapp:weapp` | 微信小程序 |
| `pnpm dev:uniapp:alipay` | 支付宝小程序 |
| `pnpm dev:uniapp:tt` | 抖音小程序 |
| `pnpm build:uniapp:weapp` | 构建微信小程序等（见 `apps/uniapp/package.json`） |
| `pnpm lint` / `pnpm format` / `pnpm typecheck` | 全 workspace 检查 |

## 与后端联调

- **Console**：`apps/console/vite.config.ts` 将 **`/api`** 代理到 **`http://localhost:9999`**，页面请求 `/api/...` 即可。
- **UniApp**：通过 `VITE_API_BASE_URL` 指向后端（见 `apps/uniapp/.env.development`）。

## 更多说明

- 管理台细节：[apps/console/README.md](apps/console/README.md)
- UniApp 细节：[apps/uniapp/README.md](apps/uniapp/README.md)
