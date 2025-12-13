import type z from "zod";

import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";

export const ingredientDetail = createSelectSchema(schema.IngredientTable);

export const foodDetail = createSelectSchema(schema.FoodTable).extend({
  ingredients: ingredientDetail.array().default([]),
});

export type IngredientDetail = z.infer<typeof ingredientDetail>;
