import type z from "zod";

import type { foodDetail, ingredientDetail } from "./dto";

export type IngredientDetail = z.infer<typeof ingredientDetail>;

export type FoodDetail = z.infer<typeof foodDetail>;
