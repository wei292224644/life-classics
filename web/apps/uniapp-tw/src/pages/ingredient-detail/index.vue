<script setup lang="ts">
import type { IngredientAnalysis } from '@/types/product'
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/card/Card.vue'
import Icon from '@/components/ui/Icon.vue'
import Screen from '@/components/ui/Screen.vue'
import StateView from '@/components/ui/StateView.vue'
import { useIngredientStore } from '@/store/ingredient'
import { useProductStore } from '@/store/product'
import { useThemeStore } from '@/store/theme'
import { getRiskConfig } from '@/utils/riskLevel'
import Separator from '@/components/ui/Separator.vue'
import Cell from '@/components/ui/Cell.vue'
import { CardHeader } from '@/components/ui/card'
// ── Store ────────────────────────────────────────────────
const ingStore = useIngredientStore()
const productStore = useProductStore()
const themeStore = useThemeStore()

const ingredient = computed(() => ingStore.current)
const fromProductName = computed(() => ingStore.fromProductName)

// ── 加载态 ───────────────────────────────────────────────
const isLoading = ref(false)
const errorMessage = ref<string>()

// ── 页面状态（用于 StateView） ───────────────────────────
const pageState = computed(() => {
  if (isLoading.value) {
    return 'loading'
  }
  if (!ingredient.value) {
    return 'not_found'
  }
  return 'success'
})

