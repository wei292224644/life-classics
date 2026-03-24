<template>
  <view :class="['analysis-card', `analysis-card--${item.level}`]">
    <view class="card-header">
      <text class="card-title">{{ ANALYSIS_LABELS[item.analysis_type] ?? item.analysis_type }}</text>
      <view :class="['level-badge', `level-badge--${item.level}`]">
        <text>{{ LEVEL_LABELS[item.level] ?? item.level }}</text>
      </view>
    </view>
    <text class="card-content">{{ extractSummary(item.results) }}</text>
  </view>
</template>

<script setup lang="ts">
import type { AnalysisSummary } from "../types/product";

defineProps<{ item: AnalysisSummary }>();

const ANALYSIS_LABELS: Record<string, string> = {
  usage_advice_summary: "食用建议",
  health_summary: "健康分析",
  pregnancy_safety: "母婴安全",
  risk_summary: "风险分析",
  recent_risk_summary: "近期风险",
};

const LEVEL_LABELS: Record<string, string> = {
  t0: "低风险",
  t1: "较低",
  t2: "中等",
  t3: "较高",
  t4: "高风险",
  unknown: "信息不足",
};

function extractSummary(results: unknown): string {
  if (!results || typeof results !== "object") return "暂无数据";
  const r = results as Record<string, unknown>;
  if (typeof r.summary === "string") return r.summary;
  return JSON.stringify(results);
}
</script>

<style lang="scss" scoped>
.analysis-card {
  @apply bg-card rounded-lg p-7 mb-5 border-l-[6rpx] border-border;

  &--t4 { border-left-color: var(--color-risk-t4); }
  &--t3 { border-left-color: var(--color-risk-t3); }
  &--t2 { border-left-color: var(--color-risk-t2); }
  &--t1 { border-left-color: var(--color-risk-t1); }
  &--t0 { border-left-color: var(--color-risk-t0); }
}

.card-header {
  @apply flex justify-between items-center mb-4;
}

.card-title {
  @apply text-2xl font-semibold text-foreground;
}

.level-badge {
  @apply px-4 py-1 rounded-full text-base;

  &--t4 {
    background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
    color: var(--color-risk-t4);
  }
  &--t3 {
    background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
    color: var(--color-risk-t3);
  }
  &--t2 {
    background: color-mix(in oklch, var(--color-risk-t2) 12%, transparent);
    color: var(--color-risk-t2);
  }
  &--t1 {
    background: color-mix(in oklch, var(--color-risk-t1) 12%, transparent);
    color: var(--color-risk-t1);
  }
  &--t0 {
    background: color-mix(in oklch, var(--color-risk-t0) 12%, transparent);
    color: var(--color-risk-t0);
  }
  &--unknown {
    background: color-mix(in oklch, var(--color-risk-unknown) 12%, transparent);
    color: var(--color-risk-unknown);
  }
}

.card-content {
  @apply text-xl text-secondary leading-relaxed;
}
</style>
