// web/apps/uniapp/src/utils/riskLevel.ts
// 纯函数，无副作用，无外部依赖
// process.env.UNI_PLATFORM 由 Vite 在编译时静态替换，不会进入运行时
import { isMp } from "./paltform";
export type RiskLevel = "t4" | "t3" | "t2" | "t1" | "t0" | "unknown";
export type VisualKey =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "safe"
  | "unknown";

export interface RiskLevelConfig {
  visualKey: VisualKey;
  /** 风险徽章文案 */
  badge: string;
  /** 风险徽章图标（Unicode） */
  icon: string;
  /** 无产品上下文时 Header 副标题 */
  subtitleNoProduct: string;
  /**
   * 风险谱条指示针 left% 值（针中心点）
   * null 表示隐藏针（unknown 状态）
   */
  needleLeft: string | null;
}

export const RISK_CONFIG: Record<VisualKey, RiskLevelConfig> = {
  critical: {
    visualKey: "critical",
    badge: "极高风险",
    icon: "riskT4",
    subtitleNoProduct: "极高风险 · 不建议摄入",
    needleLeft: "88%",
  },
  high: {
    visualKey: "high",
    badge: "高风险",
    icon: "riskT3",
    subtitleNoProduct: "高风险 · 谨慎摄入",
    needleLeft: "72%",
  },
  medium: {
    visualKey: "medium",
    badge: "中等风险",
    icon: "riskT2",
    subtitleNoProduct: "中等风险 · 适量摄入",
    needleLeft: "50%",
  },
  low: {
    visualKey: "low",
    badge: "中低风险",
    icon: "riskT1",
    subtitleNoProduct: "中低风险",
    needleLeft: "22%",
  },
  safe: {
    visualKey: "safe",
    badge: "低风险",
    icon: "riskT0",
    subtitleNoProduct: "低风险",
    needleLeft: "8%",
  },
  unknown: {
    visualKey: "unknown",
    badge: "暂无评级",
    icon: "riskUnknown",
    subtitleNoProduct: "暂无风险评级数据",
    needleLeft: null,
  },
};

const LEVEL_TO_VISUAL: Record<RiskLevel, VisualKey> = {
  t4: "critical",
  t3: "high",
  t2: "medium",
  t1: "low",
  t0: "safe",
  unknown: "unknown",
};

/** 将后端 level 枚举转换为前端视觉等级 key */
export function levelToVisualKey(
  level: RiskLevel | null | undefined,
): VisualKey {
  if (!level) return "unknown";
  return LEVEL_TO_VISUAL[level] ?? "unknown";
}

/** 获取风险等级完整配置 */
export function getRiskConfig(
  level: RiskLevel | null | undefined,
): RiskLevelConfig {
  return RISK_CONFIG[levelToVisualKey(level)];
}

/**
 * 生成风险等级对应的 Tailwind class 字符串。
 * safelist 已覆盖所有 risk 色前缀 × variant × 透明度组合，可自由动态拼接。
 *
 * @example
 * riskCls('t2', 'bg/10 border')
 * // → 'bg-risk-t2/10 border-risk-t2'
 *
 * riskCls('t2', 'bg/10 border dark:bg/5 dark:border hover:bg/20')
 * // → 'bg-risk-t2/10 border-risk-t2 dark:bg-risk-t2/5 dark:border-risk-t2 hover:bg-risk-t2/20'
 */
export function riskCls(
  level: RiskLevel | null | undefined,
  recipe: string,
): string {
  const l = level ?? "unknown";
  // 小程序中 weapp-tailwindcss 将 CSS 选择器里的 `/` 转义为 `_f`，动态生成的 class 需同步处理
  const opacitySep = isMp ? "_f" : "/";
  return recipe
    .trim()
    .split(/\s+/)
    .map((token) => {
      const colonIdx = token.lastIndexOf(":");
      const variant = colonIdx !== -1 ? token.slice(0, colonIdx + 1) : "";
      const rest = colonIdx !== -1 ? token.slice(colonIdx + 1) : token;
      const [prefix, opacity] = rest.split("/");
      const cls = opacity
        ? `${prefix}-risk-${l}${opacitySep}${opacity}`
        : `${prefix}-risk-${l}`;
      return `${variant}${cls}`;
    })
    .join(" ");
}
