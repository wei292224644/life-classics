import { Suspense, useMemo } from "react";
import Link from "next/link";
import { useQueries, useSuspenseQuery } from "@tanstack/react-query";

import type {
  AnalysisBaseDetail,
  AnalysisLevel,
  FoodDetail,
} from "@acme/api/type";

import { useTRPC } from "~/trpc/react";

interface IngredientWithRisk {
  id: number;
  name: string;
  level: AnalysisLevel;
  riskReason?: string;
}

interface RiskGroup {
  level: AnalysisLevel;
  label: string;
  ingredients: IngredientWithRisk[];
}

const levelConfig: Record<
  AnalysisLevel,
  {
    label: string;
    borderColor: string;
    bgColor: string;
    badgeBg: string;
    badgeText: string;
    dotColor: string;
    indicatorColor: string;
    decorationColor: string;
    reasonBg: string;
    reasonText: string;
  }
> = {
  t4: {
    label: "高风险",
    borderColor: "border-red-200 dark:border-red-800",
    bgColor: "bg-red-50 dark:bg-red-900/10",
    badgeBg: "bg-red-100 dark:bg-red-900/30",
    badgeText: "text-red-700 dark:text-red-400",
    dotColor: "bg-red-600 dark:bg-red-400",
    indicatorColor: "bg-red-500 dark:bg-red-600",
    decorationColor: "bg-red-500 dark:bg-red-600",
    reasonBg: "bg-red-100 dark:bg-red-900/30",
    reasonText: "text-red-700 dark:text-red-400",
  },
  t3: {
    label: "中高风险",
    borderColor: "border-orange-200 dark:border-orange-800",
    bgColor: "bg-orange-50 dark:bg-orange-900/10",
    badgeBg: "bg-orange-100 dark:bg-orange-900/30",
    badgeText: "text-orange-700 dark:text-orange-400",
    dotColor: "bg-orange-600 dark:bg-orange-400",
    indicatorColor: "bg-orange-500 dark:bg-orange-600",
    decorationColor: "bg-orange-500 dark:bg-orange-600",
    reasonBg: "bg-orange-100 dark:bg-orange-900/30",
    reasonText: "text-orange-700 dark:text-orange-400",
  },
  t2: {
    label: "中高风险",
    borderColor: "border-orange-200 dark:border-orange-800",
    bgColor: "bg-orange-50 dark:bg-orange-900/10",
    badgeBg: "bg-orange-100 dark:bg-orange-900/30",
    badgeText: "text-orange-700 dark:text-orange-400",
    dotColor: "bg-orange-600 dark:bg-orange-400",
    indicatorColor: "bg-orange-500 dark:bg-orange-600",
    decorationColor: "bg-orange-500 dark:bg-orange-600",
    reasonBg: "bg-orange-100 dark:bg-orange-900/30",
    reasonText: "text-orange-700 dark:text-orange-400",
  },
  t1: {
    label: "中风险",
    borderColor: "border-yellow-200 dark:border-yellow-800",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/10",
    badgeBg: "bg-yellow-100 dark:bg-yellow-900/30",
    badgeText: "text-yellow-700 dark:text-yellow-400",
    dotColor: "bg-yellow-600 dark:bg-yellow-400",
    indicatorColor: "bg-yellow-500 dark:bg-yellow-600",
    decorationColor: "bg-yellow-500 dark:bg-yellow-600",
    reasonBg: "bg-yellow-100 dark:bg-yellow-900/30",
    reasonText: "text-yellow-700 dark:text-yellow-400",
  },
  t0: {
    label: "低风险",
    borderColor: "border-green-200 dark:border-green-800",
    bgColor: "bg-green-50 dark:bg-green-900/10",
    badgeBg: "bg-green-100 dark:bg-green-900/30",
    badgeText: "text-green-700 dark:text-green-400",
    dotColor: "bg-green-600 dark:bg-green-400",
    indicatorColor: "bg-green-400 dark:bg-green-600",
    decorationColor: "bg-green-400 dark:bg-green-600",
    reasonBg: "bg-green-100 dark:bg-green-900/30",
    reasonText: "text-green-700 dark:text-green-400",
  },
  unknown: {
    label: "未知",
    borderColor: "border-gray-200 dark:border-gray-800",
    bgColor: "bg-gray-50 dark:bg-gray-900/10",
    badgeBg: "bg-gray-100 dark:bg-gray-900/30",
    badgeText: "text-gray-700 dark:text-gray-400",
    dotColor: "bg-gray-600 dark:bg-gray-400",
    indicatorColor: "bg-gray-400 dark:bg-gray-600",
    decorationColor: "bg-gray-400 dark:bg-gray-600",
    reasonBg: "bg-gray-100 dark:bg-gray-900/30",
    reasonText: "text-gray-700 dark:text-gray-400",
  },
};

