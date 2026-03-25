<script setup lang="ts">
import type { IngredientAnalysis } from "@/types/product";
import { onLoad } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import { useIngredientStore } from "@/store/ingredient";
import { useProductStore } from "@/store/product";
import { useThemeStore } from "@/store/theme";
import { getRiskConfig } from "@/utils/riskLevel";
import Icon from "@/components/ui/Icon.vue";

// ── Store ────────────────────────────────────────────────
const ingStore = useIngredientStore();
const productStore = useProductStore();
const themeStore = useThemeStore();

const ingredient = computed(() => ingStore.current);
const fromProductName = computed(() => ingStore.fromProductName);

// ── 加载态 ───────────────────────────────────────────────
const isLoading = ref(false);

// ── URL 路由参数（ingredientId 为必传，fromProductName 可选） ──
onLoad(async (options) => {
  const id = options?.ingredientId ? Number(options.ingredientId) : null;
  const fpn = options?.fromProductName
    ? decodeURIComponent(options.fromProductName)
    : null;

  if (ingStore.current) {
    if (fpn) {
      ingStore.set(ingStore.current, fpn);
    }
    return;
  }

  if (!id) {
    return;
  }

  const fromProduct = productStore.product?.ingredients?.find(
    (i) => i.id === id,
  );
  if (fromProduct) {
    ingStore.set(fromProduct, fpn ?? productStore.product?.name);
    return;
  }

  isLoading.value = true;
  try {
    const res = await new Promise<UniApp.RequestSuccessCallbackResult>(
      (resolve, reject) => {
        uni.request({
          url: `${import.meta.env.VITE_API_BASE_URL}/api/ingredient/${id}`,
          success: resolve,
          fail: reject,
        });
      },
    );
    if (res.statusCode === 200 && res.data) {
      const data = res.data as Record<string, unknown>;
      ingStore.set(data as any, fpn ?? undefined);
    }
  } catch {
    // 静默失败，error-state 会兜底显示
  } finally {
    isLoading.value = false;
  }
});

// ── 风险等级 ─────────────────────────────────────────────
const riskLevel = computed(() => ingredient.value?.analysis?.level ?? null);
const riskConf = computed(() => getRiskConfig(riskLevel.value));

// ── Header 副标题 ────────────────────────────────────────
const headerSubtitle = computed(() => {
  if (fromProductName.value) {
    return `来自：${fromProductName.value}`;
  }
  return riskConf.value.subtitleNoProduct;
});

// ── Risk class ───────────────────────────────────────────
const riskClass = computed(() => `risk-${riskConf.value.visualKey}`);

const spectrumOpacityStyle = computed(() =>
  riskConf.value.needleLeft === null ? { opacity: "0.4" } : {},
);

// 谱条指针从右侧计算（设计稿使用 right: 14% 等）
const needleRight = computed(() => {
  const left = riskConf.value.needleLeft;
  if (left === null) {
    return null;
  }
  return `${100 - Number.parseFloat(left) - 4}%`;
});

const needleStyle = computed(() =>
  needleRight.value ? { right: needleRight.value } : {},
);

// ── 解析 analysis.results ────────────────────────────────
function safeResults(
  analysis: IngredientAnalysis | undefined,
): Record<string, unknown> {
  if (!analysis?.results) {
    return {};
  }
  if (
    typeof analysis.results === "object" &&
    analysis.results !== null &&
    !Array.isArray(analysis.results)
  ) {
    return analysis.results as Record<string, unknown>;
  }
  return {};
}

// Mock 兜底数据
const MOCK_RESULTS: Record<string, unknown> = {
  summary:
    "香草精是一种广泛使用的食品香料，主要成分为香兰素（vanillin），可天然提取自香草豆荚，也可人工合成。常用于烘焙食品、甜点、饮料、冰淇淋等中增香。天然香草精含有超过200种风味化合物，香气更为复杂细腻。",
  risk_factors: [
    "市售香草精多为人工合成香兰素，与天然香草精成分存在差异",
    "长期大量摄入人工合成香兰素可能对肝脏产生轻微影响",
    "极少数人群可能出现过敏反应，表现为皮肤瘙痒或消化不适",
  ],
  suggestions: [
    { text: "正常烹饪用量（每次数滴）在成人中是安全的", type: "positive" },
    {
      text: "购买时注意区分天然香草精（vanilla extract）与人工香草精（artificial vanilla）",
      type: "conditional",
    },
    { text: "婴幼儿辅食建议使用天然来源香料并控制用量", type: "conditional" },
  ],
};

