# ingredient-detail 页面重构设计文档

## 概述

将 `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` 按照 `product/index.vue` 的架构标准进行重构，统一使用 `Screen` 组件、Tailwind 工具类 + 设计系统变量。

## 参考文件

- `web/apps/uniapp-tw/src/pages/product/index.vue` — 目标架构标准
- `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` — 当前实现（待重构）
- `web/ui/03-ingredient-detail.html` — 设计稿

## 核心改动

### 1. 布局结构

**重构方案**：
- 使用 `Screen` 组件作为主容器
- Header 放到 `Screen` 的 header slot，使用 `sticky` 定位
- 内容区通过 `#content` slot 实现
- 底部栏通过 `#footer` slot 实现

```vue
<Screen>
  <template #header>...</template>
  <template #content>...</template>
  <template #footer>...</template>
</Screen>
```

### 2. 样式系统

**重构方案**：
- 移除大部分自定义 SCSS（保留必要的 risk 色变量映射）
- 改用 Tailwind 类 + 设计系统 CSS 变量
- 设计稿中的 CSS 类提取为全局样式（在 `App.vue` 或全局样式文件中定义）

### 3. 状态处理

**重构方案**：
- 复用 `StateView` 组件统一处理加载/错误态

### 4. 底部栏按钮

按设计稿实现两个按钮：
- 左：「咨询 AI 助手」— ghost/outline 样式 (`btn-out`)
- 右：「查看相关食品」— primary 粉色渐变

点击行为：
- 「咨询 AI 助手」→ `goToAI()` 跳转到聊天页
- 「查看相关食品」→ `goToSearch()` 跳转到搜索页（按配料筛选）

**注意**：「添加到记录」功能在设计稿中不存在，应移除。

### 5. Hero 风险卡

**关键差异**：
- 设计稿中 **没有 emoji**
- 当前实现有 `heroEmoji`，需要移除

Hero 卡结构（按设计稿）：
- 配料名称（大号粗体）
- 添加剂代码（E250 · 食品添加剂）
- 风险等级徽章
- 风险谱条（渐变色 + 指针）
- 谱条标签（低风险/中等/高风险）
- Chips 行（防腐剂、护色剂、化学合成、孕妇禁用、别名）

### 6. AI 标签规则

只有以下卡片有 AI 标签：
- AI 风险分析
- AI 使用建议

**「描述」卡片没有 AI 标签**（当前实现错误地加了 AI 标签）。

## 全局 CSS 类定义

### ai-label（AI 标签）

