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

      return {
        ...res,
        nutritions,
      };
    }),
} satisfies TRPCRouterRecord;
