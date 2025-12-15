import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import type { IngredientDetail } from "../food/dto";
import { createIdempotencyWindow } from "../../middleware/idempotency";
import { publicProcedure } from "../../trpc";
import { foodRepository } from "../food/repository";
import { foodAiAnalysisDetail } from "./dto";
import { foodAiAnalysisRepository } from "./repository";
import { foodAiAnalysisService } from "./service";

const adviceIdempotency = createIdempotencyWindow<{ id: number }>({
  key: ({ path, input }) => `${path}:${input.id}`,
  windowMs: 60_000,
});

export const aiAnalysisRouter = {
  advice: publicProcedure
    .use(adviceIdempotency)
    .input(z.object({ id: z.number() }))
    .output(foodAiAnalysisDetail)
    .query(async ({ input }) => {
      try {
        const res = await foodAiAnalysisRepository.fetchDetailByFoodId(
          input.id,
        );

        if (!res) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Food not found",
          });
        }

        return res;
      } catch {
        console.log("AI分析中...");
        const foodDetail = await foodRepository.fetchDetailById(input.id);

        if (!foodDetail) {
          throw new TRPCError({
            code: "NOT_FOUND",
            message: "Food not found",
          });
        }

        const ingredients = foodDetail.foodIngredients.map(
          (val) => val.ingredient,
        );

        const aiAnalysis = await foodAiAnalysisService.generateAiAnalysis({
          ...foodDetail,
          ingredients: ingredients as IngredientDetail[],
        });

        //存入数据库
        const [analysis] = await foodAiAnalysisRepository.create([aiAnalysis]);

        if (!analysis) {
          console.error("Failed to create food ai analysis", aiAnalysis);
          throw new TRPCError({
            code: "INTERNAL_SERVER_ERROR",
            message: "Failed to create food ai analysis",
          });
        }

        return analysis;
      }
    }),
} satisfies TRPCRouterRecord;
