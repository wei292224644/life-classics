<template>
  <view class="ingredient-detail-page">
    <!-- ── 自定义 Header ──────────────────────────── -->
    <view class="ing-header" :class="riskClass">
      <!-- 状态栏占位（动态高度） -->
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
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
        <button class="header-btn share-btn" @click="shareToFriend">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8.684 13.342C8.886 12.938 9 12 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
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
      <button class="retry-btn" @click="goBack">返回</button>
    </view>

    <!-- ── 内容区 ────────────────────────────────── -->
    <scroll-view v-else scroll-y class="scroll-area">
    <view class="scroll-content">

      <!-- Hero 风险卡 -->
      <view class="section-card hero-card" :style="heroCardStyle">
        <view class="hero-top" :style="heroTopStyle">
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
          <!-- 来源 chip：暂用假数据（后端扩展 IngredientDetail schema 后更新）-->
          <text v-if="source" class="chip chip-neu">{{ source }}</text>
          <!-- 孕妇警告 chip：字段名暂定，后端确认 schema 后更新 -->
          <text v-if="pregnancyWarning" class="chip chip-warn">{{ pregnancyWarning }}</text>
          <template v-if="ingredient.alias?.length">
            <text v-for="alias in ingredient.alias" :key="alias" class="chip chip-neu">别名：{{ alias }}</text>
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
            <text class="kv-value kv-value-red">{{ ingredient.who_level }}</text>
          </view>
          <!-- 母婴等级、使用限量、适用区域：字段名暂定，待后端 IngredientDetail 类型扩展后更新 -->
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
                <view v-else class="related-img-placeholder">{{ p.emoji }}</view>
              </view>
              <text class="related-name">{{ p.name }}</text>
              <text v-if="p.riskTag" :class="['related-risk-tag', p.riskTag === '高风险' ? 'risk-high' : 'risk-med']">{{ p.riskTag }}</text>
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
import { ref, computed } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { useIngredientStore } from "../../store/ingredient"
import { useProductStore } from "../../store/product"
import { useThemeStore } from "../../store/theme"
import { getRiskConfig } from "../../utils/riskLevel"
import type { IngredientAnalysis } from "../../types/product"

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
    // 已有 Pinia 数据（从产品页下钻而来），URL 的 fromProductName 覆盖之
    if (fpn) ingStore.set(ingStore.current, fpn)
    return
  }

  if (!id) return

  // 独立访问：先从当前产品 store 匹配，未找到则调 API
  const fromProduct = productStore.product?.ingredients?.find(i => i.id === id)
  if (fromProduct) {
    ingStore.set(fromProduct, fpn ?? productStore.product?.name)
    return
  }

  // 调后端独立配料接口
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
  } catch {
    // 静默失败，error-state 会兜底显示
  } finally {
    isLoading.value = false
  }
})

// ── 风险等级 ─────────────────────────────────────────────
const riskLevel = computed(() => ingredient.value?.analysis?.level ?? null)
const riskConf = computed(() => getRiskConfig(riskLevel.value))

// ── Header 副标题 ────────────────────────────────────────
const headerSubtitle = computed(() => {
  if (fromProductName.value) return `来自：${fromProductName.value}`
  return riskConf.value.subtitleNoProduct
})

// ── Risk class ───────────────────────────────────────────
const riskClass = computed(() => `risk-${riskConf.value.visualKey}`)

const heroCardStyle = computed(() => ({
  background: "var(--bg-card)",
  border: "1px solid var(--border-color)",
  boxShadow: "0 2rpx 8rpx rgba(0,0,0,0.05)",
}))

const heroTopStyle = computed(() => ({
  background: `linear-gradient(135deg, var(--risk-header-bg) 60%, transparent 100%)`,
  borderBottom: "1px solid var(--risk-header-border)",
}))

const spectrumOpacityStyle = computed(() =>
  riskConf.value.needleLeft === null ? { opacity: "0.4" } : {}
)

