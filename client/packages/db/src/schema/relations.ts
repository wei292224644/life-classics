import { relations } from "drizzle-orm";

import { AnalysisDetailTable } from "./ai_analysis";
import { FoodIngredientTable, FoodNutritionTable, FoodTable } from "./food";
import { IngredientTable } from "./ingredients";
import { NutritionTable } from "./nutritions";

export const FoodRelations = relations(FoodTable, ({ many }) => ({
  ingredients: many(FoodIngredientTable),
  analysis: many(AnalysisDetailTable),
  nutritions: many(FoodNutritionTable),
}));

export const IngredientRelations = relations(IngredientTable, ({ many }) => ({
  ingredients: many(FoodIngredientTable),
  analysis: many(AnalysisDetailTable),
}));

export const FoodIngredientRelations = relations(
  FoodIngredientTable,
  ({ one }) => ({
    food: one(FoodTable, {
      fields: [FoodIngredientTable.food_id],
      references: [FoodTable.id],
    }),
    ingredient: one(IngredientTable, {
      fields: [FoodIngredientTable.ingredient_id],
      references: [IngredientTable.id],
    }),
  }),
);

export const NutritionRelations = relations(NutritionTable, ({ many }) => ({
  nutritions: many(FoodNutritionTable),
}));

export const FoodNutritionRelations = relations(
  FoodNutritionTable,
  ({ one }) => ({
    food: one(FoodTable, {
      fields: [FoodNutritionTable.food_id],
      references: [FoodTable.id],
    }),
    nutrition: one(NutritionTable, {
      fields: [FoodNutritionTable.nutrition_id],
      references: [NutritionTable.id],
    }),
  }),
);

export const AnalysisDetailRelations = relations(
  AnalysisDetailTable,
  ({ one }) => ({
    food: one(FoodTable, {
      fields: [AnalysisDetailTable.target_id],
      references: [FoodTable.id],
    }),
    ingredient: one(IngredientTable, {
      fields: [AnalysisDetailTable.target_id],
      references: [IngredientTable.id],
    }),
  }),
);
