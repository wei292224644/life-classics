# 食品安全助手 — 设计规范 v1.0

> 本文档是唯一权威的视觉设计规范。所有开发工作中的间距、颜色、字体、组件决策必须以此为准。
> 禁止在代码中出现未在此文档定义的魔法数字（如随意的 `padding: 7px`、`color: #abc`）。

---

## 0. 产品设计原则

1. **放心感优先** — 结果页的视觉重心永远是「能不能吃」这一个判断，所有其他信息让位于它
2. **用排版说话** — 不依赖插画/吉祥物，用字重、字号、字色的层次建立视觉冲击力
3. **温暖不沉闷** — 陶土橙作为点缀色带来能量感，而非医疗蓝/科技灰
4. **诚实直接** — 风险标识清晰可辨，不美化也不恐吓，给用户做决策的底气
5. **与竞品拉开距离** — 禁止绿色主色调、散落倾斜卡片、圆润吉祥物等竞品标志性元素

---

## 1. 字体系统

### 1.1 字体族

| 用途 | 字体 | 说明 |
|------|------|------|
| 拉丁字符 / 数字 / 标题 | **Plus Jakarta Sans** | 主字体，覆盖所有英文、数字、标点 |
| 中文字符 | **Noto Sans SC** | 回退字体，覆盖所有汉字 |
| 系统回退 | `-apple-system, sans-serif` | 离线或加载失败时 |

```css
font-family: 'Plus Jakarta Sans', 'Noto Sans SC', -apple-system, sans-serif;
```

### 1.2 字号梯度（设计稿 px，UniApp 对应 ×2 rpx）

| Token | px | rpx | 字重 | 行高 | 字距 | 用途 |
|-------|-----|-----|------|------|------|------|
| `text-display` | 44px | 88rpx | 800 | 1.0 | -0.04em | 结果页大字判断（成分较优 ✓） |
| `text-hero` | 28px | 56rpx | 800 | 1.1 | -0.03em | 首页标题 |
| `text-headline` | 22px | 44rpx | 700 | 1.2 | -0.02em | 页面次标题 |
| `text-title` | 18px | 36rpx | 700 | 1.3 | -0.01em | 对话页标题 |
| `text-body-lg` | 15px | 30rpx | 600 | 1.5 | 0 | 列表项名称、卡片标题 |
| `text-body` | 14px | 28rpx | 400 | 1.7 | 0 | 正文内容 |
| `text-sm` | 13px | 26rpx | 500 | 1.6 | 0 | 次要正文、建议文本 |
| `text-label` | 12px | 24rpx | 700 | 1.4 | 0 | 按钮文字、人群卡片标题 |
| `text-caption` | 11px | 22rpx | 700 | 1.4 | 0.08em | 风险标签、章节标题（大写） |
| `text-micro` | 10px | 20rpx | 700 | 1.4 | 0.12em | 角标、分类标签（大写） |

### 1.3 章节标题（Section Header）规范

章节标题统一使用 `text-micro`，全大写，`letter-spacing: 0.12em`，颜色 `--text-3`。

```
配料解析 → INGREDIENTS（不直接用中文，用中文则不大写）
实际输出：配料解析（中文不强制大写，但保持 text-micro 规格）
```

---

## 2. 色彩系统

### 2.1 背景层级（Background Layers）

背景颜色有严格的层级关系，禁止跨层使用：

```
Layer 0 — Page Background  #FAF8F3  (暖白，页面底色)
Layer 1 — Surface          #FFFFFF  (白色，卡片/Sheet 主体)
Layer 2 — Surface Raised   #F2EFE8  (浅暖灰，内嵌卡片/建议框/输入框背景)
Layer 3 — Surface Overlay  rgba(26,23,20,0.04)  (极浅遮罩，悬停态)
```

