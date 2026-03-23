# 配料详情页 (ingredient-detail) 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建 `pages/ingredient-detail/index.vue` 页面，实现风险色调 Header + Hero 风险卡 + AI 分析内容区 + 相关产品区 + 底部操作栏，替换现有旧版 `ingredient-detail.html` 设计。

**Architecture:** 数据通过 Pinia `ingredientStore` 传递（从产品详情页点击配料卡时存入，无需额外请求）；风险等级映射逻辑集中在 `utils/riskLevel.ts` 纯工具函数中；页面使用组件级 inline CSS vars 实现风险色调 Header，不污染全局变量；暗色模式通过 `uni.getSystemInfoSync().theme` 初始化 + `uni.onThemeChange()` 监听运行时切换。

**Tech Stack:** UniApp + Vue 3 `<script setup>` + Pinia (Composition API) + SCSS + CSS custom properties

> **注意：** 本项目前端无 Vitest 测试基础设施（`vite.config.ts` 中无配置）。测试步骤为在 H5 开发服务器（端口 5174）手动验证。

---

## 文件清单

| 操作 | 路径 | 职责 |
|------|------|------|
| 修改 | `web/apps/uniapp/src/styles/design-system.scss` | 添加 `--risk-t1` 变量（亮/暗色） |
| 新建 | `web/apps/uniapp/src/utils/riskLevel.ts` | 风险等级映射纯工具函数 |
| 新建 | `web/apps/uniapp/src/store/ingredient.ts` | ingredient Pinia store |
| 修改 | `web/apps/uniapp/src/pages.json` | 注册 ingredient-detail 页面 |
| 新建 | `web/apps/uniapp/src/pages/ingredient-detail/index.vue` | 配料详情页主体 |
| 修改 | `web/apps/uniapp/src/components/IngredientSection.vue` | 更新导航逻辑 + 支持 t1 级别 |

---

## Task 1：补全 design-system.scss 中的 `--risk-t1` 变量

**Files:**
- Modify: `web/apps/uniapp/src/styles/design-system.scss:56-60`（亮色 Risk colors 区域）
- Modify: `web/apps/uniapp/src/styles/design-system.scss:126-130`（暗色 Risk colors 区域）
- Modify: `web/apps/uniapp/src/styles/design-system.scss:88-98`（亮色 Risk group backgrounds 区域）
- Modify: `web/apps/uniapp/src/styles/design-system.scss:158-168`（暗色 Risk group backgrounds 区域）

- [ ] **Step 1: 在亮色 `page {}` 的 Risk colors 区块中添加 `--risk-t1`**

  在 `--risk-t2: #ca8a04;` 和 `--risk-t0: #16a34a;` 之间插入：
  ```scss
  --risk-t1: #22c55e;
  ```

- [ ] **Step 2: 在暗色 `.dark-mode {}` 的 Risk colors 区块中添加 `--risk-t1`**

  在 `--risk-t2: #eab308;` 和 `--risk-t0: #22c55e;` 之间插入：
  ```scss
  --risk-t1: #4ade80;
  ```

- [ ] **Step 3: 在亮色 Risk group backgrounds 中添加 `--risk-t1-bg` 和 `--risk-t1-border`**

  在 `--risk-t2-border: rgba(250, 240, 137, 0.4);` 和 `--risk-t0-bg: rgba(220, 252, 231);` 之间插入：
  ```scss
  --risk-t1-bg: rgba(220, 252, 231);
  --risk-t1-border: rgba(134, 239, 172, 0.5);
  ```

- [ ] **Step 4: 在暗色 Risk group backgrounds 中添加 `--risk-t1-bg` 和 `--risk-t1-border`**

  在 `--risk-t2-border: rgba(234, 179, 8, 0.15);` 和 `--risk-t0-bg: rgba(34, 197, 94, 0.08);` 之间插入：
  ```scss
  --risk-t1-bg: rgba(74, 222, 128, 0.08);
  --risk-t1-border: rgba(74, 222, 128, 0.15);
  ```

- [ ] **Step 5: 在 H5 开发服务器验证变量注入**

  ```bash
  cd web && pnpm dev:uniapp:h5
  ```
  打开浏览器 DevTools，在 `page` 元素上确认存在 `--risk-t1: #22c55e`。

- [ ] **Step 6: 提交**

  ```bash
  git add web/apps/uniapp/src/styles/design-system.scss
  git commit -m "feat(design-system): add --risk-t1 and risk-t1 group bg/border variables"
  ```

---

## Task 2：创建 `utils/riskLevel.ts` 风险等级映射工具

**Files:**
- Create: `web/apps/uniapp/src/utils/riskLevel.ts`

