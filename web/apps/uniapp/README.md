# @acme/uniapp

**UniApp**（Vue 3）客户端：H5 与微信/支付宝/抖音等多端小程序。业务上对接仓库根目录 `server/` 的 FastAPI（营养成分、配料、扫码等）。

## 环境要求

与 monorepo 根 [package.json](../../../package.json) 一致：Node 22 + pnpm 10。首次在 `web/` 执行 `pnpm install`。

## 开发命令

在 `web/` 根目录：

```bash
pnpm dev:uniapp:h5           # H5，默认端口 5174（见 vite.config.ts）
pnpm dev:uniapp:weapp        # 微信小程序
pnpm dev:uniapp:alipay       # 支付宝小程序
pnpm dev:uniapp:tt           # 抖音小程序
```

或在应用目录：

```bash
cd apps/uniapp
pnpm dev:h5
pnpm dev:mp-weixin
# 其余平台见 package.json 中 dev:mp-* / build:mp-*
```

## 后端地址

开发环境通过 **`VITE_API_BASE_URL`** 指定 API 根地址，见 [.env.development](./.env.development)（示例：`http://localhost:9999`）。请求封装与业务类型见 `src/services/`、`src/types/`。

## 构建

```bash
cd web
pnpm build:uniapp:weapp      # 示例：微信小程序
# 或 apps/uniapp 内 pnpm build:mp-weixin 等
```

各端输出目录以 UniApp / DCloud 默认为准（常见为 `unpackage/` 等，构建后勿将大体积产物提交入库）。

## 说明

页面与路由见 `src/pages.json`、`src/pages/`；全局样式与 `uview-plus` 等依赖见 `package.json`。