**使用规则：**
- 页面背景：`Layer 0`
- 内容 Sheet / 底部抽屉：`Layer 1`
- 建议框 `.advice`、输入框、人群卡片背景：`Layer 2`
- 禁止在 `Layer 1` 上直接使用 `Layer 0` 作为嵌套卡片（对比度不足）

### 2.2 文字层级（Text Hierarchy）

| Token | Hex | 用途 |
|-------|-----|------|
| `--text` | `#1A1714` | 主文字（标题、配料名） |
| `--text-2` | `#6B6560` | 次要文字（正文描述、建议内容） |
| `--text-3` | `#A09890` | 弱化文字（章节标题、辅助说明、时间戳） |
| `--text-inverse` | `#FFFFFF` | 深色背景上的文字 |

**禁止直接使用 hex**，必须通过 CSS 变量或 Tailwind token 引用。

### 2.3 品牌色（Brand）

| Token | Hex | 用途 |
|-------|-----|------|
| `--brand` | `#C4532A` | 主 CTA 按钮、对话入口、链接、强调 |
| `--brand-light` | `#FDEEE9` | 品牌色背景（浅） |
| `--brand-dark` | `#A34222` | 品牌色按压态 |

品牌色**不参与**风险色系统，不用于风险标签。

### 2.4 风险色系统（Risk Scale t0–t4）

每个等级包含三个 token：`dot`（圆点/主色）、`bg`（背景）、`text`（文字）。

| 等级 | 语义 | `--tX-dot` | `--tX-bg` | `--tX-text` |
|------|------|-----------|----------|------------|
| `t0` | 非常安全 | `#3D7A5C` | `#EEF7F2` | `#1E4D38` |
| `t1` | 较安全 | `#2E7D7A` | `#EAF4F4` | `#164D4B` |
| `t2` | 谨慎 | `#B07D1A` | `#FEF5E0` | `#6B4A0A` |
| `t3` | 存在风险 | `#C44A2B` | `#FDEEE9` | `#7A2410` |
| `t4` | 高风险 | `#8B1A1A` | `#FDDEDE` | `#5A0D0D` |

**使用规则：**
- `dot` 色：用于圆形指示点、badge 背景、边框左侧强调线
- `bg` 色：用于标签背景、区块背景（如 verdict zone、人群卡片）
- `text` 色：用于 `bg` 色之上的所有文字，保证对比度

**Verdict Zone 背景规则：**
整个顶部 verdict 区域使用当前产品等级的 `bg` 色作为背景，`dot` 色作为大字颜色，`text` 色作为描述文字颜色。

### 2.5 分析页专用色（Dark Surface）

分析进行中页面使用深色背景，形成仪式感与对比：

| Token | Hex | 用途 |
|-------|-----|------|
| `--dark-bg` | `#1A1714` | 分析页背景 |
| `--dark-text` | `rgba(255,255,255,0.9)` | 主文字 |
| `--dark-text-2` | `rgba(255,255,255,0.4)` | 次要文字 |
| `--dark-text-3` | `rgba(255,255,255,0.22)` | 弱化文字 |
| `--dark-border` | `rgba(255,255,255,0.12)` | 边框 |
| `--dark-surface` | `rgba(255,255,255,0.06)` | 卡片/框背景 |

扫描线颜色：`--brand` `#C4532A`，渐变：`linear-gradient(90deg, transparent, #C4532A, transparent)`

### 2.6 边框与分割线

| Token | 值 | 用途 |
|-------|-----|------|
| `--border` | `rgba(26,23,20,0.08)` | 卡片边框、列表分割线 |
| `--border-strong` | `rgba(26,23,20,0.15)` | 输入框边框 |

---

## 3. 间距系统

### 3.1 基础单位

**基础单位：8px**（UniApp 对应 16rpx）。所有间距必须是 4px 的倍数，优先使用 8px 的倍数。

### 3.2 间距梯度

