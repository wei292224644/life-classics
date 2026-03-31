# 食品安全助手 — 设计规范 v2.0 (Tailwind v3)

> 本文档是唯一权威的视觉设计规范。所有间距、颜色、字体、圆角**必须通过 Tailwind 原子类实现**，
> 禁止在组件内写 inline style 魔法数字（如 `style="padding: 7px"`、`style="color: #abc"`）。
>
> **Tech Stack**: UniApp + Vue 3 + Tailwind CSS v3，设计基准宽度 375px（对应 750rpx）

---

## 0. tailwind.config.ts 扩展

以下为全量 `theme.extend`，将此配置合并入项目 `tailwind.config.ts`：

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{vue,ts,tsx}"],
  theme: {
    extend: {
      // ── 字体 ───────────────────────────────────────────────
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          '"Noto Sans SC"',
          "-apple-system",
          "sans-serif",
        ],
        display: ['"Plus Jakarta Sans"', '"Noto Sans SC"', "sans-serif"],
      },

      // ── 字号（设计稿 px，UniApp 内用 rpx ×2）──────────────
      fontSize: {
        display: [
          "2.75rem",
          { lineHeight: "1.0", letterSpacing: "-0.04em", fontWeight: "800" },
        ],
        hero: [
          "1.75rem",
          { lineHeight: "1.1", letterSpacing: "-0.03em", fontWeight: "800" },
        ],
        headline: [
          "1.375rem",
          { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "700" },
        ],
        title: [
          "1.125rem",
          { lineHeight: "1.3", letterSpacing: "-0.01em", fontWeight: "700" },
        ],
        "body-lg": [
          "0.9375rem",
          { lineHeight: "1.5", letterSpacing: "0", fontWeight: "600" },
        ],
        body: [
          "0.875rem",
          { lineHeight: "1.7", letterSpacing: "0", fontWeight: "400" },
        ],
        sm: [
          "0.8125rem",
          { lineHeight: "1.6", letterSpacing: "0", fontWeight: "500" },
        ],
        label: [
          "0.75rem",
          { lineHeight: "1.4", letterSpacing: "0", fontWeight: "700" },
        ],
        caption: [
          "0.6875rem",
          { lineHeight: "1.4", letterSpacing: "0.08em", fontWeight: "700" },
        ],
        micro: [
          "0.625rem",
          { lineHeight: "1.4", letterSpacing: "0.12em", fontWeight: "700" },
        ],
      },

      // ── 颜色 ───────────────────────────────────────────────
      colors: {
        // 背景层级
        page: "#FAF8F3", // Layer 0 — 页面底色（暖白）
        surface: "#FFFFFF", // Layer 1 — 卡片/Sheet 主体
        raised: "#F2EFE8", // Layer 2 — 内嵌卡片/建议框/输入框

        // 文字层级
        ink: {
          DEFAULT: "#1A1714", // 主文字
          2: "#6B6560", // 次要文字
          3: "#A09890", // 弱化文字
        },

        // 品牌色（陶土橙）
        brand: {
          DEFAULT: "#C4532A",
          light: "#FDEEE9",
          dark: "#A34222", // 按压态
        },

        // 深色背景（分析页专用）
        dark: {
          bg: "#1A1714",
          surface: "rgba(255,255,255,0.06)",
          border: "rgba(255,255,255,0.12)",
        },

        // 风险色系（每级三个 token：dot/bg/text）
        risk: {
          "t0-dot": "#3D7A5C",
          "t0-bg": "#EEF7F2",
          "t0-text": "#1E4D38",
          "t1-dot": "#2E7D7A",
          "t1-bg": "#EAF4F4",
          "t1-text": "#164D4B",
          "t2-dot": "#B07D1A",
          "t2-bg": "#FEF5E0",
          "t2-text": "#6B4A0A",
          "t3-dot": "#C44A2B",
          "t3-bg": "#FDEEE9",
          "t3-text": "#7A2410",
          "t4-dot": "#8B1A1A",
          "t4-bg": "#FDDEDE",
          "t4-text": "#5A0D0D",
        },
      },

      // ── 间距（基于 8px 倍数）──────────────────────────────
      spacing: {
        "4.5": "18px", // 组件内小间距补充
        "13": "52px", // 历史图片尺寸
        "18": "72px", // 特殊场景
      },

      // ── 圆角 ───────────────────────────────────────────────
      borderRadius: {
        sm: "10px", // 历史图片、小标签
        md: "18px", // 建议框、人群卡片
        lg: "26px", // Sheet、主要区块
        xl: "34px", // CTA 大按钮、对话入口
        "2xl": "48px", // Phone shell（设计稿用）
        pill: "9999px", // 所有胶囊形标签
      },

      // ── 阴影 ───────────────────────────────────────────────
      boxShadow: {
        sm: "0 1px 6px rgba(26,23,20,0.08)",
        md: "0 2px 18px rgba(26,23,20,0.08), 0 0 0 1px rgba(26,23,20,0.05)",
        lg: "0 12px 48px rgba(26,23,20,0.14)",
      },

      // ── 动效 ───────────────────────────────────────────────
      transitionDuration: {
        "80": "80ms",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      animation: {
        scan: "scan 2s ease-in-out infinite",
        "dot-bounce": "dotBounce 0.6s ease-in-out infinite",
      },
      keyframes: {
        scan: {
          "0%, 100%": { top: "15%" },
          "50%": { top: "85%" },
        },
        dotBounce: {
          "0%, 100%": { opacity: "0.3" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
} satisfies Config;
```

---

## 1. 颜色层级与使用规则

### 1.1 背景层级（严格分层，禁止跨层）

```
Layer 0  bg-page     #FAF8F3   页面根背景
Layer 1  bg-surface  #FFFFFF   Sheet、卡片主体
Layer 2  bg-raised   #F2EFE8   建议框、输入框、内嵌卡片
Layer 3  bg-black/4  overlay   悬停/按压遮罩
```

| 用途                      | 类名              |
| ------------------------- | ----------------- |
| 页面背景                  | `bg-page`         |
| 内容 Sheet / 底部抽屉     | `bg-surface`      |
| 建议框 `.advice`、输入框  | `bg-raised`       |
| 人群卡片（用对应风险 bg） | `bg-risk-t1-bg`   |
| 按压遮罩                  | `bg-black/[0.04]` |

**禁止：** 在 `bg-surface` 内再嵌套 `bg-surface`（无对比度）；禁止 `bg-white` 与 `bg-surface` 混用。

### 1.2 文字层级

| 语义               | 类名         | 用途                       |
| ------------------ | ------------ | -------------------------- |
| 主文字             | `text-ink`   | 标题、配料名、列表项       |
| 次要文字           | `text-ink-2` | 正文描述、建议内容         |
| 弱化文字           | `text-ink-3` | 章节标题、时间戳、免责声明 |
| 白色（深色背景上） | `text-white` | 分析页、深色按钮内         |

**禁止：** 直接写 `text-[#1A1714]`，必须用语义 token。

### 1.3 风险色使用规则

每个风险等级有三个 token，**必须成组使用**：

```vue
<!-- ✅ 正确 -->
<view class="bg-risk-t1-bg">
  <text class="text-risk-t1-text">较安全</text>
</view>

<!-- ❌ 错误：t1-bg 配 t0-text，对比度不保证 -->
<view class="bg-risk-t1-bg">
  <text class="text-risk-t0-text">较安全</text>
</view>
```

| token     | 用途                                  |
| --------- | ------------------------------------- |
| `tX-dot`  | 圆形指示点、badge 背景、边框强调色    |
| `tX-bg`   | 标签背景、区块背景、Verdict Zone 背景 |
| `tX-text` | `tX-bg` 之上的所有文字                |

---

## 2. 字体规范

### 2.1 字号类对应表

| 类名            | px         | 典型用途                         |
| --------------- | ---------- | -------------------------------- |
| `text-display`  | 44px / 800 | 结果页「成分较优 ✓」             |
| `text-hero`     | 28px / 800 | 首页「我的分析记录」             |
| `text-headline` | 22px / 700 | 对话页标题                       |
| `text-title`    | 18px / 700 | 对话页「问问 AI 顾问」           |
| `text-body-lg`  | 15px / 600 | 列表项名称、卡片大标题           |
| `text-body`     | 14px / 400 | 正文描述、AI 回复内容            |
| `text-sm`       | 13px / 500 | 次要正文、建议文本、快捷胶囊     |
| `text-label`    | 12px / 700 | 按钮文字、人群卡片标题           |
| `text-caption`  | 11px / 700 | 风险标签、时间戳、免责声明       |
| `text-micro`    | 10px / 700 | 章节标题（SECTION HEADER）、角标 |

### 2.2 章节标题（Section Header）

所有内容章节标题必须带陶土红圆点前缀，与品牌色保持一致性：

```vue
<!-- Tailwind 原子类实现 -->
<view class="flex items-center gap-[7px] mb-3">
  <view class="w-1.5 h-1.5 rounded-full bg-brand opacity-70 flex-shrink-0" />
  <text class="text-micro text-ink-3 uppercase tracking-[0.08em]">配料解析</text>
</view>
```

**规则：**
- 圆点尺寸：`w-1.5 h-1.5`（6px）
- 圆点颜色：`bg-brand opacity-70`（陶土橙 70%）
- 圆点与文字间距：`gap-[7px]`
- 所有 Section Header（含"分析依据"等 footer 级标题）均适用

---

## 3. 间距规范

### 3.1 页面级内边距

| 场景                 | 类名          |
| -------------------- | ------------- |
| 标准页面水平 padding | `px-5` (20px) |
| 对话页水平 padding   | `px-4` (16px) |
| Status bar 后间距    | `pt-2` (8px)  |
| 底部安全区（iOS）    | `pb-7` (28px) |

### 3.2 组件间距速查

**历史记录列表项：**

```vue
<view class="flex items-center gap-3.5 px-6 py-[13px] border-b border-black/[0.08]">
  <image class="w-[50px] h-[50px] rounded-sm flex-shrink-0" />
  <view class="flex-1">
    <text class="text-body-lg text-ink">产品名</text>
    <text class="text-caption text-ink-3 mt-1">3天前 · 18种成分</text>
  </view>
  <!-- Risk Pill -->
</view>
```

**Verdict Zone（结果页顶部）：**

结果页 Verdict Zone 分为两层：**Persistent Bar**（始终可见）和 **Hero**（滚动折叠）。

```vue
<!-- ── Persistent Bar：始终固定在顶部，背景随滚动从 risk-bg 渐变为 white ── -->
<view id="vPersistent"
  class="relative z-10 flex items-center gap-2 px-5 py-2.5 min-h-[44px] bg-risk-t1-bg
         border-b border-transparent">
  <!-- 返回按钮：颜色随滚动从 risk-dot → ink-2 渐变（JS 控制） -->
  <button class="w-8 h-8 rounded-full flex items-center justify-center text-lg text-risk-t1-dot
                 active:bg-black/[0.06]" aria-label="返回">←</button>
  <!-- 紧凑信息条：hero 消失后淡入（JS opacity 控制） -->
  <!-- max-width 留出微信胶囊区（≈95px 右侧禁区） -->
  <view id="vCompact" class="flex items-center gap-2 overflow-hidden opacity-0"
        style="max-width: calc(375px - 20px - 32px - 8px - 95px)">
    <text class="text-sm font-semibold text-ink truncate">高纤 GI 饼干</text>
    <view class="bg-risk-t1-dot rounded-pill px-2.5 py-0.5 flex-shrink-0">
      <text class="text-[10px] font-bold text-white">成分较优 ✓</text>
    </view>
  </view>
</view>

<!-- ── Hero Shell：高度由 JS 收缩（控制布局）；内容 translateY 上移（GPU 合成） ── -->
<view id="vHeroShell" class="overflow-hidden">
  <view id="vHero" class="px-[22px] pb-7 bg-risk-t1-bg relative overflow-hidden will-change-transform">

    <!-- 大字水印（装饰深度，不参与语义） -->
    <!-- CSS ::before: content:"✓"; absolute; right:-8px; bottom:-22px; font-size:168px;
         font-weight:800; color:risk-t1-dot; opacity:0.07; pointer-events:none -->

    <!-- 食品名 -->
    <text class="text-micro text-risk-t1-text opacity-65 block mb-[14px]">高纤GI饼干（牛油果椰乳）</text>

    <!-- 大字判断，陶土红短线在上方 -->
    <!-- CSS ::before: display:block; width:24px; height:3px; bg:brand; border-radius:2px; mb-3 -->
    <text class="text-display text-risk-t1-dot block mb-2.5 tracking-[-0.04em]">成分较优 ✓</text>

    <!-- 描述 -->
    <text class="text-sm text-risk-t1-text opacity-72 font-medium block mb-[22px]">整体配料合规，少量添加剂需留意</text>

    <!-- Stats 数字条 -->
    <view class="flex items-stretch mb-5">
      <view class="flex flex-col pr-5">
        <text class="text-[32px] font-extrabold text-risk-t1-dot leading-none tracking-[-0.04em]">24</text>
        <text class="text-[10px] font-semibold text-risk-t1-text opacity-50 mt-1">种成分</text>
      </view>
      <view class="flex flex-col px-5 border-l border-risk-t1-dot/20">
        <text class="text-[32px] font-extrabold text-risk-t1-dot leading-none tracking-[-0.04em]">3</text>
        <text class="text-[10px] font-semibold text-risk-t1-text opacity-50 mt-1">种需留意</text>
      </view>
      <view class="flex flex-col px-5 border-l border-risk-t1-dot/20">
        <text class="text-[32px] font-extrabold text-risk-t1-dot leading-none tracking-[-0.04em]">GB</text>
        <text class="text-[10px] font-semibold text-risk-t1-text opacity-50 mt-1">标准合规</text>
      </view>
    </view>

    <!-- Badge：品牌陶土红（与 teal hero bg 形成暖色碰撞） -->
    <!-- ⚠️ 禁止再显示内部代码如 "t1 ·"，只展示用户可读信息 -->
    <view class="inline-flex items-center bg-brand px-[14px] py-1.5 rounded-pill">
      <text class="text-caption text-white">较安全 · 24 种成分</text>
    </view>
  </view>
</view><!-- /.vHeroShell -->
```

### 3.3 Verdict Zone 滚动折叠动画规范

**技术方案：Hero Shell + translateY（性能优先）**

```js
// ❌ 禁止：margin-top 动画每帧触发 layout reflow
// vHero.style.marginTop = `${-heroH * raw}px`;

// ✅ 正确：Shell 控制高度（一次 layout），Hero translateY（GPU composited）
vHeroShell.style.height = `${heroH * (1 - raw)}px`;   // 布局收缩
vHero.style.transform  = `translateY(${-heroH * raw}px)`;  // 视觉上移

// Persistent bar 背景插值：risk-bg → white
vPersistent.style.background = lerpColor(T1_BG, WHITE, raw);

// compact strip 在 50% 滚动后淡入
vCompact.style.opacity = Math.max(0, (raw - 0.5) / 0.5).toFixed(3);

// 100% 时加底边线 + 阴影
if (raw > 0.9) vPersistent.classList.add("scrolled");
```

**动画参数：**
- `SCROLL_DIST = 120px`（完成折叠所需滚动量）
- Hero opacity：`max(0, 1 - raw * 1.5)`（内容比高度更快消失）
- Compact strip：从 50% 开始 → 100% 时全显

### 3.4 微信小程序安全区域

```
右上角禁区（微信胶囊按钮）：≈ right: 0, top: 8px 的 88×32px 区域
─────────────────────────────────────
任何可交互 UI 元素禁止放在此区域内
Compact strip 的 max-width 必须预留 ≈95px 右侧空间：
  max-width: calc(375px - px-5 - back-btn-w - gap - 95px)
  ≈ calc(375px - 20px - 32px - 8px - 95px) = 220px
─────────────────────────────────────
```

**Sheet（底部抽屉）：**

```vue
<view class="bg-surface rounded-t-lg -mt-5 pb-8">
  <!-- handle -->
  <view class="w-9 h-1 bg-[#E0DCD6] rounded-full mx-auto mt-3 mb-[18px]" />
  <!-- 内容 sections -->
</view>
```

**CTA 大按钮卡片（首页）：**

```vue
<view class="mx-5 mt-[22px] bg-brand rounded-xl p-[26px_24px] flex flex-col gap-3.5 relative overflow-hidden">
  <text class="text-micro text-white/60 uppercase tracking-[0.1em]">AI 拍照分析</text>
  <text class="text-hero text-white">拍一张配料表<br>秒知成分好坏</text>
  <text class="text-sm text-white/65">支持所有包装食品</text>
  <view class="self-start bg-white text-brand text-label px-5 py-[9px] rounded-pill">
    立即拍照 →
  </view>
</view>
```

**对话入口 Bar（结果页底部固定）：**

```vue
<view class="absolute bottom-0 left-0 right-0 px-5 pt-3 pb-7"
      style="background: linear-gradient(to top, white 60%, transparent)">
  <!-- 快捷问题横滑 -->
  <scroll-view scroll-x class="flex gap-2 pb-0.5 mb-2.5 whitespace-nowrap">
    <view class="inline-flex bg-raised border border-black/10 rounded-pill px-[13px] py-[7px]">
      <text class="text-label text-ink-2">糖尿病可以吃吗？</text>
    </view>
  </scroll-view>
  <!-- 主按钮 -->
  <view class="flex items-center gap-2.5 bg-brand rounded-xl px-5 py-[14px]">
    <view class="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
      <text class="text-lg text-white">✦</text>
    </view>
    <view class="flex-1">
      <text class="text-body-lg text-white block">深入问问 AI 顾问</text>
      <text class="text-caption text-white/70 block mt-0.5">针对这款产品，随时问任何问题</text>
    </view>
    <text class="text-xl text-white/80">›</text>
  </view>
</view>
```

**人群卡片（横向滚动）：**

```vue
<scroll-view scroll-x class="flex gap-2.5 px-5 py-1">
  <view class="flex-shrink-0 w-[106px] bg-risk-t0-bg border border-black/[0.08] rounded-md p-[13px_11px] flex flex-col gap-1.5">
    <text class="text-[22px]">🧑</text>
    <text class="text-label text-ink">普通成人</text>
    <view class="bg-risk-t0-dot rounded-pill px-2 py-[3px] self-start">
      <text class="text-[10px] font-bold text-white">适量可食</text>
    </view>
    <text class="text-[10px] text-ink-3 leading-[1.5]">每日不超过2-3份</text>
  </view>
</scroll-view>
```

**对话气泡：**

```vue
<!-- 用户 -->
<view
  class="self-end bg-brand text-white rounded-[18px_18px_4px_18px] px-3.5 py-2.5 max-w-[75%]"
>
  <text class="text-body">我有2型糖尿病，这个可以吃吗？</text>
</view>

<!-- AI -->
<view
  class="self-start bg-surface shadow-md rounded-[18px_18px_18px_4px] px-3.5 py-3 max-w-[85%]"
>
  <text class="text-micro text-brand uppercase tracking-[0.06em] block mb-1.5">AI 分析参考</text>
  <text class="text-body text-ink-2 leading-[1.65]">这款饼干含有麦芽糊精…</text>
</view>
<!-- AI 免责 -->
<text
  class="text-[10px] text-ink-3 mt-1 ml-1"
>AI 生成 · 仅供参考 · 请遵医嘱</text>
```

---

## 4. 圆角规范

| 类名           | px     | 使用场景                                         |
| -------------- | ------ | ------------------------------------------------ |
| `rounded-sm`   | 10px   | 历史缩略图、小标签                               |
| `rounded-md`   | 18px   | 建议框、人群卡片、替代方案卡片                   |
| `rounded-lg`   | 26px   | Sheet 顶部、主要内容区块                         |
| `rounded-xl`   | 34px   | CTA 大按钮卡片、对话入口按钮                     |
| `rounded-pill` | 9999px | 所有胶囊标签（risk pill、badge、chip、快捷问题） |
| `rounded-full` | 50%    | 圆形按钮（发送、头像、圆点指示）                 |

**规则：** 嵌套时子元素圆角 ≤ 父元素圆角。

---

## 5. 阴影规范

| 类名        | 用途                            |
| ----------- | ------------------------------- |
| `shadow-sm` | 人群卡片、小组件                |
| `shadow-md` | 历史列表头像、AI 气泡、设置按钮 |
| `shadow-lg` | 浮动 FAB（如有）                |

---

## 6. 分析页（深色）专用原子类

分析进行中页面背景 `bg-dark-bg`，内容使用白色透明度变量：

```vue
<!-- 页面根 -->
<view class="min-h-screen bg-dark-bg flex flex-col">

  <!-- 状态文字 -->
  <text class="text-micro text-white/35 uppercase tracking-[0.14em]">Analyzing</text>
  <text class="text-headline text-white">AI 正在分析中</text>

  <!-- 相框 -->
  <view class="w-[240px] h-[168px] rounded-[16px] bg-dark-surface border border-dark-border
               relative flex items-center justify-center">
    <!-- 四角 border 用绝对定位 + brand 色 -->
    <!-- 扫描线 -->
    <view class="absolute left-2 right-2 h-px
                 bg-gradient-to-r from-transparent via-brand to-transparent
                 animate-scan" />
    <text class="text-caption text-white/22">配料表照片</text>
  </view>

  <!-- 步骤 -->
  <!-- done: w-7 h-7 rounded-full bg-brand text-white -->
  <!-- active: w-7 h-7 rounded-full border border-white/30 text-white -->
  <!-- wait: w-7 h-7 rounded-full bg-white/[0.06] text-white/20 -->
</view>
```

---

## 7. 动效规范

| 场景           | Tailwind 类 / 说明                                       |
| -------------- | -------------------------------------------------------- |
| 页面切换       | `duration-300 ease-in-out`                               |
| Sheet 弹出     | `duration-[380ms] ease-spring`                           |
| 按压缩放       | `active:scale-[0.97] transition duration-100 ease-out`   |
| CTA 按钮按压色 | `active:bg-brand-dark`                                   |
| 快捷胶囊按压   | `active:bg-page`                                         |
| 列表项按压     | `active:bg-black/[0.04]`                                 |
| 扫描线         | `animate-scan`（见 keyframes）                           |
| AI 加载三点    | `animate-dot-bounce` + `[animation-delay:150ms]` stagger |
| 结果页进场     | `animate-fadeUp` 错开延迟（见下方）                      |

### 7.1 结果页 Hero 进场动画

结果出现时，Hero 内各元素依次错开淡入上移，传递"结论到来"的仪式感：

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* 时间函数：ease-out-expo（cubic-bezier(0.22,1,0.36,1)），不可使用弹跳/弹性 */
```

| 元素        | 延迟   |
| ----------- | ------ |
| 食品名      | 50ms   |
| 大字判断    | 120ms  |
| 描述文字    | 180ms  |
| Stats 数字  | 220ms  |
| Badge       | 280ms  |

**重要：** 首次滚动时必须立即取消 CSS animation，改为 JS inline style 控制，避免 `opacity` 竞争：

```js
// 首次滚动时执行一次
heroChildren.forEach(el => {
  el.style.animation = "none";
  el.style.opacity   = "1";
  el.style.transform = "none";
});
```

---

## 8. 状态规范

### 8.1 Risk Pill 完整写法

```vue
<!-- t0 -->
<view class="bg-risk-t0-bg rounded-pill px-[11px] py-[5px]">
  <text class="text-caption text-risk-t0-text">安全</text>
</view>

<!-- t3 -->
<view class="bg-risk-t3-bg rounded-pill px-[11px] py-[5px]">
  <text class="text-caption text-risk-t3-text">存在风险</text>
</view>
```

### 8.2 建议框变体（Advice Block）

建议框使用左边框变体，比纯色背景块更有观点感：

```vue
<!-- 结果页「参考建议」：左侧 risk-dot 色边框 + raised 背景 -->
<view class="bg-raised border-l-[3px] border-risk-t1-dot
             rounded-r-md px-[14px] pl-4 py-[14px]">
  <text class="text-sm text-ink-2 leading-[1.75]">
    含膳食纤维，整体成分结构合理…
  </text>
</view>
```

**规则：**
- 左边框颜色跟随当前产品的风险等级 `border-risk-tX-dot`
- 圆角只保留右侧：`rounded-r-md`（18px），左侧为直角（边框切入感）
- 背景用 `bg-raised`（Layer 2），不用 `bg-surface`

### 8.3 前后对比组件（Before/After）

"更优替代方案"两栏必须有列头标签，用户需要明确知道哪侧是当前、哪侧是推荐：

```vue
<view class="flex items-center gap-2">
  <!-- 当前成分（caution 色调） -->
  <view class="flex-1 bg-risk-t2-bg rounded-md pt-[10px] pb-3 px-[13px]">
    <text class="text-[9px] font-bold tracking-[0.07em] uppercase text-risk-t2-text opacity-50 block mb-1.5">
      当前成分
    </text>
    <text class="text-sm font-medium text-risk-t2-text block py-0.5">麦芽糊精</text>
    <!-- ... -->
  </view>

  <!-- 箭头 -->
  <text class="text-[22px] text-brand font-bold flex-shrink-0">›</text>

  <!-- 更优选择（safe 色调） -->
  <view class="flex-1 bg-risk-t0-bg rounded-md pt-[10px] pb-3 px-[13px]">
    <text class="text-[9px] font-bold tracking-[0.07em] uppercase text-risk-t0-text opacity-50 block mb-1.5">
      更优选择
    </text>
    <text class="text-sm font-medium text-risk-t0-text block py-0.5">燕麦膳食纤维</text>
    <!-- ... -->
  </view>
</view>
```

### 8.4 横向滚动行渐变提示

所有横向滚动容器右侧需要渐变遮罩，暗示更多内容：

```vue
<!-- 包裹层：relative + overflow-hidden -->
<view class="relative">
  <scroll-view scroll-x class="flex gap-2 pb-0.5 whitespace-nowrap overflow-x-auto">
    <!-- pills / cards -->
  </scroll-view>
  <!-- 右侧渐变提示 -->
  <view class="absolute right-0 top-0 bottom-0 w-10
               pointer-events-none
               bg-gradient-to-l from-white to-transparent" />
</view>
```

**适用场景：** suggest-row（快捷问题）、demo-scroll（人群卡片）等横向滚动行

### 8.5 空状态（首页无记录）

```vue
<view class="flex flex-col items-center justify-center gap-3 px-10 py-20">
  <!-- 图标区 -->
  <view class="w-16 h-16 rounded-xl bg-raised flex items-center justify-center">
    <text class="text-3xl">📷</text>
  </view>
  <text class="text-headline text-ink-2 text-center">还没有分析记录</text>
  <text class="text-sm text-ink-3 text-center leading-relaxed">
    拍一张配料表，开始你的第一次分析
  </text>
  <!-- 复用 CTA 按钮样式 -->
</view>
```

### 8.6 错误状态（内联，非 Toast）

```vue
<view class="mx-5 bg-risk-t3-bg rounded-md px-4 py-3 flex items-center gap-3">
  <text class="text-xl text-risk-t3-dot">⚠</text>
  <view class="flex-1">
    <text class="text-label text-risk-t3-text block">分析失败</text>
    <text class="text-caption text-risk-t3-text/70 block mt-0.5">网络异常，请检查连接后重试</text>
  </view>
  <text class="text-sm text-risk-t3-dot font-bold">重试</text>
</view>
```

### 8.7 AI 加载中（三点动画）

```vue
<view class="self-start bg-surface shadow-md rounded-[18px_18px_18px_4px] px-4 py-3">
  <view class="flex items-center gap-1.5">
    <view v-for="i in 3" :key="i"
          class="w-1.5 h-1.5 rounded-full bg-ink-3 animate-dot-bounce"
          :style="`animation-delay: ${(i-1)*150}ms`" />
  </view>
</view>
```

---

## 9. 文案禁用词表

| 禁用              | 替换                        |
| ----------------- | --------------------------- |
| 放心吃 / 可以食用 | 成分较优 / 整体合规         |
| 不安全 / 有害     | 多处值得关注 / 存在风险成分 |
| 一定会导致        | 部分研究提示可能            |
| 推荐购买          | 可参考购买                  |
| 不建议购买        | 建议进一步了解              |

**必须出现的声明：**

- AI 气泡底部：`AI 生成 · 仅供参考 · 请遵医嘱`（`text-[10px] text-ink-3`）
- 结果页底部：完整免责声明（`text-caption text-ink-3 leading-[1.65]`）

---

## 10. 扫码页（Scan Page）

### 10.1 概述

入口：首页"扫一扫"按钮 / 底部 Tab
出口：扫码成功 → 产品详情页；取消 → 返回上一页

**设计原则：**

- 放心感优先：启动扫码时传递"有人在帮我把关"
- 温暖陶土色系 + 大胆排版
- 极简：只有一个核心动作，不需要解释

### 10.2 视觉规范

**背景层级：**
| Layer | 类名 | hex | 用途 |
|-------|------|-----|------|
| Layer 0 | `bg-page` | `#FAF8F3` | 页面底色（暖白） |
| Layer 1 | `bg-surface` | `#FFFFFF` | 扫描框 |

**字体：**
| 用途 | 类名 | px |
|------|------|-----|
| 页面标题 | `text-headline` / 700 | 22px |
| 副标题说明 | `text-sm` / 400 | 13px |
| 底部提示 | `text-caption` / 400 | 11px |

### 10.3 页面结构 (375px)

```
┌─────────────────────────────────────┐
│  status-bar (native)                │
├─────────────────────────────────────┤
│                                     │
│           [scan-icon]               │ ← 5rem 容器，圆角 34px
│                                     │    背景 bg-brand-light
│          扫一扫                      │ ← text-headline / 700
│                                     │
│     将条码对准框内即可自动扫描        │ ← text-sm / 400，text-ink-2
│                                     │
│       ┌───────────────┐             │
│       │               │             │ ← 扫描框 300px × 300px
│       │    扫描框      │             │    rounded-lg (26px)
│       │               │             │    border 白色半透明
│       └───────────────┘             │
│                                     │
│    轻触屏幕手动输入条形码             │ ← text-caption，text-ink-3
│                                     │
└─────────────────────────────────────┘
```

### 10.4 扫描框组件

**四角标记：**

- 位置：扫描框四角
- 尺寸：24px × 2px（横向）/ 2px × 24px（竖向）
- 颜色：`bg-brand`
- 圆角：`rounded-sm` (10px)

**扫描线：**

- 位置：扫描框内，上下扫动
- 高度：1px
- 颜色：白色半透明
- 动画：`animate-scan`

**扫描框状态：**
| 状态 | 边框色 | 扫描线色 |
|------|--------|----------|
| 默认 | `border-white/60` | 白色半透明 |
| 扫描中 | `border-brand` | brand 色 |
| 成功 | `border-risk-t0-dot` | risk-t0-dot 色 |

### 10.5 组件代码示例

```vue
<template>
  <view class="min-h-screen bg-page flex flex-col">
    <TopBar />

    <!-- 主内容区：垂直居中，重心偏上 -->
    <view class="flex-1 flex flex-col items-center justify-center px-6 -mt-12">
      <!-- 扫描图标 -->
      <view
        class="w-20 h-20 rounded-xl bg-brand-light flex items-center justify-center mb-6"
      >
        <DIcon name="scan" dclass="text-4xl text-brand" />
      </view>

      <!-- 标题 -->
      <text class="text-headline text-ink tracking-tight">扫一扫</text>

      <!-- 副标题 -->
      <text class="text-sm text-ink-2 mt-2">将条码对准框内即可自动扫描</text>

      <!-- 扫描框 -->
      <view
        class="relative w-[300px] h-[300px] mt-10 rounded-lg
                  border border-white/60 bg-white/[0.08]
                  animate-scan overflow-hidden"
      >
        <!-- 四角标记 -->
        <!-- 左上 -->
        <view class="absolute top-0 left-0 w-6 h-0.5 bg-brand rounded-sm" />
        <view class="absolute top-0 left-0 w-0.5 h-6 bg-brand rounded-sm" />
        <!-- 右上 -->
        <view class="absolute top-0 right-0 w-6 h-0.5 bg-brand rounded-sm" />
        <view class="absolute top-0 right-0 w-0.5 h-6 bg-brand rounded-sm" />
        <!-- 左下 -->
        <view class="absolute bottom-0 left-0 w-6 h-0.5 bg-brand rounded-sm" />
        <view class="absolute bottom-0 left-0 w-0.5 h-6 bg-brand rounded-sm" />
        <!-- 右下 -->
        <view class="absolute bottom-0 right-0 w-6 h-0.5 bg-brand rounded-sm" />
        <view class="absolute bottom-0 right-0 w-0.5 h-6 bg-brand rounded-sm" />

        <!-- 扫描线 -->
        <view class="absolute left-2 right-2 h-px bg-white/80 animate-scan" />
      </view>

      <!-- 底部提示 -->
      <text class="text-caption text-ink-3 mt-8" @tap="openManualInput">
        轻触屏幕手动输入条形码
      </text>
    </view>
  </view>
</template>
```

### 10.6 手动输入 Sheet

```vue
<!-- Sheet 内容 -->
<view class="bg-surface rounded-t-lg px-5 pb-8">
  <view class="w-9 h-1 bg-[#E0DCD6] rounded-full mx-auto mt-3 mb-5" />
  <text class="text-title text-ink block mb-4">手动输入条形码</text>
  <input class="w-full bg-raised rounded-lg px-4 py-3 text-body text-ink"
         type="number" placeholder="请输入条形码" />
  <view class="w-full bg-brand rounded-xl px-5 py-3 mt-4">
    <text class="text-body-lg text-white">确认</text>
  </view>
</view>
```

### 10.7 动画规范

```css
/* 扫描线动画（已内置于 tailwind.config） */
.animate-scan {
  animation: scan 2s ease-in-out infinite;
}

/* 尊重运动偏好 */
@media (prefers-reduced-motion: reduce) {
  .animate-scan {
    animation: none;
  }
}
```

---

## 11. 待设计页面

- [ ] 相机取景页（实际拍照界面）
- [ ] 我的页面（设置、账户）
- [ ] 首页空状态
- [ ] 网络错误/分析彻底失败页
- [ ] 新用户首次引导流程

---

## 11. 决策日志

| 日期       | 决策                          | 理由                           |
| ---------- | ----------------------------- | ------------------------------ |
| 2026-03-30 | 品牌色 `#C4532A` 陶土橙       | 与竞品绿色系完全差异化         |
| 2026-03-30 | 放弃暗色模式                  | 聚焦核心流程，降低复杂度       |
| 2026-03-30 | Verdict Zone 整块用风险色背景 | 颜色即结论，无需阅读文字       |
| 2026-03-30 | 对话入口固定在结果页底部      | 不打断阅读，自然引导           |
| 2026-03-30 | 分析页用深色背景              | 与白色页形成对比，增加仪式感   |
| 2026-03-30 | 规范切换为 Tailwind v3 原子类 | 防止随意内联样式，统一设计语言 |
| 2026-03-31 | Verdict Zone 改为 Hero Shell + translateY 动画 | margin-top 动画每帧触发 reflow，低端安卓掉帧；shell 高度收缩 + translateY 保证 GPU 合成 |
| 2026-03-31 | Badge 去除内部代码 "t1 ·" | 用户不懂风险等级编码，只展示可读中文 |
| 2026-03-31 | Persistent bar 初始背景 = risk-bg，滚动后变白 | 初始白色条压在彩色 Hero 上产生割裂感；同色融合再渐变更自然 |
| 2026-03-31 | Stats 数字从 20px 提升至 32px | 结果页强调数字语言，小数字与大字判断差距不够，无法产生戏剧感 |
| 2026-03-31 | Badge 颜色改为 brand 陶土红（替代 tX-dot） | teal hero 背景上用同色 badge 无对比；陶土红作为暖色碰撞引入品牌感 |
| 2026-03-31 | 章节标题加陶土红圆点前缀 | 单纯小字标题在白色背景上缺乏节奏；红点将品牌色延伸到正文区 |
| 2026-03-31 | 建议框左边框变体（border-left） | 纯色背景框缺乏观点感；左边框赋予"引用/观点"语义 |
| 2026-03-31 | 前后对比组件加列头标签（当前成分/更优选择） | 无标签时用户无法快速判断哪侧是当前产品 |
| 2026-03-31 | 横向滚动行右侧渐变遮罩 | 无提示时用户不知道有更多内容可滑动 |
