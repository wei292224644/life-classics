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
@import "@/styles/design-system.scss";

.analysis-card {
  background: var(--bg-card);
  border-radius: var(--space-4);
  padding: var(--space-7);
  margin-bottom: var(--space-5);
  border-left: 6rpx solid var(--border-color);

  &--t4 { border-left-color: var(--risk-t4); }
  &--t3 { border-left-color: var(--risk-t3); }
  &--t2 { border-left-color: var(--risk-t2); }
  &--t1 { border-left-color: var(--risk-t1); }
  &--t0 { border-left-color: var(--risk-t0); }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.card-title {
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--text-primary);
}

.level-badge {
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--text-base);

  &--t4 {
    background: var(--risktag-t4-bg);
    color: var(--risk-t4);
  }
  &--t3 {
    background: var(--risktag-t3-bg);
    color: var(--risk-t3);
  }
  &--t2 {
    background: var(--risktag-t2-bg);
    color: var(--risk-t2);
  }
  &--t1 {
    background: var(--risktag-t1-bg);
    color: var(--risk-t1);
  }
  &--t0 {
    background: var(--risktag-t1-bg);
    color: var(--risk-t1);
  }
  &--unknown {
    background: var(--risktag-unknown-bg);
    color: var(--risk-unknown);
  }
}

.card-content {
  font-size: var(--text-xl);
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
