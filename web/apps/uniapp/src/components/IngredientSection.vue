<template>
  <view class="ingredient-section">
    <template v-for="levelKey in LEVEL_ORDER" :key="levelKey">
      <view
        v-if="groupedIngredients[levelKey]?.length"
        :class="['risk-group', levelKey]"
      >
        <!-- 组头 -->
        <view class="risk-header flex items-center gap-4 mb-7">
          <view :class="['risk-dot', levelKey]" />
          <view :class="['risk-badge', levelKey]">{{ LEVEL_LABELS[levelKey] }}</view>
          <text class="risk-count ml-auto">{{ groupedIngredients[levelKey].length }} 项</text>
        </view>

        <!-- 横向滚动配料卡 -->
        <scroll-view scroll-x class="ingredient-scroll">
          <view class="ingredient-scroll-inner flex flex-row gap-5 w-max pb-2">
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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M9 5l7 7-7 7"/>
              </svg>
            </view>

            <!-- 内容 -->
            <view class="ingredient-content flex flex-col pl-4 min-w-0">
              <view class="ingredient-name flex items-center gap-3 mb-3">
                <!-- 低风险：叶子图标（stroke） -->
                <svg v-if="levelKey === 't0'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon" aria-hidden="true">
                  <path d="M6.5 21C3 17.5 3 12 6 8c2-2.5 5-4 8.5-4C18 4 21 7 21 10c0 2.5-1.5 4.5-3.5 5.5"/>
                  <path d="M12 22V12"/>
                </svg>
                <!-- 未知：问号圆（fill） -->
                <svg v-else-if="levelKey === 'unknown'" viewBox="0 0 20 20" class="icon" aria-hidden="true">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
                </svg>
                <!-- 其余：警告三角（fill） -->
                <svg v-else viewBox="0 0 20 20" class="icon" aria-hidden="true">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <text class="ingredient-name-text">{{ item.name }}</text>
              </view>
              <view v-if="getReason(item)" :class="['ingredient-reason', levelKey]">
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
import { useIngredientStore } from "../store/ingredient";
import { useProductStore } from "../store/product";

const props = defineProps<{ ingredients: IngredientDetail[] }>();
const ingStore = useIngredientStore();
const productStore = useProductStore();

const LEVEL_ORDER = ["t4", "t3", "t2", "t1", "t0", "unknown"] as const;

const LEVEL_LABELS: Record<string, string> = {
  t4: "极高风险",
  t3: "高风险",
  t2: "中等风险",
  t1: "低风险",
  t0: "安全",
  unknown: "暂无评级",
};

