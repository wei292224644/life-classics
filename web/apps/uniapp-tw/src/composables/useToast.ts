// src/composables/useToast.ts
// 全局 Toast API，类似 sonner 的用法
import { useToastStore } from '@/store/toast'

export function useToast() {
  const store = useToastStore()

  return {
    // 通用添加
    toast: store.add,
    // 便捷方法
    success: store.success,
    error: store.error,
    warning: store.warning,
    info: store.info,
    loading: store.loading,
    // 手动关闭
    dismiss: store.remove,
  }
}

// 同步便捷调用（可在任意位置导入使用）
// 注意：需要 Pinia 初始化后才能正常工作
export const toast = {
  success: (title: string, description?: string) => {
    try {
      useToastStore().success(title, description)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
  error: (title: string, description?: string) => {
    try {
      useToastStore().error(title, description)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
  warning: (title: string, description?: string) => {
    try {
      useToastStore().warning(title, description)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
  info: (title: string, description?: string) => {
    try {
      useToastStore().info(title, description)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
  loading: (title: string, description?: string) => {
    try {
      useToastStore().loading(title, description)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
  dismiss: (id: string) => {
    try {
      useToastStore().remove(id)
    } catch (e) {
      console.warn('[toast] Store not ready:', e)
    }
  },
}