const results = computed<Record<string, unknown>>(() => {
  const raw = safeResults(ingredient.value?.analysis);
  const hasRealData = raw.summary || raw.risk_factors || raw.suggestions;
  return hasRealData ? raw : MOCK_RESULTS;
});

const summary = computed(() => {
  const s = results.value.summary;
  return typeof s === "string" ? s : null;
});

const pregnancyWarning = computed(() => {
  const w = results.value.pregnancy_warning;
  return typeof w === "string" ? w : null;
});

const source = computed(() => {
  const s = results.value.source;
  return typeof s === "string" ? s : "化学合成";
});

const maternalLevel = computed(() => {
  const v = results.value.maternal_level;
  return typeof v === "string" ? v : null;
});

const usageLimit = computed(() => {
  const v = results.value.usage_limit;
  return typeof v === "string" ? v : null;
});

const applicableRegion = computed(() => {
  const v = results.value.applicable_region;
  return typeof v === "string" ? v : null;
});

const riskFactors = computed(() => {
  const rf = results.value.risk_factors;
  return Array.isArray(rf)
    ? rf.filter((x): x is string => typeof x === "string")
    : [];
});

interface Suggestion {
  text: string;
  type: "positive" | "conditional";
}

const suggestions = computed((): Suggestion[] => {
  const raw = results.value.suggestions;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map((item: unknown) => {
    const s = item as Record<string, unknown>;
    const text = typeof s?.text === "string" ? s.text : String(item);
    const type: "positive" | "conditional" =
      s?.type === "positive" ? "positive" : "conditional";
    return { text, type };
  });
});

const hasRiskMgmt = computed(
  () =>
    !!(
      ingredient.value?.who_level ||
      ingredient.value?.allergen_info ||
      ingredient.value?.standard_code ||
      maternalLevel.value ||
      usageLimit.value ||
      applicableRegion.value
    ),
);

interface RelatedProduct {
  id: number;
  name: string;
  barcode: string;
  emoji: string;
  riskTag?: string;
  image_url_list?: string[];
}

const MOCK_RELATED_PRODUCTS: RelatedProduct[] = [
  {
    id: 1,
    name: "午餐肉罐头",
    barcode: "6901234567890",
    emoji: "🥫",
    riskTag: "高风险",
  },
  {
    id: 2,
    name: "火腿肠",
    barcode: "6901234567891",
    emoji: "🌭",
    riskTag: "高风险",
  },
  {
    id: 3,
    name: "培根片",
    barcode: "6901234567892",
    emoji: "🥩",
    riskTag: "中等风险",
  },
  {
    id: 4,
    name: "烤肠",
    barcode: "6901234567893",
    emoji: "🍖",
    riskTag: "高风险",
  },
];

const relatedProducts = computed(() => {
  if (!ingredient.value) {
    return [];
  }
  return MOCK_RELATED_PRODUCTS;
});

const heroEmoji = computed(() => {
  const n = ingredient.value?.name ?? "";
  if (n.includes("苹果")) {
    return "🍎";
  }
  if (n.includes("草莓")) {
    return "🍓";
  }
  if (n.includes("柠檬")) {
    return "🍋";
  }
  if (n.includes("牛奶")) {
    return "🥛";
  }
  return "🧪";
});

// ── 导航 ─────────────────────────────────────────────────
function goBack() {
  uni.navigateBack();
}

function shareToFriend() {
  if (!ingredient.value) {
    return;
  }
  uni.showShareMenu({
    withShareTicket: true,
    menus: ["shareAppMessage", "shareTimeline"],
  });
}

function goToAI() {
  if (!ingredient.value) {
    return;
  }
  uni.navigateTo({
    url: `/pages/chat/index?context=${encodeURIComponent(ingredient.value.name)}`,
  });
}

function goToSearch() {
  if (!ingredient.value) {
    return;
  }
  uni.navigateTo({
    url: `/pages/search/index?ingredientId=${ingredient.value.id}`,
  });
}

function goToProduct(barcode: string) {
  uni.navigateTo({
    url: `/pages/product/index?barcode=${encodeURIComponent(barcode)}`,
  });
}
</script>