- [ ] **Step 1: 创建文件，内容如下**

  ```typescript
  // web/apps/uniapp/src/utils/riskLevel.ts
  // 纯函数，无副作用，无外部依赖

  export type RiskLevel = "t4" | "t3" | "t2" | "t1" | "t0" | "unknown"
  export type VisualKey = "critical" | "high" | "medium" | "low" | "safe" | "unknown"

  export interface RiskLevelConfig {
    /** 风险徽章文案 */
    badge: string
    /** 风险徽章图标（Unicode） */
    icon: string
    /** 无产品上下文时 Header 副标题 */
    subtitleNoProduct: string
    /**
     * 风险谱条指示针 left% 值（针中心点）
     * null 表示隐藏针（unknown 状态）
     */
    needleLeft: string | null
    /** 亮色 Header 背景色 */
    headerBgLight: string
    /** 亮色 Header 边框色 */
    headerBorderLight: string
    /** 亮色 Header 标题色 */
    headerTitleLight: string
    /** 亮色 Header 副标题色 */
    headerSubLight: string
    /** 亮色 Header 按钮背景色 */
    headerBtnLight: string
    /** 暗色 Header 背景色 */
    headerBgDark: string
    /** 暗色 Header 边框色 */
    headerBorderDark: string
    /** 暗色 Header 标题色 */
    headerTitleDark: string
    /** 暗色 Header 副标题色 */
    headerSubDark: string
    /** 暗色 Header 按钮背景色 */
    headerBtnDark: string
    /** 风险徽章背景色（无需亮/暗区分） */
    badgeBg: string
  }

  export const RISK_CONFIG: Record<VisualKey, RiskLevelConfig> = {
    critical: {
      badge: "极高风险",
      icon: "⛔",
      subtitleNoProduct: "⛔ 极高风险 · 不建议摄入",
      needleLeft: "88%",
      headerBgLight: "#fff1f2",
      headerBorderLight: "#fca5a5",
      headerTitleLight: "#7f1d1d",
      headerSubLight: "#dc2626",
      headerBtnLight: "rgba(220,38,38,0.15)",
      headerBgDark: "#1a0505",
      headerBorderDark: "#991b1b",
      headerTitleDark: "#fecaca",
      headerSubDark: "#f87171",
      headerBtnDark: "rgba(248,113,113,0.2)",
      badgeBg: "#dc2626",
    },
    high: {
      badge: "高风险",
      icon: "⚠",
      subtitleNoProduct: "⚠ 高风险 · 谨慎摄入",
      needleLeft: "72%",
      headerBgLight: "#fff4f0",
      headerBorderLight: "#fecaca",
      headerTitleLight: "#7f1d1d",
      headerSubLight: "#ef4444",
      headerBtnLight: "rgba(220,38,38,0.1)",
      headerBgDark: "#1a0808",
      headerBorderDark: "#7f1d1d",
      headerTitleDark: "#fca5a5",
      headerSubDark: "#f87171",
      headerBtnDark: "rgba(248,113,113,0.15)",
      badgeBg: "#ef4444",
    },
    medium: {
      badge: "中等风险",
      icon: "⚠",
      subtitleNoProduct: "⚠ 中等风险 · 适量摄入",
      needleLeft: "50%",
      headerBgLight: "#fefce8",
      headerBorderLight: "#fde68a",
      headerTitleLight: "#713f12",
      headerSubLight: "#a16207",
      headerBtnLight: "rgba(202,138,4,0.1)",
      headerBgDark: "#1a1500",
      headerBorderDark: "#713f12",
      headerTitleDark: "#fde68a",
      headerSubDark: "#fbbf24",
      headerBtnDark: "rgba(251,191,36,0.15)",
      badgeBg: "#f59e0b",
    },
    low: {
      badge: "低风险",
      icon: "✓",
      subtitleNoProduct: "✓ 低风险",
      needleLeft: "22%",
      headerBgLight: "#f0fdf4",
      headerBorderLight: "#bbf7d0",
      headerTitleLight: "#14532d",
      headerSubLight: "#16a34a",
      headerBtnLight: "rgba(22,163,74,0.1)",
      headerBgDark: "#051a0a",
      headerBorderDark: "#14532d",
      headerTitleDark: "#86efac",
      headerSubDark: "#4ade80",
      headerBtnDark: "rgba(74,222,128,0.15)",
      badgeBg: "#22c55e",
    },
    safe: {
      badge: "安全",
      icon: "✓",
      subtitleNoProduct: "✓ 安全 · 天然成分",
      needleLeft: "8%",
      headerBgLight: "#ecfdf5",
      headerBorderLight: "#6ee7b7",
      headerTitleLight: "#065f46",
      headerSubLight: "#059669",
      headerBtnLight: "rgba(5,150,105,0.1)",
      headerBgDark: "#022c22",
      headerBorderDark: "#065f46",
      headerTitleDark: "#6ee7b7",
      headerSubDark: "#34d399",
      headerBtnDark: "rgba(52,211,153,0.15)",
      badgeBg: "#10b981",
    },
    unknown: {
      badge: "暂无评级",
      icon: "?",
      subtitleNoProduct: "暂无风险评级数据",
      needleLeft: null,
      headerBgLight: "#f9fafb",
      headerBorderLight: "#d1d5db",
      headerTitleLight: "#374151",
      headerSubLight: "#6b7280",
      headerBtnLight: "rgba(107,114,128,0.1)",
      headerBgDark: "#111827",
      headerBorderDark: "#374151",
      headerTitleDark: "#9ca3af",
      headerSubDark: "#6b7280",
      headerBtnDark: "rgba(156,163,175,0.15)",
      badgeBg: "#9ca3af",
    },
  }

  const LEVEL_TO_VISUAL: Record<RiskLevel, VisualKey> = {
    t4: "critical",
    t3: "high",
    t2: "medium",
    t1: "low",
    t0: "safe",
    unknown: "unknown",
  }

  /** 将后端 level 枚举转换为前端视觉等级 key */
  export function levelToVisualKey(level: RiskLevel | null | undefined): VisualKey {
    if (!level) return "unknown"
    return LEVEL_TO_VISUAL[level] ?? "unknown"
  }

  /** 获取风险等级完整配置 */
  export function getRiskConfig(level: RiskLevel | null | undefined): RiskLevelConfig {
    return RISK_CONFIG[levelToVisualKey(level)]
  }
  ```

- [ ] **Step 2: 在 H5 开发服务器确认 TypeScript 无编译错误**

  ```bash
  cd web && pnpm dev:uniapp:h5
  ```
  终端无 TypeScript 报错即可。

