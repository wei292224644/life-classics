import type { AnalysisLevel } from "@acme/api/type";

const LEVEL_TEXT = {
  t0: "低风险",
  t1: "中低风险",
  t2: "中风险",
  t3: "中高风险",
  t4: "高风险",
  unknown: "未知",
} as const satisfies Record<AnalysisLevel, string>;

/**
 * 用于生成 Tailwind 颜色 class 的“基础色名”。
 * 注意：不要直接返回带数字的 class（如 `text-red-500`），避免各处拼接风格不一致；
 * 统一返回基础色（red / orange / ...），由调用方决定具体强度与场景（text/bg/border）。
 */
const LEVEL_COLOR = {
  t0: "green",
  t1: "lime",
  t2: "yellow",
  t3: "orange",
  t4: "red",
  unknown: "gray",
} as const satisfies Record<AnalysisLevel, string>;

export function levelToText(level: AnalysisLevel) {
  return LEVEL_TEXT[level];
}

export function levelToColor(level: AnalysisLevel) {
  return LEVEL_COLOR[level];
}
