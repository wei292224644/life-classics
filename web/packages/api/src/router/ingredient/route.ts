import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import { publicProcedure } from "../../trpc";
import { IngredientDetailSchema } from "./dto";
import { ingredientRepository } from "./repository";

export const ingredientRouter = {
  fetchDetailById: publicProcedure
    .input(z.object({ id: z.number() }))
    .output(IngredientDetailSchema)
    .query(async ({ input }) => {
      const ingredient = await ingredientRepository.fetchDetailById(input.id);

      if (!ingredient) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Ingredient not found",
        });
      }

      const analysis = ingredient.analysis;

      const ingredientSummaryAnalysis = analysis.find(
        (item) => item.analysis_type === "ingredient_summary",
      );

      return { ...ingredient, analysis: ingredientSummaryAnalysis };
    }),
} satisfies TRPCRouterRecord;
