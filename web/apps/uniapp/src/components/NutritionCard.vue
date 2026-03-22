<template>
  <view class="nutrition-card">
    <view class="nutrition-grid">
      <view v-for="item in primaryNutritions" :key="item.name" class="nutrition-cell">
        <text class="nutrition-label">{{ item.name }}</text>
        <text class="nutrition-value">{{ item.value }}</text>
        <text class="nutrition-unit">{{ item.value_unit }}</text>
      </view>
    </view>
    <button
      type="button"
      class="nutrition-toggle"
      :class="{ expanded: isExpanded }"
      :aria-expanded="isExpanded"
      @click="toggle"
    >
      <text>{{ isExpanded ? "收起详细营养成分" : "查看详细营养成分" }}</text>
      <up-icon :name="isExpanded ? 'arrow-up' : 'arrow-down'" size="16" />
    </button>
    <view v-show="isExpanded" class="nutrition-details">
      <view v-for="item in detailNutritions" :key="item.name" class="nutrition-row">
        <text class="row-label">{{ item.name }}</text>
        <text class="row-value">{{ item.value }}{{ item.value_unit }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { NutritionDetail } from "../types/product";

const MAIN_KEYS = ["能量", "蛋白质", "脂肪", "碳水化合物"];
const isExpanded = ref(false);

const props = defineProps<{ nutritions: NutritionDetail[] }>();

const primaryNutritions = computed(() => {
  return props.nutritions.filter((n) => MAIN_KEYS.includes(n.name));
});

const detailNutritions = computed(() => {
  return props.nutritions.filter((n) => !MAIN_KEYS.includes(n.name));
});

function toggle() {
  isExpanded.value = !isExpanded.value;
}
</script>

<script lang="ts">
export default {
  options: {
    styleIsolation: "isolated",
  },
};
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.nutrition-card {
  position: relative;
  overflow: hidden;
  border-radius: $radius-xl;
  padding: 40rpx;
  margin-bottom: 56rpx;
  animation: slideUp 0.5s 0.1s $ease-spring forwards;
  opacity: 0;
  transform: translateY(16px);

  background: var(--nutrition-bg);
  border: 1px solid var(--nutrition-border);

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--nutrition-glow), transparent);
  }
}

.nutrition-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40rpx;
  margin-bottom: 40rpx;
}

.nutrition-cell {
  display: flex;
  flex-direction: column;
}

.nutrition-label {
  font-size: 22rpx;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 4rpx;
  color: var(--text-muted);
}

.nutrition-value {
  font-size: 64rpx;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  color: var(--text-primary);
}

.nutrition-unit {
  font-size: 22rpx;
  margin-top: 4rpx;
  color: var(--text-muted);
}

.nutrition-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  padding: 20rpx;
  background: transparent;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  font-size: 26rpx;
  font-weight: 500;
  font-family: inherit;
  border-radius: 24rpx;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(128, 128, 128, 0.1);
  }

  &:focus-visible {
    outline: 4rpx solid var(--accent-pink);
    outline-offset: 4rpx;
  }

  svg {
    transition: transform 0.3s ease;
  }

  &.expanded svg {
    transform: rotate(180deg);
  }
}

.nutrition-details {
  border-top: 1px solid var(--border-color);
  padding-top: 32rpx;
  margin-top: 8rpx;
}

.nutrition-row {
  display: flex;
  justify-content: space-between;
  padding: 20rpx 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 28rpx;

  &:last-child {
    border-bottom: none;
  }

  .row-label {
    color: var(--text-secondary);
  }

  .row-value {
    color: var(--text-primary);
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
}

@media (prefers-reduced-motion: reduce) {
  .nutrition-card {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
</style>
