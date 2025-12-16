import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";

import { analysisDetail } from "../ai-analysis/dto";

export const ingredientDetail = createSelectSchema(
  schema.IngredientTable,
).extend({
  analysis: analysisDetail.array().default([]),
});