<template>
  <view class="h-screen bg-background flex flex-col relative overflow-hidden">
    <!-- ── 自定义 Header ──────────────────────────── -->
    <view
      class="absolute top-0 left-0 right-0 z-[100] shrink-0 transition-all duration-300 bg-transparent"
      :class="riskClass"
    >
      <!-- 状态栏占位（动态高度） -->
      <view :style="{ height: `${themeStore.statusBarHeight}px` }" />
      <view class="flex items-center px-4 pb-4 gap-[16rpx]">
        <button
          class="w-4 h-4 rounded-xl flex items-center justify-center shrink-0 p-0 m-0"
          @click="goBack"
        >
          <Icon name="arrowLeft" :size="24" />
        </button>
        <view class="flex-1 flex flex-col gap-[2rpx] pr-[96rpx]">
          <text
            class="header-title text-[34rpx] leading-[1.15] font-bold tracking-[0.01em]"
            >{{ ingredient?.name ?? "配料详情" }}</text
          >
          <text
            class="header-subtitle text-[22rpx] leading-[1.25] font-medium tracking-[0.02em]"
            >{{ headerSubtitle }}</text
          >
        </view>
        <button
          class="header-btn share-btn w-8 h-8 rounded-xl flex items-center justify-center shrink-0 p-0 m-0"
          @click="shareToFriend"
        >
          <Icon name="share" :size="24" />
        </button>
      </view>
    </view>

    <!-- ── 加载态 ──────────────────────────────── -->
    <view v-if="isLoading" class="flex-1 flex items-center justify-center">
      <text class="text-xl text-muted-foreground">加载中...</text>
    </view>

    <!-- ── 无数据错误态 ──────────────────────────── -->
    <view
      v-else-if="!ingredient"
      class="flex-1 flex flex-col items-center justify-center gap-8 px-12 py-20"
    >
      <text class="text-xl text-secondary text-center"
        >数据加载失败，请返回重试</text
      >
      <button
        class="px-12 py-5 rounded-xl bg-card border border-border text-foreground text-xl"
        @click="goBack"
      >
        返回
      </button>
    </view>

    <!-- ── 内容区 ────────────────────────────────── -->
    <scroll-view
      v-else
      scroll-y
      :show-scrollbar="false"
      class="flex-1 overflow-hidden w-full box-border"
    >
      <view class="px-3 pt-0 bg-background">
        <!-- Hero 风险卡 -->
        <view
          class="section-card hero-card bg-card mb-4 box-border w-full rounded-none overflow-hidden p-0 mx-[-24rpx] mt-0 border-none"
        >
          <view class="hero-top px-5 pt-24 pb-5">
            <view class="hero-emoji text-center leading-none">
              {{ heroEmoji }}
            </view>
            <view
              class="hero-name-row flex items-end justify-between gap-4 mb-6"
            >
              <view class="hero-name-wrap flex-1 flex flex-col gap-0.5">
                <text class="hero-name text-[36rpx] font-bold leading-tight">{{
                  ingredient.name
                }}</text>
                <text class="hero-code text-[24rpx] font-normal">{{
                  ingredient.additive_code || "食品配料"
                }}</text>
              </view>
              <view
                class="risk-badge flex items-center gap-2 px-4 py-2 rounded-2xl shrink-0"
                :class="riskClass"
              >
                <text class="badge-icon text-base">{{ riskConf.icon }}</text>
                <text class="badge-text text-sm font-semibold">{{
                  riskConf.badge
                }}</text>
              </view>
            </view>

            <!-- 风险谱条 -->
            <view class="spectrum-wrap relative mb-1">
              <view
                class="spectrum-bar h-3 rounded-xl"
                :style="spectrumOpacityStyle"
              >
                <!-- 色阶渐变已通过 CSS 实现 -->
              </view>
              <view
                v-if="riskConf.needleLeft !== null"
                class="spectrum-needle absolute top-1/2 -translate-y-1/2 rounded-full"
                :style="needleStyle"
              />
            </view>
            <view class="spectrum-labels flex justify-between mt-1">
              <text class="spec-label-safe text-xs text-secondary">低风险</text>
              <text class="spec-label-mid text-xs text-secondary">中等</text>
              <text class="spec-label-danger text-xs text-secondary"
                >高风险</text
              >
            </view>
          </view>

          <!-- Chips -->
          <view class="chips-row flex flex-wrap gap-2 px-4 py-4">
            <text
              v-if="ingredient.additive_code"
              class="chip chip-func text-sm px-4 py-0.5 rounded-lg font-medium"
              >{{ ingredient.additive_code }}</text
            >
            <text
              v-if="ingredient.function_type"
              class="chip chip-func text-sm px-4 py-0.5 rounded-lg font-medium"
              >{{ ingredient.function_type }}</text
            >
            <text
              v-if="source"
              class="chip chip-neu text-sm px-4 py-0.5 rounded-lg font-medium"
              >{{ source }}</text
            >
            <text
              v-if="pregnancyWarning"
              class="chip chip-warn text-sm px-4 py-0.5 rounded-lg font-medium"
              >{{ pregnancyWarning }}</text
            >
            <template v-if="ingredient.alias?.length">
              <text
                v-for="alias in ingredient.alias"
                :key="alias"
                class="chip chip-neu text-sm px-4 py-0.5 rounded-lg font-medium"
              >
                别名：{{ alias }}
              </text>
            </template>
          </view>
        </view>

        <!-- 描述 -->
        <view
          v-if="summary"
          class="section-card bg-card rounded-2xl p-5 mb-4 border border-border box-border w-full overflow-hidden"
        >
          <view
            class="flex items-center gap-4 mb-5 pb-4 border-b border-border"
          >
            <view
              class="section-icon-wrap icon-bg-blue w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            >
              <Icon name="info" class="w-5 h-5 text-current" :size="20" />
            </view>
            <text class="text-lg font-bold text-foreground flex-1">描述</text>
            <text
              class="ai-label text-sm font-bold px-3 py-0.5 rounded text-white"
              >AI</text
            >
          </view>
          <text class="text-base text-secondary leading-relaxed">{{
            summary
          }}</text>
        </view>

        <!-- AI 风险分析 -->
        <view
          v-if="riskFactors.length > 0"
          class="section-card bg-card rounded-2xl p-5 mb-4 border border-border box-border w-full overflow-hidden"
        >
          <view
            class="flex items-center gap-4 mb-5 pb-4 border-b border-border"
          >
            <view
              class="section-icon-wrap icon-bg-red w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            >
              <Icon
                name="alertTriangle"
                class="w-5 h-5 text-current"
                :size="20"
              />
            </view>
            <text class="text-lg font-bold text-foreground flex-1"
              >AI 风险分析</text
            >
            <text
              class="ai-label text-sm font-bold px-3 py-0.5 rounded text-white"
              >AI</text
            >
          </view>
          <view class="list-items flex flex-col gap-4">
            <view
              v-for="(item, i) in riskFactors"
              :key="i"
              class="flex items-start gap-4"
            >
              <view
                class="list-item-icon icon-x w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold shrink-0 mt-0.5"
              >
                ✕
              </view>
              <text class="text-lg text-secondary leading-relaxed flex-1">{{
                item
              }}</text>
            </view>
          </view>
        </view>

        <!-- 风险管理信息 -->
        <view
          v-if="hasRiskMgmt"
          class="section-card bg-card rounded-2xl p-5 mb-4 border border-border box-border w-full overflow-hidden"
        >
          <view
            class="flex items-center gap-4 mb-5 pb-4 border-b border-border"
          >
            <view
              class="section-icon-wrap icon-bg-purple w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            >
              <Icon
                name="alertCircle"
                class="w-5 h-5 text-current"
                :size="20"
              />
            </view>
            <text class="text-lg font-bold text-foreground flex-1"
              >风险管理信息</text
            >
          </view>
          <view class="kv-table flex flex-col gap-4">
            <view
              v-if="ingredient.who_level"
              class="kv-row flex items-start gap-4"
            >
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >WHO 致癌等级</text
              >
              <text
                class="kv-value kv-value-red text-lg text-foreground flex-1 leading-relaxed"
                >{{ ingredient.who_level }}</text
              >
            </view>
            <view v-if="maternalLevel" class="kv-row flex items-start gap-4">
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >母婴等级</text
              >
              <text
                class="kv-value kv-value-red text-lg text-foreground flex-1 leading-relaxed"
                >{{ maternalLevel }}</text
              >
            </view>
            <view v-if="usageLimit" class="kv-row flex items-start gap-4">
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >使用限量</text
              >
              <text
                class="kv-value text-lg text-foreground flex-1 leading-relaxed"
                >{{ usageLimit }}</text
              >
            </view>
            <view v-if="applicableRegion" class="kv-row flex items-start gap-4">
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >适用区域</text
              >
              <text
                class="kv-value text-lg text-foreground flex-1 leading-relaxed"
                >{{ applicableRegion }}</text
              >
            </view>
            <view
              v-if="ingredient.allergen_info"
              class="kv-row flex items-start gap-4"
            >
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >过敏信息</text
              >
              <text
                class="kv-value text-lg text-foreground flex-1 leading-relaxed"
                >{{ ingredient.allergen_info }}</text
              >
            </view>
            <view
              v-if="ingredient.standard_code"
              class="kv-row flex items-start gap-4"
            >
              <text
                class="kv-key text-base text-muted-foreground w-[200rpx] shrink-0 pt-0.5"
                >执行标准</text
              >
              <text
                class="kv-value text-lg text-foreground flex-1 leading-relaxed"
                >{{ ingredient.standard_code }}</text
              >
            </view>
          </view>
        </view>

        <!-- AI 使用建议 -->
        <view
          v-if="suggestions.length > 0"
          class="section-card bg-card rounded-2xl p-5 mb-4 border border-border box-border w-full overflow-hidden"
        >
          <view
            class="flex items-center gap-4 mb-5 pb-4 border-b border-border"
          >
            <view
              class="section-icon-wrap icon-bg-green w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            >
              <Icon name="check" class="w-5 h-5 text-current" :size="20" />
            </view>
            <text class="text-lg font-bold text-foreground flex-1"
              >AI 使用建议</text
            >
            <text
              class="ai-label text-sm font-bold px-3 py-0.5 rounded text-white"
              >AI</text
            >
          </view>
          <view class="list-items flex flex-col gap-4">
            <view
              v-for="(s, i) in suggestions"
              :key="i"
              class="flex items-start gap-4"
            >
              <view
                class="list-item-icon w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold shrink-0 mt-0.5"
                :class="
                  s.type === 'positive'
                    ? 'icon-check-green'
                    : `
                  icon-check-yellow
                `
                "
              >
                ✓
              </view>
              <text class="text-lg text-secondary leading-relaxed flex-1">{{
                s.text
              }}</text>
            </view>
          </view>
        </view>

        <!-- 含此配料的产品 -->
        <view
          v-if="relatedProducts.length > 0"
          class="section-card bg-card rounded-2xl p-5 mb-4 border border-border box-border w-full overflow-hidden"
        >
          <view
            class="flex items-center gap-4 mb-5 pb-4 border-b border-border"
          >
            <view
              class="section-icon-wrap icon-bg-orange w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            >
              <Icon
                name="shoppingCart"
                class="w-5 h-5 text-current"
                :size="20"
              />
            </view>
            <text class="text-lg font-bold text-foreground flex-1"
              >含此配料的产品</text
            >
          </view>
          <scroll-view scroll-x enable-flex class="related-scroll">
            <view class="related-inner flex flex-row gap-5 w-max pb-2">
              <view
                v-for="p in relatedProducts"
                :key="p.id"
                class="related-card flex flex-col items-center gap-3 cursor-pointer shrink-0 active:opacity-70"
                @click="goToProduct(p.barcode)"
              >
                <view
                  class="related-img-wrap w-[172rpx] h-[172rpx] rounded-xl overflow-hidden bg-background border border-border"
                >
                  <image
                    v-if="p.image_url_list?.[0]"
                    :src="p.image_url_list[0]"
                    class="related-img w-full h-full"
                    mode="aspectFill"
                  />
                  <view
                    v-else
                    class="related-img-placeholder w-full h-full flex items-center justify-center text-6xl"
                  >
                    {{ p.emoji }}
                  </view>
                </view>
                <text
                  class="related-name text-base text-secondary text-center leading-tight w-full"
                  >{{ p.name }}</text
                >
                <text
                  v-if="p.riskTag"
                  class="related-risk-tag text-xs px-3 py-0.5 rounded font-medium inline-block"
                  :class="[
                    p.riskTag === '高风险'
                      ? `
                    risk-high
                  `
                      : `risk-med`,
                  ]"
                >
                  {{ p.riskTag }}
                </text>
              </view>
            </view>
          </scroll-view>
        </view>

        <!-- 底部安全距离 -->
        <view class="h-[180rpx]" />
      </view>
    </scroll-view>

    <!-- ── 底部操作栏 ──────────────────────────────── -->
    <view
      v-if="ingredient"
      class="bottom-bar fixed bottom-0 left-0 right-0 px-2 py-2 border-t border-border flex gap-3 z-[100]"
    >
      <button
        class="bar-btn bar-btn-ghost flex-1 h-12 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold p-0 text-foreground active:opacity-80"
        @click="goToSearch"
      >
        <Icon name="search" class="w-5 h-5 text-current" :size="20" />
        <text>添加到记录</text>
      </button>
      <button
        class="bar-btn bar-btn-primary flex-1 h-12 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold p-0 text-white border-none active:opacity-80"
        @click="goToAI"
      >
        <Icon name="messageCircle" class="w-5 h-5 text-current" :size="20" />
        <text>咨询 AI 助手</text>
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