```scss
.ai-label {
  font-size: 9.5px; font-weight: 700;
  background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

### chip-red / chip-warn / chip-neu

```scss
// light mode
.chip-red { background: #fff0f0; color: #dc2626; border: 1px solid #fecaca; }
.chip-warn { background: #fefce8; color: #a16207; border: 1px solid #fde68a; }
.chip-neu { background: rgba(0,0,0,0.04); color: #4b5563; }

// dark mode
.dark .chip-red { background: #450a0a; color: #fca5a5; border: 1px solid transparent; }
.dark .chip-warn { background: #3b1a00; color: #fcd34d; border: 1px solid transparent; }
.dark .chip-neu { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6); }
```

### dot-good / dot-warn

```scss
// light mode
.dot-good { background: #f0fdf4; }
.dot-good svg { fill: #22c55e; }
.dot-warn { background: #fffbeb; }
.dot-warn svg { fill: #f59e0b; }

// dark mode
.dark .dot-good { background: #052e16; }
.dark .dot-good svg { fill: #4ade80; }
.dark .dot-warn { background: #3b1a00; }
.dark .dot-warn svg { fill: #fbbf24; }
```

### sec-card

```scss
.light .sec-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.dark .sec-card {
  background: #1a1a1a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  overflow: hidden;
}
```

### bot-bar（底部栏）

```scss
.light .bot-bar {
  background: rgba(255,255,255,0.98);
  border-top: 1px solid rgba(0,0,0,0.06);
}
.dark .bot-bar {
  background: rgba(26,26,26,0.98);
  border-top: 1px solid rgba(255,255,255,0.08);
}
.light .btn-out {
  background: transparent;
  border: 1px solid rgba(0,0,0,0.08);
  color: var(--text-primary);
}
.dark .btn-out {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-primary);
}
```

### Hero Top 渐变（按风险等级）

**t3（高风险）亮色**：
```scss
.hero-top {
  background: linear-gradient(135deg, rgba(255,244,240,0.6) 0%, transparent 100%);
  border-bottom: 1px solid #fecaca;
}
```

**t3（高风险）暗色**：
```scss
.dark .hero-top {
  background: linear-gradient(135deg, rgba(26,8,8,0.6) 0%, transparent 100%);
  border-bottom: 1px solid #7f1d1d;
}
```

其他风险等级的渐变色需要类似处理，通过 CSS 变量实现动态切换。

### ing-hdr（Header）

```scss
// light mode
.ing-hdr {
  background: #fff4f0;
  border-bottom: 2px solid #fecaca;
}
.ing-hdr-title { color: #7f1d1d; }
.ing-hdr-sub { color: #ef4444; }
.ing-hdr-btn { background: rgba(220,38,38,0.1); }
.ing-hdr svg { stroke: #ef4444; }

// dark mode
.dark .ing-hdr {
  background: #1a0808;
  border-bottom: 2px solid #7f1d1d;
}
.dark .ing-hdr-title { color: #fca5a5; }
.dark .ing-hdr-sub { color: #f87171; }
.dark .ing-hdr-btn { background: rgba(248,113,113,0.15); }
.dark .ing-hdr svg { stroke: #f87171; }
```

## Header Slot 实现

```vue
<template #header>
  <view
    class="sticky top-0 z-10 flex items-center gap-2.5 px-3.5 py-3 h-16 transition-all duration-300 ing-hdr"
  >
    <button
      class="ing-hdr-btn w-[30px] h-[30px] rounded-[9px] flex items-center justify-center flex-shrink-0"
      @click="goBack"
    >
      <Icon name="arrowLeft" :size="22" />
    </button>
    <view class="flex-1 flex flex-col">
      <text class="ing-hdr-title text-[14px] font-bold">
        {{ ingredient?.name ?? "配料详情" }}
      </text>
      <text class="ing-hdr-sub text-[10px] font-semibold mt-px">
        {{ headerSubtitle }}
      </text>
    </view>
    <button
      class="ing-hdr-btn w-[30px] h-[30px] rounded-[9px] flex items-center justify-center flex-shrink-0"
      @click="shareToFriend"
    >
      <Icon name="share" :size="22" />
    </button>
  </view>
</template>
```

## Content Slot 实现

按设计稿顺序：
1. **Hero 风险卡**（无 emoji）
2. **描述卡片**（无 AI 标签）
3. **AI 风险分析卡片**（有 AI 标签，风险项带红色方形图标背景）
4. **风险管理信息卡片**
5. **AI 使用建议卡片**（有 AI 标签，建议项带 dot-good/dot-warn 图标）
6. **含此配料的产品卡片**（横向滚动）

## Footer Slot 实现

```vue
<template #footer>
  <view class="bot-bar px-3 py-2 flex gap-2 h-16">
    <button
      class="btn-out flex-1 rounded-xl py-3 text-[12px] font-semibold active:scale-[0.97]"
      @click="goToAI"
    >
      咨询 AI 助手
    </button>
    <button
      class="flex-1 rounded-xl py-3 text-[12px] font-semibold text-white active:scale-[0.97]"
      style="background:linear-gradient(135deg,var(--accent-pink-light),var(--accent-pink));box-shadow:0 4px 12px rgba(225,29,72,0.3)"
      @click="goToSearch"
    >
      查看相关食品
    </button>
  </view>
</template>
```

## 文件变更

1. `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` — 重构主文件
2. `web/apps/uniapp-tw/src/App.vue` 或全局样式 — 添加全局 CSS 类

## 预期结果

- 移除 ~300 行自定义 SCSS
- 页面结构与 `product/index.vue` 保持一致
- 完美还原设计稿 `03-ingredient-detail.html` 的视觉效果
- 支持亮色/暗色模式切换
- Hero 卡无 emoji
- 「描述」卡片无 AI 标签
- 底部栏为「咨询 AI 助手」+「查看相关食品」
