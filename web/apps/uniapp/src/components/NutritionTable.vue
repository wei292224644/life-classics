<template>
  <view class="nutrition-table">
    <view
      v-for="group in grouped"
      :key="group.label"
      class="group"
    >
      <text class="group-label block mb-2">{{ group.label }}</text>
      <view class="row header flex justify-between">
        <text class="col-name">营养成分</text>
        <text class="col-value">每{{ group.referenceUnit }}</text>
      </view>
      <view
        v-for="item in group.items"
        :key="item.name"
        class="row flex justify-between"
      >
        <text class="col-name">{{ item.name }}</text>
        <text class="col-value">{{ item.value }} {{ item.value_unit }}</text>
      </view>
    </view>
    <text v-if="nutritions.length === 0" class="empty">暂无营养成分数据</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { NutritionDetail } from "../types/product";

const props = defineProps<{ nutritions: NutritionDetail[] }>();

const REFERENCE_LABELS: Record<string, string> = {
  PER_100_WEIGHT: "每100g",
  PER_100_ENERGY: "每100kcal",
  PER_SERVING: "每份",
  PER_DAY: "每日",
};

const grouped = computed(() => {
  const map = new Map<string, NutritionDetail[]>();
  for (const n of props.nutritions) {
    const key = n.reference_type;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(n);
  }
  return [...map.entries()].map(([type, items]) => ({
    label: REFERENCE_LABELS[type] ?? type,
    referenceUnit: items[0]?.reference_unit ?? "",
    items,
  }));
});
</script>

<style lang="scss" scoped>
.nutrition-table {
  width: 100%;

  .group { margin-bottom: var(--space-8); }

  .group-label {
    font-size: var(--text-lg);
    color: #888;
  }

  .row {
    padding: var(--space-4) 0;
    border-bottom: 1rpx solid #f0f0f0;

    &.header { font-weight: bold; }
  }

  .col-name { font-size: var(--text-xl); color: #333; }
  .col-value { font-size: var(--text-xl); color: #555; }

  .empty { color: #aaa; font-size: var(--text-xl); }
}
</style>
