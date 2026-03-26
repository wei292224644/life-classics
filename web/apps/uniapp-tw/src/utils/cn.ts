import { twMerge } from 'tailwind-merge'

/**
 * 合并 Tailwind class，解决同组属性冲突问题（如 py-3 py-0 → py-0）
 * 后面的 class 优先级更高
 */
export function cn(...inputs: (string | undefined | null | false)[]): string {
  return twMerge(inputs.filter(Boolean).join(' '))
}
