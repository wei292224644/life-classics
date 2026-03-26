<template>
  <ToastContainer />
  <Screen @scroll="onScroll">
    <template #content>
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
        <template #loading>
          <view class="w-full">
            <view
              class="h-topbar bg-root shadow-md mb-3 flex items-center px-3 gap-2"
            >
              <Skeleton dclass="w-6 h-6" />
              <Skeleton dclass="w-12 h-6" />
            </view>
            <view class="flex flex-col gap-4 w-full px-3">
              <template v-for="i in 2" :key="i">
                <Card>
                  <view class="flex items-center justify-between">
                    <Skeleton dclass="w-1/2 h-6" />
                    <Skeleton dclass="w-14 h-6" />
                  </view>
                  <Skeleton dclass="w-1/3 h-4 mt-2 " />
                  <Skeleton dclass="w-2/3 h-2 mt-6 " />
                  <Skeleton dclass="w-full h-4 mt-2 " />
                  <Skeleton dclass="w-2/3 h-4 mt-2 " />
                </Card>
              </template>
            </view>
          </view>
        </template>
        <view class="pb-10 bg-background min-h-full">
          <ProductHeader
            ref="headerRef"
            :name="store.product?.name ?? ''"
            :overall-risk-level="overallRiskLevel"
          />
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
              :class="
                cn(
                  'absolute right-4 bottom-4 rounded-sm px-4 py-2 flex items-center gap-2 z-10 border border-border shadow-md',
                  riskCls(overallRiskLevel, 'bg/20 border/60 shadow/20'),
                )
              "
            >
              <DIcon
                :name="riskConfig.icon as any"
                :dclass="riskCls(overallRiskLevel, 'text')"
              />
              <text
                :class="
                  cn('text-sm font-semibold', riskCls(overallRiskLevel, 'text'))
                "
                >{{ riskConfig.badge }}</text
              >
            </view>
          </view>

          <!-- ── 内容区 ────────────────────────────────── -->
          <view class="px-3 gap-4 flex flex-col pt-4">
            <!-- 营养成分卡片 -->
            <Card
              dclass="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards] nutrition-card"
            >
              <view class="nutrition-glow absolute top-0 left-0 right-0 h-px" />
              <view class="mb-3">
                <text class="font-bold tracking-tight text-foreground text-xl"
                  >营养成分</text
                >
              </view>
              <view class="grid grid-cols-2 gap-4 mb-4">
                <view
                  v-for="item in store.product?.nutritions?.slice(
                    0,
                    PRIMARY_NUTRITION_COUNT,
                  )"
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

              <DButton
                size="lg"
                variant="ghost"
                dclass="w-full mt-4 hover:!bg-transparent"
                @click="nutrExpanded = !nutrExpanded"
              >
                <view class="flex items-center justify-center gap-2">
                  <DIcon name="arrow-down-s" :size="20" />
                  <text class="text-sm font-medium text-muted-foreground">{{
                    nutrExpanded ? "收起详细营养成分" : "查看详细营养成分"
                  }}</text>
                </view>
              </DButton>

              <view
                v-show="nutrExpanded"
                class="border-t border-border pt-4 mt-1"
              >
                <view
                  v-for="item in store.product?.nutritions?.slice(
                    PRIMARY_NUTRITION_COUNT,
                  )"
                  :key="item.name"
                  class="flex justify-between py-2 border-b border-border text-sm last:border-b-0"
                >
                  <text class="text-secondary-foreground">{{ item.name }}</text>
                  <text
                    class="text-foreground font-medium [font-variant-numeric:tabular-nums]"
                    >{{ formatNutritionValueCompact(item) }}</text
                  >
                </view>
              </view>
            </Card>

            <!-- 配料与风险 -->
            <IngredientSection
              :ingredients="store.product?.ingredients ?? []"
            />

            <!-- 健康益处卡片 -->
            <Card
              dclass="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards]"
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
                  <DIcon name="check" :size="24" />
                  <text
                    class="text-sm leading-relaxed flex-1 text-secondary-foreground"
                    >{{ text }}</text
                  >
                </view>
              </view>
            </Card>

            <!-- AI 健康建议卡片 -->
            <Card
              dclass="animate-[slideUp_0.5s_cubic-bezier(0.34,1.56,0.64,1)_forwards]"
            >
              <view class="mb-3 flex items-center gap-0.5">
                <DIcon name="star" dclass="shrink-0 text-orange-500" />
                <text class="font-semibold">AI 健康建议</text>
              </view>
              <text class="text-sm leading-relaxed text-secondary-foreground">{{
                adviceText
              }}</text>
            </Card>
          </view>
        </view>
      </StateView>
    </template>
    <template #footer>
      <BottomBar
        primary-label="咨询 AI 助手"
        secondary-label="添加到记录"
        @primary="handleChat"
        @secondary="handleAddRecord"
      />
    </template>
  </Screen>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "@/store/product";
import { getRiskConfig, riskCls } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import ProductHeader from "@/components/business/product/ProductHeader.vue";
import IngredientSection from "@/components/business/product/IngredientSection.vue";
import BottomBar from "@/components/ui/BottomBar.vue";
import DIcon from "@/components/ui/DIcon.vue";
import Card from "@/components/ui/card/Card.vue";
import Screen from "@/components/ui/Screen.vue";
import StateView from "@/components/ui/StateView.vue";
import { formatDecimalString } from "@/utils/numberFormat";
import { extractText } from "@/utils/object";
import { formatNutritionUnit } from "@/utils/nutrition";
import { useToast } from "@/composables/useToast";
import ToastContainer from "@/components/ui/ToastContainer.vue";
import DButton from "@/components/ui/DButton.vue";
import Skeleton from "@/components/ui/Skeleton.vue";

const toast = useToast();
const store = useProductStore();
const headerRef = ref<any>(null);
const barcode = ref("");
const nutrExpanded = ref(false);

const PRIMARY_NUTRITION_COUNT = 4;

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

// ── Computed ─────────────────────────────────────────

const overallRiskLevel = computed(() => {
  const levels = (store.product?.ingredients ?? [])
    .map((i) => i.level)
    .filter(Boolean) as string[];
  if (levels.includes("t4")) return "t4";
  if (levels.includes("t3")) return "t3";
  if (levels.includes("t2")) return "t2";
  if (levels.includes("t0")) return "t0";
  if (levels.includes("t1")) return "t1";
  return "unknown";
});

const riskConfig = computed(() => getRiskConfig(overallRiskLevel.value));

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

const healthTexts = computed(() =>
  healthItems.value
    .map((item) => extractText(item.results, "summary"))
    .filter(Boolean),
);

const adviceText = computed(
  () =>
    adviceItems.value
      .map((item) => extractText(item.results, "advice", "summary"))
      .find(Boolean) ?? "",
);
</script>

<style lang="scss">
.nutrition-card {
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--color-risk-t0) 10%, transparent 10%) 0%,
    color-mix(in srgb, var(--color-risk-t0) 5%, transparent 10%) 100%
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