// ── URL 路由参数（ingredientId 为必传，fromProductName 可选） ──
onLoad(async (options) => {
  const id = options?.ingredientId ? Number(options.ingredientId) : null
  const fpn = options?.fromProductName
    ? decodeURIComponent(options.fromProductName)
    : null

  if (ingStore.current) {
    if (fpn) {
      ingStore.set(ingStore.current, fpn)
    }
    return
  }

  if (!id) {
    return
  }

  const fromProduct = productStore.product?.ingredients?.find(
    i => i.id === id,
  )
  if (fromProduct) {
    ingStore.set(fromProduct, fpn ?? productStore.product?.name)
    return
  }

  isLoading.value = true
  try {
    const res = await new Promise<UniApp.RequestSuccessCallbackResult>(
      (resolve, reject) => {
        uni.request({
          url: `${import.meta.env.VITE_API_BASE_URL}/api/ingredient/${id}`,
          success: resolve,
          fail: reject,
        })
      },
    )
    if (res.statusCode === 200 && res.data) {
      const data = res.data as Record<string, unknown>
      ingStore.set(data as any, fpn ?? undefined)
    }
  }
  catch {
    errorMessage.value = '数据加载失败，请返回重试'
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
  if (fromProductName.value) {
    return `来自：${fromProductName.value}`
  }
  return riskConf.value.subtitleNoProduct
})

// ── Risk class ───────────────────────────────────────────

const spectrumOpacityStyle = computed(() =>
  riskConf.value.needleLeft === null ? { opacity: '0.4' } : {},
)

// 谱条指针从右侧计算（设计稿使用 right: 14% 等）
const needleRight = computed(() => {
  const left = riskConf.value.needleLeft
  if (left === null) {
    return null
  }
  return `${100 - Number.parseFloat(left) - 4}%`
})

const needleStyle = computed(() =>
  needleRight.value ? { right: needleRight.value } : {},
)

// ── 解析 analysis.results ────────────────────────────────
function safeResults(
  analysis: IngredientAnalysis | undefined,
): Record<string, unknown> {
  if (!analysis?.results) {
    return {}
  }
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
const MOCK_RESULTS: Record<string, unknown> = {
  summary:
    '香草精是一种广泛使用的食品香料，主要成分为香兰素（vanillin），可天然提取自香草豆荚，也可人工合成。常用于烘焙食品、甜点、饮料、冰淇淋等中增香。天然香草精含有超过200种风味化合物，香气更为复杂细腻。',
  risk_factors: [
    '市售香草精多为人工合成香兰素，与天然香草精成分存在差异',
    '长期大量摄入人工合成香兰素可能对肝脏产生轻微影响',
    '极少数人群可能出现过敏反应，表现为皮肤瘙痒或消化不适',
  ],
  suggestions: [
    { text: '正常烹饪用量（每次数滴）在成人中是安全的', type: 'positive' },
    {
      text: '购买时注意区分天然香草精（vanilla extract）与人工香草精（artificial vanilla）',
      type: 'conditional',
    },
    { text: '婴幼儿辅食建议使用天然来源香料并控制用量', type: 'conditional' },
  ],
}

const results = computed<Record<string, unknown>>(() => {
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
  return Array.isArray(rf)
    ? rf.filter((x): x is string => typeof x === 'string')
    : []
})

interface Suggestion {
  text: string
  type: 'positive' | 'conditional'
}

const suggestions = computed((): Suggestion[] => {
  const raw = results.value.suggestions
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.map((item: unknown) => {
    const s = item as Record<string, unknown>
    const text = typeof s?.text === 'string' ? s.text : String(item)
    const type: 'positive' | 'conditional'
      = s?.type === 'positive' ? 'positive' : 'conditional'
    return { text, type }
  })
})

const hasRiskMgmt = computed(
  () =>
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
  {
    id: 1,
    name: '午餐肉罐头',
    barcode: '6901234567890',
    emoji: '🥫',
    riskTag: '高风险',
  },
  {
    id: 2,
    name: '火腿肠',
    barcode: '6901234567891',
    emoji: '🌭',
    riskTag: '高风险',
  },
  {
    id: 3,
    name: '培根片',
    barcode: '6901234567892',
    emoji: '🥩',
    riskTag: '中等风险',
  },
  {
    id: 4,
    name: '烤肠',
    barcode: '6901234567893',
    emoji: '🍖',
    riskTag: '高风险',
  },
]

const relatedProducts = computed(() => {
  if (!ingredient.value) {
    return []
  }
  return MOCK_RELATED_PRODUCTS
})

// ── 导航 ─────────────────────────────────────────────────
function goBack() {
  uni.navigateBack()
}

function shareToFriend() {
  if (!ingredient.value) {
    return
  }
  uni.showShareMenu({
    withShareTicket: true,
    menus: ['shareAppMessage', 'shareTimeline'],
  })
}

function goToAI() {
  if (!ingredient.value) {
    return
  }
  uni.navigateTo({
    url: `/pages/chat/index?context=${encodeURIComponent(ingredient.value.name)}`,
  })
}

function goToSearch() {
  if (!ingredient.value) {
    return
  }
  uni.navigateTo({
    url: `/pages/search/index?ingredientId=${ingredient.value.id}`,
  })
}

function goToProduct(barcode: string) {
  uni.navigateTo({
    url: `/pages/product/index?barcode=${encodeURIComponent(barcode)}`,
  })
}
</script>

<template>
  <Screen>
    <!-- #header slot -->
    <template #header>
      <view class="
          top-0 z-10 flex items-center gap-2.5 bg-white px-3.5 py-3
          dark:bg-black
        " :class="{
          // 'bg-risk-t4': riskLevel === 't4',
          // 'bg-risk-t3': riskLevel === 't3',
          // 'bg-risk-t2': riskLevel === 't2',
          // 'bg-risk-t1': riskLevel === 't1',
          // 'bg-risk-t0': riskLevel === 't0',
          // 'bg-risk-unknown': riskLevel === 'unknown',
        }">
        <Button size="icon" variant="ghost" @click="goBack">
          <Icon name="arrowLeft" />
        </Button>
        <view class="flex flex-1 flex-col">
          <text class="text-sm font-bold">
            {{ ingredient?.name }}
          </text>
          <text class="text-xs font-semibold">
            {{ headerSubtitle }}
          </text>
        </view>
        <Button size="icon" variant="ghost" @click="shareToFriend">
          <Icon name="share" />
        </Button>
      </view>
    </template>

    <!-- #content slot -->
    <template #content>
      <StateView :state="pageState" :message="errorMessage" go-back-label="返回" @go-back="goBack">
        <!-- 内容区 -->
        <view class="flex flex-col gap-3 bg-background p-3">
          <Card>
            <!-- Hero 风险卡 -->
            <view class="hero-top p-3" :class="[
              `
                  hero-top-${riskConf.visualKey}
                `,
              themeStore.isDark ? 'dark-mode' : 'light-mode',
            ]">
              <view class="mb-2 flex items-start justify-between">
                <view>
                  <text class="text-foreground text-2xl font-extrabold">
                    {{ ingredient.name }}
                  </text>
                  <text class="text-muted-foreground mt-0.5 text-xs">
                    {{ ingredient.additive_code || "食品添加剂" }}
                  </text>
                </view>
                <view class="
                    risk-badge flex flex-shrink-0 items-center gap-1
                    rounded-md bg-risk-t3 px-2 py-1 text-xs font-bold
                    text-white
                  ">
                  <Icon name="alertTriangle" class="h-2.5 w-2.5" :size="10" />
                  <text>{{ riskConf.badge }}</text>
                </view>
              </view>

              <!-- 风险谱条 -->
              <view class="relative" style="margin: 4px 0">
                <view class="spectrum-bar h-[7px] rounded-full" :style="spectrumOpacityStyle" />
                <view v-if="riskConf.needleLeft !== null" class="
                    spectrum-needle bg-bg-card absolute top-1/2 h-[14px]
                    w-[14px] -translate-x-1/2 -translate-y-1/2 rounded-full
                    border-[2.5px] border-risk-t3
                  " :style="needleStyle" />
              </view>
              <view class="text-muted-foreground flex justify-between px-0.5 text-xs">
                <text>低风险</text>
                <text>中等</text>
                <text>高风险</text>
              </view>
            </view>

            <!-- Chips -->
            <view class="flex flex-wrap gap-1 p-3">
              <text v-if="ingredient.additive_code" class="
                  chip chip-red rounded-md px-2 py-0.5 text-xs font-medium
                ">
                {{ ingredient.additive_code }}
              </text>
              <text v-if="ingredient.function_type" class="
                  chip chip-red rounded-md px-2 py-0.5 text-xs font-medium
                ">
                {{ ingredient.function_type }}
              </text>
              <text class="
                  chip chip-neu rounded-md px-2 py-0.5 text-xs font-medium
                ">
                {{ source }}
              </text>
              <text v-if="pregnancyWarning" class="
                  chip chip-warn rounded-md px-2 py-0.5 text-xs
                  font-medium
                ">
                {{ pregnancyWarning }}
              </text>
              <template v-if="ingredient.alias?.length">
                <text v-for="alias in ingredient.alias" :key="alias" class="
                    chip chip-neu rounded-md px-2 py-0.5 text-xs
                    font-medium
                  ">
                  别名：{{ alias }}
                </text>
              </template>
            </view>
          </Card>
          <!-- 描述 -->
          <Card>
            <view v-if="summary">
              <view class="
                flex items-center gap-2  
              ">
                <view class="
                  flex size-6 items-center justify-center rounded-sm bg-blue-100
                ">
                  <Icon name="info" class="size-4 text-blue-500" />
                </view>
                <text class="text-foreground flex-1 text-base font-bold">
                  描述
                </text>
              </view>
              <Separator />
              <view>
                <text class="text-foreground text-sm">
                  {{ summary }}
                </text>
              </view>
            </view>
          </Card>
          <!-- AI 风险分析 -->
          <Card v-if="riskFactors.length > 0" class="!p-0">
            <Cell size="sm" class="px-4 pt-4">
              <template #title>
                <view class=" flex items-center gap-2">
                  <view class="
                   flex size-6  items-center justify-center
                  rounded-md bg-red-100
                ">
                    <Icon name="alertTriangle" class="size-4 text-red-400" />
                  </view>
                  <text class="text-base text-foreground font-medium">AI 风险分析</text>
                </view>
              </template>
              <template #value>
                <text class="ai-label">
                  AI
                </text>
              </template>
            </Cell>

            <Separator class="my-0" />

            <view class="flex flex-col gap-3 px-4 pb-4 mt-3">
              <template v-for="(item, i) in riskFactors" :key="i">
                <view class="flex items-start gap-2">
                  <view class="
                    mt-px flex size-4 items-center
                    justify-center rounded-sm bg-red-100
                  ">
                    <Icon name="x" class="size-4 text-red-400" />
                  </view>
                  <text class="text-foreground flex-1 text-sm">
                    {{ item }}
                  </text>
                </view>
              </template>

            </view>
          </Card>
          <!-- 风险管理信息 -->
          <Card v-if="hasRiskMgmt" class="!p-0">
            <Cell size="sm" class="px-4 pt-4">
              <template #title>
                <view class=" flex items-center gap-2">
                  <view class="
                  flex size-6  items-center justify-center
                  rounded-md bg-blue-100
                ">
                    <Icon name="alertCircle" class="size-4 text-blue-500" />
                  </view>
                  <text class="text-base text-foreground font-medium">标题</text>
                </view>
              </template>
            </Cell>
            <Separator class="my-0" />
            <view class="flex flex-col mb-1">
              <Cell size="sm" class="px-4" title="WHO 致癌等级" :value="ingredient?.who_level" />
              <Separator class="my-0" />
              <Cell size="sm" class="px-4" title="母婴等级" :value="maternalLevel" />
              <Separator class="my-0" />
              <Cell size="sm" class="px-4" title="使用限量" :value="usageLimit" />
              <Separator class="my-0" />
              <Cell size="sm" class="px-4" title="适用区域" :value="applicableRegion" />
              <Separator class="my-0" />
              <Cell size="sm" class="px-4" title="过敏信息" :value="ingredient?.allergen_info" />
              <Separator class="my-0" />
              <Cell size="sm" class="px-4 " title="执行标准" :value="ingredient?.standard_code" />
            </view>
          </Card>
          <!-- AI 使用建议 -->
          <Card v-if="suggestions.length > 0" class="!p-0">

            <Cell size="sm" class="px-4 pt-4 pb-0">
              <template #title>
                <view class="
                flex items-center gap-2
              ">
                  <view class="
                  flex h-5 w-5 flex-shrink-0 items-center justify-center
                  rounded-md bg-pink-100
                ">
                    <Icon name="check" class="h-3 w-3 text-pink-400" :size="12" />
                  </view>
                  <text class="text-foreground flex-1 text-sm font-bold">
                    AI 使用建议
                  </text>
                </view>
              </template>
              <template #value>
                <text class="ai-label">
                  AI
                </text>
              </template>
            </Cell>
            <Separator class="my-3" />

            <view class="flex flex-col gap-3 px-4 pb-4 mt-3">
              <view v-for="(s, i) in suggestions" :key="i" class="
                  flex items-start gap-2
                ">
                <view class="
                    mt-px flex h-4 w-4 flex-shrink-0 items-center
                    justify-center rounded-sm
                  " :class="s.type === 'positive' ? 'dot-good' : 'dot-warn'">
                  <Icon name="check" class="h-2.5 w-2.5" :class="s.type === 'positive'
                    ? 'text-green-500'
                    : `text-yellow-500`
                    " :size="10" />
                </view>
                <text class="text-foreground flex-1 text-sm ">
                  {{ s.text }}
                </text>
              </view>
            </view>
          </Card>

          <!-- 含此配料的产品 -->
          <Card v-if="relatedProducts.length > 0" class="!p-0">

            <CardHeader class="
                flex items-center gap-2 px-4 pt-4 pb-3
              ">
              <view class="
                  flex h-5 w-5 flex-shrink-0 items-center justify-center
                  rounded-md bg-blue-100
                ">
                <Icon name="shoppingCart" class="h-3 w-3 text-blue-500" :size="12" />
              </view>
              <text class="text-foreground flex-1 text-base font-bold">
                含此配料的产品
              </text>
            </CardHeader>
            <Separator class="my-0" />
            <view class="overflow-x-auto" style="scrollbar-width: none; -webkit-overflow-scrolling: touch">
              <view class="flex gap-2 p-3" style="width: max-content">
                <view v-for="p in relatedProducts" :key="p.id" class="
                    bg-bg-base border-border-c w-24 flex-shrink-0
                    cursor-pointer rounded-xl border p-2
                    active:opacity-70
                  " @click="goToProduct(p.barcode)">
                  <view class="
                      bg-bg-card mb-1.5 flex size-8 items-center
                      justify-center rounded-lg text-2xl
                    ">
                    {{ p.emoji }}
                  </view>
                  <text class="
                      text-foreground mb-1 block text-xs font-semibold
                    ">
                    {{ p.name }}
                  </text>
                  <text v-if="p.riskTag" class="
                      inline-block rounded px-1 py-px text-xs font-medium
                    " :class="p.riskTag === '高风险'
                      ? 'chip chip-red'
                      : 'chip chip-warn'
                      ">
                    {{ p.riskTag }}
                  </text>
                </view>
              </view>
            </view>
          </Card>
        </view>
      </StateView>
    </template>

    <!-- #footer slot -->
    <template #footer>
      <view
        class="flex items-center gap-3 px-3 py-3 bg-white/95 dark:bg-black/95 backdrop-saturate-[180%] backdrop-blur-[16px] shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.06)] dark:shadow-[0_-8rpx_32rpx_rgba(0,0,0,0.4)] border-t border-border">
        <Button size="lg" variant="secondary" class="flex-1 rounded-md " @click="goToAI">咨询 AI 助手</Button>
        <Button size="lg" variant="default" class="flex-1 rounded-md !text-white" @click="goToSearch">查看相关食品</Button>
      </view>
    </template>
  </Screen>
</template>

<style lang="scss" scoped>
// ── ing-hdr 颜色变量 ─────────────────────────────────────
// 暗色 risk header
.dark-mode .ing-hdr {
  background: #1a0808;
  border-bottom: 2px solid #7f1d1d;
}

.dark-mode .ing-hdr-title {
  color: #fca5a5;
}

.dark-mode .ing-hdr-sub {
  color: #f87171;
}

.dark-mode .ing-hdr-btn {
  background: rgba(248, 113, 113, 0.15);
}

.dark-mode .ing-hdr :deep(.icon-svg) {
  stroke: #f87171;
}

// 亮色 risk header
.light-mode .ing-hdr {
  background: #fff4f0;
  border-bottom: 2px solid #fecaca;
}

.light-mode .ing-hdr-title {
  color: #7f1d1d;
}

.light-mode .ing-hdr-sub {
  color: #ef4444;
}

.light-mode .ing-hdr-btn {
  background: rgba(220, 38, 38, 0.1);
}

.light-mode .ing-hdr :deep(.icon-svg) {
  stroke: #ef4444;
}

// ── Section Card ──────────────────────────────────────────
.sec-card {
  border-radius: 14px;
  overflow: hidden;
}

.dark-mode .sec-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.light-mode .sec-card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

// ── Hero Top ─────────────────────────────────────────────
.hero-top {
  border-bottom: 1px solid #fecaca;
}

.dark-mode .hero-top {
  background: linear-gradient(135deg, rgba(26, 8, 8, 0.6) 0%, transparent 100%);
  border-bottom: 1px solid #7f1d1d;
}

.light-mode .hero-top {
  background: linear-gradient(135deg, rgba(255, 244, 240, 0.6) 0%, transparent 100%);
  border-bottom: 1px solid #fecaca;
}

// Risk-level specific overrides
.hero-top-t4,
.hero-top-critical {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(26, 8, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #7f1d1d;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(255, 244, 240, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fecaca;
  }
}

.hero-top-t3,
.hero-top-high {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(26, 8, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #7f1d1d;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(255, 244, 240, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fecaca;
  }
}

.hero-top-t2,
.hero-top-medium {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(26, 20, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #78350f;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(255, 251, 235, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fde68a;
  }
}

.hero-top-t1,
.hero-top-low {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(5, 20, 10, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #166534;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(240, 253, 244, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #bbf7d0;
  }
}

.hero-top-t0,
.hero-top-safe {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(5, 20, 10, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #166534;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(240, 253, 244, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #bbf7d0;
  }
}

.hero-top-unknown {
  &.dark-mode {
    background: linear-gradient(135deg, rgba(20, 20, 20, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #374151;
  }

  &.light-mode {
    background: linear-gradient(135deg, rgba(245, 245, 245, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #e5e7eb;
  }
}

// ── AI 标签 ──────────────────────────────────────────────
.ai-label {
  font-size: 9.5px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

// ── Chips ────────────────────────────────────────────────
.dark-mode .chip-red {
  background: #450a0a;
  color: #fca5a5;
  border: 1px solid transparent;
}

.dark-mode .chip-warn {
  background: #3b1a00;
  color: #fcd34d;
  border: 1px solid transparent;
}

.dark-mode .chip-neu {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
}

.light-mode .chip-red {
  background: #fff0f0;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.light-mode .chip-warn {
  background: #fefce8;
  color: #a16207;
  border: 1px solid #fde68a;
}

.light-mode .chip-neu {
  background: rgba(0, 0, 0, 0.04);
  color: #4b5563;
}

// ── 风险谱条 ─────────────────────────────────────────────
.spectrum-bar {
  background: linear-gradient(to right, #22c55e 0%, #86efac 20%, #facc15 45%, #fb923c 65%, #ef4444 82%, #dc2626 100%);
}

// ── 建议图标 ─────────────────────────────────────────────
.dot-good {
  background: #f0fdf4;
}

.dark-mode .dot-good {
  background: #052e16;
}

.dot-warn {
  background: #fffbeb;
}

.dark-mode .dot-warn {
  background: #3b1a00;
}

// ── 底部栏 ───────────────────────────────────────────────
.bot-bar {
  background: rgba(255, 255, 255, 0.98);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.dark-mode .bot-bar {
  background: rgba(26, 26, 26, 0.98);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.dark-mode .btn-out {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.light-mode .btn-out {
  background: transparent;
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: var(--text-primary);
}
</style>