export function Ingredients({ food }: { food: FoodDetail }) {
  const trpc = useTRPC();

  // 并行获取所有配料的风险分析
  const riskQueries = useQueries({
    queries: food.ingredients.map((ingredient) => ({
      ...trpc.analysis.advice.queryOptions({
        targetId: ingredient.id,
        targetType: "ingredient",
        type: "ingredient_risk_summary",
      }),
      enabled: true,
    })),
  });

  // 将配料和风险分析组合
  const ingredientsWithRisk = useMemo(() => {
    return food.ingredients.map((ingredient, index) => {
      const riskQuery = riskQueries[index];
      const riskAnalysis = riskQuery?.data;
      const level = riskAnalysis?.level ?? "unknown";

      // 获取风险原因（第一条summary）
      let riskReason: string | undefined;
      if (riskAnalysis?.results) {
        const results = riskAnalysis.results as
          | { summaries?: string[] }
          | string[];
        if (
          Array.isArray(results) &&
          results.length > 0 &&
          typeof results[0] === "string"
        ) {
          riskReason = results[0];
        } else if (
          typeof results === "object" &&
          "summaries" in results &&
          Array.isArray(results.summaries) &&
          results.summaries.length > 0
        ) {
          riskReason = results.summaries[0];
        }
      }

      return {
        id: ingredient.id,
        name: ingredient.name,
        level,
        riskReason,
      };
    });
  }, [food.ingredients, riskQueries]);

  // 按风险等级分组
  const riskGroups = useMemo(() => {
    const groups: RiskGroup[] = [
      { level: "t4", label: levelConfig.t4.label, ingredients: [] },
      { level: "t3", label: levelConfig.t3.label, ingredients: [] },
      { level: "t2", label: levelConfig.t2.label, ingredients: [] },
      { level: "t1", label: levelConfig.t1.label, ingredients: [] },
      { level: "t0", label: levelConfig.t0.label, ingredients: [] },
      { level: "unknown", label: levelConfig.unknown.label, ingredients: [] },
    ];

    ingredientsWithRisk.forEach((ingredient) => {
      const group = groups.find((g) => g.level === ingredient.level);
      if (group) {
        group.ingredients.push(ingredient);
      }
    });

    // 过滤掉空的组
    return groups.filter((group) => group.ingredients.length > 0);
  }, [ingredientsWithRisk]);

  return (
    <section className="gap-3">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-lg font-semibold">配料信息</h3>
      </div>
      <div className="flex flex-col gap-3">
        {riskGroups.length > 0 ? (
          riskGroups.map((group) => (
            <RiskGroupCard key={group.level} group={group} />
          ))
        ) : (
          <div className="bg-card border-border rounded-2xl border p-4">
            <div className="text-muted-foreground py-8 text-center text-sm">
              暂无配料信息
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function RiskGroupCard({ group }: { group: RiskGroup }) {
  const config = levelConfig[group.level];

  return (
    <div
      className={`rounded-xl border ${config.borderColor} ${config.bgColor} p-4`}
    >
      <div className="mb-3 flex items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-sm font-semibold ${config.badgeText} ${config.badgeBg}`}
        >
          <span className={`h-2 w-2 rounded-full ${config.dotColor}`}></span>
          {config.label}
        </span>
        <span className="text-muted-foreground text-xs">
          {group.ingredients.length} 项
        </span>
      </div>
      <div className="ingredient-scroll">
        {group.ingredients.map((ingredient) => (
          <IngredientCard
            key={ingredient.id}
            ingredient={ingredient}
            config={config}
          />
        ))}
      </div>
    </div>
  );
}

function IngredientCard({
  ingredient,
  config,
}: {
  ingredient: IngredientWithRisk;
  config: (typeof levelConfig)[AnalysisLevel];
}) {
  const isHighRisk =
    ingredient.level === "t4" ||
    ingredient.level === "t3" ||
    ingredient.level === "t2";

  // 根据风险等级设置边框颜色
  const borderClass =
    ingredient.level === "t4" ||
    ingredient.level === "t3" ||
    ingredient.level === "t2"
      ? "border-red-100 dark:border-red-900/30"
      : ingredient.level === "t1"
        ? "border-yellow-100 dark:border-yellow-900/30"
        : ingredient.level === "t0"
          ? "border-green-100 dark:border-green-900/30"
          : "border-gray-100 dark:border-gray-900/30";

  const hoverBgClass =
    ingredient.level === "t4" ||
    ingredient.level === "t3" ||
    ingredient.level === "t2"
      ? "hover:bg-red-50/50 dark:hover:bg-red-900/10"
      : ingredient.level === "t1"
        ? "hover:bg-yellow-50/50 dark:hover:bg-yellow-900/10"
        : ingredient.level === "t0"
          ? "hover:bg-green-50/50 dark:hover:bg-green-900/10"
          : "hover:bg-gray-50/50 dark:hover:bg-gray-900/10";

  return (
    <Link
      href={`/ingredient/${ingredient.id}`}
      className={`ingredient-card group relative flex flex-col rounded-xl border ${borderClass} bg-white p-3.5 shadow-sm transition-all ${hoverBgClass} hover:shadow-md active:scale-[0.98] dark:bg-gray-900/50`}
    >
      {/* 风险指示条 */}
      <div
        className={`risk-indicator absolute top-0 bottom-0 left-0 w-1 rounded-l-xl ${config.indicatorColor}`}
      ></div>
      {/* 装饰背景 */}
      <div
        className={`card-decoration absolute -top-5 -right-5 h-[60px] w-[60px] rounded-full opacity-10 transition-opacity group-hover:opacity-15 ${config.decorationColor}`}
      ></div>
      <div className="relative flex flex-col">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-center gap-1.5">
              {isHighRisk && (
                <svg
                  className={`h-4 w-4 shrink-0 ${config.reasonText}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {!isHighRisk && ingredient.level === "t0" && (
                <svg
                  className={`h-4 w-4 shrink-0 ${config.reasonText}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {!isHighRisk && ingredient.level !== "t0" && (
                <svg
                  className={`h-4 w-4 shrink-0 ${config.reasonText}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              <div className="text-foreground text-sm font-semibold">
                {ingredient.name}
              </div>
            </div>
          </div>
          <svg
            className="text-muted-foreground h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
        {ingredient.riskReason && (
          <div
            className={`risk-reason inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${config.reasonText} ${config.reasonBg}`}
          >
            <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            {ingredient.riskReason}
          </div>
        )}
      </div>
    </Link>
  );
}

// function IngredientAnalysis({
//   analysis,
//   id,
// }: {
//   analysis?: AnalysisBaseDetail;
//   id: number;
// }) {
//   if (!analysis) {
//     return (
//       <Suspense fallback={<IngredientAnalysisSkeleton />}>
//         <IngredientAsyncAnalysis id={id} />
//       </Suspense>
//     );
//   }

//   return <IngredientAnalysisContent analysis={analysis} />;
// }

// function IngredientAnalysisContent({
//   analysis,
// }: {
//   analysis: AnalysisBaseDetail;
// }) {
//   const results = useMemo(() => {
//     if (!analysis.results) return [];
//     if (Array.isArray(analysis.results)) {
//       return analysis.results.filter(
//         (item): item is string => typeof item === "string",
//       );
//     }
//     if (
//       typeof analysis.results === "object" &&
//       "summaries" in analysis.results
//     ) {
//       const summaries = (analysis.results as { summaries?: string[] })
//         .summaries;
//       return Array.isArray(summaries) ? summaries : [];
//     }
//     return [];
//   }, [analysis.results]);

//   return (
//     <ul className="flex list-none flex-col gap-2">
//       {results.map((item: string, index: number) => (
//         <li key={index} className="text-muted-foreground text-sm">
//           {item}
//         </li>
//       ))}
//     </ul>
//   );
// }

// function IngredientAsyncAnalysis({ id }: { id: number }) {
//   const trpc = useTRPC();

//   const { data: analysis } = useSuspenseQuery(
//     trpc.analysis.advice.queryOptions({
//       targetId: id,
//       targetType: "food",
//       type: "ingredient_health_summary",
//     }),
//   );

//   if (!analysis) {
//     return null;
//   }

//   return <IngredientAnalysisContent analysis={analysis} />;
// }

// function IngredientAnalysisSkeleton() {
//   return (
//     <ul className="flex list-none flex-col gap-3">
//       <li className="flex items-start gap-3 text-sm">
//         <div className="h-5 w-5 animate-pulse rounded-full bg-gray-200" />
//       </li>
//     </ul>
//   );
// }
