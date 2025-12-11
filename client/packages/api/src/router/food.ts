import type { TRPCRouterRecord } from "@trpc/server";

import { desc } from "@acme/db";
import { FoodTable } from "@acme/db/schema";

import { publicProcedure } from "../trpc";

// const createFoodInput = z.object({
//   id: z.string().min(1).max(32),
//   name: z.string().min(1).max(255),
//   ingredients: z.array(z.number().int()).default([]),
//   manufacturer: z.string().max(255).optional(),
//   production_address: z.string().max(255).optional(),
//   origin_place: z.string().max(255).optional(),
//   production_license: z.string().max(255).optional(),
//   product_category: z.string().max(255).optional(),
//   product_standard_code: z.string().max(255).optional(),
//   shelf_life: z.string().max(100).optional(),
//   net_content: z.string().max(100).optional(),
// });

export const foodRouter = {
  all: publicProcedure.query(({ ctx }) => {
    return ctx.db.query.FoodTable.findMany({
      orderBy: desc(FoodTable.id),
      limit: 50,
    });
  }),

  //   byId: publicProcedure
  //     .input(z.object({ id: z.string().min(1) }))
  //     .query(({ ctx, input }) => {
  //       return ctx.db.query.FoodTable.findFirst({
  //         where: eq(FoodTable.id, input.id),
  //       });
  //     }),

  //   create: publicProcedure
  //     .input(createFoodInput)
  //     .mutation(({ ctx, input }) => {
  //       return ctx.db.insert(FoodTable).values(input).onConflictDoNothing({
  //         target: FoodTable.id,
  //       });
  //     }),
} satisfies TRPCRouterRecord;
