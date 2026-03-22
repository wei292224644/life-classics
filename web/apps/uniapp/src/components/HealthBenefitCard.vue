<template>
  <view class="health-card">
    <view class="section-title">健康益处</view>
    <view v-if="items.length > 0" class="health-list">
      <view v-for="item in items" :key="item.id" class="health-item">
        <up-icon name="checkmark-circle" size="18" color="var(--risk-t0)" />
        <text class="health-text">{{ extractSummary(item.results) }}</text>
      </view>
    </view>
    <text v-else class="empty">暂无健康益处数据</text>
  </view>
</template>

<script setup lang="ts">
interface AnalysisSummary {
  id: number;
  analysis_type: string;
  results: unknown;
  level: string;
}

defineProps<{ items: AnalysisSummary[] }>();

function extractSummary(results: unknown): string {
  if (!results || typeof results !== 'object') return '暂无数据';
  const r = results as Record<string, unknown>;
  if (typeof r.summary === 'string') return r.summary;
  return JSON.stringify(results);
}
</script>

<style lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.health-card {
  border-radius: 20px;
  padding: 18px;
  margin-bottom: 28px;
  animation: slideUp 0.5s 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);
}

.dark-mode .health-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.light-mode .health-card {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 14px;
}

.dark-mode .section-title {
  color: var(--text-primary);
}

.light-mode .section-title {
  color: #111;
}

.health-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.health-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.health-item svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.dark-mode .health-item svg {
  fill: var(--risk-t0);
}

.light-mode .health-item svg {
  fill: var(--risk-t0);
}

.health-item span {
  font-size: 14px;
  line-height: 1.5;
}

.dark-mode .health-item span {
  color: var(--text-secondary);
}

.light-mode .health-item span {
  color: #4b5563;
}
</style>
