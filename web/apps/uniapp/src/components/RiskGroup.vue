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
@import "~/@/styles/design-system.scss";

.risk-group {
  border-radius: 20px;
  padding: 16px;
  margin-bottom: 12px;
  position: relative;
  overflow: hidden;

  // Dark mode backgrounds
  :global(.dark-mode) &.t4 {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.15);
  }
  :global(.dark-mode) &.t3 {
    background: rgba(249, 115, 22, 0.08);
    border: 1px solid rgba(249, 115, 22, 0.15);
  }
  :global(.dark-mode) &.t2 {
    background: rgba(234, 179, 8, 0.08);
    border: 1px solid rgba(234, 179, 8, 0.15);
  }
  :global(.dark-mode) &.t0 {
    background: rgba(34, 197, 94, 0.08);
    border: 1px solid rgba(34, 197, 94, 0.15);
  }
  :global(.dark-mode) &.unknown {
    background: rgba(156, 163, 175, 0.08);
    border: 1px solid rgba(156, 163, 175, 0.15);
  }

  // Light mode backgrounds
  :global(.light-mode) &.t4 {
    background: rgba(254, 226, 226);
    border: 1px solid rgba(252, 165, 165, 0.3);
  }
  :global(.light-mode) &.t3 {
    background: rgba(254, 235, 200);
    border: 1px solid rgba(252, 196, 110, 0.4);
  }
  :global(.light-mode) &.t2 {
    background: rgba(254, 249, 195);
    border: 1px solid rgba(250, 240, 137, 0.4);
  }
  :global(.light-mode) &.t0 {
    background: rgba(220, 252, 231);
    border: 1px solid rgba(187, 247, 208, 0.5);
  }
  :global(.light-mode) &.unknown {
    background: rgba(229, 231, 235);
    border: 1px solid rgba(209, 213, 219, 0.5);
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

  :global(.dark-mode) &.t4 {
    background: var(--risk-t4);
    box-shadow: 0 0 8px var(--risk-t4);
  }
  :global(.dark-mode) &.t3 {
    background: var(--risk-t3);
    box-shadow: 0 0 8px var(--risk-t3);
  }
  :global(.dark-mode) &.t2 {
    background: var(--risk-t2);
    box-shadow: 0 0 8px var(--risk-t2);
  }
  :global(.dark-mode) &.t0 {
    background: var(--risk-t0);
    box-shadow: 0 0 8px var(--risk-t0);
  }
  :global(.dark-mode) &.unknown {
    background: var(--risk-unknown);
    box-shadow: 0 0 8px var(--risk-unknown);
  }

  :global(.light-mode) &.t4 { background: var(--risk-t4); }
  :global(.light-mode) &.t3 { background: var(--risk-t3); }
  :global(.light-mode) &.t2 { background: var(--risk-t2); }
  :global(.light-mode) &.t0 { background: var(--risk-t0); }
  :global(.light-mode) &.unknown { background: var(--risk-unknown); }
}

.risk-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 8px;

  :global(.dark-mode) &.t4 {
    color: #fca5a5;
    background: rgba(239, 68, 68, 0.15);
  }
  :global(.dark-mode) &.t3 {
    color: #fdba74;
    background: rgba(249, 115, 22, 0.15);
  }
  :global(.dark-mode) &.t2 {
    color: #fde047;
    background: rgba(234, 179, 8, 0.15);
  }
  :global(.dark-mode) &.t0 {
    color: #86efac;
    background: rgba(34, 197, 94, 0.15);
  }
  :global(.dark-mode) &.unknown {
    color: #d1d5db;
    background: rgba(156, 163, 175, 0.15);
  }

  :global(.light-mode) &.t4 {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
  }
  :global(.light-mode) &.t3 {
    color: #ea580c;
    background: rgba(234, 88, 12, 0.1);
  }
  :global(.light-mode) &.t2 {
    color: #ca8a04;
    background: rgba(202, 138, 4, 0.1);
  }
  :global(.light-mode) &.t0 {
    color: #16a34a;
    background: rgba(22, 163, 74, 0.1);
  }
  :global(.light-mode) &.unknown {
    color: #6b7280;
    background: rgba(156, 163, 175, 0.1);
  }
}

.risk-count {
  font-size: 11px;
  margin-left: auto;

  :global(.dark-mode) & {
    color: var(--text-muted);
  }
  :global(.light-mode) & {
    color: #9ca3af;
  }
}
</style>
