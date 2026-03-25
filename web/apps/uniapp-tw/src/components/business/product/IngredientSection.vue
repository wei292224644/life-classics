<template>
  <view>
    <view class="mb-3">
      <text class="text-xl font-bold text-secondary-foreground"
        >配料与风险</text
      >
    </view>
    <template v-for="levelGroup in levelGroups" :key="levelGroup.levelKey">
      <view
        v-if="levelGroup.levelIngredients?.length"
        :class="[
          'rounded-2xl p-3 mb-3 relative overflow-hidden border border-transparent',
          `bg-risk-${levelGroup.levelKey}/10`,
          `border-risk-${levelGroup.levelKey}/60`,
        ]"
      >
        <!-- 组头 -->
        <view class="flex items-center gap-2 mb-3">
          <view
            :class="[
              'w-2 h-2 rounded-full flex-shrink-0',
              `bg-risk-${levelGroup.levelKey}`,
              levelGroup.levelKey === 'unknown'
                ? 'shadow-none'
                : `shadow-risk-${levelGroup.levelKey}/20 shadow-[0_0_8px_var(--tw-shadow-color)]`,
            ]"
          />
          <Tag
            :class="{
              'bg-risk-t4/40': levelGroup.levelKey === 't4',
              'bg-risk-t3/40': levelGroup.levelKey === 't3',
              'bg-risk-t2/40': levelGroup.levelKey === 't2',
              'bg-risk-t1/40': levelGroup.levelKey === 't1',
              'bg-risk-t0/40': levelGroup.levelKey === 't0',
              'bg-risk-unknown/40': levelGroup.levelKey === 'unknown',
            }"
          >
            {{ levelGroup.config.badge }}
          </Tag>
          <text class="text-xs ml-auto text-muted-foreground"
            >{{ levelGroup.levelIngredients.length }} 项</text
          >
        </view>

        <!-- 横向滚动配料卡 -->
        <scroll-view scroll-x class="ingredient-scroll" :show-scrollbar="false">
          <view class="flex flex-row gap-4 w-max pb-1">
            <view
              v-for="item in levelGroup.levelIngredients"
              :key="item.id"
              :class="[
                'flex-none rounded-2xl p-3 px-2 relative overflow-hidden cursor-pointer min-w-36 box-border transition-transform duration-200 ease-[cubic-bezier(0.34,1.56,0.64,1)] active:scale-[0.96] bg-white/80 dark:bg-white/5 border',
                `border-risk-${levelGroup.levelKey}/60`,
              ]"
              @click="goToDetail(item.id)"
            >
              <!-- 左侧风险色条 -->
              <view
                :class="[
                  'absolute left-0 top-0 bottom-0 w-1.5',
                  `flow-bg-risk-${levelGroup.levelKey}`,
                ]"
              />
              <View
                class="size-14 absolute -right-4 -top-4 bg-background opacity-70 rounded-full"
              >
              </View>
              <!-- 右上角箭头 -->
              <view
                class="absolute right-2.5 top-2.5 w-4 h-4 opacity-40 text-secondary-foreground"
              >
                <Icon name="arrowRight" :size="20" class="w-4 h-4" />
              </view>

              <!-- 内容 -->
              <view class="flex flex-col pl-2">
                <view class="flex items-center gap-1 mb-2">
                  <Icon
                    :name="levelGroup.config.icon as any"
                    :size="16"
                    :class="'text-risk-' + levelGroup.levelKey"
                  />
                  <text class="text-sm font-medium text-foreground">{{
                    item.name
                  }}</text>
                </view>
                <Tag
                  class="w-24"
                  textClass="block max-w-full truncate"
                  :class="{
                    '!text-risk-t4 bg-risk-t4/10': levelGroup.levelKey === 't4',
                    '!text-risk-t3 bg-risk-t3/10': levelGroup.levelKey === 't3',
                    '!text-risk-t2 bg-risk-t2/10': levelGroup.levelKey === 't2',
                    '!text-risk-t1 bg-risk-t1/10': levelGroup.levelKey === 't1',
                    '!text-risk-t0 bg-risk-t0/10': levelGroup.levelKey === 't0',
                    '!text-risk-unknown bg-risk-unknown/10':
                      levelGroup.levelKey === 'unknown',
                  }"
                >
                  {{ getReason(item) }}
                </Tag>
              </view>
            </view>
          </view>
        </scroll-view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { IngredientDetail } from "@/types/product";
import { useIngredientStore } from "@/store/ingredient";
import { useProductStore } from "@/store/product";
import { getRiskConfig } from "@/utils/riskLevel";
import Icon from "@/components/ui/Icon.vue";
import Tag from "@/components/ui/Tag.vue";

const props = defineProps<{ ingredients: IngredientDetail[] }>();
const ingStore = useIngredientStore();
const productStore = useProductStore();

