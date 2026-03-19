import type z from "zod";

import type { IngredientDetailSchema } from "./dto";

export type IngredientDetail = z.infer<typeof IngredientDetailSchema>;