| Token | px | rpx | 用途 |
|-------|-----|-----|------|
| `space-1` | 4px | 8rpx | 极小间距（标签内垂直 padding） |
| `space-2` | 8px | 16rpx | 紧凑间距（列表项内元素间距） |
| `space-3` | 12px | 24rpx | 小间距（卡片内部元素间距） |
| `space-4` | 16px | 32rpx | 标准间距（Section 内 padding） |
| `space-5` | 20px | 40rpx | 页面水平 padding |
| `space-6` | 24px | 48rpx | 页面水平 padding（宽松场景） |
| `space-8` | 32px | 64rpx | Section 间距 |
| `space-10` | 40px | 80rpx | 大区块间距 |

### 3.3 页面级间距规范

| 场景 | 规范 |
|------|------|
| 页面水平内边距 | `20px`（首页/结果页），`16px`（对话页） |
| 顶部 Status Bar 后间距 | `8px` |
| Section 标题距上方内容 | `20px` |
| Section 内列表项垂直 padding | `11px 0` |
| 章节之间分割线 | `height: 1px`，颜色 `--border`，`margin: 4px 20px 20px` |
| 底部安全区额外 padding | `28px`（iOS 底部手势条区域） |

### 3.4 组件内部间距

**历史记录列表项：**
```
padding: 13px 24px
gap（图片与文字）: 14px
图片尺寸: 50×50px，border-radius: 10px
```

**Verdict Zone：**
```
padding: 16px 22px 36px
食品名到大字距离: 5px
大字到描述文字距离: 8px
描述文字到 badge 距离: 12px
```

**Sheet 内 Section：**
```
padding: 0 20px 20px
section header margin-bottom: 12px
```

**人群卡片（横向滚动）：**
```
卡片宽: 106px
卡片内 padding: 13px 11px
卡片间 gap: 10px
滚动区左右 padding: 20px
```

**对话气泡：**
```
用户气泡: border-radius: 18px 18px 4px 18px，padding: 10px 14px
AI 气泡:   border-radius: 18px 18px 18px 4px，padding: 12px 14px
气泡间距: 14px
最大宽度: 用户 75%，AI 85%
```

---

## 4. 圆角系统（Border Radius）

| Token | px | 用途 |
|-------|-----|------|
| `r-xs` | 6px | 极小圆角（暂未使用） |
| `r-sm` | 10px | 历史图片、小标签角标 |
| `r-md` | 18px | 建议框、人群卡片、替代方案卡片 |
| `r-lg` | 26px | Sheet 顶部、主要卡片区块 |
| `r-xl` | 34px | CTA 大按钮卡片、对话入口按钮 |
| `r-full` | 9999px | 所有胶囊形标签（risk pill、badge、chip） |
| `r-circle` | 50% | 圆形按钮（FAB、发送按钮、头像） |

**规则：**
- 越大的容器使用越大的圆角
- 嵌套时子元素圆角应小于父元素（如 Sheet 内卡片用 `r-md`，Sheet 本身用 `r-lg`）
- 胶囊标签（pill）统一 `r-full`，禁止使用固定 px

---

## 5. 阴影与层叠（Elevation）

| Level | CSS 值 | 用途 |
|-------|--------|------|
| `shadow-sm` | `0 1px 6px rgba(26,23,20,.08)` | 人群卡片、小组件 |
| `shadow-md` | `0 2px 18px rgba(26,23,20,.08), 0 0 0 1px rgba(26,23,20,.05)` | 历史列表头像、设置按钮 |
| `shadow-lg` | `0 12px 48px rgba(26,23,20,.14)` | 浮动 FAB（暂未设计） |
| `shadow-phone` | `0 28px 80px rgba(0,0,0,.20), 0 0 0 1px rgba(0,0,0,.09)` | 设计稿手机框（非生产） |

**规则：**
- 对话气泡 AI 消息使用 `shadow-md`
- 页面内容不使用 `shadow-lg`（过重）
- 禁止随意叠加多个阴影

---

## 6. 组件规范

### 6.1 Risk Pill（风险标签）