- [ ] **Step 3: 提交**

  ```bash
  git add web/apps/uniapp/src/utils/riskLevel.ts
  git commit -m "feat(uniapp): add riskLevel utility for ingredient-detail"
  ```

---

## Task 3：创建 `store/ingredient.ts` Pinia Store

**Files:**
- Create: `web/apps/uniapp/src/store/ingredient.ts`

- [ ] **Step 1: 创建文件，内容如下**

  ```typescript
  // web/apps/uniapp/src/store/ingredient.ts
  import { defineStore } from "pinia"
  import { ref } from "vue"
  import type { IngredientDetail } from "../types/product"

  export const useIngredientStore = defineStore("ingredient", () => {
    /** 当前查看的配料，从产品详情页点入时由上游页面写入 */
    const current = ref<IngredientDetail | null>(null)
    /** 来源产品名称（可选），用于 Header 副标题 */
    const fromProductName = ref<string | null>(null)

    function set(ingredient: IngredientDetail, productName?: string) {
      current.value = ingredient
      fromProductName.value = productName ?? null
    }

    function reset() {
      current.value = null
      fromProductName.value = null
    }

    return { current, fromProductName, set, reset }
  })
  ```

- [ ] **Step 2: 确认 TypeScript 无报错**

  查看 H5 dev 服务器终端，无红色编译报错。

- [ ] **Step 3: 提交**

  ```bash
  git add web/apps/uniapp/src/store/ingredient.ts
  git commit -m "feat(uniapp): add ingredient Pinia store"
  ```

---

## Task 4：注册 ingredient-detail 页面

**Files:**
- Modify: `web/apps/uniapp/src/pages.json`

- [ ] **Step 1: 在 `pages.json` 的 pages 数组末尾添加新页面**

  在 `pages/product/index` 条目之后添加：
  ```json
  {
    "path": "pages/ingredient-detail/index",
    "style": {
      "navigationStyle": "custom",
      "statusBarStyle": "dark"
    }
  }
  ```
  > 注意：`statusBarHeight` 不是 UniApp `pages.json` 的有效字段，状态栏高度由平台运行时提供。页面组件中通过 `.status-bar-placeholder { height: 88rpx }` 固定高度占位。

- [ ] **Step 2: H5 dev 服务器验证页面可访问**

  浏览器访问 `http://localhost:5174/#/pages/ingredient-detail/index`，应显示空白页（组件文件尚未创建时会报 404，待 Task 5 完成后验证）。

- [ ] **Step 3: 提交**

  ```bash
  git add web/apps/uniapp/src/pages.json
  git commit -m "feat(uniapp): register ingredient-detail page route"
  ```

---

## Task 5：构建 `pages/ingredient-detail/index.vue` 主页面

**Files:**
- Create: `web/apps/uniapp/src/pages/ingredient-detail/index.vue`

