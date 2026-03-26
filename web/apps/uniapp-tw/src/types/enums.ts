export const RISK_LEVELS = ["t0", "t1", "t2", "t3", "t4", "unknown"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export type WhoLevel =
  | "Group 1"
  | "Group 2A"
  | "Group 2B"
  | "Group 3"
  | "Group 4"
  | "Unknown";

export type UnitValue = "g" | "mg" | "kJ" | "kcal" | "mL";

export type ReferenceType =
  | "PER_100_WEIGHT"
  | "PER_100_ENERGY"
  | "PER_SERVING"
  | "PER_DAY";
