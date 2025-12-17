import type z from "zod";

import type {
  AnalysisDetailSchema,
  AnalysisLevelSchema,
  AnalysisTargetTypeSchema,
  AnalysisTypeSchema,
} from "./dto";

// ============================================================================
// Base Types
// ============================================================================

export type AnalysisBaseDetail = z.infer<typeof AnalysisDetailSchema>;

export type AnalysisLevel = z.infer<typeof AnalysisLevelSchema>;
export type AnalysisType = z.infer<typeof AnalysisTypeSchema>;
export type AnalysisTargetType = z.infer<typeof AnalysisTargetTypeSchema>;

// ============================================================================
// Analysis Result Types
// ============================================================================

export interface AnalysisResultWithResultsUsageAdvice {
  summaries: string[];
}

export interface AnalysisResultWithResultsHealthSummary {
  summaries: string[];
}

export interface AnalysisResultWithResultsIngredientAnalysis {
  summaries: string[];
}

export interface AnalysisResultWithResultsPregnancySafetyAnalysis {
  summaries: string[];
}

export interface AnalysisResultWithIngredientsRiskAnalysis {
  summaries: string[];
}

export interface AnalysisResultWithResultsFoodRiskSummary {
  summaries: string[];
}

export interface AnalysisResultWithResultsIngredientSummary {
  // summaries: string[];
  result: string; //审核结果
  reason: string; //审核原因
}
// ============================================================================
// Type Mappings
// ============================================================================

interface AnalysisResultMap {
  usage_advice_summary: AnalysisResultWithResultsUsageAdvice;
  health_summary: AnalysisResultWithResultsHealthSummary;
  pregnancy_safety: AnalysisResultWithResultsPregnancySafetyAnalysis;
  risk_summary: AnalysisResultWithResultsFoodRiskSummary;
  recent_risk_summary: AnalysisResultWithResultsFoodRiskSummary;
  ingredient_summary: AnalysisResultWithResultsIngredientSummary;
}

// ============================================================================
// Utility Types
// ============================================================================

export type AnalysisResultWithResults<T extends AnalysisType> =
  T extends keyof AnalysisResultMap ? AnalysisResultMap[T] : never;

export type AnalysisDetailWithResults<T extends AnalysisType> = Omit<
  AnalysisBaseDetail,
  "results"
> & {
  results: AnalysisResultWithResults<T>;
};

export type AnalysisDetailCreate = Omit<
  AnalysisBaseDetail,
  | "id"
  | "createdAt"
  | "updatedAt"
  | "lastUpdatedAt"
  | "lastUpdatedByUser"
  | "deletedAt"
  | "createdByUser"
>;
