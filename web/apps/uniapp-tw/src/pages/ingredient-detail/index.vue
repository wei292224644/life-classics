<script setup lang="ts">
import type { IngredientAnalysis } from "@/types/product";
import { onLoad } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import { useIngredientStore } from "@/store/ingredient";
import { useProductStore } from "@/store/product";
import { useThemeStore } from "@/store/theme";
import { getRiskConfig } from "@/utils/riskLevel";
import Icon from "@/components/ui/Icon.vue";
import Screen from "@/components/ui/Screen.vue";
import Button from "@/components/ui/Button.vue";
import StateView from "@/components/ui/StateView.vue";
// ── Store ────────────────────────────────────────────────
const ingStore = useIngredientStore();
const productStore = useProductStore();
const themeStore = useThemeStore();

const ingredient = computed(() => ingStore.current);
const fromProductName = computed(() => ingStore.fromProductName);

// ── 加载态 ───────────────────────────────────────────────
const isLoading = ref(false);
const errorMessage = ref<string>();

// ── 页面状态（用于 StateView） ───────────────────────────
const pageState = computed(() => {
  if (isLoading.value) return "loading";
  if (!ingredient.value) return "not_found";
  return "success";
});

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
    errorMessage.value = "数据加载失败，请返回重试";
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
  <Screen>
    <!-- #header slot -->
    <template #header>
      <view
        class="top-0 z-10 flex items-center gap-2.5 px-3.5 py-3"
        :class="{
          'bg-risk-t4': riskLevel === 't4',
          'bg-risk-t3': riskLevel === 't3',
          'bg-risk-t2': riskLevel === 't2',
          'bg-risk-t1': riskLevel === 't1',
          'bg-risk-t0': riskLevel === 't0',
          'bg-risk-unknown': riskLevel === 'unknown',
        }"
      >
        <Button size="icon" variant="ghost" @click="goBack">
          <Icon name="arrowLeft" />
        </Button>
        <view class="flex-1 flex flex-col">
          <text class="text-sm font-bold">{{ ingredient?.name }}</text>
          <text class="text-xs font-semibold">{{ headerSubtitle }}</text>
        </view>
        <Button size="icon" variant="ghost" @click="shareToFriend">
          <Icon name="share" />
        </Button>
      </view>
    </template>

    <!-- #content slot -->
    <template #content>
      <StateView
        :state="pageState"
        :message="errorMessage"
        go-back-label="返回"
        @go-back="goBack"
      >
        <template #default>
          <!-- 内容区 -->
          <view class="px-3 flex flex-col gap-3">
        <!-- Hero 风险卡 -->
        <view class="sec-card">
          <view
            class="hero-top p-3"
            :class="[
              `hero-top-${riskConf.visualKey}`,
              themeStore.isDark ? 'dark-mode' : 'light-mode',
            ]"
          >
            <view class="flex items-start justify-between mb-2">
              <view>
                <text class="text-[18px] font-extrabold text-text-primary">{{
                  ingredient.name
                }}</text>
                <text class="text-[11px] text-text-muted mt-0.5">{{
                  ingredient.additive_code || "食品添加剂"
                }}</text>
              </view>
              <view
                class="risk-badge bg-risk-t3 text-white px-[9px] py-1 rounded-[7px] text-[11px] font-bold flex items-center gap-1 flex-shrink-0"
              >
                <Icon name="alertTriangle" class="w-2.5 h-2.5" :size="10" />
                <text>{{ riskConf.badge }}</text>
              </view>
            </view>

            <!-- 风险谱条 -->
            <view class="relative" style="margin: 4px 0">
              <view
                class="spectrum-bar h-[7px] rounded-full"
                :style="spectrumOpacityStyle"
              />
              <view
                v-if="riskConf.needleLeft !== null"
                class="spectrum-needle absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[14px] h-[14px] rounded-full bg-bg-card border-[2.5px] border-risk-t3"
                :style="needleStyle"
              />
            </view>
            <view
              class="flex justify-between text-[9px] text-text-muted px-0.5"
            >
              <text>低风险</text>
              <text>中等</text>
              <text>高风险</text>
            </view>
          </view>

          <!-- Chips -->
          <view class="flex flex-wrap gap-[5px] p-3">
            <text
              v-if="ingredient.additive_code"
              class="chip chip-red text-[10.5px] font-medium px-2 py-0.5 rounded-md"
              >{{ ingredient.additive_code }}</text
            >
            <text
              v-if="ingredient.function_type"
              class="chip chip-red text-[10.5px] font-medium px-2 py-0.5 rounded-md"
              >{{ ingredient.function_type }}</text
            >
            <text
              class="chip chip-neu text-[10.5px] font-medium px-2 py-0.5 rounded-md"
              >{{ source }}</text
            >
            <text
              v-if="pregnancyWarning"
              class="chip chip-warn text-[10.5px] font-medium px-2 py-0.5 rounded-md"
              >{{ pregnancyWarning }}</text
            >
            <template v-if="ingredient.alias?.length">
              <text
                v-for="alias in ingredient.alias"
                :key="alias"
                class="chip chip-neu text-[10.5px] font-medium px-2 py-0.5 rounded-md"
              >
                别名：{{ alias }}
              </text>
            </template>
          </view>
        </view>

        <!-- 描述 -->
        <view v-if="summary" class="sec-card">
          <view
            class="flex items-center gap-2 px-3 py-[11px] border-b border-border-c"
          >
            <view
              class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-blue-100"
            >
              <Icon name="info" class="w-3 h-3 text-blue-500" :size="12" />
            </view>
            <text class="text-[13px] font-bold text-text-primary flex-1"
              >描述</text
            >
          </view>
          <view class="px-3 py-[11px]">
            <text class="text-[12px] text-text-secondary leading-[1.7]">{{
              summary
            }}</text>
          </view>
        </view>

        <!-- AI 风险分析 -->
        <view v-if="riskFactors.length > 0" class="sec-card">
          <view
            class="flex items-center gap-2 px-3 py-[11px] border-b border-border-c"
          >
            <view
              class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-red-100"
            >
              <Icon
                name="alertTriangle"
                class="w-3 h-3 text-red-400"
                :size="12"
              />
            </view>
            <text class="text-[13px] font-bold text-text-primary flex-1"
              >AI 风险分析</text
            >
            <text class="ai-label ml-auto">AI</text>
          </view>
          <view class="px-3 py-[11px] flex flex-col gap-2">
            <view
              v-for="(item, i) in riskFactors"
              :key="i"
              class="flex items-start gap-2"
            >
              <view
                class="w-[18px] h-[18px] rounded-[5px] flex items-center justify-center flex-shrink-0 mt-px bg-red-100"
              >
                <Icon name="x" class="w-2.5 h-2.5 text-red-400" :size="10" />
              </view>
              <text
                class="text-[12px] text-text-primary leading-[1.55] flex-1"
                >{{ item }}</text
              >
            </view>
          </view>
        </view>

        <!-- 风险管理信息 -->
        <view v-if="hasRiskMgmt" class="sec-card">
          <view
            class="flex items-center gap-2 px-3 py-[11px] border-b border-border-c"
          >
            <view
              class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-blue-100"
            >
              <Icon
                name="alertCircle"
                class="w-3 h-3 text-blue-500"
                :size="12"
              />
            </view>
            <text class="text-[13px] font-bold text-text-primary flex-1"
              >风险管理信息</text
            >
          </view>
          <view>
            <view
              v-if="ingredient.who_level"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border-c"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >WHO 致癌等级</text
              >
              <text class="text-[11.5px] font-medium text-risk-t4 text-right">{{
                ingredient.who_level
              }}</text>
            </view>
            <view
              v-if="maternalLevel"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border-c"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >母婴等级</text
              >
              <text class="text-[11.5px] font-medium text-risk-t4 text-right">{{
                maternalLevel
              }}</text>
            </view>
            <view
              v-if="usageLimit"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border-c"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >使用限量</text
              >
              <text
                class="text-[11.5px] font-medium text-text-primary text-right"
                >{{ usageLimit }}</text
              >
            </view>
            <view
              v-if="applicableRegion"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border-c"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >适用区域</text
              >
              <text
                class="text-[11.5px] font-medium text-text-primary text-right"
                >{{ applicableRegion }}</text
              >
            </view>
            <view
              v-if="ingredient.allergen_info"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border-c"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >过敏信息</text
              >
              <text
                class="text-[11.5px] font-medium text-text-primary text-right"
                >{{ ingredient.allergen_info }}</text
              >
            </view>
            <view
              v-if="ingredient.standard_code"
              class="flex justify-between items-start py-[9px] px-3 gap-2.5"
            >
              <text class="text-[11.5px] text-text-secondary flex-shrink-0"
                >执行标准</text
              >
              <text
                class="text-[11.5px] font-medium text-text-primary text-right"
                >{{ ingredient.standard_code }}</text
              >
            </view>
          </view>
        </view>

        <!-- AI 使用建议 -->
        <view v-if="suggestions.length > 0" class="sec-card">
          <view
            class="flex items-center gap-2 px-3 py-[11px] border-b border-border-c"
          >
            <view
              class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-pink-100"
            >
              <Icon name="check" class="w-3 h-3 text-pink-400" :size="12" />
            </view>
            <text class="text-[13px] font-bold text-text-primary flex-1"
              >AI 使用建议</text
            >
            <text class="ai-label ml-auto">AI</text>
          </view>
          <view class="px-3 py-[11px] flex flex-col gap-2">
            <view
              v-for="(s, i) in suggestions"
              :key="i"
              class="flex items-start gap-2"
            >
              <view
                class="w-[18px] h-[18px] rounded-[5px] flex items-center justify-center flex-shrink-0 mt-px"
                :class="s.type === 'positive' ? 'dot-good' : 'dot-warn'"
              >
                <Icon
                  name="check"
                  class="w-2.5 h-2.5"
                  :class="
                    s.type === 'positive' ? 'text-green-500' : 'text-yellow-500'
                  "
                  :size="10"
                />
              </view>
              <text
                class="text-[12px] text-text-primary leading-[1.55] flex-1"
                >{{ s.text }}</text
              >
            </view>
          </view>
        </view>

        <!-- 含此配料的产品 -->
        <view v-if="relatedProducts.length > 0" class="sec-card">
          <view
            class="flex items-center gap-2 px-3 py-[11px] border-b border-border-c"
          >
            <view
              class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-blue-100"
            >
              <Icon
                name="shoppingCart"
                class="w-3 h-3 text-blue-500"
                :size="12"
              />
            </view>
            <text class="text-[13px] font-bold text-text-primary flex-1"
              >含此配料的产品</text
            >
          </view>
          <view
            class="overflow-x-auto"
            style="scrollbar-width: none; -webkit-overflow-scrolling: touch"
          >
            <view class="flex gap-2 p-3" style="width: max-content">
              <view
                v-for="p in relatedProducts"
                :key="p.id"
                class="w-[86px] flex-shrink-0 bg-bg-base border border-border-c rounded-xl p-2 cursor-pointer active:opacity-70"
                @click="goToProduct(p.barcode)"
              >
                <view
                  class="w-full h-12 rounded-lg bg-bg-card flex items-center justify-center text-[20px] mb-1.5"
                >
                  {{ p.emoji }}
                </view>
                <text
                  class="text-[10px] font-semibold text-text-primary leading-[1.3] mb-1 block"
                  >{{ p.name }}</text
                >
                <text
                  v-if="p.riskTag"
                  class="text-[9px] font-medium px-[5px] py-px rounded inline-block"
                  :class="
                    p.riskTag === '高风险' ? 'chip chip-red' : 'chip chip-warn'
                  "
                >
                  {{ p.riskTag }}
                </text>
              </view>
            </view>
          </view>
        </view>
        </template>
      </StateView>
    </template>

    <!-- #footer slot -->
    <template #footer>
      <view
        v-if="ingredient"
        class="bot-bar sticky bottom-0 z-10 px-3 py-2 flex gap-2 h-16"
      >
        <button
          class="btn-out flex-1 rounded-xl py-3 text-[12px] font-semibold text-center cursor-pointer active:scale-[0.97]"
          @click="goToAI"
        >
          咨询 AI 助手
        </button>
        <button
          class="flex-1 rounded-xl py-3 text-[12px] font-semibold text-white text-center cursor-pointer active:scale-[0.97]"
          style="
            background: linear-gradient(
              135deg,
              var(--accent-pink-light),
              var(--accent-pink)
            );
            box-shadow: 0 4px 12px rgba(225, 29, 72, 0.3);
          "
          @click="goToSearch"
        >
          查看相关食品
        </button>
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
  background: linear-gradient(
    135deg,
    rgba(255, 244, 240, 0.6) 0%,
    transparent 100%
  );
  border-bottom: 1px solid #fecaca;
}

