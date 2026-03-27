<script setup lang="ts">
import type { IngredientDetail } from "@/types/ingredient";
import { onLoad } from "@dcloudio/uni-app";
import { computed, ref } from "vue";
import DButton from "@/components/ui/DButton.vue";
import Card from "@/components/ui/card/Card.vue";
import DIcon from "@/components/ui/DIcon.vue";
import Screen from "@/components/ui/Screen.vue";
import StateView from "@/components/ui/StateView.vue";
import { getRiskConfig, riskCls, RiskLevel } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import Separator from "@/components/ui/Separator.vue";
import Cell from "@/components/ui/Cell.vue";
import AITag from "@/components/ui/AITag.vue";
import RiskTag from "@/components/ui/RiskTag.vue";
import TopBar from "@/components/ui/TopBar.vue";
import BottomBar from "@/components/ui/BottomBar.vue";
import { fetchIngredientById } from "@/services/ingredient";
import { extractText } from "@/utils/object";
import SkeletonGroup from "@/components/SkeletonGroup.vue";
import Tag from "@/components/ui/Tag.vue";
// ── Store ────────────────────────────────────────────────
const ingredient = ref<IngredientDetail | null>(null);

// ── 加载态 ───────────────────────────────────────────────
const isLoading = ref(false);
const errorMessage = ref<string>();

// ── 页面状态（用于 StateView） ───────────────────────────
const pageState = computed(() => {
  if (isLoading.value) {
    return "loading";
  }
  if (!ingredient.value) {
    return "not_found";
  }
  return "success";
});

// ── URL 路由参数（ingredientId 为必传） ──
onLoad(async (options) => {
  const id = options?.ingredientId ? Number(options.ingredientId) : null;

  if (!id) {
    return;
  }

  isLoading.value = true;
  try {
    ingredient.value = await fetchIngredientById(id);
  } catch {
    errorMessage.value = "数据加载失败，请返回重试";
  } finally {
    isLoading.value = false;
  }
});

// ── 风险等级 ─────────────────────────────────────────────
const overallRisk = computed(() =>
  ingredient.value?.analyses?.find((a) => a.analysis_type === "overall_risk"),
);
const riskLevel = computed(() => overallRisk.value?.level ?? "unknown");
const riskConf = computed(() => getRiskConfig(riskLevel.value));

// ── Header 副标题 ────────────────────────────────────────

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

const relatedProducts = computed(() => {
  return ingredient.value?.related_products ?? [];
});

// ── Analysis 数据处理 ─────────────────────────────────────
const analysisItems = computed(() => {
  const analysis = ingredient.value?.analyses;
  if (Array.isArray(analysis)) return analysis;
  return [];
});

const analysisResult = computed(() => {
  const item = analysisItems.value.find(
    (a) => a.analysis_type === "description" || a.analysis_type === "overview",
  );
  if (!item) return "";
  if (typeof item.result === "string") return item.result;
  return extractText(item.result, "description", "summary");
});

const analysisRiskFactors = computed(() => {
  return analysisItems.value
    .filter(
      (a) =>
        a.analysis_type === "risk_factors" ||
        a.analysis_type === "health_summary" ||
        a.analysis_type === "health_risks",
    )
    .map((item) => {
      if (typeof item.result === "string") return item.result;
      return extractText(item.result, "risk_factor", "summary");
    })
    .filter(Boolean);
});

