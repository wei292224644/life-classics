import type { TRPCRouterRecord } from "@trpc/server";

import { aiAnalysisRouter } from "./router/ai-analysis/route";
import { foodRouter } from "./router/food/route";
import { ingredientRouter } from "./router/ingredient/route";
import { createTRPCRouter } from "./trpc";

const routes = {
  food: foodRouter,
  analysis: aiAnalysisRouter,
  ingredient: ingredientRouter,
} satisfies TRPCRouterRecord;

export const appRouter = createTRPCRouter(routes);

// export type definition of API
export type AppRouter = typeof appRouter;
