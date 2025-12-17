import type { AnalysisLevel } from "@acme/api/type";

export function levelToText(level: AnalysisLevel) {
  switch (level) {
    case "t0":
      return "低风险";
    case "t1":
      return "中风险";
    case "t2":
      return "中高风险";
    case "t3":
      return "高风险";
    case "t4":
      return "严重风险";
    case "unknown":
      return "未知";
  }
}