const levelGroups = computed(() => {
  const order = ["t4", "t3", "t2", "t1", "t0", "unknown"] as const;
  const groups: Record<(typeof order)[number], IngredientDetail[]> = {
    t4: [],
    t3: [],
    t2: [],
    t1: [],
    t0: [],
    unknown: [],
  };

  const ingredients = props.ingredients ?? [];
  for (const ing of ingredients) {
    const level = (ing.analysis?.level ?? "unknown") as (typeof order)[number];
    if (groups[level] !== undefined) groups[level].push(ing);
    else groups.unknown.push(ing);
  }

  return order.map((levelKey) => ({
    levelKey,
    levelIngredients: groups[levelKey],
    config: getRiskConfig(levelKey as any),
  }));
});

function getReason(item: IngredientDetail): string {
  // if (!item.analysis?.results) return "";
  // const r = item.analysis.results as Record<string, unknown>;
  // if (typeof r.reason === "string") return r.reason;
  return "teetetetetetetetetteetetetetetetetet";
}

function goToDetail(id: number) {
  const ing = props.ingredients.find((i) => i.id === id);
  if (!ing) return;
  const productName = productStore.product?.name;
  ingStore.set(ing, productName);
  const fpn = productName
    ? `&fromProductName=${encodeURIComponent(productName)}`
    : "";
  uni.navigateTo({
    url: `/pages/ingredient-detail/index?ingredientId=${id}${fpn}`,
  });
}
</script>

