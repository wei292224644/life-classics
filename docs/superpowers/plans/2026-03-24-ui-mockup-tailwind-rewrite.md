# UI Mockup Tailwind 重写实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `web/ui/` 下三个设计稿 HTML 全部重写为 Tailwind CDN + 统一 config token + 设计系统颜色规范，并修正 03 文件宽度至 375px。

**Architecture:** 每个文件在 `<style>` 中定义 `.light-mode` / `.dark-mode` 作用域的 CSS 变量，Tailwind CDN config 通过 `var(--token)` 引用这些变量，从而一套 utility class 在两种模式下自动切换颜色。复杂的组件级颜色（风险分组背景、ingredient-detail Header）使用 Tailwind 任意值语法 `bg-[...]`。

**Tech Stack:** Tailwind CSS CDN v3，Google Fonts (DM Sans)，纯 HTML/CSS/JS

---

## 共享 Tailwind Config + CSS 变量模板

以下模板在三个文件中完全一致，必须逐字复制（不要自行发挥）：

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        'bg-base':           'var(--bg-base)',
        'bg-card':           'var(--bg-card)',
        'bg-card-hover':     'var(--bg-card-hover)',
        'text-primary':      'var(--text-primary)',
        'text-secondary':    'var(--text-secondary)',
        'text-muted':        'var(--text-muted)',
        'border-c':          'var(--border-color)',
        'accent-pink':       'var(--accent-pink)',
        'accent-pink-light': 'var(--accent-pink-light)',
        'risk-t4':           'var(--risk-t4)',
        'risk-t3':           'var(--risk-t3)',
        'risk-t2':           'var(--risk-t2)',
        'risk-t1':           'var(--risk-t1)',
        'risk-t0':           'var(--risk-t0)',
        'risk-unknown':      'var(--risk-unknown)',
      },
      fontFamily: {
        sans: ['DM Sans', '-apple-system', 'sans-serif'],
      },
    }
  }
}
</script>
```

```css
/* 在每个文件 <style> 中定义 */
.light-mode {
  --bg-base: #f5f5f5;
  --bg-card: #ffffff;
  --bg-card-hover: #f9fafb;
  --text-primary: #111;
  --text-secondary: #4b5563;
  --text-muted: #9ca3af;
  --border-color: rgba(0,0,0,0.06);
  --accent-pink: #db2777;
  --accent-pink-light: #ec4899;
  --risk-t4: #dc2626;
  --risk-t3: #ea580c;
  --risk-t2: #ca8a04;
  --risk-t1: #16a34a;
  --risk-t0: #059669;
  --risk-unknown: #9ca3af;
}
.dark-mode {
  --bg-base: #0f0f0f;
  --bg-card: #1a1a1a;
  --bg-card-hover: #222222;
  --text-primary: #f5f5f5;
  --text-secondary: #a1a1a1;
  --text-muted: #6b7280;
  --border-color: rgba(255,255,255,0.08);
  --accent-pink: #ec4899;
  --accent-pink-light: #f472b6;
  --risk-t4: #ef4444;
  --risk-t3: #f97316;
  --risk-t2: #eab308;
  --risk-t1: #86efac;
  --risk-t0: #22c55e;
  --risk-unknown: #9ca3af;
}
```

**Tailwind class 用法规范：**

| 场景 | class |
|------|-------|
| 页面背景 | `bg-bg-base` |
| 卡片背景 | `bg-bg-card` |
| 主文字 | `text-text-primary` |
| 次要文字 | `text-text-secondary` |
| 辅助文字 | `text-text-muted` |
| 描边 | `border border-border-c` |
| 强调粉色 | `text-accent-pink` / `bg-accent-pink` |
| 风险色 | `text-risk-t4` / `bg-risk-t4` |
| 风险半透明背景 | `bg-risk-t4/10` |

---

## 文件结构

| 文件 | 操作 | 内容 |
|------|------|------|
| `web/ui/01-index.html` | 重写 | 首页（扫码 + 最近扫描 + TabBar），已有 Tailwind，颜色替换为 token |
| `web/ui/02-product-detail.html` | 重写 | 产品详情页（Header + Banner + 营养卡 + 配料区 + 健康益处 + 底部栏） |
| `web/ui/03-ingredient-detail.html` | 重写 | 配料详情页（Header + Hero卡 + 5个 Section + 底部栏），修正宽度为 375px |

---

## Task 1：重写 01-index.html（首页）

**Files:**
- Modify: `web/ui/01-index.html`

**页面内容（保持不变，仅更新颜色实现）：**
- 页面外框：白色页面标题 + 亮色/暗色两个手机并排
- 手机壳：`width: 399px`（含 12px padding）→ 内部屏幕 375px
- 屏幕高度：812px
- Light 手机内容：白色背景扫码首页
- Dark 手机内容：深色背景扫码首页

**关键结构：**
```
body (flex, align-center, gap-10)
  页面标题 h1 + 副标题
  phones-row (flex gap-10)
    phone-col × 2 (light/dark)
      mode-badge
      phone-shell (399px)
        phone-notch
        phone-screen (overflow:hidden, h-[812px])
          [模式容器 .light-mode / .dark-mode]
            Hero区 (app标题 + 扫一扫按钮)
            分隔线 + "最近扫描"标题
            扫描历史列表 (3条)
            TabBar (fixed bottom)
