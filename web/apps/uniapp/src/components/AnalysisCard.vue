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
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  border-left: 6rpx solid #e5e7eb;

  &--t4 { border-left-color: #dc2626; }
  &--t3 { border-left-color: #ea580c; }
  &--t2 { border-left-color: #ca8a04; }
  &--t1 { border-left-color: #16a34a; }
  &--t0 { border-left-color: #22c55e; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.card-title { font-size: 30rpx; font-weight: bold; color: #1a1a1a; }

.level-badge {
  padding: 4rpx 16rpx;
  border-radius: 100rpx;
  font-size: 22rpx;

  &--t4 { background: #fee2e2; color: #dc2626; }
  &--t3 { background: #ffedd5; color: #ea580c; }
  &--t2 { background: #fef9c3; color: #ca8a04; }
  &--t1, &--t0 { background: #dcfce7; color: #16a34a; }
  &--unknown { background: #f3f4f6; color: #6b7280; }
}

.card-content { font-size: 28rpx; color: #555; line-height: 1.6; }
</style>
