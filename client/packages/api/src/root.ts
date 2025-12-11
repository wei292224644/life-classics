import type { TRPCRouterRecord } from "@trpc/server";

import { foodRouter } from "./router/food";
import { createTRPCRouter } from "./trpc";

const routes = {
  food: foodRouter,
} satisfies TRPCRouterRecord;

export const appRouter = createTRPCRouter(routes);

// export type definition of API
export type AppRouter = typeof appRouter;