// ── Header ──────────────────────────────────────────────

.header-btn {
  background: transparent;
  color: var(--color-foreground);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  border: none;

  :deep(.icon-svg) {
    color: var(--risk-btn-color);
  }
}

.header-title {
  color: var(--color-foreground);
}

.dark .header-subtitle {
  color: color-mix(in oklch, var(--color-foreground) 54%, transparent);
}

// ── Section Card 通用 ────────────────────────────────────
.section-card {
  box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.06);
}

.dark .section-card {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.25);
}

.section-icon-wrap {
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

.ai-label {
  background: var(--ai-label-bg);
  letter-spacing: 0.05em;
}

// ── Hero 风险卡 ──────────────────────────────────────────
.section-card.hero-card {
  box-shadow: none;
}

.hero-top {
  background: linear-gradient(145deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%);
  min-height: 420rpx;
}

.dark .hero-top {
  background: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 50%, #151515 100%);
}

.hero-emoji {
  font-size: 110rpx;
  margin-bottom: 20rpx;
  filter: drop-shadow(0 8rpx 18rpx rgba(0, 0, 0, 0.18));
}

.hero-name {
  color: var(--color-foreground);
}

.hero-code {
  color: color-mix(in oklch, var(--color-foreground) 58%, transparent);
}

.risk-badge {
  background: color-mix(in oklch, var(--risk-badge-bg) 24%, transparent);
  border: 1px solid color-mix(in oklch, var(--risk-badge-bg) 36%, transparent);
  backdrop-filter: blur(8px);
}

.badge-text {
  color: var(--risk-btn-color);
}

// ── 风险谱条 ─────────────────────────────────────────────
.spectrum-bar {
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
  width: 28rpx;
  height: 28rpx;
  background: var(--color-card);
  border: 5rpx solid var(--color-risk-t4);
  box-shadow: 0 2rpx 6rpx
    color-mix(in oklch, oklch(55% 0.2 25) 35%, transparent);
}

// ── Chips ────────────────────────────────────────────────
.chips-row {
  background: var(--color-background);
  border-top-left-radius: 28rpx;
  border-top-right-radius: 28rpx;
  margin-top: -8rpx;
}

.chip {
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
    border: 1px solid
      color-mix(in oklch, var(--color-secondary) 15%, transparent);
  }
}

