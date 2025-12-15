import type { TRPCRouterRecord } from "@trpc/server";
import { TRPCError } from "@trpc/server";
import z from "zod";

import { desc } from "@acme/db";
import { FoodTable } from "@acme/db/schema";

import { publicProcedure } from "../../trpc";
import { foodDetail } from "./dto";
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
    .output(foodDetail)
    .query(async ({ input }) => {
      const res = await foodRepository.fetchDetailByBarcode(input.barcode);

      if (!res) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Food not found",
        });
      }

      const ingredients = res.foodIngredients.map((val) => val.ingredient);

      return { ...res, ingredients: ingredients };
    }),

  fetchDetailById: publicProcedure
    .input(z.object({ id: z.number() }))
    .output(foodDetail)
    .query(async ({ input }) => {
      const res = await foodRepository.fetchDetailById(input.id);

      if (!res) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Food not found",
        });
      }

      const ingredients = res.foodIngredients.map((val) => val.ingredient);

      return { ...res, ingredients: ingredients };
    }),
} satisfies TRPCRouterRecord;
