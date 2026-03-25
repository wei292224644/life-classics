<template>
  <view class="ingredient-section">
    <text class="text-xl font-bold text-secondary-foreground">配料与风险</text>
    <template v-for="levelKey in LEVEL_ORDER" :key="levelKey">
      <view
        v-if="groupedIngredients[levelKey]?.length"
        :class="['risk-group', levelKey]"
      >
        <!-- 组头 -->
        <view class="risk-header">
          <view :class="['risk-dot', levelKey]" />
          <view :class="['risk-badge', levelKey]">{{
            LEVEL_LABELS[levelKey]
          }}</view>
          <text class="risk-count"
            >{{ groupedIngredients[levelKey].length }} 项</text
          >
        </view>

        <!-- 横向滚动配料卡 -->
        <scroll-view scroll-x class="ingredient-scroll">
          <view class="ingredient-scroll-inner">
            <view
              v-for="item in groupedIngredients[levelKey]"
              :key="item.id"
              :class="['ingredient-card', levelKey]"
              @click="goToDetail(item.id)"
            >
              <!-- 左侧风险色条 -->
              <view :class="['risk-bar', levelKey]" />

              <!-- 右上角箭头 -->
              <view class="ingredient-arrow">
                <Icon name="arrowRight" :size="20" />
              </view>

              <!-- 内容 -->
              <view class="ingredient-content">
                <view class="ingredient-name">
                  <!-- 低风险：叶子图标（stroke） -->
                  <svg
                    v-if="levelKey === 't0'"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    class="icon"
                    aria-hidden="true"
                  >
                    <path
                      d="M6.5 21C3 17.5 3 12 6 8c2-2.5 5-4 8.5-4C18 4 21 7 21 10c0 2.5-1.5 4.5-3.5 5.5"
                    />
                    <path d="M12 22V12" />
                  </svg>
                  <!-- 未知：问号圆（fill） -->
                  <svg
                    v-else-if="levelKey === 'unknown'"
                    viewBox="0 0 20 20"
                    class="icon"
                    aria-hidden="true"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <!-- 其余：警告三角（fill） -->
                  <svg
                    v-else
                    viewBox="0 0 20 20"
                    class="icon"
                    aria-hidden="true"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <text class="ingredient-name-text">{{ item.name }}</text>
                </view>
                <view
                  v-if="getReason(item)"
                  :class="['ingredient-reason', levelKey]"
                >
                  {{ getReason(item) }}
                </view>
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
import type { IngredientDetail } from "../types/product";
import { useIngredientStore } from "../../../store/ingredient";
import { useProductStore } from "../../../store/product";
import Icon from "../../ui/Icon.vue";

const props = defineProps<{ ingredients: IngredientDetail[] }>();
const ingStore = useIngredientStore();
const productStore = useProductStore();

const LEVEL_ORDER = ["t4", "t3", "t2", "t1", "t0", "unknown"] as const;

const LEVEL_LABELS: Record<string, string> = {
  t4: "严重风险",
  t3: "较高风险",
  t2: "中等风险",
  t1: "低风险",
  t0: "安全",
  unknown: "未知",
};

const groupedIngredients = computed(() => {
  const groups: Record<string, IngredientDetail[]> = {
    t4: [],
    t3: [],
    t2: [],
    t1: [],
    t0: [],
    unknown: [],
  };
  const ingredients = props.ingredients ?? [];
  for (const ing of ingredients) {
    const level = ing.analysis?.level ?? "unknown";
    if (groups[level] !== undefined) groups[level].push(ing);
    else groups["unknown"].push(ing);
  }
  return groups;
});

function getReason(item: IngredientDetail): string {
  if (!item.analysis?.results) return "";
  const r = item.analysis.results as Record<string, unknown>;
  if (typeof r.reason === "string") return r.reason;
  return "";
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
  .t4 & .icon { color: var(--color-risk-t4); }
  .t3 & .icon { color: var(--color-risk-t3); }
  .t2 & .icon { color: var(--color-risk-t2); }
  .t1 & .icon { color: var(--color-risk-t1); }
  .t0 & .icon { color: var(--color-risk-t0); }
  .unknown & .icon { color: var(--color-risk-unknown); }
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
</style>