// 谱条指针从右侧计算（设计稿使用 right: 14% 等）
const needleRight = computed(() => {
  const left = riskConf.value.needleLeft
  if (left === null) return null
  // 将 left 百分比转换为 right 百分比（假设指针宽度约 14px 占谱条 4%）
  return `${100 - parseFloat(left) - 4}%`
})

// ── 解析 analysis.results ────────────────────────────────
function safeResults(analysis: IngredientAnalysis | undefined): Record<string, unknown> {
  if (!analysis?.results) return {}
  if (
    typeof analysis.results === "object" &&
    analysis.results !== null &&
    !Array.isArray(analysis.results)
  ) {
    return analysis.results as Record<string, unknown>
  }
  return {}
}

// Mock 兜底数据：真实 analysis.results 中无内容时使用，待后端数据完善后可移除
const MOCK_RESULTS = {
  summary: "香草精是一种广泛使用的食品香料，主要成分为香兰素（vanillin），可天然提取自香草豆荚，也可人工合成。常用于烘焙食品、甜点、饮料、冰淇淋等中增香。天然香草精含有超过200种风味化合物，香气更为复杂细腻。",
  risk_factors: [
    "市售香草精多为人工合成香兰素，与天然香草精成分存在差异",
    "长期大量摄入人工合成香兰素可能对肝脏产生轻微影响",
    "极少数人群可能出现过敏反应，表现为皮肤瘙痒或消化不适"
  ],
  suggestions: [
    { text: "正常烹饪用量（每次数滴）在成人中是安全的", type: "positive" },
    { text: "购买时注意区分天然香草精（vanilla extract）与人工香草精（artificial vanilla）", type: "conditional" },
    { text: "婴幼儿辅食建议使用天然来源香料并控制用量", type: "conditional" }
  ]
}

const results = computed(() => {
  const raw = safeResults(ingredient.value?.analysis)
  const hasRealData = raw.summary || raw.risk_factors || raw.suggestions
  return hasRealData ? raw : MOCK_RESULTS
})

// 以数据接口章节为准（信息架构中的 `description` 为笔误），使用 `results.summary`
const summary = computed(() => {
  const s = results.value.summary
  return typeof s === "string" ? s : null
})

// 孕妇警告 chip：字段名暂定（待后端确认），隐藏时不渲染
const pregnancyWarning = computed(() => {
  const w = results.value.pregnancy_warning
  return typeof w === "string" ? w : null
})

