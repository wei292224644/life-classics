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
@import "~/@/styles/design-system.scss";

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

  // Dark mode default background
  :global(.dark-mode) & {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.06);
  }

  // Light mode default background
  :global(.light-mode) & {
    background: rgba(255, 255, 255, 0.8);
    border-color: rgba(0, 0, 0, 0.06);
  }

  &:active {
    transform: scale(0.96);

    :global(.dark-mode) & {
      background: rgba(255, 255, 255, 0.06);
    }

    :global(.light-mode) & {
      background: #fff;
    }
  }

  // Risk border colors - dark mode
  :global(.dark-mode) &--t4 { border-color: rgba(239, 68, 68, 0.2); }
  :global(.dark-mode) &--t3 { border-color: rgba(249, 115, 22, 0.2); }
  :global(.dark-mode) &--t2 { border-color: rgba(234, 179, 8, 0.2); }
  :global(.dark-mode) &--t0 { border-color: rgba(34, 197, 94, 0.2); }
  :global(.dark-mode) &--unknown {
    border-color: rgba(156, 163, 175, 0.2);
    background: rgba(156, 163, 175, 0.05);
  }

  // Risk border colors - light mode
  :global(.light-mode) &--t4 { border-color: rgba(252, 165, 165, 0.4); }
  :global(.light-mode) &--t3 { border-color: rgba(252, 196, 110, 0.5); }
  :global(.light-mode) &--t2 { border-color: rgba(250, 240, 137, 0.5); }
  :global(.light-mode) &--t0 { border-color: rgba(187, 247, 208, 0.6); }
  :global(.light-mode) &--unknown { border-color: rgba(156, 163, 175, 0.4); }

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

  :global(.dark-mode) &--t4::before { background: var(--risk-t4); }
  :global(.dark-mode) &--t3::before { background: var(--risk-t3); }
  :global(.dark-mode) &--t2::before { background: var(--risk-t2); }
  :global(.dark-mode) &--t0::before { background: var(--risk-t0); }
  :global(.dark-mode) &--unknown::before { background: var(--risk-unknown); }

  :global(.light-mode) &--t4::before { background: var(--risk-t4); }
  :global(.light-mode) &--t3::before { background: var(--risk-t3); }
  :global(.light-mode) &--t2::before { background: var(--risk-t2); }
  :global(.light-mode) &--t0::before { background: var(--risk-t0); }
  :global(.light-mode) &--unknown::before { background: var(--risk-unknown); }

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

  :global(.dark-mode) &--t4 {
    background: var(--risk-t4);
    box-shadow: 0 0 16rpx var(--risk-t4);
  }
  :global(.dark-mode) &--t3 {
    background: var(--risk-t3);
    box-shadow: 0 0 16rpx var(--risk-t3);
  }
  :global(.dark-mode) &--t2 {
    background: var(--risk-t2);
    box-shadow: 0 0 16rpx var(--risk-t2);
  }
  :global(.dark-mode) &--t0 {
    background: var(--risk-t0);
    box-shadow: 0 0 16rpx var(--risk-t0);
  }
  :global(.dark-mode) &--unknown {
    background: var(--risk-unknown);
    box-shadow: 0 0 16rpx var(--risk-unknown);
  }

  :global(.light-mode) &--t4 { background: var(--risk-t4); }
  :global(.light-mode) &--t3 { background: var(--risk-t3); }
  :global(.light-mode) &--t2 { background: var(--risk-t2); }
  :global(.light-mode) &--t0 { background: var(--risk-t0); }
  :global(.light-mode) &--unknown { background: var(--risk-unknown); }
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

  :global(.dark-mode) & { color: #d1d5db; }
  :global(.light-mode) & { color: #6b7280; }

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

  :global(.dark-mode) &--t4 .icon-circle { fill: var(--risk-t4); }
  :global(.dark-mode) &--t3 .icon-circle { fill: var(--risk-t3); }
  :global(.dark-mode) &--t2 .icon-circle { fill: var(--risk-t2); }
  :global(.dark-mode) &--t0 .icon-leaf { stroke: var(--risk-t0); }
  :global(.dark-mode) &--unknown .icon-circle { fill: var(--risk-unknown); }

  :global(.light-mode) &--t4 .icon-circle { fill: var(--risk-t4); }
  :global(.light-mode) &--t3 .icon-circle { fill: var(--risk-t3); }
  :global(.light-mode) &--t2 .icon-circle { fill: var(--risk-t2); }
  :global(.light-mode) &--t0 .icon-leaf { stroke: var(--risk-t0); }
  :global(.light-mode) &--unknown .icon-circle { fill: var(--risk-unknown); }

  span {
    font-size: 26rpx;
    font-weight: 600;
    :global(.dark-mode) & { color: var(--text-primary); }
    :global(.light-mode) & { color: #111; }
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

  :global(.dark-mode) &--t4 {
    color: #fca5a5;
    background: rgba(239, 68, 68, 0.12);
  }
  :global(.dark-mode) &--t3 {
    color: #fdba74;
    background: rgba(249, 115, 22, 0.12);
  }
  :global(.dark-mode) &--t2 {
    color: #fde047;
    background: rgba(234, 179, 8, 0.12);
  }
  :global(.dark-mode) &--t0 {
    color: #86efac;
    background: rgba(34, 197, 94, 0.12);
  }
  :global(.dark-mode) &--unknown {
    color: #d1d5db;
    background: rgba(156, 163, 175, 0.12);
  }

  :global(.light-mode) &--t4 {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
  }
  :global(.light-mode) &--t3 {
    color: #ea580c;
    background: rgba(234, 88, 12, 0.1);
  }
  :global(.light-mode) &--t2 {
    color: #ca8a04;
    background: rgba(234, 179, 8, 0.1);
  }
  :global(.light-mode) &--t0 {
    color: #16a34a;
    background: rgba(34, 197, 94, 0.1);
  }
  :global(.light-mode) &--unknown {
    color: #6b7280;
    background: rgba(156, 163, 175, 0.1);
  }
}
</style>
