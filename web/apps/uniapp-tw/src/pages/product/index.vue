<template>
  <ToastContainer />
  <Screen @scroll="onScroll">
    <template #content>
      <view class="pb-10 bg-background">
        <ProductHeader
          ref="headerRef"
          :name="store.product?.name ?? ''"
          :overall-risk-level="overallRiskLevel"
        />

        <StateView
          :state="store.state"
          :message="
            store.state === 'error'
              ? store.errorMessage || '网络请求失败'
              : undefined
          "
          go-back-label="返回重新扫码"
          action-label="重试"
          @go-back="goBack"
          @action="load"
        >
          <view>
            <view
              class="relative overflow-hidden flex flex-col items-center justify-center w-full h-[520rpx]"
            >
              <image
                v-if="store.product?.image_url_list?.[0]"
                :src="store.product?.image_url_list?.[0] || ''"
                class="absolute inset-0 w-full h-full"
                mode="aspectFill"
              />
              <view
                :class="[
                  'absolute right-4 bottom-4 rounded-sm px-4 py-2 flex items-center gap-2 z-10 border border-border shadow-md',
                  `bg-risk-${overallRiskLevel}/10`,
                  `border-risk-${overallRiskLevel}/60`,
                  `shadow-risk-${overallRiskLevel}/20`,
                ]"
              >
                <Icon
                  :name="riskConfig.icon as any"
                  size="22"
                  :class="'text-risk-' + overallRiskLevel"
                />
                <text
                  :class="`text-sm font-semibold text-risk-${overallRiskLevel}`"
                  >{{ riskConfig.badge }}</text
                >
              </view>
            </view>

            <!-- ── 内容区 ────────────────────────────────── -->
            <view class="px-3 gap-4 flex flex-col pt-4">
              <!-- 营养成分卡片 -->
              <Card
                class="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards] nutrition-card"
              >
                <view
                  class="nutrition-glow absolute top-0 left-0 right-0 h-px"
                />
                <view class="mb-3">
                  <text class="font-bold tracking-tight text-foreground text-xl"
                    >营养成分</text
                  >
                </view>
                <view class="grid grid-cols-2 gap-4 mb-4">
                  <view
                    v-for="item in primaryNutritions"
                    :key="item.name"
                    class="flex flex-col"
                  >
                    <text
                      class="text-sm tracking-widest uppercase mb-0.5 text-muted-foreground"
                      >{{ item.name }}</text
                    >
                    <text
                      class="text-4xl font-bold tracking-[-0.03em] leading-none mt-0.5 text-foreground [font-variant-numeric:tabular-nums]"
                      >{{
                        formatDecimalString(item.value, {
                          maxFractionDigits: 0,
                        })
                      }}</text
                    >
                    <text class="text-sm mt-0.5 text-muted-foreground">{{
                      formatNutritionUnit(item)
                    }}</text>
                  </view>
                </view>
                <button
                  type="button"
                  class="w-full flex items-center justify-center gap-2 py-2 bg-transparent cursor-pointer active:bg-muted/10"
                  :aria-expanded="nutrExpanded"
                  @click="nutrExpanded = !nutrExpanded"
                >
                  <Icon
                    name="chevronDown"
                    class="w-4 h-4 transition-transform duration-300 text-muted-foreground"
                    :class="{ 'rotate-180': nutrExpanded }"
                  />
                  <text class="text-sm font-medium text-muted-foreground">{{
                    nutrExpanded ? "收起详细营养成分" : "查看详细营养成分"
                  }}</text>
                </button>
                <view
                  v-show="nutrExpanded"
                  class="border-t border-border pt-4 mt-1"
                >
                  <view
                    v-for="item in detailNutritions"
                    :key="item.name"
                    class="flex justify-between py-2 border-b border-border text-sm last:border-b-0"
                  >
                    <text class="text-secondary-foreground">{{
                      item.name
                    }}</text>
                    <text
                      class="text-foreground font-medium [font-variant-numeric:tabular-nums]"
                      >{{ formatNutritionValueCompact(item) }}</text
                    >
                  </view>
                </view>
              </Card>

              <!-- 配料与风险 -->
              <IngredientSection :ingredients="mockIngredients" />

              <!-- 健康益处卡片 -->
              <Card
                class="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards]"
              >
                <view class="mb-3">
                  <text class="font-semibold tracking-tight text-foreground"
                    >健康益处</text
                  >
                </view>
                <view class="flex flex-col gap-3.5">
                  <view
                    v-for="(text, idx) in healthTexts"
                    :key="idx"
                    class="flex items-center gap-3"
                  >
                    <Icon name="check" :size="24" />
                    <text
                      class="text-sm leading-relaxed flex-1 text-secondary-foreground"
                      >{{ text }}</text
                    >
                  </view>
                </view>
              </Card>

              <!-- AI 健康建议卡片 -->
              <Card
                class="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards]"
              >
                <view class="mb-3 flex items-center gap-0.5">
                  <Icon
                    name="star"
                    :size="20"
                    class="shrink-0 text-orange-500"
                  />
                  <text class="font-semibold">AI 健康建议</text>
                </view>
                <text
                  class="text-sm leading-relaxed text-secondary-foreground"
                  >{{ adviceText }}</text
                >
              </Card>
            </view>
          </view>
        </StateView>
      </view>
    </template>
    <template #footer>
      <BottomBar @add-record="handleAddRecord" @chat="handleChat" />
    </template>
  </Screen>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "@/store/product";