const analysisSuggestions = computed(() => {
  return analysisItems.value
    .filter(
      (a) =>
        a.analysis_type === "usage_advice_summary" ||
        a.analysis_type === "advice" ||
        a.analysis_type === "suggestions",
    )
    .map((item) => {
      if (typeof item.result === "string") {
        return { type: "warn" as const, text: item.result };
      }
      const text = extractText(item.result, "advice", "suggestion", "summary");
      return { type: "positive" as const, text };
    })
    .filter((s) => s.text);
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
      <template v-if="pageState === 'success'">
        <view class="bg-white dark:bg-black">
          <view class="border-b" :class="riskCls(riskLevel, 'bg/10 border')">
            <TopBar />
            <view class="flex items-center gap-2.5 px-3 h-topbar">
              <DButton
                size="icon"
                variant="ghost"
                @click="goBack"
                :dclass="cn('rounded-sm size-8', riskCls(riskLevel, 'bg/30'))"
              >
                <DIcon name="arrow-left" :dclass="riskCls(riskLevel, 'text')" />
              </DButton>
              <view class="flex flex-1 flex-col">
                <text class="text-foreground text-sm font-bold">
                  {{ ingredient?.name }}
                </text>
                <text class="text-muted-foreground text-xs font-semibold">
                  {{ riskConf.subtitleNoProduct }}
                </text>
              </view>
            </view>
          </view>
        </view>
      </template>
    </template>

    <!-- #content slot -->
    <template #content>
      <StateView
        :state="pageState"
        :message="errorMessage"
        go-back-label="返回"
        @go-back="goBack"
      >
        <template #loading>
          <SkeletonGroup />
        </template>
        <!-- 内容区 -->
        <view class="flex flex-col gap-3 bg-background p-3 pb-10">
          <Card dclass="p-0 overflow-hidden">
            <!-- Hero 风险卡 -->
            <view
              class="p-3 border-b"
              :class="riskCls(riskLevel, 'bg/10 border')"
            >
              <view class="flex items-center justify-between">
                <view class="flex flex-col gap-0.5">
                  <text class="text-foreground text-2xl font-extrabold">
                    {{ ingredient?.name }}
                  </text>

                  <text class="text-muted-foreground text-xs">
                    {{ ingredient?.additive_code }}
                  </text>
                </view>
                <view
                  class="flex items-center gap-1 rounded-sm px-2 py-1"
                  :class="riskCls(riskLevel, 'bg/100')"
                >
                  <DIcon
                    :name="riskConf.icon as any"
                    dclass="size-4 text-secondary"
                  />
                  <text class="text-secondary text-xs font-bold">{{
                    riskConf.badge
                  }}</text>
                </view>
              </view>

              <!-- 风险谱条 -->
              <template v-if="riskLevel !== 'unknown'">
                <view class="relative mt-2">
                  <view
                    class="spectrum-bar h-1.5 rounded-full"
                    :style="spectrumOpacityStyle"
                  />
                  <view
                    class="spectrum-needle bg-card absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2"
                    :class="riskCls(riskLevel, 'border')"
                    :style="needleStyle"
                  />
                </view>
                <view
                  class="text-muted-foreground flex justify-between px-0.5 text-xs mt-2"
                >
                  <text>低风险</text>
                  <text>中等</text>
                  <text>高风险</text>
                </view>
              </template>
            </view>

            <view class="flex flex-wrap gap-2 p-3">
              <template v-for="type in ingredient?.function_type" :key="type">
                <Tag
                  dclass=" bg-risk-t3/70 border-risk-t3 text-white"
                  variant="secondary"
                >
                  {{ type }}
                </Tag>
              </template>
              <template v-if="ingredient?.origin_type">
                <Tag variant="secondary"
                  >来源：{{ ingredient?.origin_type }}</Tag
                >
              </template>
              <template v-for="value in ingredient?.allergen_info" :key="value">
                <Tag
                  dclass="bg-risk-t2/70 border-risk-t2 text-white"
                  variant="secondary"
                  >{{ value }}</Tag
                >
              </template>
            </view>
          </Card>
          <!-- 描述 -->
          <Card dclass="p-0">
            <Cell size="sm" dclass="px-4 pt-4 pb-3">
              <template #title>
                <view class="flex items-center gap-2">
                  <view
                    class="flex size-6 items-center justify-center rounded-sm bg-blue-100"
                  >
                    <DIcon name="information" dclass="text-blue-400" />
                  </view>
                  <text class="text-base text-foreground font-medium"
                    >描述</text
                  >
                </view>
              </template>
            </Cell>
            <Separator dclass="my-0" />
            <view class="flex flex-col gap-3 px-4 pb-4 mt-3">
              <text class="text-foreground text-sm">
                {{ ingredient?.description }}
              </text>
            </view>
          </Card>
          <!-- AI 风险分析 -->
          <Card v-if="analysisRiskFactors.length > 0" dclass="p-0">
            <Cell size="sm" dclass="px-4 pt-4 pb-3">
              <template #title>
                <view class="flex items-center gap-2">
                  <view
                    class="flex size-6 items-center justify-center rounded-sm bg-red-100"
                  >
                    <DIcon name="alert" dclass="text-red-400" />
                  </view>
                  <text class="text-base text-foreground font-medium"
                    >AI 风险分析</text
                  >
                </view>
              </template>
              <template #value>
                <AITag />
              </template>
            </Cell>

            <Separator dclass="my-0" />

            <view class="flex flex-col gap-3 px-4 pb-4 mt-3">
              <template v-for="(item, i) in analysisRiskFactors" :key="i">
                <view class="flex items-start gap-2">
                  <view
                    class="mt-px flex size-4 items-center justify-center rounded-sm bg-red-100"
                  >
                    <DIcon name="x" dclass="size-4 text-red-400" />
                  </view>
                  <text class="text-foreground flex-1 text-sm">
                    {{ item }}
                  </text>
                </view>
              </template>
            </view>
          </Card>
          <!-- 风险管理信息 -->
          <Card dclass="p-0">
            <Cell size="sm" dclass="px-4 pt-4 pb-3">
              <template #title>
                <view class="flex items-center gap-2">
                  <view
                    class="flex size-6 items-center justify-center rounded-sm bg-blue-100"
                  >
                    <DIcon
                      name="shield-cross"
                      type="fill"
                      dclass="text-blue-400"
                    />
                  </view>
                  <text class="text-base text-foreground font-medium"
                    >风险管理信息</text
                  >
                </view>
              </template>
            </Cell>
            <Separator dclass="my-0" />
            <view class="flex flex-col mb-1">
              <Cell
                size="sm"
                dclass="px-4"
                title="WHO 致癌等级"
                :value="ingredient?.who_level"
              />
              <Separator dclass="my-0" />
              <!-- <Cell
                size="sm"
                dclass="px-4"
                title="母婴等级"
                :value="ingredient?.pregnancy_safety"
              />
              <Separator dclass="my-0" /> -->
              <Cell
                size="sm"
                dclass="px-4"
                title="使用限量"
                :value="ingredient?.limit_usage"
              />
              <Separator dclass="my-0" />
              <Cell
                size="sm"
                dclass="px-4"
                title="适用区域"
                :value="ingredient?.legal_region"
              />
              <Separator dclass="my-0" />
              <Cell
                size="sm"
                dclass="px-4"
                title="过敏信息"
                :value="ingredient?.allergen_info?.join(', ')"
              />
              <Separator dclass="my-0" />
              <Cell
                size="sm"
                dclass="px-4"
                title="执行标准"
                :value="ingredient?.standard_code"
              />
            </view>
          </Card>
          <!-- AI 使用建议 -->
          <Card v-if="analysisSuggestions.length > 0" dclass="p-0">
            <Cell size="sm" dclass="px-4 pt-4 pb-3">
              <template #title>
                <view class="flex items-center gap-2">
                  <view
                    class="flex size-6 items-center justify-center rounded-sm bg-red-100"
                  >
                    <DIcon name="star" type="fill" dclass="text-red-400" />
                  </view>
                  <text class="text-base text-foreground font-medium"
                    >AI 使用建议</text
                  >
                </view>
              </template>
              <template #value>
                <AITag />
              </template>
            </Cell>
            <Separator dclass="my-0" />

            <view class="flex flex-col gap-3 px-4 pb-4 mt-3">
              <view
                v-for="(s, i) in analysisSuggestions"
                :key="i"
                class="flex items-start gap-2"
              >
                <view
                  class="mt-px flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm"
                  :class="s.type === 'positive' ? 'dot-good' : 'dot-warn'"
                >
                  <DIcon
                    name="check"
                    :dclass="
                      cn(
                        'h-2.5 w-2.5',
                        s.type === 'positive'
                          ? 'text-green-500'
                          : 'text-yellow-500',
                      )
                    "
                    :size="10"
                  />
                </view>
                <text class="text-foreground flex-1 text-sm">
                  {{ s.text }}
                </text>
              </view>
            </view>
          </Card>
          <!-- 含此配料的产品 -->
          <Card dclass="p-0">
            <Cell size="sm" dclass="px-4 pt-4 pb-3">
              <template #title>
                <view class="flex items-center gap-2">
                  <view
                    class="flex size-6 items-center justify-center rounded-sm bg-blue-100"
                  >
                    <DIcon
                      name="shopping-cart"
                      type="fill"
                      dclass="text-blue-400"
                    />
                  </view>
                  <text class="text-base text-foreground font-medium"
                    >含此配料的产品</text
                  >
                </view>
              </template>
            </Cell>
            <Separator dclass="my-0" />
            <view
              class="overflow-x-auto"
              style="scrollbar-width: none; -webkit-overflow-scrolling: touch"
            >
              <view class="flex gap-2 p-3" style="width: max-content">
                <view
                  v-for="p in relatedProducts"
                  :key="p.id"
                  class="bg-background border-border-c w-24 flex-shrink-0 cursor-pointer rounded-xl border p-2 active:opacity-70"
                  @click="goToProduct(p.barcode)"
                >
                  <view class="mb-1.5 flex items-center justify-center">
                    <image
                      :src="p.image_url"
                      class="h-20 rounded-md w-full"
                      mode="aspectFill"
                    />
                  </view>
                  <text class="text-foreground block text-sm font-semibold">
                    {{ p.name }}
                  </text>

                  <text class="text-muted-foreground text-xs">
                    {{ p.category }}
                  </text>
                  <!-- <RiskTag :level="p.category as RiskLevel" size="sm" /> -->
                </view>
              </view>
            </view>
          </Card>
        </view>
      </StateView>
    </template>

    <!-- #footer slot -->
    <template #footer>
      <BottomBar secondary-label="咨询 AI 助手" @secondary="goToAI" />
    </template>
  </Screen>
</template>

<style lang="scss" scoped>
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
