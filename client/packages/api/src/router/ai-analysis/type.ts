import type z from "zod";

import type {
  analysisDetailDetail,
  analysisLevel,
  analysisTargetType,
  analysisType,
} from "./dto";

export type AnalysisDetailDetail = z.infer<typeof analysisDetailDetail>;

export type AnalysisDetailCreate = Omit<
  AnalysisDetailDetail,
  | "id"
  | "createdAt"
  | "updatedAt"
  | "lastUpdatedAt"
  | "lastUpdatedByUser"
  | "deletedAt"
  | "createdByUser"
>;

export type AnalysisLevel = z.infer<typeof analysisLevel>;
export type AnalysisType = z.infer<typeof analysisType>;
export type AnalysisTargetType = z.infer<typeof analysisTargetType>;
