# Taro 多端适配设计文档

**日期：** 2026-03-22
**状态：** 已批准

---

## 目标

在现有 T3 Turbo monorepo 基础上，新增 Taro 应用，实现一套代码覆盖：

- 微信小程序
- 支付宝小程序
- 抖音/头条小程序
- H5 网页
- iOS / Android 原生 App（via React Native）

核心功能：**扫描条形码 → 产品营养成分分析展示**

---

## 架构

### 目录结构

```
web/
├── apps/
│   ├── nextjs/          # 现有 PC 端（已有营养成分展示逻辑）
│   ├── console/         # 现有管理后台
│   └── taro/            # 新增
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
└── packages/
    └── validators/      # 现有：共享 Zod schema（Taro 端复用类型定义）
```

### 编译目标

| 命令 | 目标平台 |
|---|---|
| `pnpm dev:weapp` | 微信小程序 |
| `pnpm dev:alipay` | 支付宝小程序 |
| `pnpm dev:tt` | 抖音小程序 |
| `pnpm dev:h5` | H5 网页 |
| `pnpm dev:rn` | React Native（iOS/Android）|

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

### API 对接

- 统一使用 `Taro.request()` 调用后端 HTTP REST API
- **不使用 tRPC**（在 Taro/RN 环境兼容性差）
- 共享 `@acme/validators` 中的 Zod schema 做类型推断和数据校验

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

  // RN 端：通过 react-native-vision-camera 桥接
  throw new Error("RN_NOT_IMPLEMENTED")
}
```

**H5 降级策略：** H5 端不强行调用摄像头，改为展示手动输入条形码的输入框。H5 主要承担信息展示功能，扫码主战场是小程序和 App。

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

## 复用与不复用

### 可复用（来自现有 monorepo）

- `@acme/validators`：产品数据的 Zod schema 和 TypeScript 类型
- 后端 REST API：Taro 端直接调用，和 Next.js 共享同一套接口
- TypeScript / ESLint / Prettier 配置

### 不复用

- `@acme/ui`（shadcn/Radix）：依赖 DOM，Taro 不支持，UI 组件需重写
- tRPC 客户端：兼容性差，改用普通 fetch
- `@acme/auth`（better-auth）：小程序登录体系不同，需单独处理（超出本期范围）

---

## 超出本期范围

- 用户登录 / 鉴权（小程序 OAuth）
- 历史扫码记录
- 产品收藏功能
- App 打包上架（AppStore / Google Play）

---

## 关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 多端框架 | Taro（全家桶） | 一套代码覆盖三端，项目已预留 dev:taro 脚本 |
| API 层 | REST fetch，不用 tRPC | tRPC 在 Taro/RN 兼容性差 |
| H5 扫码 | 降级为手动输入 | 浏览器摄像头权限限制，体验差 |
| Turborepo | 保留 | 已配置好，迁移成本高于收益 |
