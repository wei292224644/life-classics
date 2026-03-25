// src/store/toast.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading'

export interface Toast {
  id: string
  type: ToastType
  title: string
  description?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function add(toast: Omit<Toast, 'id'>) {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    const newToast: Toast = { ...toast, id }
    toasts.value.push(newToast)

    // auto remove
    const duration = toast.duration ?? 3000
    if (duration > 0 && toast.type !== 'loading') {
      setTimeout(() => {
        remove(id)
      }, duration)
    }

    return id
  }

  function remove(id: string) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function success(title: string, description?: string) {
    return add({ type: 'success', title, description })
  }

  function error(title: string, description?: string) {
    return add({ type: 'error', title, description, duration: 5000 })
  }

  function warning(title: string, description?: string) {
    return add({ type: 'warning', title, description })
  }

  function info(title: string, description?: string) {
    return add({ type: 'info', title, description })
  }

  function loading(title: string, description?: string) {
    return add({ type: 'loading', title, description, duration: 0 })
  }

  return {
    toasts,
    add,
    remove,
    success,
    error,
    warning,
    info,
    loading,
  }
})