import type { NutritionDetail, IngredientDetail } from "@/types/product";
import { getRiskConfig } from "@/utils/riskLevel";
import ProductHeader from "@/components/business/product/ProductHeader.vue";
import IngredientSection from "@/components/business/product/IngredientSection.vue";
import BottomBar from "@/components/ui/BottomBar.vue";
import Icon from "@/components/ui/Icon.vue";
import Card from "@/components/ui/card/Card.vue";
import Screen from "@/components/ui/Screen.vue";
import StateView from "@/components/ui/StateView.vue";
import { formatDecimalString } from "@/utils/numberFormat";
import { useToast } from "@/composables/useToast";
import ToastContainer from "@/components/ui/ToastContainer.vue";

const toast = useToast();
const store = useProductStore();
const headerRef = ref<any>(null);
const barcode = ref("");
const nutrExpanded = ref(false);

const PRIMARY_NUTRITION_COUNT = 4;

const UNIT_LABELS: Record<string, string> = {
  g: "克",
  mg: "毫克",
  kJ: "千焦",
  kcal: "千卡",
  mL: "毫升",
};

const FALLBACK_NUTRITIONS: NutritionDetail[] = [
  {
    name: "热量",
    alias: [],
    value: "52",
    value_unit: "kcal",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "碳水",
    alias: [],
    value: "14",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "膳食纤维",
    alias: [],
    value: "2.4",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "维生素C",
    alias: [],
    value: "4.6",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "蛋白质",
    alias: [],
    value: "0.3",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "脂肪",
    alias: [],
    value: "0.2",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "糖",
    alias: [],
    value: "10",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "钠",
    alias: [],
    value: "1",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "钾",
    alias: [],
    value: "107",
    value_unit: "mg",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
  {
    name: "水分",
    alias: [],
    value: "85.6",
    value_unit: "g",
    reference_type: "PER_100_WEIGHT",
    reference_unit: "100g",
  },
];

const FALLBACK_HEALTH_TEXTS = [
  "富含膳食纤维，有助于肠道健康",
  "含有抗氧化剂，可延缓细胞衰老",
  "维生素C有助于增强免疫力",
];

const FALLBACK_ADVICE_TEXT =
  "建议每日食用1-2个中等大小的苹果，约200-300克为宜。餐前30分钟食用可增加饱腹感，有助于控制热量摄入。";

const FALLBACK_INGREDIENTS: IngredientDetail[] = [
  {
    id: 9001,
    name: "亚硝酸钠",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Group 2A",
    allergen_info: null,
    function_type: "防腐剂",
    standard_code: null,
    analysis: {
      id: 9101,
      analysis_type: "risk_assessment",
      level: "t4",
      results: { reason: "可能致癌" },
    },
  },
  {
    id: 9002,
    name: "焦糖色",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Group 2B",
    allergen_info: null,
    function_type: "着色剂",
    standard_code: null,
    analysis: {
      id: 9102,
      analysis_type: "risk_assessment",
      level: "t3",
      results: { reason: "潜在致癌" },
    },
  },
  {
    id: 9003,
    name: "天然香料",
    alias: [],
    is_additive: false,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "增香",
    standard_code: null,
    analysis: {
      id: 9103,
      analysis_type: "risk_assessment",
      level: "t0",
      results: {},
    },
  },
  {
    id: 9004,
    name: "复合调味料",
    alias: [],
    is_additive: false,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "调味",
    standard_code: null,
    analysis: {
      id: 9104,
      analysis_type: "risk_assessment",
      level: "t0",
      results: {},
    },
  },
  {
    id: 9005,
    name: "其他添加剂",
    alias: [],
    is_additive: true,
    additive_code: null,
    who_level: "Unknown",
    allergen_info: null,
    function_type: "复配",
    standard_code: null,
    analysis: {
      id: 9105,
      analysis_type: "risk_assessment",
      level: "unknown",
      results: {},
    },
  },
];

function formatNutritionUnit(item: {
  value_unit: string;
  reference_unit?: string;
}): string {
  const unit = UNIT_LABELS[item.value_unit] ?? item.value_unit;
  return item.reference_unit ? `${unit} / ${item.reference_unit}` : unit;
}

function formatNutritionValueCompact(item: {
  value: string;
  value_unit: string;
}): string {
  const formattedValue = formatDecimalString(item.value, {
    maxFractionDigits: 1,
  });
  return `${formattedValue}${item.value_unit}`;
}

onMounted(() => {
  const pages = getCurrentPages();
  const current = pages[pages.length - 1] as
    | { options?: Record<string, string> }
    | undefined;
  barcode.value = current?.options?.barcode ?? "";
  load();
});

function load() {
  if (barcode.value) store.loadProduct(barcode.value);
}

function goBack() {
  uni.navigateBack();
}

function onScroll(e: { detail: { scrollTop: number } }) {
  headerRef.value?.updateScroll(e.detail.scrollTop);
}

function handleAddRecord() {
  toast.success("已添加到记录");
}

function handleChat() {
  const name = store.product?.name ?? "";
  uni.navigateTo({
    url: `/pages/chat/index?product=${encodeURIComponent(name)}`,
  });
}

function extractText(results: unknown, ...keys: string[]): string {
  if (!results || typeof results !== "object") return "";
  const r = results as Record<string, unknown>;
  for (const key of keys) {
    if (typeof r[key] === "string") return r[key] as string;
  }
  return "";
}

// ── Computed ─────────────────────────────────────────

const overallRiskLevel = computed(() => {
  const levels = (store.product?.ingredients ?? [])
    .map((i) => i.analysis?.level)
    .filter(Boolean) as string[];
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0")) return "t0";
  if (levels.includes("t1")) return "t1";
  return "unknown";
});

const riskConfig = computed(() => getRiskConfig(overallRiskLevel.value));

const primaryNutritions = computed(() =>
  ((store.product?.nutritions?.length ?? 0) > 0
    ? store.product?.nutritions
    : FALLBACK_NUTRITIONS)!.slice(0, PRIMARY_NUTRITION_COUNT),
);

const detailNutritions = computed(() =>
  ((store.product?.nutritions?.length ?? 0) > PRIMARY_NUTRITION_COUNT
    ? store.product?.nutritions
    : FALLBACK_NUTRITIONS)!.slice(PRIMARY_NUTRITION_COUNT),
);

const healthItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) =>
      a.analysis_type === "health_summary" ||
      a.analysis_type === "health_benefits",
  ),
);

const adviceItems = computed(() =>
  (store.product?.analysis ?? []).filter(
    (a) =>
      a.analysis_type === "usage_advice_summary" ||
      a.analysis_type === "advice",
  ),
);

const healthTexts = computed(() => {
  const texts = healthItems.value
    .map((item) => extractText(item.results, "summary"))
    .filter(Boolean);
  return texts.length > 0 ? texts : FALLBACK_HEALTH_TEXTS;
});

const adviceText = computed(() => {
  const fromAnalysis =
    adviceItems.value
      .map((item) => extractText(item.results, "advice", "summary"))
      .find(Boolean) ?? "";
  return fromAnalysis || FALLBACK_ADVICE_TEXT;
});

const mockIngredients = computed(() =>
  (store.product?.ingredients?.length ?? 0) > 0
    ? store.product!.ingredients
    : FALLBACK_INGREDIENTS,
);
</script>

<style lang="scss" scoped>
.nutrition-card {
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--color-risk-t0) 2%, transparent 20%) 0%,
    color-mix(in srgb, var(--color-risk-t0) 5%, transparent 20%) 100%
  );
}

.nutrition-glow {
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--color-risk-t0) 50%, transparent 20%),
    transparent
  );
}
</style>
