import { createSelectSchema } from "@acme/db";
import {
  AnalysisTypeEnum,
  FoodAiAnalysisTable,
  LevelEnum,
} from "@acme/db/schema";

export const foodAiAnalysisDetail = createSelectSchema(FoodAiAnalysisTable);

export const analysisLevel = createSelectSchema(LevelEnum);

export const analysisType = createSelectSchema(AnalysisTypeEnum);
