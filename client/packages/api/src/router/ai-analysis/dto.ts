import { createSelectSchema } from "@acme/db";
import {
  AnalysisDetailTable,
  AnalysisTypeEnum,
  LevelEnum,
  AnalysisTargetEnum,
} from "@acme/db/schema";

export const analysisDetail = createSelectSchema(AnalysisDetailTable);

export const analysisLevel = createSelectSchema(LevelEnum);

export const analysisType = createSelectSchema(AnalysisTypeEnum);

export const analysisTargetType = createSelectSchema(AnalysisTargetEnum);