```

- [ ] **Step 1：替换文件**

  完整重写 `web/ui/01-index.html`，要求：
  1. `<head>` 引入 Tailwind CDN + config（见共享模板），引入 DM Sans
  2. `<style>` 定义 `.light-mode` / `.dark-mode` CSS 变量（见共享模板）
  3. 补充动画：
     ```css
     @keyframes pulse-ring {
       0%   { transform: scale(1); opacity: 0.6; }
       70%  { transform: scale(1.15); opacity: 0; }
       100% { transform: scale(1.15); opacity: 0; }
     }
     .animate-pulse-ring { animation: pulse-ring 2s ease-out infinite; }
     ```
  4. 手机壳 CSS（非 Tailwind，保留 class 写法）：
     ```css
     .phone-shell { background:#141414; border-radius:52px; padding:12px; width:399px;
       box-shadow: 0 0 0 1px #2a2a2a, 0 32px 64px rgba(0,0,0,0.7), inset 0 0 0 2px #1a1a1a; }
     .phone-notch { background:#141414; width:90px; height:22px; border-radius:0 0 16px 16px;
       margin:0 auto -5px; position:relative; z-index:2; }
     .phone-screen { border-radius:40px; overflow:hidden; height:812px;
       scrollbar-width:none; position:relative; }
     .phone-screen::-webkit-scrollbar { display:none; }
     ```
  5. 亮色模式内容（`.light-mode`，Tailwind class）：
     - 页面：`min-h-screen bg-bg-base flex flex-col pb-20`
     - Hero区：`bg-bg-card px-6 pt-10 pb-8 flex flex-col items-center border-b border-border-c`
       - App标题行：`🍎` emoji + `text-[17px] font-bold text-text-primary tracking-tight`
       - 副标题：`text-xs text-text-muted mb-7`
       - 扫码按钮：`w-[140px] h-[140px] rounded-full bg-gradient-to-br from-accent-pink-light to-accent-pink flex flex-col items-center justify-center gap-1.5 relative shadow-lg shadow-accent-pink/30`，含 `animate-pulse-ring` 边框
     - 分隔线：`flex items-center gap-3 px-6 pt-6 pb-3`，含"最近扫描"标签（`text-[11px] font-semibold text-text-muted uppercase tracking-widest`）+ 数量徽章（`bg-risk-t4/10 text-risk-t4 text-[10px] font-bold px-1.5 py-0.5 rounded-full`）
     - 列表区：`px-6 pb-10 flex flex-col gap-2`
       - 每条：`bg-bg-card border border-border-c rounded-xl px-4 py-3.5 flex items-center gap-3`
         - 图标：`w-10 h-10 rounded-lg bg-bg-base border border-border-c flex items-center justify-center text-xl`
         - 名称：`text-sm font-semibold text-text-primary mb-0.5 truncate`
         - 时间：`text-xs text-text-muted`
         - 箭头：`w-4 h-4 text-text-muted`
     - TabBar：`absolute bottom-0 left-0 right-0 h-20 bg-bg-card border-t border-border-c flex justify-around items-start pt-2 px-2`，`padding-bottom: calc(8px + env(safe-area-inset-bottom))`
       - 激活 tab：图标 `fill` = `var(--accent-pink)`，文字 `text-accent-pink`
       - 非激活 tab：图标/文字 `text-text-muted`
  6. 暗色模式内容（`.dark-mode`）：结构同亮色，所有颜色 class 相同（CSS变量自动切换）；TabBar 额外加 `backdrop-blur-xl`
  7. 亮色/暗色手机外的 mode badge：
     ```css
     .mode-badge { font-size:12px; font-weight:600; padding:4px 14px; border-radius:20px; letter-spacing:0.02em; }
     .mode-light { background:#f3f4f6; color:#374151; }
     .mode-dark  { background:#1f2937; color:#9ca3af; }
     ```

- [ ] **Step 2：浏览器验证**

  在浏览器打开 `web/ui/01-index.html`，检查：
  - [ ] 两个手机并排显示
  - [ ] 扫码按钮粉色渐变 + 脉冲动画
  - [ ] 亮色手机背景 `#f5f5f5`，暗色 `#0f0f0f`（非 zinc 近似色）
  - [ ] TabBar 激活项为 `--accent-pink` 颜色

- [ ] **Step 3：提交**

  ```bash
  git add web/ui/01-index.html
  git commit -m "refactor(ui): rewrite 01-index with Tailwind config tokens and design system colors"
  ```

---

## Task 2：重写 02-product-detail.html（产品详情页）

**Files:**
- Modify: `web/ui/02-product-detail.html`

**页面区域清单（按布局顺序）：**

| 区域 | 要素 |
|------|------|
| 外框 | body 居中 + 标题 + 两手机并排 |
| phone | 375px × 812px，overflow hidden |
| status-bar | 44px，显示时间"9:41" |
| header | fixed，透明→毛玻璃，返回+标题+分享按钮 |
| scroll-area | absolute top-[44px] bottom-[88px]，overflow-y auto |
| banner | 260px，emoji+label+右下角风险徽章 |
| content | px-5 pt-6 pb-10 |
| ├ 营养成分 section | section-title + nutrition-card |
| ├ 配料信息 section | section-title + 4个风险分组（t4/t3/t0/unknown）|
| ├ 健康益处 section | section-title + 健康卡片 |
| └ 食用建议 section | section-title + 建议卡片 |
| bottom-bar | fixed bottom，两按钮 |

**风险分组颜色（用任意值，不进config）：**

```
暗色 t4: bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.15)]
暗色 t3: bg-[rgba(249,115,22,0.08)] border-[rgba(249,115,22,0.15)]
暗色 t0: bg-[rgba(34,197,94,0.08)] border-[rgba(34,197,94,0.15)]
暗色 unknown: bg-[rgba(156,163,175,0.08)] border-[rgba(156,163,175,0.15)]

亮色 t4: bg-[#fee2e2] border-[rgba(252,165,165,0.3)]
亮色 t3: bg-[#ffedd5] border-[rgba(252,196,110,0.4)]
亮色 t0: bg-[#dcfce7] border-[rgba(187,247,208,0.5)]
亮色 unknown: bg-[#e5e7eb] border-[rgba(209,213,219,0.5)]
```

由于亮/暗配色不同，风险分组用独立的 `.dark-mode .t4` / `.light-mode .t4` CSS class（写在 `<style>` 中），而非 Tailwind class。

- [ ] **Step 1：重写文件**

  完整重写 `web/ui/02-product-detail.html`：
  1. `<head>`：Tailwind CDN + config（共享模板），DM Sans
  2. `<style>`：
     - `.light-mode` / `.dark-mode` CSS 变量（共享模板）
     - 手机壳 CSS（同 Task 1）
     - 动画（`slideUp`，`floatIn`，`slideUpBadge`）：
       ```css
       @keyframes slideUp {
         from { opacity: 0; transform: translateY(16px); }
         to   { opacity: 1; transform: translateY(0); }
       }
       @keyframes floatIn {
         from { opacity: 0; transform: scale(0.8); }
         to   { opacity: 1; transform: scale(1); }
       }
       @keyframes slideUpBadge {
         from { opacity: 0; transform: translateY(10px); }
         to   { opacity: 1; transform: translateY(0); }
       }
       @media (prefers-reduced-motion: reduce) {
         *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
       }
       ```
     - 风险分组背景色（独立 class，见上方色值表）
     - Header scrolled 状态阴影：
       ```css
       .dark-mode .header-scrolled { box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.06); }
       .light-mode .header-scrolled { box-shadow: 0 4px 24px rgba(0,0,0,0.08), 0 1px 0 rgba(0,0,0,0.04); }
       ```
     - `* { -webkit-tap-highlight-color: rgba(0,0,0,0); }`
     - `body { touch-action: manipulation; }`

  3. 亮色+暗色手机内容（两个手机共用 Tailwind class，颜色 token 自动切换）：

     **Status bar：**
     `h-11 flex items-center justify-center relative z-50`
     - 文字：`text-sm font-semibold tracking-wide text-text-primary`
     - 亮色额外：`bg-bg-card border-b border-border-c`

     **Header（position:absolute，Tailwind 处理不了 fixed inside overflow:hidden，用 sticky/absolute 替代）：**
     - 容器：`absolute top-0 left-0 right-0 z-50 px-4 py-2 flex items-center gap-3 transition-all duration-300`
     - 按钮（返回/分享）：`w-10 h-10 rounded-xl flex items-center justify-center border-none bg-transparent`
     - 标题：`flex-1 text-[17px] font-semibold tracking-tight text-text-primary`
     - 滚动后通过 JS 添加 `.header-scrolled` class，并加 `backdrop-blur` + `bg-bg-card/90`

     **Banner（260px）：**
     - 暗色：`bg-[linear-gradient(145deg,#1a1a1a_0%,#0d0d0d_50%,#151515_100%)]`
     - 亮色：`bg-[linear-gradient(145deg,#fef3c7_0%,#fde68a_50%,#fcd34d_100%)]`
     - Emoji：`text-[80px]`，`animation: floatIn 0.8s cubic-bezier(0.34,1.56,0.64,1) forwards`
     - 风险徽章（右下角）：`absolute right-5 bottom-5 rounded-2xl px-4 py-2.5 flex items-center gap-2 backdrop-blur-md`，`animation: slideUpBadge 0.6s 0.2s ...`

     **Section title：** `text-[20px] font-bold tracking-tight text-text-primary mb-3.5`

     **营养卡片（border-radius:24px）：**
     - 容器：`rounded-3xl p-5 mb-7 relative overflow-hidden border border-[rgba(34,197,94,0.1)] bg-[rgba(34,197,94,0.06)]`
     - 顶部发光线（伪元素）：CSS 处理
     - 数值：`text-[32px] font-bold tracking-[-0.03em] font-variant-numeric: tabular-nums text-text-primary`
     - 标签：`text-[11px] uppercase tracking-[0.08em] text-text-muted`
     - 展开按钮：`aria-expanded` + `aria-controls`

     **风险分组（`.risk-group.t4` 等）：**
     - 用 `<style>` 中的背景色 class
     - 圆角：`rounded-[20px]`，padding：`p-4`，margin-bottom：`mb-3`
     - 风险点（8px圆）：暗色加 `box-shadow: 0 0 8px var(--risk-tN)`（CSS写）
     - 横向滚动配料卡片：`flex gap-2.5 overflow-x-auto pb-1 snap-x snap-mandatory`，无滚动条
     - 配料卡（min-w-[140px]）：`rounded-2xl p-3.5 relative overflow-hidden snap-start cursor-pointer`
       - 左侧风险条：`absolute left-0 top-0 bottom-0 w-[3px] bg-risk-t4`（暗色加 glow，CSS写）

     **健康益处卡片 / 食用建议卡片：**
     - 暗色：`bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)] rounded-[20px] p-5`
     - 亮色：`bg-bg-card border border-border-c rounded-[20px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.04)]`
     - 由于亮/暗不同，用 `<style>` 中的独立 class：
       ```css
       .dark-mode .health-card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); }
       .light-mode .health-card { background: #ffffff; border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
       ```

     **Bottom bar（position:sticky 在 scroll-area 外，fixed inside phone）：**
     - `absolute bottom-0 left-0 right-0 z-40 px-5 py-4 flex gap-3 backdrop-blur-xl`
     - 暗色：`bg-[rgba(15,15,15,0.95)] border-t border-border-c`
     - 亮色：`bg-[rgba(255,255,255,0.95)] border-t border-border-c`
     - 主按钮：`flex-1 rounded-xl py-3.5 text-sm font-semibold text-white bg-gradient-to-br from-accent-pink-light to-accent-pink shadow-[0_4px_20px_rgba(236,72,153,0.3)]`
     - 次按钮：`flex-1 rounded-xl py-3.5 text-sm font-semibold text-text-primary bg-bg-card border border-border-c`

  4. 添加简单 JS 实现 header 滚动效果和营养卡展开：
     ```javascript
     // Header scroll effect
     document.querySelectorAll('.scroll-area').forEach(area => {
       const header = area.closest('.phone').querySelector('.phone-header');
       area.addEventListener('scroll', () => {
         header.classList.toggle('header-scrolled', area.scrollTop > 60);
       });
     });
     // Nutrition toggle
     document.querySelectorAll('.nutrition-toggle').forEach(btn => {
       btn.addEventListener('click', () => {
         const details = btn.closest('.nutrition-card').querySelector('.nutrition-details');
         const expanded = btn.getAttribute('aria-expanded') === 'true';
         btn.setAttribute('aria-expanded', !expanded);
         btn.classList.toggle('expanded');
         details.classList.toggle('show');
       });
     });
     ```

- [ ] **Step 2：浏览器验证**

  打开 `web/ui/02-product-detail.html`，检查：
  - [ ] 两个手机并排，375px 宽
  - [ ] Banner 260px 高，emoji 有 floatIn 动画
  - [ ] 风险分组背景色正确（t4 红色调，t3 橙色调，t0 绿色调）
  - [ ] 亮色模式背景 `#f5f5f5`，暗色 `#0f0f0f`
  - [ ] 点击营养卡"展开"按钮可展开/收起
  - [ ] 主按钮粉色渐变正确

- [ ] **Step 3：提交**

  ```bash
  git add web/ui/02-product-detail.html
  git commit -m "refactor(ui): rewrite 02-product-detail with Tailwind config tokens and design system colors"
  ```

---

## Task 3：重写 03-ingredient-detail.html（配料详情页）

**Files:**
- Modify: `web/ui/03-ingredient-detail.html`

**关键修正：**
- 手机壳宽度：**290px → 399px**（内容区 375px）
- 屏幕高度：**620px → 812px**
- 字体：**`-apple-system, Inter` → DM Sans**
- 颜色：**oklch 变量 → 设计系统 CSS 变量**

**页面区域清单：**

| 区域 | 要素 |
|------|------|
| Header | 风险色背景 + 返回按钮 + 标题/副标题 + 分享按钮 |
| Hero 卡片 | 成分名 + 风险徽章 + 风险谱条 + chips |
| 描述 section | 文字描述 |
| AI 风险分析 section | 风险列表（×4条） |
| 风险管理信息 section | KV 表格（×6条） |
| AI 使用建议 section | 建议列表（×4条） |
| 含此配料的产品 section | 横向滚动卡片（×4张） |
| Bottom bar | 两按钮 |

**ingredient-detail Header 颜色（"high"风险，section 2.5）：**

写在 `<style>` 中（非 Tailwind）：
```css
.dark-mode .ing-hdr { background: #1a0808; border-bottom: 2px solid #7f1d1d; }
.light-mode .ing-hdr { background: #fff4f0; border-bottom: 2px solid #fecaca; }
.dark-mode .ing-hdr-title { color: #fca5a5; }
.light-mode .ing-hdr-title { color: #7f1d1d; }
.dark-mode .ing-hdr-sub { color: #f87171; }
.light-mode .ing-hdr-sub { color: #ef4444; }
.dark-mode .ing-hdr-btn { background: rgba(248,113,113,0.15); }
.light-mode .ing-hdr-btn { background: rgba(220,38,38,0.1); }
```

**Section 卡片（亮/暗不同，CSS class）：**
```css
.dark-mode .sec-card { background: #1a1a1a; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; overflow: hidden; }
.light-mode .sec-card { background: #ffffff; border: 1px solid rgba(0,0,0,0.06); border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
```

**AI 标签渐变（非 Tailwind）：**
```css
.ai-label { font-size: 9.5px; font-weight: 700; background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
```

- [ ] **Step 1：重写文件**

  完整重写 `web/ui/03-ingredient-detail.html`：
  1. `<head>`：Tailwind CDN + config（共享模板），DM Sans
  2. `<style>`：
     - `.light-mode` / `.dark-mode` CSS 变量（共享模板）
     - 手机壳 CSS（同 Task 1，**width: 399px**）
     - 上方所有独立 CSS class（`.ing-hdr`、`.sec-card`、`.ai-label` 等）
     - 底部栏背景（亮/暗不同，同 Task 2 模式）
  3. 页面外框：`body` 居中 + 标题"配料详情 · 最终设计稿" + 副标题 + 两手机并排

  4. 手机内容（亮/暗共用 Tailwind class）：

     **Header（`.ing-hdr`，sticky top-0 z-10）：**
     - 结构：`flex items-center gap-2.5 px-3.5 py-3`
     - 按钮（`.ing-hdr-btn`）：`w-[30px] h-[30px] rounded-[9px] flex items-center justify-center flex-shrink-0`
     - 按钮内 SVG：stroke 颜色 = 对应风险色（`var(--risk-t3)` = high 风险）
     - 标题区：`flex-1 flex flex-col`
       - 标题：`.ing-hdr-title`，`text-sm font-bold`
       - 副标题：`.ing-hdr-sub`，`text-[10px] font-semibold mt-px`
     - 分享按钮：同返回按钮样式

     **内容区：`p-3 flex flex-col gap-3`**

     **Hero 卡片（`.sec-card`）：**
     - 顶部区（背景来自 CSS var，因 risk 等级而定）：
       ```css
       .dark-mode .hero-top { background: linear-gradient(135deg, rgba(26,8,8,0.6) 0%, transparent 100%); border-bottom: 1px solid #7f1d1d; }
       .light-mode .hero-top { background: linear-gradient(135deg, rgba(255,244,240,0.6) 0%, transparent 100%); border-bottom: 1px solid #fecaca; }
       ```
     - 成分名：`text-[18px] font-extrabold text-text-primary`
     - 编码：`text-[11px] text-text-muted mt-0.5`
     - 风险徽章：`inline-flex items-center gap-1 bg-risk-t3 text-white px-[9px] py-1 rounded-[7px] text-[11px] font-bold flex-shrink-0`
     - 谱条（8px 高，固定渐变）：
       ```
       bg-[linear-gradient(to_right,#22c55e_0%,#86efac_20%,#facc15_45%,#fb923c_65%,#ef4444_82%,#dc2626_100%)]
       rounded-full h-[7px] relative
       ```
     - 指示针（高风险 left 72%）：`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-bg-card border-[2.5px] border-risk-t3`，`left: 72%`
     - Chips 区：`flex flex-wrap gap-[5px] p-3`
       - 功能 chip（红）：`bg-risk-t4/10 text-risk-t4 border border-risk-t4/20 px-2 py-0.5 rounded-md text-[10.5px] font-medium`
       - 警告 chip（黄）：`bg-risk-t2/10 text-risk-t2 border border-risk-t2/20 px-2 py-0.5 rounded-md text-[10.5px] font-medium`
       - 中性 chip：`bg-bg-base text-text-secondary px-2 py-0.5 rounded-md text-[10.5px] font-medium`

     **Section 卡片（`.sec-card`）统一结构：**
     - Header行：`flex items-center gap-2 px-3 py-[11px] border-b border-border-c`
       - 图标框：`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0`
       - 标题：`text-[13px] font-bold text-text-primary`
       - AI标签（可选）：`.ai-label ml-auto`
     - 内容区：`px-3 py-[9px]`

     **描述 section：** `text-xs text-text-secondary leading-[1.7]`

     **AI 风险分析：** 列表项 flex，图标框 `w-[18px] h-[18px] rounded-[5px] bg-risk-t4/10 flex items-center justify-center`，文字 `text-xs text-text-primary leading-[1.55]`

     **KV 表格：** `flex justify-between items-start py-[9px] gap-2.5`，边框用 `border-t border-border-c`，key `text-[11.5px] text-text-secondary`，value `text-[11.5px] font-medium text-text-primary text-right`，危险值 `text-risk-t4`

     **建议列表：** 正面建议图标框 `bg-risk-t0/10`，图标 `text-risk-t0`；条件建议图标框 `bg-risk-t2/10`，图标 `text-risk-t2`

     **含此配料的产品：** 横向滚动 `overflow-x-auto scrollbar-none`，卡片 `w-[86px] flex-shrink-0 bg-bg-base border border-border-c rounded-xl p-2`，图示区 `w-full h-12 rounded-lg bg-bg-card flex items-center justify-center text-xl mb-1.5`

     **Bottom bar：**
     - `sticky bottom-0 border-t border-border-c px-3 py-[9px] flex gap-2`
     - 暗色/亮色背景：CSS class（同 Task 2 bottombar 写法）
     - 次按钮：`flex-1 border border-border-c bg-transparent rounded-xl py-[9px] text-xs font-semibold text-text-primary text-center`
     - 主按钮：`flex-1 rounded-xl py-[9px] text-xs font-semibold text-white text-center bg-gradient-to-br from-accent-pink-light to-accent-pink shadow-[0_4px_12px_rgba(225,29,72,0.3)]`

- [ ] **Step 2：浏览器验证**

  打开 `web/ui/03-ingredient-detail.html`，检查：
  - [ ] 手机宽度 375px（外壳 399px）
  - [ ] 屏幕高度 812px，可上下滚动
  - [ ] Header 有风险色背景（高风险 - 橙红色调）
  - [ ] 风险谱条 + 指示针位置正确（high = 72%）
  - [ ] Section 卡片颜色使用设计系统 token
  - [ ] 字体为 DM Sans（非 Inter）

- [ ] **Step 3：提交**

  ```bash
  git add web/ui/03-ingredient-detail.html
  git commit -m "refactor(ui): rewrite 03-ingredient-detail with Tailwind config tokens, 375px width, design system colors"
  ```

---

## 最终验收清单

所有三个文件均满足：

- [ ] `<script src="https://cdn.tailwindcss.com"></script>` 且 `tailwind.config` 包含完整 token 映射
- [ ] `.light-mode` / `.dark-mode` CSS 变量值与 `web/2026-design-system.md` 完全一致
- [ ] 手机宽度 375px（外壳 399px），屏幕高度 812px
- [ ] 字体 DM Sans（Google Fonts）
- [ ] 亮色 `--bg-base: #f5f5f5`，暗色 `--bg-base: #0f0f0f`（不是 zinc 近似值）
- [ ] 强调色 `--accent-pink` 亮色 `#db2777`，暗色 `#ec4899`
- [ ] 无 oklch() 色值，无 zinc-*/sky-* 等内置 Tailwind 色阶直接使用（粉色按钮除外，需通过 token）
