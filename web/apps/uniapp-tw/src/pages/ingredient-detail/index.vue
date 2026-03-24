<script setup lang="ts">
import type { IngredientAnalysis } from '../../types/product'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useIngredientStore } from '../../store/ingredient'
import { useProductStore } from '../../store/product'
import { useThemeStore } from '../../store/theme'
import { getRiskConfig } from '../../utils/riskLevel'

// ── Store ────────────────────────────────────────────────
const ingStore = useIngredientStore()
const productStore = useProductStore()
const themeStore = useThemeStore()

const ingredient = computed(() => ingStore.current)
const fromProductName = computed(() => ingStore.fromProductName)

// ── 加载态 ───────────────────────────────────────────────
const isLoading = ref(false)

// ── URL 路由参数（ingredientId 为必传，fromProductName 可选） ──
onLoad(async (options) => {
  const id = options?.ingredientId ? Number(options.ingredientId) : null
  const fpn = options?.fromProductName ? decodeURIComponent(options.fromProductName) : null

  if (ingStore.current) {
    if (fpn) { ingStore.set(ingStore.current, fpn) }
    return
  }

  if (!id) { return }

  const fromProduct = productStore.product?.ingredients?.find(i => i.id === id)
  if (fromProduct) {
    ingStore.set(fromProduct, fpn ?? productStore.product?.name)
    return
  }

  isLoading.value = true
  try {
    const res = await new Promise<UniApp.RequestSuccessCallbackResult>((resolve, reject) => {
      uni.request({
        url: `${import.meta.env.VITE_API_BASE_URL}/api/ingredient/${id}`,
        success: resolve,
        fail: reject,
      })
    })
    if (res.statusCode === 200 && res.data) {
      const data = res.data as Record<string, unknown>
      ingStore.set(data as any, fpn ?? null)
    }
  }
  catch {
    // 静默失败，error-state 会兜底显示
  }
  finally {
    isLoading.value = false
  }
})

// ── 风险等级 ─────────────────────────────────────────────
const riskLevel = computed(() => ingredient.value?.analysis?.level ?? null)
const riskConf = computed(() => getRiskConfig(riskLevel.value))

// ── Header 副标题 ────────────────────────────────────────
const headerSubtitle = computed(() => {
  if (fromProductName.value) { return `来自：${fromProductName.value}` }
  return riskConf.value.subtitleNoProduct
})

// ── Risk class ───────────────────────────────────────────
const riskClass = computed(() => `risk-${riskConf.value.visualKey}`)

const spectrumOpacityStyle = computed(() =>
  riskConf.value.needleLeft === null ? { opacity: '0.4' } : {},
)

// 谱条指针从右侧计算（设计稿使用 right: 14% 等）
const needleRight = computed(() => {
  const left = riskConf.value.needleLeft
  if (left === null) { return null }
  return `${100 - Number.parseFloat(left) - 4}%`
})

// ── 解析 analysis.results ────────────────────────────────
function safeResults(analysis: IngredientAnalysis | undefined): Record<string, unknown> {
  if (!analysis?.results) { return {} }
  if (
    typeof analysis.results === 'object'
    && analysis.results !== null
    && !Array.isArray(analysis.results)
  ) {
    return analysis.results as Record<string, unknown>
  }
  return {}
}

// Mock 兜底数据
const MOCK_RESULTS = {
  summary: '香草精是一种广泛使用的食品香料，主要成分为香兰素（vanillin），可天然提取自香草豆荚，也可人工合成。常用于烘焙食品、甜点、饮料、冰淇淋等中增香。天然香草精含有超过200种风味化合物，香气更为复杂细腻。',
  risk_factors: [
    '市售香草精多为人工合成香兰素，与天然香草精成分存在差异',
    '长期大量摄入人工合成香兰素可能对肝脏产生轻微影响',
    '极少数人群可能出现过敏反应，表现为皮肤瘙痒或消化不适',
  ],
  suggestions: [
    { text: '正常烹饪用量（每次数滴）在成人中是安全的', type: 'positive' },
    { text: '购买时注意区分天然香草精（vanilla extract）与人工香草精（artificial vanilla）', type: 'conditional' },
    { text: '婴幼儿辅食建议使用天然来源香料并控制用量', type: 'conditional' },
  ],
}

const results = computed(() => {
  const raw = safeResults(ingredient.value?.analysis)
  const hasRealData = raw.summary || raw.risk_factors || raw.suggestions
  return hasRealData ? raw : MOCK_RESULTS
})

