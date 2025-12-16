import { Suspense, useMemo } from "react";
import Link from "next/link";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";

import type { AnalysisDetailDetail, FoodDetail } from "@acme/api/type";

import { useTRPC } from "~/trpc/react";
import { RiskBadge } from "./risk-badge";

export function Ingredients({ food }: { food: FoodDetail }) {
  const ingredientAnalysis = useMemo(() => {
    return food.analysis.find(
      (item) => item.analysis_type === "ingredient_health_summary",
    );
  }, [food.analysis]);
  return (
    <section className="gap-3">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-lg font-semibold">配料信息</h3>
      </div>
      <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
        <div className="flex flex-col gap-3">
          {food.ingredients.length > 0 ? (
            food.ingredients.map((item) => (
              <IngredientItem key={item.id} ingredient={item} />
            ))
          ) : (
            <div className="text-muted-foreground py-8 text-center text-sm">
              暂无配料信息
            </div>
          )}
        </div>

        <div className="border-border text-muted-foreground mt-4 flex items-start gap-2 border-t pt-3 text-sm">
          <IngredientAnalysis analysis={ingredientAnalysis} id={food.id} />
        </div>
      </div>
    </section>
  );
}

function IngredientItem({
  ingredient,
}: {
  ingredient: { id: number; name: string };
}) {
  const trpc = useTRPC();

  // 获取该配料的风险分析（使用普通query，因为可能不存在）
  const { data: riskAnalysis, isLoading } = useQuery(
    trpc.analysis.advice.queryOptions({
      targetId: ingredient.id,
      targetType: "ingredient",
      type: "ingredient_risk_summary",
    }),
  );

  const riskReason = useMemo(() => {
    if (!riskAnalysis || !riskAnalysis.results) return null;
    const results = Array.isArray(riskAnalysis.results)
      ? riskAnalysis.results
      : [];
    // 只显示第一条作为简短原因
    return results[0] || null;
  }, [riskAnalysis]);

  const hasRiskInfo = riskAnalysis && riskAnalysis.level !== "unknown";

  return (
    <Link
      href={`/ingredient/${ingredient.id}`}
      className="group relative flex flex-col gap-2 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="text-base font-semibold text-foreground">
              {ingredient.name}
            </span>
            {isLoading ? (
              <div className="h-6 w-16 animate-pulse rounded-lg bg-muted" />
            ) : hasRiskInfo ? (
              <RiskBadge level={riskAnalysis.level} showText={true} />
            ) : (
              <RiskBadge level="unknown" showText={true} />
            )}
          </div>
          {hasRiskInfo && riskReason && (
            <div className="mt-2 text-sm text-muted-foreground leading-relaxed line-clamp-2">
              {riskReason}
            </div>
          )}
        </div>
        <svg
          className="text-muted-foreground h-5 w-5 shrink-0 transition-transform group-hover:translate-x-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </div>
    </Link>
  );
}

export function IngredientAnalysis({
  analysis,
  id,
}: {
  analysis?: AnalysisDetailDetail;
  id: number;
}) {
  if (!analysis) {
    return (
      <Suspense fallback={<IngredientAnalysisSkeleton />}>
        <IngredientAsyncAnalysis id={id} />
      </Suspense>
    );
  }

  return <IngredientAnalysisContent analysis={analysis} />;
}

function IngredientAnalysisContent({
  analysis,
}: {
  analysis: AnalysisDetailDetail;
}) {
  return (
    <ul className="flex list-none flex-col gap-2">
      {Array.isArray(analysis.results) &&
        analysis.results.map((item: string, index: number) => (
          <li key={index} className="text-muted-foreground text-sm">
            {item}
          </li>
        ))}
    </ul>
  );
}

function IngredientAsyncAnalysis({ id }: { id: number }) {
  const trpc = useTRPC();

  const { data: analysis } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({
      targetId: id,
      targetType: "food",
      type: "ingredient_health_summary",
    }),
  );

  return <IngredientAnalysisContent analysis={analysis} />;
}

function IngredientAnalysisSkeleton() {
  return (
    <ul className="flex list-none flex-col gap-3">
      <li className="flex items-start gap-3 text-sm">
        <div className="h-5 w-5 animate-pulse rounded-full bg-gray-200" />
      </li>
    </ul>
  );
}
