<template>
  <view class="ingredient-list">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['ingredient-item', isHighRisk(item.who_level) && 'ingredient-item--risk']"
    >
      <view class="ingredient-header">
        <text class="ingredient-name">{{ item.name }}</text>
        <RiskBadge :who-level="item.who_level" />
      </view>
      <text v-if="item.function_type" class="ingredient-meta">
        {{ item.function_type }}
      </text>
      <text v-if="item.allergen_info" class="ingredient-allergen">
        过敏提示：{{ item.allergen_info }}
      </text>
    </view>
    <text v-if="ingredients.length === 0" class="empty">暂无配料数据</text>
  </view>
</template>

<script setup lang="ts">
import type { IngredientDetail } from "../types/product";
import RiskBadge from "./RiskBadge.vue";

defineProps<{ ingredients: IngredientDetail[] }>();

function isHighRisk(whoLevel: string | null): boolean {
  return whoLevel === "Group 1" || whoLevel === "Group 2A";
}
</script>

<style lang="scss" scoped>
.ingredient-list { width: 100%; }

.ingredient-item {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;

  &--risk { background: #fff8f8; border-radius: 8rpx; padding: 16rpx; }
}

.ingredient-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ingredient-name { font-size: 30rpx; color: #1a1a1a; }

.ingredient-meta {
  display: block;
  font-size: 24rpx;
  color: #888;
  margin-top: 6rpx;
}

.ingredient-allergen {
  display: block;
  font-size: 24rpx;
  color: #dc2626;
  margin-top: 6rpx;
}

.empty { color: #aaa; font-size: 28rpx; }
</style>
