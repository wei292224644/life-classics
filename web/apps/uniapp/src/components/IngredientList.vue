<template>
  <view class="ingredient-list">
    <view
      v-for="item in ingredients"
      :key="item.id"
      :class="['ingredient-item', isHighRisk(item.who_level) && 'ingredient-item--risk']"
    >
      <view class="flex items-center justify-between">
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
@import "@/styles/design-system.scss";

.ingredient-list { width: 100%; }

.ingredient-item {
  padding: var(--space-5) 0;
  border-bottom: 1rpx solid var(--border-color);

  &--risk { background: color-mix(in oklch, var(--risk-t4) 4%, transparent); border-radius: var(--space-2); padding: var(--space-4); }
}


.ingredient-name { font-size: var(--text-2xl); color: var(--text-primary); }

.ingredient-meta {
  display: block;
  font-size: var(--text-md);
  color: var(--text-muted);
  margin-top: var(--space-2);
}

.ingredient-allergen {
  display: block;
  font-size: var(--text-md);
  color: var(--risk-t4);
  margin-top: var(--space-2);
}

.empty { color: var(--text-muted); font-size: var(--text-xl); }
</style>
