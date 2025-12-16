import type z from "zod";

import type { ingredientDetail } from "./dto";

export type IngredientDetail = z.infer<typeof ingredientDetail>;