const summary = computed(() => {
  const s = results.value.summary
  return typeof s === 'string' ? s : null
})

const pregnancyWarning = computed(() => {
  const w = results.value.pregnancy_warning
  return typeof w === 'string' ? w : null
})

const source = computed(() => {
  const s = results.value.source
  return typeof s === 'string' ? s : '化学合成'
})

const maternalLevel = computed(() => {
  const v = results.value.maternal_level
  return typeof v === 'string' ? v : null
})

const usageLimit = computed(() => {
  const v = results.value.usage_limit
  return typeof v === 'string' ? v : null
})

const applicableRegion = computed(() => {
  const v = results.value.applicable_region
  return typeof v === 'string' ? v : null
})

const riskFactors = computed(() => {
  const rf = results.value.risk_factors
  return Array.isArray(rf) ? rf.filter((x): x is string => typeof x === 'string') : []
})

interface Suggestion { text: string, type: 'positive' | 'conditional' }

const suggestions = computed((): Suggestion[] => {
  const raw = results.value.suggestions
  if (!Array.isArray(raw)) { return [] }
  return raw.map((item: unknown) => {
    const s = item as Record<string, unknown>
    const text = typeof s?.text === 'string' ? s.text : String(item)
    const type: 'positive' | 'conditional'
      = s?.type === 'positive' ? 'positive' : 'conditional'
    return { text, type }
  })
})

const hasRiskMgmt = computed(() =>
  !!(
    ingredient.value?.who_level
    || ingredient.value?.allergen_info
    || ingredient.value?.standard_code
    || maternalLevel.value
    || usageLimit.value
    || applicableRegion.value
  ),
)

interface RelatedProduct {
  id: number
  name: string
  barcode: string
  emoji: string
  riskTag?: string
  image_url_list?: string[]
}

const MOCK_RELATED_PRODUCTS: RelatedProduct[] = [
  { id: 1, name: '午餐肉罐头', barcode: '6901234567890', emoji: '🥫', riskTag: '高风险' },
  { id: 2, name: '火腿肠', barcode: '6901234567891', emoji: '🌭', riskTag: '高风险' },
  { id: 3, name: '培根片', barcode: '6901234567892', emoji: '🥩', riskTag: '中等风险' },
  { id: 4, name: '烤肠', barcode: '6901234567893', emoji: '🍖', riskTag: '高风险' },
]

const relatedProducts = computed(() => {
  if (!ingredient.value) { return [] }
  return MOCK_RELATED_PRODUCTS
})

// ── 导航 ─────────────────────────────────────────────────
function goBack() {
  uni.navigateBack()
}

function shareToFriend() {
  if (!ingredient.value) { return }
  uni.showShareMenu({
    withShareTicket: true,
    menus: ['shareAppMessage', 'shareTimeline'],
  })
}

function goToAI() {
  if (!ingredient.value) { return }
  uni.navigateTo({ url: `/pages/chat/index?context=${encodeURIComponent(ingredient.value.name)}` })
}

function goToSearch() {
  if (!ingredient.value) { return }
  uni.navigateTo({ url: `/pages/search/index?ingredientId=${ingredient.value.id}` })
}

function goToProduct(barcode: string) {
  uni.navigateTo({ url: `/pages/product/index?barcode=${encodeURIComponent(barcode)}` })
}
</script>

