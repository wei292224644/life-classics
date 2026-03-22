<template>
  <view v-if="ingredients.length > 0" :class="['risk-group', level]">
    <view class="risk-header">
      <view :class="['risk-dot', level]"></view>
      <view :class="['risk-badge', level]">{{ levelLabel }}</view>
      <text class="risk-count">{{ ingredients.length }} 项</text>
    </view>
    <slot />
  </view>
</template>

<script setup lang="ts">
import type { IngredientDetail } from "../types/product";

const LEVEL_LABELS: Record<string, string> = {
  t4: "严重风险",
  t3: "高风险",
  t2: "中风险",
  t0: "低风险",
  unknown: "未知",
};

const props = defineProps<{
  level: "t0" | "t1" | "t2" | "t3" | "t4" | "unknown";
  ingredients: IngredientDetail[];
}>();

const levelLabel = LEVEL_LABELS[props.level] ?? "未知";
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.risk-group {
  border-radius: 20px;
  padding: 16px;
  margin-bottom: 12px;
  position: relative;
  overflow: hidden;

  &.t4 {
    background: var(--risk-t4-bg);
    border: 1px solid var(--risk-t4-border);
  }
  &.t3 {
    background: var(--risk-t3-bg);
    border: 1px solid var(--risk-t3-border);
  }
  &.t2 {
    background: var(--risk-t2-bg);
    border: 1px solid var(--risk-t2-border);
  }
  &.t0 {
    background: var(--risk-t0-bg);
    border: 1px solid var(--risk-t0-border);
  }
  &.unknown {
    background: var(--risk-unknown-bg);
    border: 1px solid var(--risk-unknown-border);
  }
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.risk-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.t4 {
    background: var(--risk-t4);
    box-shadow: 0 0 8px var(--risk-t4);
  }
  &.t3 {
    background: var(--risk-t3);
    box-shadow: 0 0 8px var(--risk-t3);
  }
  &.t2 {
    background: var(--risk-t2);
    box-shadow: 0 0 8px var(--risk-t2);
  }
  &.t0 {
    background: var(--risk-t0);
    box-shadow: 0 0 8px var(--risk-t0);
  }
  &.unknown {
    background: var(--risk-unknown);
    box-shadow: 0 0 8px var(--risk-unknown);
  }
}

.risk-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 8px;

  &.t4 {
    color: var(--risk-t4);
    background: rgba(220, 38, 38, 0.1);
  }
  &.t3 {
    color: var(--risk-t3);
    background: rgba(234, 88, 12, 0.1);
  }
  &.t2 {
    color: var(--risk-t2);
    background: rgba(202, 138, 4, 0.1);
  }
  &.t0 {
    color: var(--risk-t0);
    background: rgba(22, 163, 74, 0.1);
  }
  &.unknown {
    color: var(--risk-unknown);
    background: rgba(156, 163, 175, 0.1);
  }
}

.risk-count {
  font-size: 11px;
  margin-left: auto;
  color: var(--text-muted);
}
</style>
