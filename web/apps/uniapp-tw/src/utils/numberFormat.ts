/**
 * 数字字符串格式化：用于把后端返回的类似 "2.40" / "4.600" 变成更适合展示的 "2.4" / "4.6"。
 */

export function formatDecimalString(
  value: string | number | null | undefined,
  options?: {
    maxFractionDigits?: number
    trimTrailingZeros?: boolean
  },
): string {
  if (value === null || value === undefined) return ""

  const s = String(value).trim()
  if (!s) return ""

  const num = Number(s)
  if (!Number.isFinite(num)) return s

  const maxFractionDigits = options?.maxFractionDigits ?? 1
  const trimTrailingZeros = options?.trimTrailingZeros ?? true

  // toFixed 会把整数也变成例如 "52.0"，因此可选地裁掉末尾多余 0
  const fixed = num.toFixed(maxFractionDigits)
  if (!trimTrailingZeros) return fixed

  // 处理 "52.0" -> "52"；"2.40" -> "2.4"
  return fixed.replace(/\.?0+$/, "")
}

