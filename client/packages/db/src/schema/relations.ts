import { relations } from "drizzle-orm";

import { FoodIngredientTable, FoodTable } from "./food";
import { AnalysisDetailTable } from "./ai_analysis";
import { IngredientTable } from "./ingredients";

export const FoodRelations = relations(FoodTable, ({ many }) => ({
  ingredients: many(FoodIngredientTable),
  analysis: many(AnalysisDetailTable),
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
