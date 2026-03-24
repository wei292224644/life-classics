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
.ingredient-list {
  @apply w-full;
}

.ingredient-item {
  @apply py-5;
  border-bottom: 1px solid var(--color-border);

  &--risk {
    background: color-mix(in oklch, var(--color-risk-t4) 4%, transparent);
    border-radius: 0.375rem;
    padding: 0.75rem;
    border-bottom-color: transparent;
  }
}

.ingredient-header {
  @apply flex items-center justify-between;
}

.ingredient-name {
  @apply text-xl text-foreground;
}

.ingredient-meta {
  @apply block text-base mt-2;
  color: var(--color-muted-foreground);
}

.ingredient-allergen {
  @apply block text-base mt-2;
  color: var(--color-risk-t4);
}

.empty {
  @apply text-xl;
  color: var(--color-muted);
}
</style>