- [ ] **Step 1: 创建目录并创建文件**

  ```bash
  mkdir -p web/apps/uniapp/src/pages/ingredient-detail
  ```

  创建 `web/apps/uniapp/src/pages/ingredient-detail/index.vue`，内容如下：

  ```vue
  <template>
    <view
      class="ingredient-detail-page"
      :class="{ 'dark-mode': isDark }"
      :style="pageStyle"
    >
      <!-- ── 自定义 Header ──────────────────────────── -->
      <view class="ing-header" :style="headerStyle">
        <!-- 状态栏占位 -->
        <view class="status-bar-placeholder" />
        <view class="header-content">
          <button class="header-btn back-btn" @click="goBack">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
          <view class="header-text">
            <text class="header-title">配料详情</text>
            <text class="header-subtitle">{{ headerSubtitle }}</text>
          </view>
          <view class="header-spacer" />
        </view>
      </view>

      <!-- ── 无数据错误态 ──────────────────────────── -->
      <view v-if="!ingredient" class="error-state">
        <text class="error-text">数据加载失败，请返回重试</text>
        <button class="retry-btn" @click="goBack">返回</button>
      </view>

      <!-- ── 内容区 ────────────────────────────────── -->
      <scroll-view v-else scroll-y class="scroll-area">

        <!-- Hero 风险卡 -->
        <view class="section-card hero-card" :style="heroCardStyle">
          <view class="hero-top">
            <text class="hero-name">{{ ingredient.name }}</text>
            <view class="risk-badge" :style="badgeStyle">
              <text class="badge-icon">{{ riskConf.icon }}</text>
              <text class="badge-text">{{ riskConf.badge }}</text>
            </view>
          </view>

          <!-- 风险谱条 -->
          <view class="spectrum-wrap">
            <view class="spectrum-bar" :style="spectrumOpacityStyle">
              <!-- 色阶渐变已通过 CSS 实现 -->
            </view>
            <view
              v-if="riskConf.needleLeft !== null"
              class="spectrum-needle"
              :style="{ left: riskConf.needleLeft }"
            />
          </view>
          <view class="spectrum-labels">
            <text class="spec-label-safe">安全</text>
            <text class="spec-label-danger">极高风险</text>
          </view>

          <!-- Chips -->
          <view class="chips-row">
            <text v-if="ingredient.additive_code" class="chip chip-danger">{{ ingredient.additive_code }}</text>
            <text v-if="ingredient.function_type" class="chip chip-danger">{{ ingredient.function_type }}</text>
            <!-- 来源 chip：规格要求"来源 chip（灰色中性）"，但 IngredientDetail 类型中尚无对应字段，
                 backend schema 待扩展后补充（不阻塞本次实现）-->
            <!-- 孕妇警告 chip：字段名暂定，后端确认 schema 后更新 -->
            <text v-if="pregnancyWarning" class="chip chip-warning">{{ pregnancyWarning }}</text>
            <template v-if="ingredient.alias?.length">
              <text v-for="alias in ingredient.alias" :key="alias" class="chip chip-neutral">{{ alias }}</text>
            </template>
          </view>
        </view>

        <!-- 描述 -->
        <view v-if="summary" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-blue">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
              </svg>
            </view>
            <text class="section-title">描述</text>
            <text class="ai-label">AI</text>
          </view>
          <text class="section-body">{{ summary }}</text>
        </view>

        <!-- AI 风险分析 -->
        <view v-if="riskFactors.length > 0" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-red">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </view>
            <text class="section-title">AI 风险分析</text>
            <text class="ai-label">AI</text>
          </view>
          <view class="list-items">
            <view v-for="(item, i) in riskFactors" :key="i" class="list-item">
              <view class="list-item-icon icon-x">✕</view>
              <text class="list-item-text">{{ item }}</text>
            </view>
          </view>
        </view>

        <!-- 风险管理信息 -->
        <view v-if="hasRiskMgmt" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-purple">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" clip-rule="evenodd"/>
              </svg>
            </view>
            <text class="section-title">风险管理信息</text>
          </view>
          <view class="kv-table">
            <view v-if="ingredient.who_level" class="kv-row">
              <text class="kv-key">WHO 致癌等级</text>
              <text class="kv-value">{{ ingredient.who_level }}</text>
            </view>
            <!-- 母婴等级、使用限量、适用区域：字段名暂定，待后端 IngredientDetail 类型扩展后更新 -->
            <view v-if="maternalLevel" class="kv-row">
              <text class="kv-key">母婴等级</text>
              <text class="kv-value">{{ maternalLevel }}</text>
            </view>
            <view v-if="usageLimit" class="kv-row">
              <text class="kv-key">使用限量</text>
              <text class="kv-value">{{ usageLimit }}</text>
            </view>
            <view v-if="applicableRegion" class="kv-row">
              <text class="kv-key">适用区域</text>
              <text class="kv-value">{{ applicableRegion }}</text>
            </view>
            <view v-if="ingredient.allergen_info" class="kv-row">
              <text class="kv-key">过敏信息</text>
              <text class="kv-value">{{ ingredient.allergen_info }}</text>
            </view>
            <view v-if="ingredient.standard_code" class="kv-row">
              <text class="kv-key">执行标准</text>
              <text class="kv-value">{{ ingredient.standard_code }}</text>
            </view>
          </view>
        </view>

        <!-- AI 使用建议 -->
        <view v-if="suggestions.length > 0" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-green">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
            </view>
            <text class="section-title">AI 使用建议</text>
            <text class="ai-label">AI</text>
          </view>
          <view class="list-items">
            <view v-for="(s, i) in suggestions" :key="i" class="list-item">
              <view
                class="list-item-icon"
                :class="s.type === 'positive' ? 'icon-check-green' : 'icon-check-yellow'"
              >✓</view>
              <text class="list-item-text">{{ s.text }}</text>
            </view>
          </view>
        </view>

        <!-- 含此配料的产品 -->
        <view v-if="relatedProducts.length > 0" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-orange">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3z"/>
              </svg>
            </view>
            <text class="section-title">含此配料的产品</text>
          </view>
          <scroll-view scroll-x class="related-scroll">
            <view class="related-inner">
              <view
                v-for="p in relatedProducts"
                :key="p.id"
                class="related-card"
                @click="goToProduct(p.barcode)"
              >
                <view class="related-img-wrap">
                  <image
                    v-if="p.image_url_list?.[0]"
                    :src="p.image_url_list[0]"
                    class="related-img"
                    mode="aspectFill"
                  />
                  <view v-else class="related-img-placeholder">🍎</view>
                </view>
                <text class="related-name">{{ p.name }}</text>
              </view>
            </view>
          </scroll-view>
        </view>

        <!-- 底部安全距离 -->
        <view class="bottom-spacer" />
      </scroll-view>

      <!-- ── 底部操作栏 ──────────────────────────────── -->
      <view v-if="ingredient" class="bottom-bar">
        <button class="bar-btn bar-btn-ghost" @click="goToAI">
          <svg viewBox="0 0 20 20" class="bar-icon" aria-hidden="true">
            <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/>
          </svg>
          <text>咨询 AI 助手</text>
        </button>
        <button class="bar-btn bar-btn-primary" @click="goToSearch">
          <svg viewBox="0 0 20 20" class="bar-icon" aria-hidden="true">
            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
          </svg>
          <text>查看相关食品</text>
        </button>
      </view>
    </view>
  </template>

  <script setup lang="ts">
  import { ref, computed, onMounted, onUnmounted } from "vue"
  import { useIngredientStore } from "../../store/ingredient"
  import { useProductStore } from "../../store/product"
  import { getRiskConfig } from "../../utils/riskLevel"
  import type { IngredientAnalysis } from "../../types/product"

  // ── Store ────────────────────────────────────────────────
  const ingStore = useIngredientStore()
  const productStore = useProductStore()

  const ingredient = computed(() => ingStore.current)
  const fromProductName = computed(() => ingStore.fromProductName)

  // ── 暗色模式 ─────────────────────────────────────────────
  const isDark = ref(false)

  onMounted(() => {
    isDark.value = uni.getSystemInfoSync().theme === "dark"
    uni.onThemeChange(({ theme }) => {
      isDark.value = theme === "dark"
    })
  })

  onUnmounted(() => {
    uni.offThemeChange()
  })

  // ── 风险等级 ─────────────────────────────────────────────
  const riskLevel = computed(() => ingredient.value?.analysis?.level ?? null)
  const riskConf = computed(() => getRiskConfig(riskLevel.value))

  // ── Header 副标题 ────────────────────────────────────────
  const headerSubtitle = computed(() => {
    if (fromProductName.value) return `来自：${fromProductName.value}`
    return riskConf.value.subtitleNoProduct
  })

  // ── Inline CSS Vars（风险色调 Header） ───────────────────
  const pageStyle = computed(() => {
    const c = riskConf.value
    return isDark.value
      ? {
          "--risk-bg": c.headerBgDark,
          "--risk-border": c.headerBorderDark,
          "--risk-title": c.headerTitleDark,
          "--risk-sub": c.headerSubDark,
          "--risk-btn": c.headerBtnDark,
        }
      : {
          "--risk-bg": c.headerBgLight,
          "--risk-border": c.headerBorderLight,
          "--risk-title": c.headerTitleLight,
          "--risk-sub": c.headerSubLight,
          "--risk-btn": c.headerBtnLight,
        }
  })

  const headerStyle = computed(() => ({
    background: "var(--risk-bg)",
    borderBottom: `1px solid var(--risk-border)`,
  }))

  const heroCardStyle = computed(() => ({
    background: "var(--risk-bg)",
    border: `1px solid var(--risk-border)`,
  }))

  const badgeStyle = computed(() => ({
    background: riskConf.value.badgeBg,
  }))

  const spectrumOpacityStyle = computed(() =>
    riskConf.value.needleLeft === null ? { opacity: "0.4" } : {}
  )

  // ── 解析 analysis.results ────────────────────────────────
  function safeResults(analysis: IngredientAnalysis | undefined): Record<string, unknown> {
    if (!analysis?.results) return {}
    if (typeof analysis.results === "object" && analysis.results !== null) {
      return analysis.results as Record<string, unknown>
    }
    return {}
  }

  const results = computed(() => safeResults(ingredient.value?.analysis))

  // 规格信息架构章节写 `results.description`，数据接口章节写 `results.summary`；
  // 以数据接口章节为准（`description` 为笔误），使用 `results.summary`。
  const summary = computed(() => {
    const s = results.value.summary
    return typeof s === "string" ? s : null
  })

  // 孕妇警告 chip：字段名暂定（待后端确认），隐藏时不渲染
  const pregnancyWarning = computed(() => {
    const w = results.value.pregnancy_warning
    return typeof w === "string" ? w : null
  })

  // 以下三个字段在当前 IngredientDetail 类型中不存在，暂时从 analysis.results 读取；
  // 后端扩展 IngredientDetail schema 后迁移到顶层字段并更新此处。
  const maternalLevel = computed(() => {
    const v = results.value.maternal_level
    return typeof v === "string" ? v : null
  })

  const usageLimit = computed(() => {
    const v = results.value.usage_limit
    return typeof v === "string" ? v : null
  })

  const applicableRegion = computed(() => {
    const v = results.value.applicable_region
    return typeof v === "string" ? v : null
  })

  const riskFactors = computed(() => {
    const rf = results.value.risk_factors
    return Array.isArray(rf) ? rf.filter((x): x is string => typeof x === "string") : []
  })

  interface Suggestion { text: string; type: "positive" | "conditional" }

  const suggestions = computed((): Suggestion[] => {
    const raw = results.value.suggestions
    if (!Array.isArray(raw)) return []
    return raw.map((item: unknown) => {
      const s = item as Record<string, unknown>
      const text = typeof s?.text === "string" ? s.text : String(item)
      const type: "positive" | "conditional" =
        s?.type === "positive" ? "positive" : "conditional"
      return { text, type }
    })
  })

  // ── 风险管理信息是否有内容 ────────────────────────────────
  const hasRiskMgmt = computed(() =>
    !!(
      ingredient.value?.who_level ||
      ingredient.value?.allergen_info ||
      ingredient.value?.standard_code ||
      maternalLevel.value ||
      usageLimit.value ||
      applicableRegion.value
    )
  )

  // ── 含此配料的相关产品 ────────────────────────────────────
  // [已知降级] 规格要求从"全局产品列表"过滤，但全局产品列表 store 尚未实现。
  // 当前降级策略：仅从当前已加载的单个产品中过滤。
  // 后续扩展：实现全局产品列表 store 后，将此处改为从全局列表过滤。
  const relatedProducts = computed(() => {
    if (!ingredient.value || !productStore.product) return []
    const ingId = ingredient.value.id
    const prod = productStore.product
    const hasIng = prod.ingredients.some((i) => i.id === ingId)
    return hasIng ? [prod] : []
  })

  // ── 导航 ─────────────────────────────────────────────────
  function goBack() {
    uni.navigateBack()
  }

  function goToAI() {
    if (!ingredient.value) return
    uni.navigateTo({ url: `/pages/chat/index?context=${encodeURIComponent(ingredient.value.name)}` })
  }

  function goToSearch() {
    if (!ingredient.value) return
    uni.navigateTo({ url: `/pages/search/index?ingredientId=${ingredient.value.id}` })
  }

  function goToProduct(barcode: string) {
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` })
  }
  </script>

  <style lang="scss" scoped>
  @import "@/styles/design-system.scss";

  .ingredient-detail-page {
    min-height: 100vh;
    background: var(--bg-base);
    display: flex;
    flex-direction: column;
    position: relative;
  }

  // ── Header ──────────────────────────────────────────────
  .ing-header {
    position: sticky;
    top: 0;
    z-index: 100;
    flex-shrink: 0;
    transition: background 0.3s ease, border-color 0.3s ease;
  }

  .status-bar-placeholder {
    height: 88rpx; // 约 44px 状态栏
  }

  .header-content {
    display: flex;
    align-items: center;
    padding: 20rpx 24rpx 24rpx;
    gap: 16rpx;
  }

  .header-btn {
    width: 72rpx;
    height: 72rpx;
    border-radius: 50%;
    background: var(--risk-btn);
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    padding: 0;
    margin: 0;

    svg {
      width: 40rpx;
      height: 40rpx;
      color: var(--risk-title);
    }

    &:active { opacity: 0.7; }
  }

  .header-text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4rpx;
  }

  .header-title {
    font-size: 34rpx;
    font-weight: 700;
    color: var(--risk-title);
    line-height: 1.2;
  }

  .header-subtitle {
    font-size: 24rpx;
    color: var(--risk-sub);
    line-height: 1.3;
  }

  .header-spacer {
    width: 72rpx; // 与 back-btn 等宽，保持标题居中
  }

  // ── 错误态 ───────────────────────────────────────────────
  .error-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 32rpx;
    padding: 80rpx 48rpx;
  }

  .error-text {
    font-size: 28rpx;
    color: var(--text-secondary);
    text-align: center;
  }

  .retry-btn {
    padding: 20rpx 48rpx;
    border-radius: $radius-md;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    font-size: 28rpx;
  }

  // ── 滚动区 ───────────────────────────────────────────────
  .scroll-area {
    flex: 1;
    padding: 24rpx 24rpx 0;
  }

  .bottom-spacer {
    height: 180rpx; // 留出底部 bar 的空间
  }

  // ── Section Card 通用 ────────────────────────────────────
  .section-card {
    background: var(--bg-card);
    border-radius: $radius-lg;
    padding: 32rpx;
    margin-bottom: 24rpx;
    border: 1px solid var(--border-color);
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 16rpx;
    margin-bottom: 24rpx;
  }

  .section-icon-wrap {
    width: 40rpx;
    height: 40rpx;
    border-radius: 12rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    &.icon-bg-blue { background: rgba(59, 130, 246, 0.12); }
    &.icon-bg-red { background: rgba(239, 68, 68, 0.12); }
    &.icon-bg-purple { background: rgba(139, 92, 246, 0.12); }
    &.icon-bg-green { background: rgba(34, 197, 94, 0.12); }
    &.icon-bg-orange { background: rgba(249, 115, 22, 0.12); }
  }

  .section-icon {
    width: 24rpx;
    height: 24rpx;
    fill: currentColor;
  }

  .icon-bg-blue .section-icon { color: #3b82f6; }
  .icon-bg-red .section-icon { color: #ef4444; }
  .icon-bg-purple .section-icon { color: #8b5cf6; }
  .icon-bg-green .section-icon { color: #22c55e; }
  .icon-bg-orange .section-icon { color: #f97316; }

  .section-title {
    font-size: 26rpx;
    font-weight: 700;
    color: var(--text-primary);
    flex: 1;
  }

  .ai-label {
    font-size: 20rpx;
    font-weight: 700;
    padding: 4rpx 12rpx;
    border-radius: 8rpx;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
    letter-spacing: 0.05em;
  }

  .section-body {
    font-size: 26rpx;
    color: var(--text-secondary);
    line-height: 1.7;
  }

  // ── Hero 风险卡 ──────────────────────────────────────────
  .hero-card {
    border-radius: $radius-xl !important;
  }

  .hero-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16rpx;
    margin-bottom: 32rpx;
  }

  .hero-name {
    font-size: 40rpx;
    font-weight: 800;
    color: var(--risk-title);
    line-height: 1.2;
    flex: 1;
  }

  .risk-badge {
    display: flex;
    align-items: center;
    gap: 8rpx;
    padding: 10rpx 20rpx;
    border-radius: 24rpx;
    flex-shrink: 0;
  }

  .badge-icon {
    font-size: 24rpx;
  }

  .badge-text {
    font-size: 22rpx;
    font-weight: 700;
    color: #fff;
  }

  // ── 风险谱条 ─────────────────────────────────────────────
  .spectrum-wrap {
    position: relative;
    margin-bottom: 12rpx;
  }

  .spectrum-bar {
    height: 16rpx;
    border-radius: 8rpx;
    background: linear-gradient(to right,
      #10b981 0%,
      #22c55e 20%,
      #eab308 45%,
      #f97316 70%,
      #ef4444 85%,
      #dc2626 100%
    );
    transition: opacity 0.3s ease;
  }

  .spectrum-needle {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 24rpx;
    height: 24rpx;
    border-radius: 50%;
    background: #fff;
    border: 4rpx solid var(--text-primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    transition: left 0.4s $ease-spring;
  }

  .spectrum-labels {
    display: flex;
    justify-content: space-between;
  }

  .spec-label-safe,
  .spec-label-danger {
    font-size: 20rpx;
    color: var(--text-muted);
  }

  // ── Chips ────────────────────────────────────────────────
  .chips-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12rpx;
    margin-top: 24rpx;
  }

  .chip {
    font-size: 22rpx;
    padding: 8rpx 20rpx;
    border-radius: 16rpx;
    font-weight: 500;

    &.chip-danger {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
    }

    &.chip-warning {
      color: #a16207;
      background: rgba(234, 179, 8, 0.1);
      border: 1px solid rgba(234, 179, 8, 0.25);
    }

    &.chip-neutral {
      color: var(--text-secondary);
      background: var(--bg-base);
      border: 1px solid var(--border-color);
    }
  }

  // ── KV 表格 ──────────────────────────────────────────────
  .kv-table {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  .kv-row {
    display: flex;
    align-items: flex-start;
    gap: 16rpx;
  }

  .kv-key {
    font-size: 24rpx;
    color: var(--text-muted);
    width: 200rpx;
    flex-shrink: 0;
    padding-top: 2rpx;
  }

  .kv-value {
    font-size: 26rpx;
    color: var(--text-primary);
    flex: 1;
    line-height: 1.5;
  }

  // ── 列表项（风险分析 / 使用建议） ───────────────────────────
  .list-items {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  .list-item {
    display: flex;
    align-items: flex-start;
    gap: 16rpx;
  }

  .list-item-icon {
    width: 36rpx;
    height: 36rpx;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20rpx;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 4rpx;

    &.icon-x {
      background: rgba(239, 68, 68, 0.12);
      color: #ef4444;
    }

    &.icon-check-green {
      background: rgba(34, 197, 94, 0.12);
      color: #22c55e;
    }

    &.icon-check-yellow {
      background: rgba(234, 179, 8, 0.12);
      color: #eab308;
    }
  }

  .list-item-text {
    font-size: 26rpx;
    color: var(--text-secondary);
    line-height: 1.6;
    flex: 1;
  }

  // ── 相关产品横向滚动 ─────────────────────────────────────
  .related-scroll {
    :deep(.uni-scroll-view:first-child) {
      overflow: hidden;
    }
    &::-webkit-scrollbar { display: none; }
  }

  .related-inner {
    display: flex;
    flex-direction: row;
    gap: 20rpx;
    width: max-content;
    padding-bottom: 8rpx;
  }

  .related-card {
    flex: 0 0 auto;
    width: 172rpx;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12rpx;
    cursor: pointer;

    &:active { opacity: 0.7; }
  }

  .related-img-wrap {
    width: 172rpx;
    height: 172rpx;
    border-radius: $radius-md;
    overflow: hidden;
    background: var(--bg-base);
    border: 1px solid var(--border-color);
  }

  .related-img {
    width: 100%;
    height: 100%;
  }

  .related-img-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48rpx;
  }

  .related-name {
    font-size: 22rpx;
    color: var(--text-secondary);
    text-align: center;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    width: 100%;
  }

  // ── 底部操作栏 ───────────────────────────────────────────
  .bottom-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 20rpx 24rpx 48rpx;
    background: var(--bottom-bar-bg);
    border-top: 1px solid var(--bottom-bar-border);
    box-shadow: var(--bottom-bar-shadow);
    display: flex;
    gap: 16rpx;
    z-index: 100;
  }

  .bar-btn {
    flex: 1;
    height: 88rpx;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12rpx;
    font-size: 26rpx;
    font-weight: 600;
    border: none;
    padding: 0;

    &:active { opacity: 0.8; }

    text {
      font-size: 26rpx;
    }
  }

  .bar-icon {
    width: 32rpx;
    height: 32rpx;
    fill: currentColor;
  }

  .bar-btn-ghost {
    background: var(--bg-card);
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary);
  }

  .bar-btn-primary {
    background: #111111;
    color: #ffffff;

    .dark-mode & {
      background: #f5f5f5;
      color: #111111;
    }
  }
  </style>
  ```

- [ ] **Step 2: 在 H5 开发服务器验证页面渲染**

  1. 启动 H5 开发服务器：`cd web && pnpm dev:uniapp:h5`
  2. 在产品详情页点击一个配料卡（需要 Task 6 完成后才能完整测试），或直接访问 `http://localhost:5174/#/pages/ingredient-detail/index`
  3. 验证：无数据时显示错误态"数据加载失败，请返回重试"

- [ ] **Step 3: 提交**

  ```bash
  git add web/apps/uniapp/src/pages/ingredient-detail/index.vue
  git commit -m "feat(uniapp): add ingredient-detail page with risk-tinted header and sections"
  ```

---

## Task 6：更新 `IngredientSection.vue` 导航与 t1 支持

**Files:**
- Modify: `web/apps/uniapp/src/components/IngredientSection.vue`

当前问题：
1. `LEVEL_ORDER` 不含 `t1`，`t1` 被静默合并到 `t0` 组（`key === "t1" ? "t0" : level`）
2. `goToDetail` 导航到错误路径 `/pages/ingredient/detail` 而非 `/pages/ingredient-detail/index`
3. 跳转前未将配料数据存入 Pinia，也未传递 `fromProductName`

- [ ] **Step 1: 更新 `LEVEL_ORDER` 常量，添加 `t1`**

  将：
  ```typescript
  const LEVEL_ORDER = ["t4", "t3", "t2", "t0", "unknown"] as const;
  ```
  改为：
  ```typescript
  const LEVEL_ORDER = ["t4", "t3", "t2", "t1", "t0", "unknown"] as const;
  ```

- [ ] **Step 2: 更新 `LEVEL_LABELS`，添加 `t1`**

  将：
  ```typescript
  const LEVEL_LABELS: Record<string, string> = {
    t4: "严重风险",
    t3: "高风险",
    t2: "中风险",
    t0: "低风险",
    unknown: "未知",
  };
  ```
  改为：
  ```typescript
  const LEVEL_LABELS: Record<string, string> = {
    t4: "极高风险",
    t3: "高风险",
    t2: "中等风险",
    t1: "低风险",
    t0: "安全",
    unknown: "暂无评级",
  };
  ```

- [ ] **Step 3: 更新 `groupedIngredients` computed，不再合并 t1 → t0**

  将：
  ```typescript
  const groupedIngredients = computed(() => {
    const groups: Record<string, IngredientDetail[]> = {
      t4: [], t3: [], t2: [], t0: [], unknown: [],
    };
    for (const ing of props.ingredients) {
      const level = ing.analysis?.level ?? "unknown";
      const key = level === "t1" ? "t0" : level; // t1 归入 t0
      if (groups[key]) groups[key].push(ing);
      else groups["unknown"].push(ing);
    }
    return groups;
  });
  ```
  改为：
  ```typescript
  const groupedIngredients = computed(() => {
    const groups: Record<string, IngredientDetail[]> = {
      t4: [], t3: [], t2: [], t1: [], t0: [], unknown: [],
    };
    for (const ing of props.ingredients) {
      const level = ing.analysis?.level ?? "unknown";
      if (groups[level] !== undefined) groups[level].push(ing);
      else groups["unknown"].push(ing);
    }
    return groups;
  });
  ```

- [ ] **Step 4: 在 `<script setup>` 中导入 ingredient store 并更新 `goToDetail`**

  在 `<script setup>` 顶部现有 import 之后添加：
  ```typescript
  import { useIngredientStore } from "../store/ingredient";
  import { useProductStore } from "../store/product";

  const ingStore = useIngredientStore();
  const productStore = useProductStore();
  ```

  将 `goToDetail` 函数替换为：
  ```typescript
  function goToDetail(id: number) {
    const ing = props.ingredients.find((i) => i.id === id);
    if (!ing) return;
    const productName = productStore.product?.name;
    ingStore.set(ing, productName);
    uni.navigateTo({ url: "/pages/ingredient-detail/index" });
  }
  ```

- [ ] **Step 5: 更新 SCSS，添加 t1 的样式变体**

  在 `.risk-group` 规则中，在 `&.t2` 和 `&.t0` 之间添加：
  ```scss
  &.t1 { background: var(--risk-t1-bg); border: 1px solid var(--risk-t1-border); }
  ```

  在 `.risk-dot` 中添加：
  ```scss
  &.t1 { background: var(--risk-t1); box-shadow: 0 0 8px var(--risk-t1); }
  ```

  在 `.risk-badge` 中添加：
  ```scss
  .t1 & { color: var(--risk-t1); background: rgba(74, 222, 128, 0.15); }
  ```

  在 `.ingredient-card` 中添加：
  ```scss
  &.t1 { border-color: var(--risk-t1-border); }
  ```

  在 `.ingredient-card::before` 中添加：
  ```scss
  &.t1::before { background: var(--risk-t1); }
  ```

  在 `.risk-bar` 中添加：
  ```scss
  .t1 & { background: var(--risk-t1); box-shadow: 0 0 16rpx var(--risk-t1); }
  ```

  在 `.ingredient-name` 图标颜色中添加：
  ```scss
  .t1 & .icon { stroke: var(--risk-t1); fill: none; }
  ```

  在 `.ingredient-reason` 中添加：
  ```scss
  &.t1 { color: var(--risk-t1); background: rgba(74, 222, 128, 0.12); }
  ```

- [ ] **Step 6: 端到端手动验证**

  1. `cd web && pnpm dev:uniapp:h5`
  2. 在首页扫码或输入条形码加载产品
  3. 点击配料区中的任意配料卡
  4. 验证：跳转到 ingredient-detail 页；Header 背景色与该配料风险等级匹配；Hero 卡显示正确的配料名、风险徽章、谱条针位置；底部操作栏可见

- [ ] **Step 7: 提交**

  ```bash
  git add web/apps/uniapp/src/components/IngredientSection.vue
  git commit -m "fix(uniapp): wire ingredient navigation to ingredient-detail page, add t1 level support"
  ```

---

## 完成检查清单

- [ ] `--risk-t1` 及 `--risk-t1-bg/border` 已添加（亮/暗色）
- [ ] `utils/riskLevel.ts` 导出 `RISK_CONFIG`、`levelToVisualKey`、`getRiskConfig`
- [ ] `store/ingredient.ts` 提供 `current`、`fromProductName`、`set()`、`reset()`
- [ ] `pages.json` 已注册 `pages/ingredient-detail/index`，`navigationStyle: "custom"`
- [ ] `ingredient-detail/index.vue` 可渲染 Hero + 各 Section + 底部栏，无数据时显示错误态
- [ ] `IngredientSection.vue` 的 `goToDetail` 存入 Pinia 后跳转，t1 有独立视觉分组
- [ ] 暗色模式：`isDark` 初始化 + `onThemeChange` 监听 + `offThemeChange` 清除
- [ ] H5 开发服务器无 TypeScript 编译错误

## 已知 Gap（本次不实现）

| Gap | 原因 | 后续动作 |
|-----|------|----------|
| 来源 chip | `IngredientDetail` 类型无对应字段 | 后端扩展 schema 后补充 |
| 母婴等级 / 使用限量 / 适用区域 KV 行 | 字段名暂定，从 `analysis.results` 读取 | 后端确认字段名后迁移至顶层字段 |
| 全局产品列表过滤 | 全局产品列表 store 尚未实现 | 实现全局列表 store 后替换 `relatedProducts` 逻辑 |
| 搜索/AI 入口数据加载 | 独立配料接口 `GET /api/ingredient/{id}` 未就绪 | 接口就绪后移除降级错误态 |

> `IngredientDetail.id: number` 已在 `types/product.ts` 中确认存在，`goToDetail` 和 `relatedProducts` 的 `.id` 访问类型安全。
