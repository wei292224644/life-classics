import { createSelectSchema } from "@acme/db";
import * as schema from "@acme/db/schema";

import { AnalysisDetailSchema } from "../ai-analysis/dto";

export const IngredientDetailSchema = createSelectSchema(
  schema.IngredientTable,
).extend({
  analysis: AnalysisDetailSchema.optional(),
});
