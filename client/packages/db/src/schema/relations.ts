import { relations } from "drizzle-orm";

import { FoodIngredientTable, FoodTable } from "./food";
import { IngredientTable } from "./ingredients";

export const FoodRelations = relations(FoodTable, ({ many }) => ({
  foodIngredients: many(FoodIngredientTable),
}));

export const IngredientRelations = relations(IngredientTable, ({ many }) => ({
  foodIngredients: many(FoodIngredientTable),
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