```
background: var(--tX-bg)
color: var(--tX-text)
padding: 5px 11px
border-radius: r-full (9999px)
font-size: 11px (text-caption)
font-weight: 700
```

禁止给 risk pill 添加边框或阴影。

### 6.2 Verdict Badge

```
background: var(--tX-dot)
color: white
padding: 5px 13px
border-radius: r-full
font-size: 11px
font-weight: 700
display: inline-flex, gap: 6px
```

### 6.3 CTA 大按钮卡片（首页拍照入口）

```
background: --brand (#C4532A)
border-radius: r-xl (34px)
padding: 26px 24px
内部元素间距: gap 14px
内嵌按钮: background white, color --brand, padding 9px 20px, border-radius r-full
```

装饰圆圈（伪元素）：
```css
::before { top:-40px; right:-40px; width:130px; height:130px; border-radius:50%; background:rgba(255,255,255,.08) }
```

### 6.4 对话入口按钮（Chat CTA Bar）

```
position: absolute, bottom: 0
padding: 12px 20px 28px（28px 为 iOS 安全区）
background: linear-gradient(to top, white 60%, rgba(255,255,255,0))

主按钮:
  background: --brand
  border-radius: r-xl
  padding: 14px 20px
  内部 icon: 36×36px, border-radius 50%, background rgba(255,255,255,.2)

快捷问题胶囊:
  background: --cream-2 (#F2EFE8)
  border: 1px solid rgba(26,23,20,.1)
  border-radius: r-full
  padding: 7px 13px
  font-size: 12px, font-weight: 500, color: --text-2
```

### 6.5 Sheet Handle

```
width: 36px
height: 4px
background: #E0DCD6
border-radius: 2px
margin: 12px auto 18px
```

### 6.6 分析页扫描线

```
position: absolute
left: 8px, right: 8px
height: 1px
background: linear-gradient(90deg, transparent, #C4532A, transparent)
animation: 2s ease-in-out infinite
运动范围: top 15% → 85%
```

### 6.7 对话产品 Chip

```
background: var(--tX-bg)（当前产品等级）
border-radius: r-full
padding: 5px 12px 5px 8px
内部圆点: 8×8px, background: var(--tX-dot)
文字: font-size 12px, font-weight 600, color: var(--tX-text)
```

---

## 7. 页面结构规范

### 7.1 Status Bar

```
padding-top: 14px
padding-left/right: 28px
font-size: 12px, font-weight: 700
颜色跟随页面主色调（亮色页面用 --text，深色页面用 rgba(255,255,255,.4)，Verdict Zone 用 --tX-text）
```

### 7.2 页面导航

当前产品无底部 Tab Bar（单一主流程），导航通过以下方式完成：

| 入口 | 跳转目标 |
|------|---------|
| 首页 CTA 卡片 | → 相机/拍照页 |
| 首页历史列表项 | → 对应结果页 |
| 结果页「深入问问 AI」| → 对话页（携带产品上下文） |
| 对话页 ← 返回 | → 结果页 |
| 结果页 ← 返回 | → 首页 |

### 7.3 底部安全区（iOS）

所有底部固定元素（Chat Bar、输入栏）额外 padding-bottom `28px`，避免被 iOS Home Indicator 遮挡。

---

## 8. 状态规范

### 8.1 空状态（首页无历史记录）

```
图标: 相机图标（outline 风格）
标题: "还没有分析记录"（text-headline，颜色 --text-2）
描述: "拍一张配料表，开始你的第一次分析"（text-sm，颜色 --text-3）
按钮: 与 CTA 卡片样式一致，但宽度自适应居中
```

### 8.2 错误状态

| 场景 | 处理方式 |
|------|---------|
| 照片识别失败 | Toast 提示「未能识别配料表，请确保照片清晰」，保留重拍按钮 |
| 网络错误 | 内联错误提示（非 Toast），提供重试按钮 |
| AI 分析超时 | 分析页显示「分析时间较长，请稍候…」，超过 30s 提供取消选项 |
| 对话响应失败 | 气泡内显示「回复失败，点击重试」，颜色 `--text-3` |