<template>
  <view class="ingredient-detail-page">
    <!-- ── 自定义 Header ──────────────────────────── -->
    <view class="ing-header" :class="riskClass">
      <!-- 状态栏占位（动态高度） -->
      <view :style="{ height: `${themeStore.statusBarHeight}px` }" />
      <view class="header-content">
        <button class="header-btn back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <view class="header-text">
          <text class="header-title">配料详情</text>
          <text class="header-subtitle">{{ headerSubtitle }}</text>
        </view>
        <button class="header-btn share-btn" @click="shareToFriend">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8.684 13.342C8.886 12.938 9 12 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>
      </view>
    </view>

    <!-- ── 加载态 ──────────────────────────────── -->
    <view v-if="isLoading" class="loading-state">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- ── 无数据错误态 ──────────────────────────── -->
    <view v-else-if="!ingredient" class="error-state">
      <text class="error-text">数据加载失败，请返回重试</text>
      <button class="retry-btn" @click="goBack">
        返回
      </button>
    </view>

    <!-- ── 内容区 ────────────────────────────────── -->
    <scroll-view v-else scroll-y class="scroll-area">
      <view class="scroll-content">
        <!-- Hero 风险卡 -->
        <view class="section-card hero-card">
          <view class="hero-top">
            <view class="hero-name-row">
              <view class="hero-name-wrap">
                <text class="hero-name">{{ ingredient.name }}</text>
                <text v-if="ingredient.additive_code" class="hero-code">{{ ingredient.additive_code }} · 食品添加剂</text>
              </view>
              <view class="risk-badge" :class="riskClass">
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
                :style="{ right: needleRight }"
              />
            </view>
            <view class="spectrum-labels">
              <text class="spec-label-safe">低风险</text>
              <text class="spec-label-mid">中等</text>
              <text class="spec-label-danger">高风险</text>
            </view>
          </view>

          <!-- Chips -->
          <view class="chips-row">
            <text v-if="ingredient.additive_code" class="chip chip-func">{{ ingredient.additive_code }}</text>
            <text v-if="ingredient.function_type" class="chip chip-func">{{ ingredient.function_type }}</text>
            <text v-if="source" class="chip chip-neu">{{ source }}</text>
            <text v-if="pregnancyWarning" class="chip chip-warn">{{ pregnancyWarning }}</text>
            <template v-if="ingredient.alias?.length">
              <text
                v-for="alias in ingredient.alias" :key="alias" class="
                  chip chip-neu
                "
              >
                别名：{{ alias }}
              </text>
            </template>
          </view>
        </view>

        <!-- 描述 -->
        <view v-if="summary" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-blue">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
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
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </view>
            <text class="section-title">AI 风险分析</text>
            <text class="ai-label">AI</text>
          </view>
          <view class="list-items">
            <view v-for="(item, i) in riskFactors" :key="i" class="list-item">
              <view class="list-item-icon icon-x">
                ✕
              </view>
              <text class="list-item-text">{{ item }}</text>
            </view>
          </view>
        </view>

        <!-- 风险管理信息 -->
        <view v-if="hasRiskMgmt" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-purple">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" clip-rule="evenodd" />
              </svg>
            </view>
            <text class="section-title">风险管理信息</text>
          </view>
          <view class="kv-table">
            <view v-if="ingredient.who_level" class="kv-row">
              <text class="kv-key">WHO 致癌等级</text>
              <text class="kv-value kv-value-red">{{ ingredient.who_level }}</text>
            </view>
            <view v-if="maternalLevel" class="kv-row">
              <text class="kv-key">母婴等级</text>
              <text class="kv-value kv-value-red">{{ maternalLevel }}</text>
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
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </view>
            <text class="section-title">AI 使用建议</text>
            <text class="ai-label">AI</text>
          </view>
          <view class="list-items">
            <view v-for="(s, i) in suggestions" :key="i" class="list-item">
              <view
                class="list-item-icon"
                :class="s.type === 'positive' ? 'icon-check-green' : `
                  icon-check-yellow
                `"
              >
                ✓
              </view>
              <text class="list-item-text">{{ s.text }}</text>
            </view>
          </view>
        </view>

        <!-- 含此配料的产品 -->
        <view v-if="relatedProducts.length > 0" class="section-card">
          <view class="section-header">
            <view class="section-icon-wrap icon-bg-orange">
              <svg viewBox="0 0 20 20" class="section-icon" aria-hidden="true">
                <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3z" />
              </svg>
            </view>
            <text class="section-title">含此配料的产品</text>
          </view>
          <scroll-view scroll-x enable-flex class="related-scroll">
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
                  <view v-else class="related-img-placeholder">
                    {{ p.emoji }}
                  </view>
                </view>
                <text class="related-name">{{ p.name }}</text>
                <text
                  v-if="p.riskTag" class="related-risk-tag" :class="[p.riskTag === '高风险' ? `
                    risk-high
                  ` : `risk-med`]"
                >
                  {{ p.riskTag }}
                </text>
              </view>
            </view>
          </scroll-view>
        </view>

        <!-- 底部安全距离 -->
        <view class="bottom-spacer" />
      </view>
    </scroll-view>

    <!-- ── 底部操作栏 ──────────────────────────────── -->
    <view v-if="ingredient" class="bottom-bar">
      <button class="bar-btn bar-btn-ghost" @click="goToAI">
        <svg viewBox="0 0 20 20" class="bar-icon" aria-hidden="true">
          <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
        </svg>
        <text>咨询 AI 助手</text>
      </button>
      <button class="bar-btn bar-btn-primary" @click="goToSearch">
        <svg viewBox="0 0 20 20" class="bar-icon" aria-hidden="true">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
        <text>查看相关食品</text>
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
// Risk level color classes — scoped to this component
.risk-critical {
  --risk-header-bg: oklch(97% 0.02 25);
  --risk-header-border: oklch(92% 0.04 25);
  --risk-badge-bg: oklch(55% 0.2 25);
  --risk-bg: oklch(97% 0.02 25);
  --risk-border: oklch(92% 0.04 25);
  --risk-btn-bg: oklch(97% 0.02 25);
  --risk-btn-color: oklch(55% 0.2 25);
  --risk-title-color: oklch(45% 0.12 25);
  --risk-sub-color: oklch(55% 0.2 25);
}
.risk-high {
  --risk-header-bg: oklch(97% 0.03 60);
  --risk-header-border: oklch(90% 0.06 60);
  --risk-badge-bg: oklch(60% 0.18 50);
  --risk-bg: oklch(97% 0.03 60);
  --risk-border: oklch(90% 0.06 60);
  --risk-btn-bg: oklch(97% 0.03 60);
  --risk-btn-color: oklch(60% 0.18 50);
  --risk-title-color: oklch(45% 0.14 50);
  --risk-sub-color: oklch(60% 0.18 50);
}
.risk-medium {
  --risk-header-bg: oklch(97% 0.03 85);
  --risk-header-border: oklch(90% 0.06 85);
  --risk-badge-bg: oklch(65% 0.16 85);
  --risk-bg: oklch(97% 0.03 85);
  --risk-border: oklch(90% 0.06 85);
  --risk-btn-bg: oklch(97% 0.03 85);
  --risk-btn-color: oklch(65% 0.16 85);
  --risk-title-color: oklch(45% 0.14 85);
  --risk-sub-color: oklch(65% 0.16 85);
}
.risk-low {
  --risk-header-bg: oklch(97% 0.03 145);
  --risk-header-border: oklch(90% 0.06 145);
  --risk-badge-bg: oklch(55% 0.15 145);
  --risk-bg: oklch(97% 0.03 145);
  --risk-border: oklch(90% 0.06 145);
  --risk-btn-bg: oklch(97% 0.03 145);
  --risk-btn-color: oklch(55% 0.15 145);
  --risk-title-color: oklch(40% 0.1 145);
  --risk-sub-color: oklch(55% 0.15 145);
}
.risk-safe {
  --risk-header-bg: oklch(97% 0.03 145);
  --risk-header-border: oklch(90% 0.06 145);
  --risk-badge-bg: oklch(55% 0.15 145);
  --risk-bg: oklch(97% 0.03 145);
  --risk-border: oklch(90% 0.06 145);
  --risk-btn-bg: oklch(97% 0.03 145);
  --risk-btn-color: oklch(55% 0.15 145);
  --risk-title-color: oklch(40% 0.1 145);
  --risk-sub-color: oklch(55% 0.15 145);
}
.risk-unknown {
  --risk-header-bg: oklch(97% 0.01 265);
  --risk-header-border: oklch(93% 0.01 265);
  --risk-badge-bg: oklch(55% 0.01 265);
  --risk-bg: oklch(97% 0.01 265);
  --risk-border: oklch(93% 0.01 265);
  --risk-btn-bg: oklch(97% 0.01 265);
  --risk-btn-color: oklch(55% 0.01 265);
  --risk-title-color: oklch(45% 0.01 265);
  --risk-sub-color: oklch(55% 0.01 265);
}

// ── Page ─────────────────────────────────────────────────
.ingredient-detail-page {
  @apply h-screen bg-background flex flex-col relative overflow-hidden;
  --bottom-bar-shadow: 0 -8rpx 32rpx rgba(0, 0, 0, 0.06);
}

// ── Header ──────────────────────────────────────────────
.ing-header {
  @apply sticky top-0 z-[100] flex-shrink-0;
  background: var(--risk-header-bg);
  border-bottom: 1px solid var(--risk-header-border);
  transition:
    background 0.3s ease,
    border-color 0.3s ease;
}

.header-content {
  @apply flex items-center px-6 pb-6;
  gap: 16rpx;
}

.header-btn {
  @apply w-5 h-5 rounded-xl flex items-center justify-center flex-shrink-0 p-0 m-0;
  background: var(--risk-btn-bg);
  color: var(--risk-btn-color);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  border: none;

  svg {
    @apply w-9 h-9;
    stroke-width: 2;
    color: var(--risk-btn-color);
    stroke: var(--risk-btn-color);
  }

  &:active {
    @apply scale-95 opacity-80;
  }
}

.header-text {
  @apply flex-1 flex flex-col gap-0.5;
}

.header-title {
  @apply text-2xl font-bold leading-tight;
  color: var(--risk-title-color);
}

.header-subtitle {
  @apply text-base leading-relaxed;
  color: var(--risk-sub-color);
}

// ── 加载态 ───────────────────────────────────────────────
.loading-state {
  @apply flex-1 flex items-center justify-center;
}

.loading-text {
  @apply text-xl text-muted-foreground;
}

// ── 错误态 ───────────────────────────────────────────────
.error-state {
  @apply flex-1 flex flex-col items-center justify-center gap-8 px-12 py-20;
}

.error-text {
  @apply text-xl text-secondary text-center;
}

.retry-btn {
  @apply px-12 py-5 rounded-xl bg-card border border-border text-foreground text-xl;
}

// ── 滚动区 ───────────────────────────────────────────────
.scroll-area {
  @apply flex-1 overflow-hidden w-full;
  box-sizing: border-box;
}

.scroll-content {
  @apply px-6 pt-0;
}

.bottom-spacer {
  height: 180rpx;
}

// ── Section Card 通用 ────────────────────────────────────
.section-card {
  @apply bg-card rounded-xl p-8 mb-6 border border-border box-border w-full overflow-hidden;
  box-shadow: var(--shadow-sm);
}

.section-header {
  @apply flex items-center gap-4 mb-5 pb-4 border-b border-border;
}

.section-icon-wrap {
  @apply w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0;

  &.icon-bg-blue {
    background: color-mix(in oklch, oklch(55% 0.15 245) 12%, transparent);
  }
  &.icon-bg-red {
    background: color-mix(in oklch, oklch(55% 0.2 25) 12%, transparent);
  }
  &.icon-bg-purple {
    background: color-mix(in oklch, oklch(55% 0.15 300) 12%, transparent);
  }
  &.icon-bg-green {
    background: color-mix(in oklch, oklch(55% 0.15 145) 12%, transparent);
  }
  &.icon-bg-orange {
    background: color-mix(in oklch, oklch(60% 0.18 50) 12%, transparent);
  }
}

.section-icon {
  @apply w-5 h-5;
  fill: currentColor;
}

.icon-bg-blue .section-icon {
  color: oklch(55% 0.15 245);
}
.icon-bg-red .section-icon {
  color: oklch(55% 0.2 25);
}
.icon-bg-purple .section-icon {
  color: oklch(55% 0.15 300);
}
.icon-bg-green .section-icon {
  color: oklch(55% 0.15 145);
}
.icon-bg-orange .section-icon {
  color: oklch(60% 0.18 50);
}

.section-title {
  @apply text-lg font-bold text-foreground flex-1;
}

.ai-label {
  @apply text-sm font-bold px-3 py-0.5 rounded text-white;
  background: var(--ai-label-bg);
  letter-spacing: 0.05em;
}

.section-body {
  @apply text-base text-secondary leading-relaxed;
}

// ── Hero 风险卡 ──────────────────────────────────────────
.section-card.hero-card {
  @apply rounded-2xl overflow-hidden p-0;
}

.hero-top {
  background: linear-gradient(135deg, var(--risk-header-bg) 60%, transparent 100%);
  border-bottom: 1px solid var(--risk-header-border);
  @apply px-6 pb-5;
}

.hero-name-row {
  @apply flex items-start justify-between gap-4 mb-4;
}

.hero-name-wrap {
  @apply flex-1 flex flex-col gap-0.5;
}

.hero-name {
  @apply text-[36rpx] font-extrabold text-foreground leading-tight;
}

.hero-code {
  @apply text-base text-secondary font-normal;
}

.risk-badge {
  @apply flex items-center gap-2 px-5 py-2 rounded-xl flex-shrink-0;
  background: var(--risk-badge-bg);
}

.badge-icon {
  @apply text-base;
}

.badge-text {
  @apply text-base font-bold text-white;
}

// ── 风险谱条 ─────────────────────────────────────────────
.spectrum-wrap {
  @apply relative mb-1;
}

.spectrum-bar {
  @apply h-3 rounded-xl;
  background: linear-gradient(
    to right,
    oklch(55% 0.15 145) 0%,
    oklch(65% 0.12 145) 20%,
    oklch(65% 0.16 85) 45%,
    oklch(60% 0.18 50) 65%,
    oklch(55% 0.2 25) 82%,
    oklch(55% 0.2 25) 100%
  );
  transition: opacity 0.3s ease;
}

.spectrum-needle {
  @apply absolute top-1/2 -translate-y-1/2 rounded-full;
  width: 28rpx;
  height: 28rpx;
  background: var(--color-card);
  border: 5rpx solid var(--color-risk-t4);
  box-shadow: 0 2rpx 6rpx color-mix(in oklch, oklch(55% 0.2 25) 35%, transparent);
}

.spectrum-labels {
  @apply flex justify-between mt-1;
}

.spec-label-safe,
.spec-label-mid,
.spec-label-danger {
  @apply text-xs text-secondary;
}

// ── Chips ────────────────────────────────────────────────
.chips-row {
  @apply flex flex-wrap gap-3 px-6 py-5;
}

.chip {
  @apply text-sm px-4 py-0.5 rounded-lg font-medium;

  &.chip-func {
    color: var(--color-risk-t3);
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-risk-t3) 20%, transparent);
  }

  &.chip-warn {
    color: var(--color-risk-t4);
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-risk-t4) 20%, transparent);
  }

  &.chip-neu {
    color: var(--color-secondary);
    background: var(--color-secondary);
    background: color-mix(in oklch, var(--color-secondary) 8%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-secondary) 15%, transparent);
  }
}

// ── KV 表格 ──────────────────────────────────────────────
.kv-table {
  @apply flex flex-col gap-4;
}

.kv-row {
  @apply flex items-start gap-4;
}

.kv-key {
  @apply text-base text-muted-foreground w-[200rpx] flex-shrink-0 pt-0.5;
}

.kv-value {
  @apply text-lg text-foreground flex-1 leading-relaxed;

  &.kv-value-red {
    color: var(--color-risk-t4);
  }
}

// ── 列表项（风险分析 / 使用建议） ───────────────────────────
.list-items {
  @apply flex flex-col gap-4;
}

.list-item {
  @apply flex items-start gap-4;
}

.list-item-icon {
  @apply w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 mt-0.5;

  &.icon-x {
    background: color-mix(in oklch, oklch(55% 0.2 25) 12%, transparent);
    color: oklch(55% 0.2 25);
  }

  &.icon-check-green {
    background: color-mix(in oklch, oklch(55% 0.15 145) 12%, transparent);
    color: oklch(55% 0.15 145);
  }

  &.icon-check-yellow {
    background: color-mix(in oklch, oklch(65% 0.16 85) 12%, transparent);
    color: oklch(65% 0.16 85);
  }
}

.list-item-text {
  @apply text-lg text-secondary leading-relaxed flex-1;
}

// ── 相关产品横向滚动 ─────────────────────────────────────
.related-scroll {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }
  &::-webkit-scrollbar {
    display: none;
  }
}

.related-inner {
  @apply flex flex-row gap-5 w-max pb-2;
}

.related-card {
  @apply flex flex-col items-center gap-3 cursor-pointer flex-shrink-0;

  &:active {
    @apply opacity-70;
  }
}

.related-img-wrap {
  @apply w-[172rpx] h-[172rpx] rounded-xl overflow-hidden bg-background border border-border;
}

.related-img {
  @apply w-full h-full;
}

.related-img-placeholder {
  @apply w-full h-full flex items-center justify-center text-6xl;
}

.related-name {
  @apply text-base text-secondary text-center leading-tight line-clamp-2 w-full;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-risk-tag {
  @apply text-xs px-3 py-0.5 rounded font-medium inline-block;

  &.risk-high {
    color: var(--color-risk-t3);
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
  }

  &.risk-med {
    color: var(--color-risk-t2);
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
  }
}

// ── 底部操作栏 ───────────────────────────────────────────
.bottom-bar {
  @apply fixed bottom-0 left-0 right-0 px-6 pb-12 bg-background border-t border-border flex gap-4 z-[100];
  padding-bottom: max(48rpx, env(safe-area-inset-bottom));
  box-shadow: var(--bottom-bar-shadow);
}

.bar-btn {
  @apply flex-1 h-14 rounded-xl flex items-center justify-center gap-3 text-lg font-semibold p-0;

  &:active {
    @apply opacity-80;
  }

  text {
    @apply text-lg;
  }
}

.bar-icon {
  @apply w-5 h-5;
  fill: currentColor;
}

.bar-btn-ghost {
  @apply bg-card border border-border text-foreground;
}

.bar-btn-primary {
  @apply bg-accent text-white border-none;

  .dark & {
    background: var(--color-accent);
    color: #ffffff;
  }
}
</style>
