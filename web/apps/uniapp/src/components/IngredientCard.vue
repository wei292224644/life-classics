<template>
  <view class="ingredient-scroll">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['ingredient-card', `ingredient-card--${getLevel(item)}`]"
      @click="goToDetail(item.id)"
    >
      <!-- Left risk color bar -->
      <view :class="['ingredient-risk-bar', `ingredient-risk-bar--${getLevel(item)}`]"></view>

      <!-- Decorative circle (top-right, via CSS pseudo-element) -->

      <!-- Content -->
      <view class="ingredient-content">
        <view class="ingredient-name">
          <!-- Leaf icon for t0 (stroke), filled circle for others (fill) -->
          <svg v-if="getLevel(item) === 't0'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon-leaf">
            <path d="M6.5 21C3 17.5 3 12 6 8c2-2.5 5-4 8.5-4C18 4 21 7 21 10c0 2.5-1.5 4.5-3.5 5.5"/>
            <path d="M12 22V12"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" class="icon-circle">
            <circle cx="12" cy="12" r="10"/>
          </svg>
          <span>{{ item.name }}</span>
        </view>
        <view v-if="item.analysis" :class="['ingredient-reason', `ingredient-reason--${getLevel(item)}`]">
          {{ getRiskReason(item.analysis) }}
        </view>
      </view>

      <!-- Arrow (top-right) -->
      <view class="ingredient-arrow">
        <up-icon name="arrow-right" size="14" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { IngredientDetail } from "../types/product";

defineProps<{ ingredients: IngredientDetail[] }>();

function getLevel(item: IngredientDetail): string {
  return item.analysis?.level ?? "unknown";
}

function getRiskReason(analysis: { analysis_type: string; results: unknown }): string {
  const r = analysis.results as Record<string, unknown>;
  if (typeof r.reason === "string") return r.reason;
  return "";
}

function goToDetail(id: number) {
  uni.navigateTo({ url: `/pages/ingredient/detail?id=${id}` });
}
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.ingredient-scroll {
  display: flex;
  gap: 20rpx;
  overflow-x: auto;
  padding-bottom: 8rpx;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar {
    display: none;
  }
}

.ingredient-card {
  flex: 0 0 auto;
  min-width: 280rpx;
  scroll-snap-align: start;
  border-radius: $radius-md;
  padding: 28rpx;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s $ease-spring;
  box-sizing: border-box;
  border: 1px solid transparent;

  background: var(--bg-card);
  border-color: var(--border-color);

  &:active {
    transform: scale(0.96);
    background: var(--bg-card-hover);
  }

  &--t4 { border-color: var(--risk-t4-border); }
  &--t3 { border-color: var(--risk-t3-border); }
  &--t2 { border-color: var(--risk-t2-border); }
  &--t0 { border-color: var(--risk-t0-border); }
  &--unknown {
    border-color: var(--risk-unknown-border);
    background: var(--risk-unknown-bg);
  }

  // Decorative circle (top-right)
  &::before {
    content: "";
    position: absolute;
    top: -30rpx;
    right: -30rpx;
    width: 100rpx;
    height: 100rpx;
    border-radius: 50%;
    opacity: 0.1;
    transition: opacity 0.3s ease;
  }

  &--t4::before { background: var(--risk-t4); }
  &--t3::before { background: var(--risk-t3); }
  &--t2::before { background: var(--risk-t2); }
  &--t0::before { background: var(--risk-t0); }
  &--unknown::before { background: var(--risk-unknown); }

  &:hover::before {
    opacity: 0.15;
  }
}

// Risk bar (left colored stripe)
.ingredient-risk-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6rpx;

  &--t4 {
    background: var(--risk-t4);
    box-shadow: 0 0 16rpx var(--risk-t4);
  }
  &--t3 {
    background: var(--risk-t3);
    box-shadow: 0 0 16rpx var(--risk-t3);
  }
  &--t2 {
    background: var(--risk-t2);
    box-shadow: 0 0 16rpx var(--risk-t2);
  }
  &--t0 {
    background: var(--risk-t0);
    box-shadow: 0 0 16rpx var(--risk-t0);
  }
  &--unknown {
    background: var(--risk-unknown);
    box-shadow: 0 0 16rpx var(--risk-unknown);
  }
}

// Arrow (top-right)
.ingredient-arrow {
  position: absolute;
  right: 14rpx;
  top: 14rpx;
  width: 28rpx;
  height: 28rpx;
  opacity: 0.4;
  transition: all 0.2s ease;
  color: var(--text-muted);

  .ingredient-card:hover & {
    opacity: 0.8;
  }
}

// Content area
.ingredient-content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-left: 16rpx;
}

// Name row with icon
.ingredient-name {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
  padding-left: 0;
  flex-shrink: 0;

  .icon-leaf {
    width: 28rpx;
    height: 28rpx;
    flex-shrink: 0;
  }

  .icon-circle {
    width: 28rpx;
    height: 28rpx;
    flex-shrink: 0;
  }

  .ingredient-card--t4 & .icon-circle { fill: var(--risk-t4); }
  .ingredient-card--t3 & .icon-circle { fill: var(--risk-t3); }
  .ingredient-card--t2 & .icon-circle { fill: var(--risk-t2); }
  .ingredient-card--t0 & .icon-leaf { stroke: var(--risk-t0); }
  .ingredient-card--unknown & .icon-circle { fill: var(--risk-unknown); }

  span {
    font-size: 26rpx;
    font-weight: 600;
    color: var(--text-primary);
  }
}

// Risk reason badge
.ingredient-reason {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  font-size: 20rpx;
  padding: 8rpx 16rpx;
  border-radius: 12rpx;
  margin-left: 0;

  &--t4 {
    color: var(--risk-t4);
    background: rgba(220, 38, 38, 0.1);
  }
  &--t3 {
    color: var(--risk-t3);
    background: rgba(234, 88, 12, 0.1);
  }
  &--t2 {
    color: var(--risk-t2);
    background: rgba(234, 179, 8, 0.1);
  }
  &--t0 {
    color: var(--risk-t0);
    background: rgba(34, 197, 94, 0.1);
  }
  &--unknown {
    color: var(--risk-unknown);
    background: rgba(156, 163, 175, 0.1);
  }
}
</style>