### 8.3 加载状态

**分析进行中：** 使用深色分析页 + 扫描线动画（见 6.6），不使用通用 Spinner。

**对话回复中：** AI 气泡内显示三点跳动动画：
```css
三个圆点: width 6px, height 6px, border-radius 50%, background rgba(255,255,255,.6)
动画: 交替 opacity 0.3 → 1，stagger 150ms
```

### 8.4 按压状态（Pressed）

```
所有可点击元素: scale(0.97), transition 100ms ease-out
CTA 卡片:       background 变深至 --brand-dark (#A34222)
快捷问题胶囊:   background 变为 --cream (#FAF8F3)
列表项:         background rgba(26,23,20,0.04)
```

---

## 9. 文案规范（法律合规）

### 9.1 禁用表达

以下表达**禁止出现**（存在法律风险）：

| 禁用 | 替换 |
|------|------|
| 放心吃 / 可以放心食用 | 成分较优 / 整体合规 |
| 不安全 / 有害 | 多处值得关注 / 存在风险成分 |
| 一定会导致 | 部分研究提示可能 |
| 适合 XXX 人群食用 | 供 XXX 人群参考 |
| 推荐购买 / 不建议购买 | 可参考购买 / 建议进一步了解 |

### 9.2 必须出现的声明

**AI 气泡底部：**
```
AI 生成 · 仅供参考 · 请遵医嘱
font-size: 10px, color: --text-3
```

**结果页底部：**
```
本内容仅供参考，不构成任何医疗、营养或食品安全方面的专业建议。
分析基于包装配料表信息，实际健康影响因个人情况而异。
font-size: 11px, color: --text-3, line-height: 1.65
```

---

## 10. 动效规范

| 场景 | Duration | Easing |
|------|----------|--------|
| 页面切换 | 300ms | ease-in-out |
| Sheet 弹出 | 380ms | cubic-bezier(0.32, 0.72, 0, 1) |
| 按压反馈 (scale) | 100ms enter / 150ms exit | ease-out |
| 快捷标签横滑 | 原生惯性滚动 | — |
| 扫描线循环 | 2000ms | ease-in-out |
| AI 三点加载 | 600ms/循环 | ease-in-out |

**禁止：**
- 超过 400ms 的 UI 动画
- 使用 width/height 做过渡（改用 transform/opacity）
- 无意义的装饰性动画

---

## 11. 尚未设计的页面（待补充）

以下页面尚未完成设计，开发前需补全：

- [ ] **相机/拍照页** — 实际相机取景界面，非分析中页
- [ ] **我的页面** — 设置、账户信息
- [ ] **首页空状态** — 无历史记录时的引导
- [ ] **错误页** — 分析彻底失败、网络断开
- [ ] **首次引导** — 新用户第一次打开的引导流程

---

## 12. 决策日志

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-03-30 | 品牌色定为陶土橙 #C4532A | 与竞品绿色系完全差异化，在健康类应用中独特 |
| 2026-03-30 | 放弃暗色模式 | 聚焦核心流程，暗色模式增加复杂度但不提升核心体验 |
| 2026-03-30 | 结果页顶部整块用风险色作背景 | 让用户第一眼通过颜色就能判断风险等级，无需阅读文字 |
| 2026-03-30 | 对话入口放在结果页底部固定栏 | 不打断阅读流程，用户看完详情自然看到入口 |
| 2026-03-30 | 分析中使用深色背景 | 与白色首页/结果页形成对比，增加仪式感和等待期的沉浸感 |
| 2026-03-30 | 禁用"放心吃"等直接表达 | 规避食品安全相关法律风险 |
| 2026-03-30 | 风险色从绿/琥珀/橙/红重新设计 | 与品牌色（陶土橙）区分，确保语义清晰 |
