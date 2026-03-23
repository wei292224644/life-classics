// web/apps/uniapp/src/utils/riskLevel.ts
// 纯函数，无副作用，无外部依赖

export type RiskLevel = "t4" | "t3" | "t2" | "t1" | "t0" | "unknown"
export type VisualKey = "critical" | "high" | "medium" | "low" | "safe" | "unknown"

export interface RiskLevelConfig {
  visualKey: VisualKey
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
}

export const RISK_CONFIG: Record<VisualKey, RiskLevelConfig> = {
  critical: {
    visualKey: "critical",
    badge: "极高风险",
    icon: "⛔",
    subtitleNoProduct: "⛔ 极高风险 · 不建议摄入",
    needleLeft: "88%",
  },
  high: {
    visualKey: "high",
    badge: "高风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 高风险 · 谨慎摄入",
    needleLeft: "72%",
  },
  medium: {
    visualKey: "medium",
    badge: "中等风险",
    icon: "⚠",
    subtitleNoProduct: "⚠ 中等风险 · 适量摄入",
    needleLeft: "50%",
  },
  low: {
    visualKey: "low",
    badge: "低风险",
    icon: "✓",
    subtitleNoProduct: "✓ 低风险",
    needleLeft: "22%",
  },
  safe: {
    visualKey: "safe",
    badge: "安全",
    icon: "✓",
    subtitleNoProduct: "✓ 安全 · 天然成分",
    needleLeft: "8%",
  },
  unknown: {
    visualKey: "unknown",
    badge: "暂无评级",
    icon: "?",
    subtitleNoProduct: "暂无风险评级数据",
    needleLeft: null,
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