const groupedIngredients = computed(() => {
  const groups: Record<string, IngredientDetail[]> = {
    t4: [], t3: [], t2: [], t1: [], t0: [], unknown: [],
  };
  for (const ing of props.ingredients) {
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
  const fpn = productName ? `&fromProductName=${encodeURIComponent(productName)}` : "";
  uni.navigateTo({ url: `/pages/ingredient-detail/index?ingredientId=${id}${fpn}` });
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

// ── 风险分组容器 ──────────────────────────────────────
.risk-group {
  border-radius: 40rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  position: relative;
  overflow: hidden;

  &.t4 { background: var(--risk-t4-bg); border: 1px solid var(--risk-t4-border); }
  &.t3 { background: var(--risk-t3-bg); border: 1px solid var(--risk-t3-border); }
  &.t2 { background: var(--risk-t2-bg); border: 1px solid var(--risk-t2-border); }
  &.t1 { background: var(--risk-t1-bg); border: 1px solid var(--risk-t1-border); }
  &.t0 { background: var(--risk-t0-bg); border: 1px solid var(--risk-t0-border); }
  &.unknown { background: var(--risk-unknown-bg); border: 1px solid var(--risk-unknown-border); }
}

// ── 组头 ──────────────────────────────────────────────
.risk-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;

  &.t4 { background: var(--risk-t4); box-shadow: 0 0 8px var(--risk-t4); }
  &.t3 { background: var(--risk-t3); box-shadow: 0 0 8px var(--risk-t3); }
  &.t2 { background: var(--risk-t2); box-shadow: 0 0 8px var(--risk-t2); }
  &.t1 { background: var(--risk-t1); box-shadow: 0 0 8px var(--risk-t1); }
  &.t0 { background: var(--risk-t0); box-shadow: 0 0 8px var(--risk-t0); }
  &.unknown { background: var(--risk-unknown); }
}

.risk-badge {
  font-size: 24rpx;
  font-weight: 600;
  padding: 8rpx 20rpx;
  border-radius: 24rpx;

  .t4 & { color: var(--risk-t4); background: color-mix(in oklch, var(--risk-t4) 15%, transparent); }
  .t3 & { color: var(--risk-t3); background: color-mix(in oklch, var(--risk-t3) 15%, transparent); }
  .t2 & { color: var(--risk-t2); background: color-mix(in oklch, var(--risk-t2) 15%, transparent); }
  .t1 & { color: var(--risk-t1); background: color-mix(in oklch, var(--risk-t1) 15%, transparent); }
  .t0 & { color: var(--risk-t0); background: color-mix(in oklch, var(--risk-t0) 15%, transparent); }
  .unknown & { color: var(--risk-unknown); background: color-mix(in oklch, var(--risk-unknown) 15%, transparent); }
}

.risk-count {
  font-size: 28rpx;
  color: var(--text-muted);
}

// ── 横向滚动 ──────────────────────────────────────────
.ingredient-scroll {
  // UniApp H5 的 uni-scroll-view 外层 wrapper 是 overflow:visible
  // 用 :deep 强制 clip，使内容不溢出父级
  :deep(.uni-scroll-view:first-child) {
    overflow: hidden;
  }

  &::-webkit-scrollbar { display: none; }
}

// ── 配料卡片 ──────────────────────────────────────────
.ingredient-card {
  flex: 0 0 auto;
  width: 280rpx;
  border-radius: 32rpx;
  padding: 28rpx;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s $ease-spring;
  box-sizing: border-box;
  background: var(--bg-card);
  border: 1px solid var(--border-color);

  &.t4 { border-color: var(--risk-t4-border); }
  &.t3 { border-color: var(--risk-t3-border); }
  &.t2 { border-color: var(--risk-t2-border); }
  &.t1 { border-color: var(--risk-t1-border); }
  &.t0 { border-color: var(--risk-t0-border); }
  &.unknown { border-color: var(--risk-unknown-border); }

  &:active { transform: scale(0.96); }

  // 右上角装饰圆
  &::before {
    content: "";
    position: absolute;
    top: -30rpx;
    right: -30rpx;
    width: 100rpx;
    height: 100rpx;
    border-radius: 50%;
    opacity: 0.1;
  }
  &.t4::before { background: var(--risk-t4); }
  &.t3::before { background: var(--risk-t3); }
  &.t2::before { background: var(--risk-t2); }
  &.t1::before { background: var(--risk-t1); }
  &.t0::before { background: var(--risk-t0); }
  &.unknown::before { background: var(--risk-unknown); }
}

// ── 左侧风险色条 ──────────────────────────────────────
.risk-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6rpx;

  .t4 & { background: var(--risk-t4); box-shadow: 0 0 16rpx var(--risk-t4); }
  .t3 & { background: var(--risk-t3); box-shadow: 0 0 16rpx var(--risk-t3); }
  .t2 & { background: var(--risk-t2); box-shadow: 0 0 16rpx var(--risk-t2); }
  .t1 & { background: var(--risk-t1); box-shadow: 0 0 16rpx var(--risk-t1); }
  .t0 & { background: var(--risk-t0); box-shadow: 0 0 16rpx var(--risk-t0); }
  .unknown & { background: var(--risk-unknown); }
}

// ── 右上角箭头 ────────────────────────────────────────
.ingredient-arrow {
  position: absolute;
  right: 12rpx;
  top: 12rpx;
  width: 28rpx;
  height: 28rpx;
  opacity: 0.4;
  color: var(--text-muted);

  svg { width: 28rpx; height: 28rpx; }
}

// ── 内容区 ────────────────────────────────────────────
.ingredient-name {
  .icon {
    width: 28rpx;
    height: 28rpx;
    flex-shrink: 0;
  }

  // 图标颜色
  .t4 & .icon { fill: var(--risk-t4); }
  .t3 & .icon { fill: var(--risk-t3); }
  .t2 & .icon { fill: var(--risk-t2); }
  .t1 & .icon { stroke: var(--risk-t1); fill: none; }
  .t0 & .icon { stroke: var(--risk-t0); fill: none; }
  .unknown & .icon { fill: var(--risk-unknown); }
}

.ingredient-name-text {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-primary);
}

// ── 原因标签 ──────────────────────────────────────────
.ingredient-reason {
  display: inline-block;
  font-size: 20rpx;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
  align-self: flex-start;
  max-width: 100%;
  box-sizing: border-box;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &.t4 { color: var(--risk-t4); background: color-mix(in oklch, var(--risk-t4) 12%, transparent); }
  &.t3 { color: var(--risk-t3); background: color-mix(in oklch, var(--risk-t3) 12%, transparent); }
  &.t2 { color: var(--risk-t2); background: color-mix(in oklch, var(--risk-t2) 12%, transparent); }
  &.t1 { color: var(--risk-t1); background: color-mix(in oklch, var(--risk-t1) 12%, transparent); }
  &.t0 { color: var(--risk-t0); background: color-mix(in oklch, var(--risk-t0) 12%, transparent); }
  &.unknown { color: var(--risk-unknown); background: color-mix(in oklch, var(--risk-unknown) 12%, transparent); }
}
</style>
