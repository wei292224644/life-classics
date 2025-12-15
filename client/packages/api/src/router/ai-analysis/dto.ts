import type z from "zod";

import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";
import { PregnancyLevelEnum, RiskLevelEnum } from "@acme/db/schema";

export const foodAiAnalysisDetail = createSelectSchema(
  schema.FoodAiAnalysisTable,
);

export const riskLevel = createSelectSchema(RiskLevelEnum);
export const pregnancyLevel = createSelectSchema(PregnancyLevelEnum);

export type FoodAiAnalysisDetail = z.infer<typeof foodAiAnalysisDetail>;
export type FoodAiAnalysisCreate = Omit<
  FoodAiAnalysisDetail,
  "id" | "createdAt" | "lastUpdatedAt" | "deletedAt" | "lastUpdatedByUser"
>;

export type RiskLevel = z.infer<typeof riskLevel>;
export type PregnancyLevel = z.infer<typeof pregnancyLevel>;
