import { createSelectSchema } from "@acme/db";
import {
  AnalysisDetailTable,
  AnalysisTargetEnum,
  AnalysisTypeEnum,
  LevelEnum,
} from "@acme/db/schema";

export const AnalysisDetailSchema = createSelectSchema(AnalysisDetailTable);

export const AnalysisLevelSchema = createSelectSchema(LevelEnum);

export const AnalysisTypeSchema = createSelectSchema(AnalysisTypeEnum);

export const AnalysisTargetTypeSchema = createSelectSchema(AnalysisTargetEnum);
