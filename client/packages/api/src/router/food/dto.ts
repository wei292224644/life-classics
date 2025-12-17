import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";

import { AnalysisDetailSchema } from "../ai-analysis/dto";

export const AnalysisFoodDetailSchema = AnalysisDetailSchema.pick({
  id: true,
  analysis_type: true,
  results: true,
  level: true,
});

const nutritionDetailSchema = createSelectSchema(schema.NutritionTable);
const foodNutritionValueDetailSchema = createSelectSchema(
  schema.FoodNutritionTable,
);
export const FoodNutritionDetailSchema = foodNutritionValueDetailSchema
  .pick({
    value: true,
    value_unit: true,
    reference_type: true,
    reference_unit: true,
  })
  .extend(
    nutritionDetailSchema.pick({
      id: true,
      name: true,
      alias: true,
    }).shape,
  );

export const FoodIngredientDetailSchema = createSelectSchema(
  schema.IngredientTable,
).extend({
  analysis: AnalysisFoodDetailSchema.optional(),
});

export const FoodDetailSchema = createSelectSchema(schema.FoodTable).extend({
  ingredients: FoodIngredientDetailSchema.array().default([]),
  analysis: AnalysisFoodDetailSchema.array().default([]),
  nutritions: FoodNutritionDetailSchema.array().default([]),

  foodUsageAdviceSummaryAnalysis: AnalysisFoodDetailSchema.optional(),
  foodHealthSummaryAnalysis: AnalysisFoodDetailSchema.optional(),
  foodIngredientRiskSummaryAnalysis: AnalysisFoodDetailSchema.optional(),
  foodPregnancySafetyAnalysis: AnalysisFoodDetailSchema.optional(),
  foodSafetyRiskSummaryAnalysis: AnalysisFoodDetailSchema.optional(),
});