<style lang="scss" scoped>
.flow-bg-risk-t4 {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-t4) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-t4) 12%, transparent) 100%
  );
}
.flow-bg-risk-t3 {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-t3) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-t3) 12%, transparent) 100%
  );
}
.flow-bg-risk-t2 {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-t2) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-t2) 12%, transparent) 100%
  );
}
.flow-bg-risk-t1 {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-t1) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-t1) 12%, transparent) 100%
  );
}
.flow-bg-risk-t0 {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-t0) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-t0) 12%, transparent) 100%
  );
}
.flow-bg-risk-unknown {
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--color-risk-unknown) 80%, transparent) 0%,
    color-mix(in oklch, var(--color-risk-unknown) 12%, transparent) 100%
  );
}
/*
// ── 风险分组容器 ──────────────────────────────────────
.risk-group {
  @apply rounded-[40rpx] p-6 mb-3 relative overflow-hidden;
  border: 1px solid transparent;

  &.t4 {
    background: #fee2e2;
    border-color: rgba(252, 165, 165, 0.35);
  }
  &.t3 {
    background: #ffedd5;
    border-color: rgba(252, 196, 110, 0.45);
  }
  &.t2 {
    background: #fef3c7;
    border-color: rgba(252, 211, 77, 0.45);
  }
  &.t1,
  &.t0 {
    background: #dcfce7;
    border-color: rgba(187, 247, 208, 0.6);
  }
  &.unknown {
    background: #e5e7eb;
    border-color: rgba(209, 213, 219, 0.55);
  }

  :global(.dark) &.t4 {
    background: rgba(239, 68, 68, 0.08);
    border-color: rgba(239, 68, 68, 0.15);
  }
  :global(.dark) &.t3 {
    background: rgba(249, 115, 22, 0.08);
    border-color: rgba(249, 115, 22, 0.15);
  }
  :global(.dark) &.t2 {
    background: rgba(234, 179, 8, 0.08);
    border-color: rgba(234, 179, 8, 0.15);
  }
  :global(.dark) &.t1,
  :global(.dark) &.t0 {
    background: rgba(34, 197, 94, 0.08);
    border-color: rgba(34, 197, 94, 0.15);
  }
  :global(.dark) &.unknown {
    background: rgba(156, 163, 175, 0.08);
    border-color: rgba(156, 163, 175, 0.15);
  }
}



// ── 组头 ──────────────────────────────────────────────
.risk-header {
  @apply flex items-center gap-2 mb-[28rpx];
}

.risk-dot {
  @apply w-2 h-2 rounded-full flex-shrink-0;

  &.t4 {
    background: var(--color-risk-t4);
    box-shadow: 0 0 8px var(--color-risk-t4);
  }
  &.t3 {
    background: var(--color-risk-t3);
    box-shadow: 0 0 8px var(--color-risk-t3);
  }
  &.t2 {
    background: var(--color-risk-t2);
    box-shadow: 0 0 8px var(--color-risk-t2);
  }
  &.t1 {
    background: var(--color-risk-t1);
    box-shadow: 0 0 8px var(--color-risk-t1);
  }
  &.t0 {
    background: var(--color-risk-t0);
    box-shadow: 0 0 8px var(--color-risk-t0);
  }
  &.unknown {
    background: var(--color-risk-unknown);
  }
}

.risk-badge {
  @apply text-xs font-semibold px-[20rpx] py-[8rpx] rounded-[12rpx];

  .t4 & {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
  }
  .t3 & {
    color: #ea580c;
    background: rgba(234, 88, 12, 0.1);
  }
  .t2 & {
    color: #ca8a04;
    background: rgba(202, 138, 4, 0.1);
  }
  .t1 &,
  .t0 & {
    color: #16a34a;
    background: rgba(22, 163, 74, 0.1);
  }
  .unknown & {
    color: #6b7280;
    background: rgba(107, 114, 128, 0.1);
  }
}

.risk-count {
  @apply text-[22rpx] ml-auto;
  color: var(--color-muted-foreground);
}

// ── 横向滚动 ──────────────────────────────────────────
.ingredient-scroll {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar {
    display: none;
  }
}

.ingredient-scroll-inner {
  @apply flex flex-row gap-[20rpx] w-max pb-1;
}

// ── 配料卡片 ──────────────────────────────────────────
.ingredient-card {
  @apply flex-none rounded-2xl p-[28rpx] relative overflow-hidden cursor-pointer;
  min-width: 280rpx;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.06);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-sizing: border-box;

  &.t4 {
    border-color: var(--risk-t4-border);
  }
  &.t3 {
    border-color: var(--risk-t3-border);
  }
  &.t2 {
    border-color: var(--risk-t2-border);
  }
  &.t1 {
    border-color: var(--risk-t1-border);
  }
  &.t0 {
    border-color: var(--risk-t0-border);
  }
  &.unknown {
    border-color: var(--risk-unknown-border);
  }

  &:active {
    transform: scale(0.96);
  }

  :global(.dark) & {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.06);
  }
}

// ── 左侧风险色条 ──────────────────────────────────────
.risk-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6rpx;

  .t4 & {
    background: var(--color-risk-t4);
    box-shadow: 0 0 16rpx var(--color-risk-t4);
  }
  .t3 & {
    background: var(--color-risk-t3);
    box-shadow: 0 0 16rpx var(--color-risk-t3);
  }
  .t2 & {
    background: var(--color-risk-t2);
    box-shadow: 0 0 16rpx var(--color-risk-t2);
  }
  .t1 & {
    background: var(--color-risk-t1);
    box-shadow: 0 0 16rpx var(--color-risk-t1);
  }
  .t0 & {
    background: var(--color-risk-t0);
    box-shadow: 0 0 16rpx var(--color-risk-t0);
  }
  .unknown & {
    background: var(--color-risk-unknown);
  }
}

// ── 右上角箭头 ────────────────────────────────────────
.ingredient-arrow {
  @apply absolute w-[28rpx] h-[28rpx];
  right: 12rpx;
  top: 12rpx;
  opacity: 0.4;
  color: var(--color-muted-foreground);

  svg {
    @apply w-[28rpx] h-[28rpx];
  }
}

// ── 内容区 ────────────────────────────────────────────
.ingredient-content {
  @apply flex flex-col pl-2 min-w-0;
}

// ── 配料名称 ──────────────────────────────────────────
.ingredient-name {
  @apply flex items-center gap-[12rpx] mb-[12rpx];

  .icon {
    @apply flex-shrink-0;
    width: 28rpx;
    height: 28rpx;
    // 通过 color 继承给 SVG 的 currentColor
    color: var(--color-muted-foreground);
  }

  // 图标颜色：通过 currentColor 继承给 SVG path
  .t4 & .icon {
    color: var(--color-risk-t4);
  }
  .t3 & .icon {
    color: var(--color-risk-t3);
  }
  .t2 & .icon {
    color: var(--color-risk-t2);
  }
  .t1 & .icon {
    color: var(--color-risk-t1);
  }
  .t0 & .icon {
    color: var(--color-risk-t0);
  }
  .unknown & .icon {
    color: var(--color-risk-unknown);
  }
}

.ingredient-name-text {
  @apply text-[26rpx] font-semibold;
  color: var(--foreground);
}

// ── 原因标签 ──────────────────────────────────────────
.ingredient-reason {
  @apply inline-block text-[20rpx] px-[16rpx] py-[6rpx] rounded-md self-start max-w-full box-border whitespace-nowrap overflow-hidden text-ellipsis;

  &.t4 {
    color: var(--color-risk-t4);
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
  }
  &.t3 {
    color: var(--color-risk-t3);
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
  }
  &.t2 {
    color: var(--color-risk-t2);
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
  }
  &.t1 {
    color: var(--color-risk-t1);
    background: color-mix(in oklch, var(--color-risk-t1) 12%, transparent);
  }
  &.t0 {
    color: var(--color-risk-t0);
    background: color-mix(in oklch, var(--color-risk-t0) 12%, transparent);
  }
  &.unknown {
    color: var(--color-risk-unknown);
    background: color-mix(in oklch, var(--color-risk-unknown) 12%, transparent);
  }
}
*/

.ingredient-scroll {
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar {
    display: none;
  }
}
</style>
