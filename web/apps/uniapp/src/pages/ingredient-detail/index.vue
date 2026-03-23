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
