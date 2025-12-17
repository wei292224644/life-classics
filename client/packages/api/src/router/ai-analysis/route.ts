import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import { createIdempotencyWindow } from "../../middleware/idempotency";
import { publicProcedure } from "../../trpc";
import {
  AnalysisDetailSchema,
  AnalysisTargetTypeSchema,
  AnalysisTypeSchema,
} from "./dto";
import { analysisDetailRepository } from "./repository";

const adviceIdempotency = createIdempotencyWindow<{ id: number }>({
  key: ({ path, input }) => `${path}:${input.id}`,
  windowMs: 60_000,
});

export const aiAnalysisRouter = {
  advice: publicProcedure
    .use(adviceIdempotency)
    .input(
      z.object({
        targetId: z.number(),
        type: AnalysisTypeSchema,
        targetType: AnalysisTargetTypeSchema,
      }),
    )
    .output(AnalysisDetailSchema.nullable())
    .query(async ({ input }) => {
      try {
        const res =
          await analysisDetailRepository.fetchDetailByTargetIdAndTargetTypeAndAnalysisType(
            input.targetId,
            input.targetType,
            input.type,
          );

        if (!res) {
          return null;
        }

        // if (res.length === 0) {
        //   // 只有非TRPCError的异常（如数据库连接错误等）才继续处理
        //   console.log("AI分析中...");
        //   const foodDetail = await foodRepository.fetchDetailById(input.id);

        //   if (!foodDetail) {
        //     throw new TRPCError({
        //       code: "NOT_FOUND",
        //       message: "Food not found",
        //     });
        //   }

        //   const ingredients = foodDetail.foodIngredients.map(
        //     (val) => val.ingredient,
        //   );

        //   const aiAnalysis = await foodAiAnalysisService.generateAiAnalysisList(
        //     {
        //       ...foodDetail,
        //       ingredients: ingredients as IngredientDetail[],
        //     },
        //   );

        //   //存入数据库
        //   const analysisList =
        //     await foodAiAnalysisRepository.create(aiAnalysis);

        //   if (analysisList.length === 0) {
        //     return [];
        //   }

        //   return analysisList;
        // }

        return res;
      } catch (error) {
        console.error("Failed to get food ai analysis", error);
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to get food ai analysis",
        });
      }
    }),
} satisfies TRPCRouterRecord;
