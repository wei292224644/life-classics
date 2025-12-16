import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";

import { analysisDetailDetail } from "../ai-analysis/dto";

export const ingredientDetail = createSelectSchema(schema.IngredientTable).extend({
  analysis: analysisDetailDetail.array().default([]),
});