// 来源 chip：暂用假数据（后端扩展 IngredientDetail schema 后更新）
const source = computed(() => {
  const s = results.value.source
  return typeof s === "string" ? s : "化学合成"
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
// 当前降级策略：使用假数据模拟多个产品卡片。
// 后续扩展：实现全局产品列表 store 后，将此处改为从全局列表过滤。
// 假数据格式
interface RelatedProduct {
  id: number
  name: string
  barcode: string
  emoji: string
  riskTag?: string
  image_url_list?: string[]
}

const MOCK_RELATED_PRODUCTS: RelatedProduct[] = [
  { id: 1, name: "午餐肉罐头", barcode: "6901234567890", emoji: "🥫", riskTag: "高风险" },
  { id: 2, name: "火腿肠", barcode: "6901234567891", emoji: "🌭", riskTag: "高风险" },
  { id: 3, name: "培根片", barcode: "6901234567892", emoji: "🥩", riskTag: "中等风险" },
  { id: 4, name: "烤肠", barcode: "6901234567893", emoji: "🍖", riskTag: "高风险" },
]

const relatedProducts = computed(() => {
  if (!ingredient.value) return []
  // 暂时返回假数据，后续接入全局产品列表后改为过滤逻辑
  return MOCK_RELATED_PRODUCTS
})

// ── 导航 ─────────────────────────────────────────────────
function goBack() {
  uni.navigateBack()
}

function shareToFriend() {
  if (!ingredient.value) return
  uni.showShareMenu({
    withShareTicket: true,
    menus: ["shareAppMessage", "shareTimeline"],
  })
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
  uni.navigateTo({ url: `/pages/product/index?barcode=${encodeURIComponent(barcode)}` })
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

// Risk level color classes — scoped to this component
.risk-critical { --risk-header-bg: var(--palette-red-50); --risk-header-border: var(--palette-red-200); --risk-badge-bg: var(--palette-red-500); --risk-bg: var(--palette-red-50); --risk-border: var(--palette-red-200); --risk-btn-bg: var(--risk-t4-bg); --risk-btn-color: var(--risk-t4); --risk-title-color: var(--palette-red-800); --risk-sub-color: var(--risk-t4); }
.risk-high      { --risk-header-bg: var(--palette-orange-50); --risk-header-border: var(--palette-orange-200); --risk-badge-bg: var(--palette-orange-500); --risk-bg: var(--palette-orange-50); --risk-border: var(--palette-orange-200); --risk-btn-bg: var(--risk-t3-bg); --risk-btn-color: var(--risk-t3); --risk-title-color: var(--palette-orange-800); --risk-sub-color: var(--risk-t3); }
.risk-medium    { --risk-header-bg: var(--palette-yellow-50); --risk-header-border: var(--palette-yellow-200); --risk-badge-bg: var(--palette-yellow-500); --risk-bg: var(--palette-yellow-50); --risk-border: var(--palette-yellow-200); --risk-btn-bg: var(--risk-t2-bg); --risk-btn-color: var(--risk-t2); --risk-title-color: var(--palette-yellow-800); --risk-sub-color: var(--risk-t2); }
.risk-low       { --risk-header-bg: var(--palette-green-50); --risk-header-border: var(--palette-green-200); --risk-badge-bg: var(--palette-green-500); --risk-bg: var(--palette-green-50); --risk-border: var(--palette-green-200); --risk-btn-bg: var(--risk-t1-bg); --risk-btn-color: var(--risk-t1); --risk-title-color: var(--palette-green-800); --risk-sub-color: var(--risk-t1); }
.risk-safe      { --risk-header-bg: var(--palette-green-50); --risk-header-border: var(--palette-green-200); --risk-badge-bg: var(--palette-green-500); --risk-bg: var(--palette-green-50); --risk-border: var(--palette-green-200); --risk-btn-bg: var(--risk-t0-bg); --risk-btn-color: var(--risk-t0); --risk-title-color: var(--palette-green-800); --risk-sub-color: var(--risk-t0); }
.risk-unknown   { --risk-header-bg: var(--palette-gray-50); --risk-header-border: var(--palette-gray-200); --risk-badge-bg: var(--palette-gray-500); --risk-bg: var(--palette-gray-50); --risk-border: var(--palette-gray-200); --risk-btn-bg: var(--risk-unknown-bg); --risk-btn-color: var(--risk-unknown); --risk-title-color: var(--palette-gray-600); --risk-sub-color: var(--risk-unknown); }

.ingredient-detail-page {
  height: 100vh;
  background: var(--bg-base);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  --bottom-bar-shadow: 0 -8rpx 32rpx rgba(0, 0, 0, 0.06);
}

// ── Header ──────────────────────────────────────────────
.ing-header {
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
  background: var(--risk-header-bg);
  border-bottom: 1px solid var(--risk-header-border);
  transition: background 0.3s ease, border-color 0.3s ease;
}

.header-content {
  display: flex;
  align-items: center;
  padding: var(--space-5) var(--space-6) var(--space-6);
  gap: var(--space-4);
}

.header-btn {
  width: var(--space-20);
  height: var(--space-20);
  border-radius: 24rpx;
  background: var(--risk-btn-bg);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0;
  margin: 0;
  color: var(--risk-btn-color);
  transition: all 0.2s $ease-spring;
  outline: none;
  -webkit-appearance: none;
  appearance: none;

  svg {
    width: var(--space-9);
    height: var(--space-9);
    stroke-width: 2;
    color: var(--risk-btn-color);
    stroke: var(--risk-btn-color);
  }

  &:active {
    transform: scale(0.92);
    opacity: 0.8;
  }
}

.header-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.header-title {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--risk-title-color);
  line-height: 1.2;
}

.header-subtitle {
  font-size: var(--text-md);
  color: var(--risk-sub-color);
  line-height: 1.3;
}

.header-spacer {
  width: var(--space-18); // 与 back-btn 等宽，保持标题居中
}

// ── 加载态 ───────────────────────────────────────────────
.loading-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-text {
  font-size: var(--text-xl);
  color: var(--text-muted);
}

// ── 错误态 ───────────────────────────────────────────────
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  padding: var(--space-20) var(--space-12);
}

.error-text {
  font-size: var(--text-xl);
  color: var(--text-secondary);
  text-align: center;
}

.retry-btn {
  padding: var(--space-5) var(--space-12);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: var(--text-xl);
}

// ── 滚动区 ───────────────────────────────────────────────
.scroll-area {
  flex: 1;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}

.scroll-content {
  padding: var(--space-6) var(--space-6) 0;
}

.bottom-spacer {
  height: 180rpx; // 留出底部 bar 的空间
}

// ── Section Card 通用 ────────────────────────────────────
.section-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  margin-bottom: var(--space-6);
  border: 1px solid var(--border-color);
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-color);
}