// ── KV 表格 ──────────────────────────────────────────────
.kv-value {
  &.kv-value-red {
    color: var(--color-risk-t4);
  }
}

// ── 列表项（风险分析 / 使用建议） ───────────────────────────
.list-item-icon {
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

// ── 相关产品横向滚动 ─────────────────────────────────────
.related-scroll {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }
  &::-webkit-scrollbar {
    display: none;
  }
}

.related-name {
  line-clamp: 2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-risk-tag {
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
  --bottom-bar-shadow: 0 -8rpx 32rpx rgba(0, 0, 0, 0.06);
  background: color-mix(in oklch, var(--color-background) 95%, transparent);
  backdrop-filter: saturate(180%) blur(14px);
  padding-bottom: max(16rpx, env(safe-area-inset-bottom));
  box-shadow: var(--bottom-bar-shadow);
}

.bar-btn-ghost {
  background: color-mix(in oklch, var(--color-foreground) 6%, transparent);
  border: 1px solid
    color-mix(in oklch, var(--color-foreground) 10%, transparent);
}

.bar-btn-primary {
  background: linear-gradient(
    135deg,
    var(--color-accent),
    color-mix(in oklch, var(--color-accent) 80%, #f472b6)
  );
  box-shadow: 0 8rpx 22rpx
    color-mix(in oklch, var(--color-accent) 32%, transparent);

  .dark & {
    background: var(--color-accent);
    color: #ffffff;
  }
}
</style>
