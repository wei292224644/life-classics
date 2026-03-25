<script setup lang="ts">
import { useToastStore } from '@/store/toast'
import Toast from './Toast.vue'

const toastStore = useToastStore()
</script>

<template>
  <view class="toast-container fixed bottom-0 left-0 right-0 z-50 pointer-events-none">
    <view class="pb-6 px-4 pt-4">
      <view class="toast-list flex flex-col items-center gap-2 pointer-events-auto">
        <Toast
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          :type="toast.type"
          :title="toast.title"
          :description="toast.description"
          :action="toast.action"
          @close="toastStore.remove(toast.id)"
        />
      </view>
    </view>
  </view>
</template>

<style scoped>
</style>