.section-icon-wrap {
  width: var(--icon-xl);
  height: var(--icon-xl);
  border-radius: var(--space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.icon-bg-blue { background: color-mix(in oklch, var(--palette-blue-500) 12%, transparent); }
  &.icon-bg-red { background: color-mix(in oklch, var(--palette-red-500) 12%, transparent); }
  &.icon-bg-purple { background: color-mix(in oklch, var(--palette-purple-500) 12%, transparent); }
  &.icon-bg-green { background: color-mix(in oklch, var(--palette-green-500) 12%, transparent); }
  &.icon-bg-orange { background: color-mix(in oklch, var(--palette-orange-400) 12%, transparent); }
}

.section-icon {
  width: var(--icon-sm);
  height: var(--icon-sm);
  fill: currentColor;
}

.icon-bg-blue .section-icon { color: var(--palette-blue-500); }
.icon-bg-red .section-icon { color: var(--palette-red-500); }
.icon-bg-purple .section-icon { color: var(--palette-purple-500); }
.icon-bg-green .section-icon { color: var(--palette-green-500); }
.icon-bg-orange .section-icon { color: var(--palette-orange-400); }

.section-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}

.ai-label {
  font-size: var(--text-sm);
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--space-2);
  background: var(--ai-label-bg);
  color: #fff;
  letter-spacing: 0.05em;
}

.section-body {
  font-size: var(--text-md);
  color: var(--text-secondary);
  line-height: 1.7;
}

// ── Hero 风险卡 ──────────────────────────────────────────
.section-card.hero-card {
  border-radius: var(--radius-xl);
  overflow: hidden;
  padding: 0;
}

.hero-top {
  background: linear-gradient(135deg, var(--risk-header-bg) 60%, transparent 100%);
  border-bottom: 1px solid var(--risk-header-border);
  padding: var(--space-6) var(--space-6) var(--space-5);
}

.hero-name-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.hero-name-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.hero-name {
  font-size: var(--text-4xl);
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.2;
}

.hero-code {
  font-size: var(--text-base);
  color: var(--text-secondary);
  font-weight: 400;
}

.risk-badge {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  background: var(--risk-badge-bg);
}

.badge-icon {
  font-size: var(--text-md);
}

.badge-text {
  font-size: var(--text-base);
  font-weight: 700;
  color: #fff;
}

// ── 风险谱条 ─────────────────────────────────────────────
.spectrum-wrap {
  position: relative;
  margin: var(--space-1) 0 var(--space-2);
}

.spectrum-bar {
  height: var(--space-3);
  border-radius: var(--space-2);
  background: linear-gradient(to right,
    var(--palette-green-500) 0%,
    var(--palette-green-300) 20%,
    var(--palette-yellow-500) 45%,
    var(--palette-orange-400) 65%,
    var(--palette-red-500) 82%,
    var(--palette-red-500) 100%
  );
  transition: opacity 0.3s ease;
}

