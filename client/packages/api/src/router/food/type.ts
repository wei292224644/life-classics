import type z from "zod";

import type {
  AnalysisResultWithResults,
  AnalysisType,
} from "../ai-analysis/type";
import type {
  AnalysisFoodDetailSchema,
  FoodDetailSchema,
  FoodIngredientDetailSchema,
  FoodNutritionDetailSchema,
} from "./dto";

export type FoodIngredientDetail = z.infer<typeof FoodIngredientDetailSchema>;

export type FoodDetail = z.infer<typeof FoodDetailSchema>;

export type FoodNutritionDetail = z.infer<typeof FoodNutritionDetailSchema>;

export type AnalysisFoodDetail = z.infer<typeof AnalysisFoodDetailSchema>;

export type AnalysisFoodDetailWithResults<T extends AnalysisType> =
  AnalysisFoodDetail & {
    results: AnalysisResultWithResults<T>;
  };
