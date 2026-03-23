# UniApp 首页及搜索功能设计（Phase 1）

## 1. 概述

本设计针对"食品安全助手"UniApp 小程序的第一阶段，明确首页定位、搜索能力及底部 Tab 结构。

**核心业务链路：** 用户扫描条形码 → 进入产品详情（如数据库有）→ 点击配料进入配料详情。

**Phase 1 交付范围：**
- 极简扫码体验
- 食品/配料通用搜索
- 最近扫描记录（本地存储）
- 底部 Tab 框架预留

**后续扩展预留：**
- AI 助手 Tab（限流/付费）
- 广告 Banner 位
- 家庭成员档案
- 账号系统

---

## 2. 底部 Tab 结构

| Tab | 页面路径 | 功能 |
|-----|----------|------|
| 首页 | `pages/index/index` | 扫码 + 最近扫描 |
| 搜索 | `pages/search/index` | 食品/配料搜索 → 结果列表 |
| 我的 | `pages/profile/index` | 框架占位（后续扩展） |

**Phase 1 不设 AI Tab** — AI 能力从产品详情页/配料详情页底部栏触发，避免用户过度使用付费能力。

### 2.1 pages.json TabBar 配置

```json
{
  "tabBar": {
    "color": "var(--text-muted)",
    "selectedColor": "var(--accent)",
    "backgroundColor": "var(--bg-card)",
    "borderStyle": "black",
    "list": [
      {
        "pagePath": "pages/index/index",
        "text": "首页",
        "iconPath": "static/tab-home.png",
        "selectedIconPath": "static/tab-home-active.png"
      },
      {
        "pagePath": "pages/search/index",
        "text": "搜索",
        "iconPath": "static/tab-search.png",
        "selectedIconPath": "static/tab-search-active.png"
      },
      {
        "pagePath": "pages/profile/index",
        "text": "我的",
        "iconPath": "static/tab-profile.png",
        "selectedIconPath": "static/tab-profile-active.png"
      }
    ]
  }
}
```

> **图标资源：** Phase 1 临时占位，需替换为真实图标文件（放置于 `static/tab-*.png`）。

---

## 3. 页面详细设计

### 3.1 首页（`/pages/index`）

#### 3.1.1 布局结构

**设计决策：**
- 去掉首页搜索入口（TabBar 已有搜索 Tab）
- 扫一扫为圆形按钮（直径 140px），作为页面唯一视觉焦点
- 最近扫描作为次要内容，视觉权重轻
- Logo 区域精简为一行

```
┌──────────────────────────────────┐
│  🍎 食品安全助手                  │  ← Logo 行，26px emoji + 17px 标题
│  扫码查配料 · 了解你吃的每一口      │  ← 副标题，12px
├──────────────────────────────────┤
│                                  │
│           ┌─────────┐            │
│           │  📷     │            │  ← 圆形 CTA，直径 140px
│           │  扫一扫  │            │  ← 粉渐变 + 脉冲动画 + 阴影
│           └─────────┘            │
│                                  │
│  ──── 最近扫描 ────              │  ← 分隔标题，小号
│                                  │
│  ┌──────────────────────────┐   │
│  │ 🥫 午餐肉       2分钟前  │   │  ← 扫描列表，14px 圆角卡片
│  ├──────────────────────────┤   │
│  │ 🍝 康师傅方便面   昨天    │   │
│  └──────────────────────────┘   │
│                                  │
└──────────────────────────────────┘
┌──────────────────────────────────┐
│  首页        搜索        我的     │  ← TabBar，80px
└──────────────────────────────────┘
```

#### 3.1.2 组件说明

| 组件 | 类型 | 说明 |
|------|------|------|
| Logo 区域 | 行内块 | emoji(26px) + 标题(17px) + 副标题(12px muted) |
| 圆形 CTA | 按钮 | 直径 140px，`--accent-pink` 渐变，带外圈脉冲动画，悬停放大 |
| 最近扫描分隔 | 分隔标题 | 小号 label + 数字标签（红色圆角） |
| 扫描列表 | 卡片列表 | 每行 14px 圆角，左侧 emoji 卡片 + 名称 + 时间右侧 |
| TabBar | 底部导航 | 3 Tab，首页图标粉色填充，其他灰色描边 |

#### 3.1.3 样式规格