// Risk-level specific overrides
.hero-top-t4,
.hero-top-critical {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(26, 8, 8, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #7f1d1d;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(255, 244, 240, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #fecaca;
  }
}
.hero-top-t3,
.hero-top-high {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(26, 8, 8, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #7f1d1d;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(255, 244, 240, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #fecaca;
  }
}
.hero-top-t2,
.hero-top-medium {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(26, 20, 8, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #78350f;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(255, 251, 235, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #fde68a;
  }
}
.hero-top-t1,
.hero-top-low {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(5, 20, 10, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #166534;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(240, 253, 244, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #bbf7d0;
  }
}
.hero-top-t0,
.hero-top-safe {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(5, 20, 10, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #166534;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(240, 253, 244, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #bbf7d0;
  }
}
.hero-top-unknown {
  &.dark-mode {
    background: linear-gradient(
      135deg,
      rgba(20, 20, 20, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #374151;
  }
  &.light-mode {
    background: linear-gradient(
      135deg,
      rgba(245, 245, 245, 0.6) 0%,
      transparent 100%
    );
    border-bottom: 1px solid #e5e7eb;
  }
}

// ── AI 标签 ──────────────────────────────────────────────
.ai-label {
  font-size: 9.5px;
  font-weight: 700;
  background: linear-gradient(
    135deg,
    var(--accent-pink-light),
    var(--accent-pink)
  );
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
  background: linear-gradient(
    to right,
    #22c55e 0%,
    #86efac 20%,
    #facc15 45%,
    #fb923c 65%,
    #ef4444 82%,
    #dc2626 100%
  );
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
