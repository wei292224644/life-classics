import type { TRPCRouterRecord } from "@trpc/server";

import { aiAnalysisRouter } from "./router/ai-analysis/route";
import { foodRouter } from "./router/food/route";
import { createTRPCRouter } from "./trpc";

const routes = {
  food: foodRouter,
  analysis: aiAnalysisRouter,
} satisfies TRPCRouterRecord;

export const appRouter = createTRPCRouter(routes);

// export type definition of API
export type AppRouter = typeof appRouter;
