import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import { publicProcedure } from "../../trpc";
import { ingredientDetail } from "./dto";
import { ingredientRepository } from "./repository";
import { analysisDetailRepository } from "../ai-analysis/repository";

export const ingredientRouter = {
  fetchDetailById: publicProcedure
    .input(z.object({ id: z.number() }))
    .output(ingredientDetail)
    .query(async ({ input }) => {
      const ingredient = await ingredientRepository.fetchDetailById(input.id);

      if (!ingredient) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Ingredient not found",
        });
      }

      // 获取该配料的所有AI分析
      const analysis = await analysisDetailRepository.fetchDetailByTargetId(
        input.id,
      );

      return {
        ...ingredient,
        analysis: analysis,
      };
    }),
} satisfies TRPCRouterRecord;