.spectrum-needle {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: var(--space-7);
  height: var(--space-7);
  border-radius: 50%;
  background: var(--bg-card);
  border: 5rpx solid var(--risk-t4);
  box-shadow: 0 2rpx 6rpx color-mix(in oklch, var(--palette-red-500) 35%, transparent);
}

.spectrum-labels {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-1);
}

.spec-label-safe,
.spec-label-mid,
.spec-label-danger {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

// ── Chips ────────────────────────────────────────────────
.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6) var(--space-5);
}

.chip {
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-4);
  border-radius: var(--space-3);
  font-weight: 500;

  &.chip-func {
    color: var(--chip-risk-text);
    background: var(--chip-risk-bg);
    border: 1px solid var(--chip-risk-border);
  }

  &.chip-warn {
    color: var(--chip-warn-text);
    background: var(--chip-warn-bg);
    border: 1px solid var(--chip-warn-border);
  }

  &.chip-neu {
    color: var(--chip-neu-text);
    background: var(--chip-neu-bg);
  }
}

// ── KV 表格 ──────────────────────────────────────────────
.kv-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.kv-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.kv-key {
  font-size: var(--text-md);
  color: var(--text-muted);
  width: 200rpx;
  flex-shrink: 0;
  padding-top: var(--space-1);
}

.kv-value {
  font-size: var(--text-lg);
  color: var(--text-primary);
  flex: 1;
  line-height: 1.5;

  &.kv-value-red {
    color: var(--risk-t4);
  }
}

// ── 列表项（风险分析 / 使用建议） ───────────────────────────
.list-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.list-item-icon {
  width: var(--icon-lg);
  height: var(--icon-lg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 700;
  flex-shrink: 0;
  margin-top: var(--space-1);

  &.icon-x {
    background: color-mix(in oklch, var(--palette-red-500) 12%, transparent);
    color: var(--palette-red-500);
  }

  &.icon-check-green {
    background: color-mix(in oklch, var(--palette-green-500) 12%, transparent);
    color: var(--palette-green-500);
  }

  &.icon-check-yellow {
    background: color-mix(in oklch, var(--palette-yellow-500) 12%, transparent);
    color: var(--palette-yellow-500);
  }
}

.list-item-text {
  font-size: var(--text-lg);
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
  gap: var(--space-5);
  width: max-content;
  padding-bottom: var(--space-2);
}

.related-card {
  flex: 0 0 auto;
  width: 172rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;

  &:active { opacity: 0.7; }
}

.related-img-wrap {
  width: 172rpx;
  height: 172rpx;
  border-radius: var(--radius-md);
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
  font-size: var(--text-7xl);
}

.related-name {
  font-size: var(--text-base);
  color: var(--text-secondary);
  text-align: center;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  width: 100%;
}

.related-risk-tag {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--space-2);
  font-weight: 500;
  display: inline-block;

  &.risk-high {
    color: var(--chip-risk-text);
    background: var(--chip-risk-bg);
  }

  &.risk-med {
    color: var(--chip-warn-text);
    background: var(--chip-warn-bg);
  }
}

// ── 底部操作栏 ───────────────────────────────────────────
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: var(--space-5) var(--space-6) var(--space-12);
  padding-bottom: max(var(--space-12), constant(safe-area-inset-bottom));
  padding-bottom: max(var(--space-12), env(safe-area-inset-bottom));
  background: var(--bottom-bar-bg);
  border-top: 1px solid var(--bottom-bar-border);
  box-shadow: var(--bottom-bar-shadow);
  display: flex;
  gap: var(--space-4);
  z-index: 100;
}

.bar-btn {
  flex: 1;
  height: var(--btn-height-xl);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  font-size: var(--text-lg);
  font-weight: 600;
  padding: 0;

  &:active { opacity: 0.8; }

  text {
    font-size: var(--text-lg);
  }
}

.bar-icon {
  width: var(--icon-md);
  height: var(--icon-md);
  fill: currentColor;
}

.bar-btn-ghost {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.bar-btn-primary {
  background: var(--accent);
  color: #ffffff;
  border: none;

  .dark & {
    background: var(--accent);
    color: #ffffff;
  }
}
</style>
