<script setup lang="ts">
import { computed } from 'vue'
import DIcon from './DIcon.vue'
import type { ToastType } from '@/store/toast'
import { cn } from '@/utils/cn'

interface Props {
  type: ToastType
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const iconMap: Record<ToastType, string> = {
  success: 'check-circle',
  error: 'x-circle',
  warning: 'alert-triangle',
  info: 'info',
  loading: 'loader',
}

const iconBgClass: Record<ToastType, string> = {
  success: 'bg-green-500',
  error: 'bg-red-500',
  warning: 'bg-yellow-500',
  info: 'bg-blue-500',
  loading: 'bg-pink-500',
}

const isLoading = computed(() => props.type === 'loading')
const iconName = computed(() => iconMap[props.type])
const iconBg = computed(() => iconBgClass[props.type])
</script>

<template>
  <view class="toast-item relative flex items-start gap-3 w-full max-w-[340px] px-4 py-3 rounded-xl border border-border bg-white dark:bg-gray-800 shadow-lg">
    <!-- Icon Badge -->
    <view
      :class="cn('toast-icon flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl text-white', iconBg)"
    >
      <DIcon :name="iconName" :size="20" :dclass="isLoading ? 'animate-spin' : ''" />
    </view>

    <!-- Content -->
    <view class="toast-content flex-1 min-w-0 pt-1">
      <text class="toast-title block text-sm font-semibold text-gray-900 dark:text-white leading-tight">
        {{ title }}
      </text>
      <text
        v-if="description"
        class="toast-description block mt-1 text-xs text-gray-500 dark:text-gray-400 leading-relaxed"
      >
        {{ description }}
      </text>

      <!-- Action Button -->
      <view
        v-if="action"
        class="toast-action mt-2"
        @tap="action.onClick"
      >
        <text class="text-xs font-medium text-pink-500">
          {{ action.label }}
        </text>
      </view>
    </view>

    <!-- Close Button -->
    <view
      class="toast-close flex-shrink-0 p-1 -mr-1 -mt-1 rounded-lg opacity-60 active:opacity-100"
      @tap="emit('close')"
    >
      <DIcon name="x" :size="16" dclass="text-gray-400" />
    </view>

    <!-- Progress bar for auto-dismiss -->
    <view
      v-if="type !== 'loading'"
      class="toast-progress absolute bottom-0 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700"
    >
      <view
        class="toast-progress-bar h-full bg-pink-500 animate-shrink"
        :style="{ animationDuration: '3000ms' }"
      />
    </view>
  </view>
</template>

<style scoped>
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16rpx) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes shrink {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

.toast-item {
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.toast-progress-bar {
  animation: shrink linear forwards;
}

@media (prefers-reduced-motion: reduce) {
  .toast-item {
    animation: none;
    opacity: 1;
  }
  .toast-progress-bar {
    animation: none;
    width: 0%;
  }
}
</style>
