import type z from "zod";

import type {
  analysisDetail,
  analysisLevel,
  analysisTargetType,
  analysisType,
} from "./dto";

// ============================================================================
// Base Types
// ============================================================================

export type AnalysisBaseDetail = z.infer<typeof analysisDetail>;
export type AnalysisLevel = z.infer<typeof analysisLevel>;
export type AnalysisType = z.infer<typeof analysisType>;
export type AnalysisTargetType = z.infer<typeof analysisTargetType>;

// ============================================================================
// Analysis Result Types
// ============================================================================

export type AnalysisResultWithResultsUsageAdvice = {
  summaries: string[];
};

export type AnalysisResultWithResultsHealthSummary = {
  summaries: string[];
};

export type AnalysisResultWithResultsIngredientAnalysis = {
  summaries: string[];
};

export type AnalysisResultWithResultsPregnancySafetyAnalysis = {
  summaries: string[];
};

export type AnalysisResultWithIngredientsRiskAnalysis = {
  summaries: string[];
};

export type AnalysisResultWithResultsFoodRiskSummary = {
  summaries: string[];
};

// ============================================================================
// Type Mappings
// ============================================================================

type AnalysisResultMap = {
  ingredient_usage_advice: AnalysisResultWithResultsUsageAdvice;
  ingredient_health_summary: AnalysisResultWithResultsHealthSummary;
  ingredient_risk_summary: AnalysisResultWithResultsIngredientAnalysis;
  ingredient_pregnancy_safety: AnalysisResultWithResultsPregnancySafetyAnalysis;
  food_risk_summary: AnalysisResultWithResultsFoodRiskSummary;
};

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
