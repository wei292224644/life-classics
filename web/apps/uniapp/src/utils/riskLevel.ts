// web/apps/uniapp/src/utils/riskLevel.ts
// 纯函数，无副作用，无外部依赖

export type RiskLevel = "t4" | "t3" | "t2" | "t1" | "t0" | "unknown"
export type VisualKey = "critical" | "high" | "medium" | "low" | "safe" | "unknown"

export interface RiskLevelConfig {
  /** 风险徽章文案 */
  badge: string
  /** 风险徽章图标（Unicode） */
  icon: string
  /** 无产品上下文时 Header 副标题 */
  subtitleNoProduct: string
  /**
   * 风险谱条指示针 left% 值（针中心点）
   * null 表示隐藏针（unknown 状态）
   */
  needleLeft: string | null
  /** 亮色 Header 背景色 */
  headerBgLight: string
  /** 亮色 Header 边框色 */
  headerBorderLight: string
  /** 亮色 Header 标题色 */
  headerTitleLight: string
  /** 亮色 Header 副标题色 */
  headerSubLight: string
  /** 亮色 Header 按钮背景色 */
  headerBtnLight: string
  /** 暗色 Header 背景色 */
  headerBgDark: string
  /** 暗色 Header 边框色 */
  headerBorderDark: string
  /** 暗色 Header 标题色 */
  headerTitleDark: string
  /** 暗色 Header 副标题色 */
  headerSubDark: string
  /** 暗色 Header 按钮背景色 */
  headerBtnDark: string
  /** 风险徽章背景色（无需亮/暗区分） */
  badgeBg: string
}

export const RISK_CONFIG: Record<VisualKey, RiskLevelConfig> = {
  critical: {
    badge: "极高风险",
    icon: "⛔",
    subtitleNoProduct: "⛔ 极高风险 · 不建议摄入",
    needleLeft: "88%",
    headerBgLight: "#fff1f2",
    headerBorderLight: "#fca5a5",
    headerTitleLight: "#7f1d1d",
    headerSubLight: "#dc2626",
    headerBtnLight: "rgba(220,38,38,0.15)",
    headerBgDark: "#1a0505",
    headerBorderDark: "#991b1b",
    headerTitleDark: "#fecaca",
    headerSubDark: "#f87171",
    headerBtnDark: "rgba(248,113,113,0.2)",
    badgeBg: "#dc2626",
  },
  high: {
    badge: "高风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 高风险 · 谨慎摄入",
    needleLeft: "72%",
    headerBgLight: "#fff4f0",
    headerBorderLight: "#fecaca",
    headerTitleLight: "#7f1d1d",
    headerSubLight: "#ef4444",
    headerBtnLight: "rgba(220,38,38,0.1)",
    headerBgDark: "#1a0808",
    headerBorderDark: "#7f1d1d",
    headerTitleDark: "#fca5a5",
    headerSubDark: "#f87171",
    headerBtnDark: "rgba(248,113,113,0.15)",
    badgeBg: "#ef4444",
  },
  medium: {
    badge: "中等风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 中等风险 · 适量摄入",
    needleLeft: "50%",
    headerBgLight: "#fefce8",
    headerBorderLight: "#fde68a",
    headerTitleLight: "#713f12",
    headerSubLight: "#a16207",
    headerBtnLight: "rgba(202,138,4,0.1)",
    headerBgDark: "#1a1500",
    headerBorderDark: "#713f12",
    headerTitleDark: "#fde68a",
    headerSubDark: "#fbbf24",
    headerBtnDark: "rgba(251,191,36,0.15)",
    badgeBg: "#f59e0b",
  },
  low: {
    badge: "低风险",
    icon: "✓",
    subtitleNoProduct: "✓ 低风险",
    needleLeft: "22%",
    headerBgLight: "#f0fdf4",
    headerBorderLight: "#bbf7d0",
    headerTitleLight: "#14532d",
    headerSubLight: "#16a34a",
    headerBtnLight: "rgba(22,163,74,0.1)",
    headerBgDark: "#051a0a",
    headerBorderDark: "#14532d",
    headerTitleDark: "#86efac",
    headerSubDark: "#4ade80",
    headerBtnDark: "rgba(74,222,128,0.15)",
    badgeBg: "#22c55e",
  },
  safe: {
    badge: "安全",
    icon: "✓",
    subtitleNoProduct: "✓ 安全 · 天然成分",
    needleLeft: "8%",
    headerBgLight: "#ecfdf5",
    headerBorderLight: "#6ee7b7",
    headerTitleLight: "#065f46",
    headerSubLight: "#059669",
    headerBtnLight: "rgba(5,150,105,0.1)",
    headerBgDark: "#022c22",
    headerBorderDark: "#065f46",
    headerTitleDark: "#6ee7b7",
    headerSubDark: "#34d399",
    headerBtnDark: "rgba(52,211,153,0.15)",
    badgeBg: "#10b981",
  },
  unknown: {
    badge: "暂无评级",
    icon: "?",
    subtitleNoProduct: "暂无风险评级数据",
    needleLeft: null,
    headerBgLight: "#f9fafb",
    headerBorderLight: "#d1d5db",
    headerTitleLight: "#374151",
    headerSubLight: "#6b7280",
    headerBtnLight: "rgba(107,114,128,0.1)",
    headerBgDark: "#111827",
    headerBorderDark: "#374151",
    headerTitleDark: "#9ca3af",
    headerSubDark: "#6b7280",
    headerBtnDark: "rgba(156,163,175,0.15)",
    badgeBg: "#9ca3af",
  },
}

const LEVEL_TO_VISUAL: Record<RiskLevel, VisualKey> = {
  t4: "critical",
  t3: "high",
  t2: "medium",
  t1: "low",
  t0: "safe",
  unknown: "unknown",
}

/** 将后端 level 枚举转换为前端视觉等级 key */
export function levelToVisualKey(level: RiskLevel | null | undefined): VisualKey {
  if (!level) return "unknown"
  return LEVEL_TO_VISUAL[level] ?? "unknown"
}

/** 获取风险等级完整配置 */
export function getRiskConfig(level: RiskLevel | null | undefined): RiskLevelConfig {
  return RISK_CONFIG[levelToVisualKey(level)]
}
