# @acme/console

基于 **React 19**、**Vite**、**Tailwind CSS v4** 的知识库**管理台**：上传国标 Markdown、浏览与编辑 Chunk、简单对话等。面向内部或运营使用，生产构建可由后端 FastAPI 以静态资源形式挂载在 **`/admin`**。

## 开发

在 monorepo 的 `web/` 目录安装依赖后：

```bash
cd web
pnpm dev:console
# 或
cd apps/console && pnpm dev
```

默认开发地址：<http://localhost:5173>。

## API 与代理

后端默认 <http://localhost:9999>。开发环境下 [vite.config.ts](./vite.config.ts) 将 **`/api`** 代理到 **`http://localhost:9999`**，前端使用相对路径 `/api/...` 即可，无需配置 CORS。

## 页面概览（`src/pages/`）

- **上传** — 文档入库（SSE 进度）
- **Chunks** — 按文档筛选、查看与编辑 Chunk
- **对话** — 与后端 RAG/聊天接口联调

具体路由与组件以源码为准。

## 构建

```bash
cd web
pnpm build:console
```

产物在 `apps/console/dist/`。后端若检测到该目录存在，会在 `server/api/main.py` 中挂载为 `/admin`。

## 技术栈摘要

React Router、Radix UI 风格组件（`src/components/ui/`）、react-markdown 等。代码风格与 ESLint 配置继承自 `web/tooling/`。