| 元素 | 值 |
|------|---|
| 页面背景（亮） | `--bg-base: #f5f5f5` |
| 页面背景（暗） | `--bg-base: #0f0f0f` |
| 卡片背景 | `--bg-card: #ffffff`（亮）/`#1a1a1a`（暗） |
| 主 CTA 背景 | `linear-gradient(135deg, #ec4899, #db2777)` |
| 主 CTA 阴影 | `0 8px 40px rgba(236,72,153,0.4)` |
| 主 CTA 脉冲圈 | `border: 2px solid rgba(236,72,153,0.25)`，动画扩散 |
| 列表卡片圆角 | 14px |
| TabBar 高度 | 80px（含 safe-area） |
| TabBar 阴影（亮） | `0 -8px 32px rgba(0,0,0,0.06)` |
| TabBar 阴影（暗） | `0 -8px 32px rgba(0,0,0,0.4)` |

#### 3.1.4 交互逻辑

```
扫一扫按钮点击
       │
       ▼
uni.scanCode({
  onlyFromCamera: true,
  success: (res) => {
    const barcode = res.result
    // 写入最近扫描
    addToRecentScans({ barcode, name: '待获取', time: Date.now() })
    // 跳转产品页
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` })
  },
  fail: (err) => {
    if (err.errMsg && err.errMsg.includes('auth deny')) {
      uni.showToast({ title: '请允许摄像头权限', icon: 'none' })
    } else {
      uni.showToast({ title: '扫码失败', icon: 'error' })
    }
  }
})
```

```
最近扫描项点击
       │
       ▼
uni.navigateTo({ url: `/pages/product/index?barcode=${item.barcode}` })
```

---

### 3.2 搜索页（`/pages/search`）

#### 3.2.1 布局结构

```
┌──────────────────────────────────┐
│  ←  返回      搜索食品或配料        │  ← Header，高度 88rpx
├──────────────────────────────────┤
│  ┌────────────────────────────┐ │
│  │ 🔍 输入框          ✕ 清空  │ │  ← 搜索输入框，高 80rpx
│  └────────────────────────────┘ │
├──────────────────────────────────┤
│  搜索历史              清空全部  │  ← 有历史时显示
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │苯甲酸钠│ │香兰素 │ │方便面 │   │  ← 历史标签，可点击
│  └──────┘ └──────┘ └──────┘   │
├──────────────────────────────────┤
│                                  │
│  （无内容时：空状态占位）          │
│                                  │
└──────────────────────────────────┘
```

**有搜索结果时：**

```
┌──────────────────────────────────┐
│  ←  返回      搜索食品或配料        │
├──────────────────────────────────┤
│  ┌────────────────────────────┐ │
│  │ 🔍 输入框          ✕ 清空  │ │
│  └────────────────────────────┘ │
├──────────────────────────────────┤
│  搜索结果（共 N 条）              │
│                                  │
│  ┌────────────────────────────┐ │
│  │ 🏷️ 配料                    │ │
│  │ 苯甲酸钠                    │ │  ← 配料类型
│  │ 食品添加剂 · 防腐剂          │ │
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │ 🥫 食品                    │ │
│  │ 康师傅方便面                │ │  ← 食品类型
│  │ 方便食品 · 高盐             │ │
│  └────────────────────────────┘ │
│                                  │
└──────────────────────────────────┘
```

#### 3.2.2 组件说明

| 组件 | 类型 | 说明 |
|------|------|------|
| Header 返回按钮 | ICON 按钮 | 左侧返回箭头，点击 `uni.navigateBack()` |
| 搜索标题 | 静态文字 | 居中，28rpx |
| 搜索输入框 | `up-input` | 高 80rpx，左侧搜索图标，右侧清空按钮 |
| 历史标签 | 胶囊按钮 | 高 56rpx，padding 0 24rpx，圆角 28rpx |
| 结果列表 | ListView | 每项高 120rpx，左侧类型图标 + 名称 + 描述 |

#### 3.2.3 交互逻辑

```
输入框输入 → 防抖 300ms → 调用搜索接口
       │
       ▼
GET /api/search?q={keyword}&limit=20
       │
       ▼
返回结果列表 [{ type: 'product'|'ingredient', id, name, desc }, ...]
       │
       ▼
渲染结果列表（最多显示 20 条）
```

> **分页策略：** Phase 1 不做分页，单次搜索最多返回 20 条结果，由后端控制上限。

```
点击历史标签 → 填入输入框 → 触发搜索
```

```
点击搜索结果
       │
  ┌────┴────┐
  │         │
  ▼         ▼
