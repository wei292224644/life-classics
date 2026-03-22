<template>
  <view class="advice-card">
    <view class="advice-header">
      <up-icon name="star" size="18" color="#f59e0b" />
      <text>AI 健康建议</text>
    </view>
    <view v-if="items.length > 0" class="advice-list">
      <view v-for="item in items" :key="item.id" class="advice-item">
        <up-icon name="checkmark-circle" size="16" color="var(--text-muted)" />
        <text>{{ extractAdvice(item.results) }}</text>
      </view>
    </view>
    <text v-else class="empty">暂无建议</text>
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

function extractAdvice(results: unknown): string {
  if (!results || typeof results !== 'object') return '暂无建议';
  const r = results as Record<string, unknown>;
  if (typeof r.advice === 'string') return r.advice;
  if (typeof r.summary === 'string') return r.summary;
  return JSON.stringify(results);
}
</script>

<style lang="scss" scoped>
@import "~/@/styles/design-system.scss";

.advice-card {
  border-radius: 20px;
  padding: 18px;
  margin-bottom: 28px;
  animation: slideUp 0.5s 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  transform: translateY(16px);
}

.dark-mode .advice-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.light-mode .advice-card {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.advice-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 600;
}

.dark-mode .advice-header {
  color: var(--text-primary);
}

.light-mode .advice-header {
  color: #111;
}

.advice-header svg {
  width: 18px;
  height: 18px;
  fill: #f59e0b;
}

.advice-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.advice-item svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.dark-mode .advice-item svg {
  fill: var(--text-muted);
}

.light-mode .advice-item svg {
  fill: #9ca3af;
}

.advice-item span {
  font-size: 14px;
  line-height: 1.5;
}

.dark-mode .advice-item span {
  color: var(--text-secondary);
}

.light-mode .advice-item span {
  color: #4b5563;
}
</style>
