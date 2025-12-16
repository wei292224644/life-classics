import type z from "zod";

import type { analysisLevel, analysisType, foodAiAnalysisDetail } from "./dto";

export type FoodAiAnalysisDetail = z.infer<typeof foodAiAnalysisDetail>;
export type FoodAiAnalysisCreate = Omit<
  FoodAiAnalysisDetail,
  "id" | "createdAt" | "lastUpdatedAt" | "deletedAt" | "lastUpdatedByUser"
>;

export type AnalysisLevel = z.infer<typeof analysisLevel>;
export type AnalysisType = z.infer<typeof analysisType>;
