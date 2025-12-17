import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import { desc } from "@acme/db";
import { FoodTable } from "@acme/db/schema";

import { publicProcedure } from "../../trpc";
import { FoodDetailSchema } from "./dto";
import { foodRepository } from "./repository";

export const foodRouter = {
  all: publicProcedure.query(({ ctx }) => {
    return ctx.db.query.FoodTable.findMany({
      orderBy: desc(FoodTable.id),
      limit: 50,
    });
  }),

  fetchByBarcode: publicProcedure
    .input(z.object({ barcode: z.string().min(1).max(32) }))
    .output(FoodDetailSchema)
    .query(async ({ input }) => {
      const res = await foodRepository.fetchDetailByBarcode(input.barcode);

      if (!res) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Food not found",
        });
      }

      const nutritions = res.nutritions.map((val) => ({
        ...val,
        name: val.nutrition.name,
        alias: val.nutrition.alias,
      }));

      const ingredients = res.ingredients.map((val) => val.ingredient);
      const analysis = res.analysis;

      const foodUsageAdviceSummaryAnalysis = analysis.find(
        (item) => item.analysis_type === "usage_advice_summary",
      );
      const foodHealthSummaryAnalysis = analysis.find(
        (item) => item.analysis_type === "health_summary",
      );
      const foodIngredientRiskSummaryAnalysis = analysis.find(
        (item) => item.analysis_type === "risk_summary",
      );
      const foodPregnancySafetyAnalysis = analysis.find(
        (item) => item.analysis_type === "pregnancy_safety",
      );
      const foodSafetyRiskSummaryAnalysis = analysis.find(
        (item) => item.analysis_type === "recent_risk_summary",
      );

      return {
        ...res,
        nutritions,
        ingredients: ingredients,
        analysis: analysis,
        foodUsageAdviceSummaryAnalysis,
        foodHealthSummaryAnalysis,
        foodIngredientRiskSummaryAnalysis,
        foodPregnancySafetyAnalysis,
        foodSafetyRiskSummaryAnalysis,
      };
    }),
} satisfies TRPCRouterRecord;
