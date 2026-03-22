# Taro 多端适配设计文档

**日期：** 2026-03-22
**状态：** 已批准（2026-03-22 更新架构决策）

---

## 目标

重构 Web 工程结构，新增 Taro 应用，实现一套代码覆盖：

**本期目标：**
- 微信小程序
- 支付宝小程序
- 抖音/头条小程序
- H5 网页

**二期目标：**
- iOS / Android 原生 App（via React Native）

核心功能：**扫描条形码 → 产品营养成分分析展示**

---

## 架构

### 目录结构

```
web/
├── apps/
│   ├── console/             # 管理后台（Vite/React，独立管理自己的 UI）
│   └── taro/                # 新增，多端小程序
│       ├── src/
│       │   ├── pages/
│       │   │   ├── index/        # 首页 + 扫码入口
│       │   │   ├── scan/         # 扫码页
│       │   │   └── product/      # 产品详情 + 营养成分展示
│       │   ├── components/       # Taro 原生组件
│       │   ├── utils/
│       │   │   └── scanner.ts    # 扫码工具（平台差异收口）
│       │   └── app.config.ts
│       ├── project.config.json   # 微信小程序配置
│       └── package.json
├── tooling/
│   ├── eslint/              # 共享 ESLint 规则
│   ├── prettier/            # 共享 Prettier 配置
│   └── tsconfig/            # 共享 TS 配置（从 packages/ 移入）
└── pnpm-workspace.yaml      # 只声明 apps/** 和 tooling/**
```

**删除的包：** `@acme/nextjs`、`@acme/db`、`@acme/ui`、`@acme/api`、`@acme/auth`、`@acme/validators`、`@acme/tailwind-config`

`packages/` 目录整体删除。

### 编译目标

| 命令 | 目标平台 |
|---|---|
| `pnpm dev:weapp` | 微信小程序 |
| `pnpm dev:alipay` | 支付宝小程序 |
| `pnpm dev:tt` | 抖音小程序 |
| `pnpm dev:h5` | H5 网页 |
| `pnpm dev:rn` | React Native（iOS/Android，二期）|

---

## 核心组件

### 页面

| 页面 | 职责 |
|---|---|
| `index` | 首页，展示扫码入口按钮 |
| `scan` | 调用摄像头扫码，获取条形码值 |
| `product` | 展示产品信息和营养成分分析结果 |

### 数据流

```
用户点击"扫一扫"
  → scan 页调用 scanBarcode()
  → 获得条形码字符串
  → Taro.request() 调用后端 REST API: GET /api/product?barcode=xxx
  → 跳转 product 页，渲染营养成分数据
```

### API 端点定义

**`GET /api/product?barcode={barcode}`**

- **实现位置：** FastAPI（`server/`）新增端点
- **数据来源：** 现有 PostgreSQL，数据结构已就绪，通过 SQLAlchemy/asyncpg 连接
- **响应结构：**
  ```ts
  {
    barcode: string
    name: string
    brand: string
    nutrition: {
      energy: number       // kcal/100g
      protein: number      // g/100g
      fat: number          // g/100g
      carbohydrate: number // g/100g
      sodium: number       // mg/100g
    }
    // 可能扩展：成分表、过敏原、GB 标准关联
  }
  ```
- 条形码未命中时返回 404，前端展示"暂无数据"页

### API 对接

- 统一使用 `Taro.request()` 调用 FastAPI REST 接口
- **不使用 tRPC**（在 Taro/RN 环境兼容性差）
- 各端自己管理类型定义，不共享 validators 包

---

## 平台差异处理

扫码能力差异收口在 `src/utils/scanner.ts`：

```ts
import Taro from "@tarojs/taro"

export async function scanBarcode(): Promise<string> {
  // 小程序端：微信/支付宝/抖音
  if (process.env.TARO_ENV !== "rn" && process.env.TARO_ENV !== "h5") {
    const res = await Taro.scanCode({ onlyFromCamera: true })
    return res.result
  }

  // H5 端：降级为手动输入
  if (process.env.TARO_ENV === "h5") {
    throw new Error("H5_MANUAL_INPUT")
  }

  // RN 端：二期实现，通过 react-native-vision-camera 桥接
  throw new Error("RN_NOT_IMPLEMENTED")
}
```

**H5 降级策略：** H5 端不强行调用摄像头，改为展示手动输入条形码的输入框。

---

## 错误处理

| 错误场景 | 处理方式 |
|---|---|
| 用户拒绝/取消扫码 | 静默回到首页 |
| 条形码未收录 | 展示"暂无数据"页，提示手动搜索 |
| 网络请求失败 | Toast 提示 + 重试按钮 |
| H5 不支持扫码 | 显示手动输入框替代 |
| RN 端原生模块缺失 | 构建时检测，缺失则隐藏扫码入口 |

---

## 超出本期范围

- 用户登录 / 鉴权（小程序 OAuth）
- 历史扫码记录
- 产品收藏功能
- App 打包上架（AppStore / Google Play）
- Console 的 UI 重构（剥离 @acme/ui 是技术债，本期不动功能）

---

## 关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 多端框架 | Taro（全家桶） | 一套代码覆盖三端小程序 + H5 |
| API 层 | REST fetch，不用 tRPC | tRPC 在 Taro/RN 兼容性差 |
| REST API 位置 | FastAPI（`server/`） | 数据在现有 PostgreSQL，Next.js 将被移除 |
| 数据层 | FastAPI + SQLAlchemy/asyncpg → PostgreSQL | 数据结构已就绪，@acme/db 随 Next.js 一起废弃 |
| H5 扫码 | 降级为手动输入 | 浏览器摄像头权限限制，体验差 |
| 构建工具 | 放弃 Turborepo，改用纯 pnpm workspace | Next.js 移除后共享包（ui/db/api/auth）全部失去意义，turborepo 仅剩管理负担 |
| 目录结构 | 保持 apps/ + tooling/，删除 packages/ | pnpm workspace 无需 turborepo 也能用此结构，tooling/ 统一管理 eslint/prettier/tsconfig |
| 共享包 | 只保留 tooling（eslint/prettier/tsconfig） | validators 和 tailwind-config 在 console（Web）和 taro（小程序）之间无法有效共用 |