type=      type=
product    ingredient
  │         │
  ▼         ▼
/pages/product/index   /pages/ingredient/index
?barcode=xxx          ?ingredientId=xxx
```

**搜索历史存储：** 本地 `search_history`，最多 10 条，新搜索词插入顶部，去重。

#### 3.2.4 样式规格

| 元素 | 样式值 |
|------|--------|
| Header 背景 | `--bg-base` |
| 返回按钮 | 60rpx × 60rpx，图标 `--icon-md` |
| 搜索框背景 | `--bg-card`，border-radius: `--radius-xl` |
| 搜索框高度 | 80rpx |
| 搜索框图标 | `--icon-md`，color: `--text-muted` |
| 历史标签背景 | `--bg-card`，border: 1px solid `--border-color` |
| 历史标签字号 | `--text-sm` |
| 结果项背景 | `--bg-card` |
| 结果项圆角 | `--radius-md` |
| 结果项内边距 | `--card-padding-lg` |
| 类型标签 | 背景色区分，配料用 `--accent-blue`（需补充定义），食品用 `--accent-orange`（需补充定义） |
| 类型标签字号 | `--text-xs` |
| 结果名称字号 | `--text-2xl`，font-weight: 600 |
| 结果描述字号 | `--text-sm`，color: `--text-muted` |

---

### 3.3 产品详情页（`/pages/product`）

**已有功能，本设计不做调整。** 仅记录关键跳转关系。

#### 3.3.1 现有功能清单

| 区块 | 说明 |
|------|------|
| Banner | 产品图片 + 风险标签 |
| 营养成分 | 主营养素网格 + 展开详细 |
| 配料信息 | 可点击的配料列表 → 跳转配料详情 |
| 健康益处 | AI 分析结果展示 |
| 食用建议 | AI 建议展示 |
| 底部栏 | 咨询 AI / 查看相关食品 |

#### 3.3.2 关键跳转

| 来源 | 目标 | 触发条件 |
|------|------|----------|
| 配料列表项 | `pages/ingredient/index` | 点击任意配料行 |
| 底部栏"查看相关食品" | `pages/search/index` | 传入 ingredientId 参数 |

---

### 3.4 配料详情页（`/pages/ingredient`）

**已有功能，本设计不做调整。** 仅记录路径变更：将 `/pages/ingredient-detail` 重命名为 `/pages/ingredient`。

#### 3.4.1 现有功能清单

| 区块 | 说明 |
|------|------|
| Hero 风险卡 | 配料名 + 风险等级 + 风险谱条 |
| 描述 | AI 生成描述 |
| AI 风险分析 | 风险因素列表 |
| 风险管理信息 | WHO 等级、使用限量、适用区域等 |
| AI 使用建议 | 正面/条件性建议 |
| 含此配料的产品 | 横向滚动产品卡片列表 |
| 底部栏 | 咨询 AI / 查看相关食品 |

#### 3.4.2 关键跳转

| 来源 | 目标 | 触发条件 |
|------|------|----------|
| 相关产品卡片 | `pages/product/index` | 点击产品卡片 |
| 底部栏"咨询 AI" | `pages/chat/index` | 传入配料名 context |
| 底部栏"查看相关食品" | `pages/search/index` | 传入 ingredientId 参数 |

---

### 3.5 我的页面（`/pages/profile`）

#### 3.5.1 布局结构（Phase 1 框架）

```
┌──────────────────────────────────┐
│  ←  返回          我的            │  ← Header
├──────────────────────────────────┤
│                                  │
│  ┌────────────────────────────┐ │
│  │      👤  点击登录           │ │  ← 登录卡片（Phase 1）
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │  📋 扫描记录          >    │ │
│  ├────────────────────────────┤ │
│  │  👨‍👩‍👧 家庭成员管理    →    │ │  ← Phase 2
│  ├────────────────────────────┤ │
│  │  ⭐ 收藏夹            >    │ │  ← Phase 2
│  ├────────────────────────────┤ │
│  │  ⚙️ 设置            >    │ │  ← Phase 2
│  └────────────────────────────┘ │
│                                  │
└──────────────────────────────────┘
┌──────────────────────────────────┐
│  首页        搜索        我的     │
└──────────────────────────────────┘
```

#### 3.5.2 组件说明

| 组件 | 类型 | 说明 |
|------|------|------|
| 登录卡片 | 卡片 | Phase 1 点击弹出"即将上线"提示 |
| 菜单项 | ListItem | Phase 1 仅"扫描记录"可点击，其他灰态 |

#### 3.5.3 交互逻辑

```
点击登录卡片 → uni.showToast({ title: '即将上线', icon: 'none' })
点击扫描记录 → uni.navigateTo({ url: '/pages/scan-history/index' })  // Phase 2
点击其他菜单 → uni.showToast({ title: '即将上线', icon: 'none' })
```

#### 3.5.4 样式规格

| 元素 | 样式值 |
|------|--------|
| 登录卡片背景 | 渐变浅色，height: 200rpx |
| 头像占位 | 100rpx × 100rpx，圆形，灰色背景 |
| 登录提示文字 | 32rpx，color: `--text-muted` |
| 菜单项高度 | 100rpx |
| 菜单项背景 | `--bg-card` |
| 菜单项圆角 | 16rpx（最后一项单独圆角） |
| 菜单项图标 | 40rpx |
| 菜单项文字 | 28rpx |
| 分割线 | 1px `--border-color` |

---

## 4. 路由跳转汇总

| 来源 | 目标 | 参数 |
|------|------|------|
| 首页扫码 | `pages/product/index` | `barcode` |
| 首页搜索入口 | `pages/search/index`（switchTab） | — |
| 搜索结果-食品 | `pages/product/index` | `barcode` |
| 搜索结果-配料 | `pages/ingredient/index` | `ingredientId` |
| 产品页点击配料 | `pages/ingredient/index` | `ingredientId` |
| 配料页点击相关产品 | `pages/product/index` | `barcode` |
| 首页最近扫描 | `pages/product/index` | `barcode` |
| 搜索历史标签 | 触发搜索 | — |
| 我的-扫描记录 | `pages/scan-history/index` | Phase 2 |

---

## 5. 数据存储

| 数据 | 存储方式 | 键名 | 限制 |
|------|----------|------|------|
| 最近扫描 | `uni.setStorageSync` | `recent_scans` | 最多 20 条 |
| 搜索历史 | `uni.setStorageSync` | `search_history` | 最多 10 条 |

**`recent_scans` 数据结构：**
```ts
interface RecentScan {
  barcode: string
  name: string
  emoji: string       // 产品emoji，暂无则用默认
  time: number        // timestamp
}
```

**`search_history` 数据结构：**
```ts
type SearchHistory = string[]  // 搜索词数组
```

---

## 6. API 接口需求

### 6.1 搜索接口（新建）

**请求：**
```
GET /api/search?q={keyword}
```

**响应：**
```ts
interface SearchResponse {
  results: Array<{
    type: 'product' | 'ingredient'
    id: string | number
    name: string
    description: string   // 配料：功能分类；食品：简短描述
    emoji?: string        // 食品才有
  }>
}
```

---

## 7. 新增/调整页面清单

| 页面 | 操作 | 说明 |
|------|------|------|
| `pages/index/index` | **重新实现** | 替换现有首页，添加搜索入口 + 最近扫描 + TabBar 图标 |
| `pages/search/index` | 新建 | 通用搜索页（含搜索历史） |
| `pages/profile/index` | 新建 | Tab 框架占位（UI 先做，内容后续） |
| `pages/product/index` | 不变 | 已有功能 |
| `pages/ingredient/index` | 路径重命名 | 原 `pages/ingredient-detail/index`，需同步修改 `pages.json`、跳转引用、`IngredientSection.vue` 等 |

**受影响的已有文件（路径重命名联动）：**
- `web/apps/uniapp/src/pages.json` — 将 `pages/ingredient-detail/index` 改为 `pages/ingredient/index`
- `web/apps/uniapp/src/components/IngredientSection.vue` — 将跳转路径 `/pages/ingredient-detail/index` 改为 `/pages/ingredient/index`
- `web/apps/uniapp/src/pages/ingredient-detail/` — 目录重命名为 `ingredient`

---

## 8. 后续扩展预留

| 预留点 | 说明 |
|--------|------|
| AI Tab | 独立 Tab，限未登录用户使用次数，后续接入付费 |
| 广告 Banner | 首页最近扫描下方，预留 120rpx 高度 |
| 家庭成员档案 | 我的页扩展，支持创建家庭成员 Profile |
| 账号系统 | 支持登录/注册，数据同步到服务端 |
| 扫描历史页 | 我的-扫描记录，后续独立页面 |
| 收藏夹 | 我的-收藏夹，后续独立页面 |
