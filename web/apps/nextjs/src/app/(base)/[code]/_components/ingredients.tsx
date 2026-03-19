import { useMemo } from "react";
import Link from "next/link";

import type {
  AnalysisFoodDetailWithResults,
  AnalysisLevel,
  FoodIngredientDetail,
} from "@acme/api/type";
import { AnalysisLevelSchema } from "@acme/api/dto";
import { cn } from "@acme/ui";

interface RiskGroup {
  level: AnalysisLevel;
  label: string;
  ingredients: FoodIngredientDetail[];
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
    card: {
      borderColor: string;
      hoverBgColor: string;
      shadowColor: string;
    };
  }
> = {
  t4: {
    label: "严重风险",
    borderColor: "border-red-200 dark:border-red-800",
    bgColor: "bg-red-50 dark:bg-red-900/10",
    badgeBg: "bg-red-100 dark:bg-red-900/30",
    badgeText: "text-red-700 dark:text-red-400",
    dotColor: "bg-red-600 dark:bg-red-400",
    indicatorColor:
      "from-red-500/50 via-red-500/30 dark:from-red-500/60 dark:via-red-500/30 ",
    decorationColor: "bg-red-500 dark:bg-red-600",
    reasonBg: "bg-red-100 dark:bg-red-900/30",
    reasonText: "text-red-700 dark:text-red-400",
    card: {
      borderColor: "border-red-100 dark:border-red-900/30",
      hoverBgColor: "hover:bg-red-50/50 dark:hover:bg-red-900/10",
      shadowColor: "shadow-red-100 dark:shadow-red-900/30",
    },
  },
  t3: {
    label: "高风险",
    borderColor: "border-orange-200 dark:border-orange-800",
    bgColor: "bg-orange-50 dark:bg-orange-900/10",
    badgeBg: "bg-orange-100 dark:bg-orange-900/30",
    badgeText: "text-orange-700 dark:text-orange-400",
    dotColor: "bg-orange-600 dark:bg-orange-400",
    indicatorColor:
      "from-orange-500/50 via-orange-500/30 dark:from-orange-500/60 dark:via-orange-500/30 ",
    decorationColor: "bg-orange-500 dark:bg-orange-600",
    reasonBg: "bg-orange-100 dark:bg-orange-900/30",
    reasonText: "text-orange-700 dark:text-orange-400",
    card: {
      borderColor: "border-orange-100 dark:border-orange-900/30",
      hoverBgColor: "hover:bg-orange-50/50 dark:hover:bg-orange-900/10",
      shadowColor: "shadow-orange-100 dark:shadow-orange-900/30",
    },
  },
  t2: {
    label: "中高风险",
    borderColor: "border-yellow-200 dark:border-yellow-800",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/10",
    badgeBg: "bg-yellow-100 dark:bg-yellow-900/30",
    badgeText: "text-yellow-700 dark:text-yellow-400",
    dotColor: "bg-yellow-600 dark:bg-yellow-400",
    indicatorColor:
      "from-yellow-500/50 via-yellow-500/30 dark:from-yellow-500/60 dark:via-yellow-500/30 ",
    decorationColor: "bg-yellow-500 dark:bg-yellow-600",
    reasonBg: "bg-yellow-100 dark:bg-yellow-900/30",
    reasonText: "text-yellow-700 dark:text-yellow-400",
    card: {
      borderColor: "border-yellow-100 dark:border-yellow-900/30",
      hoverBgColor: "hover:bg-yellow-50/50 dark:hover:bg-yellow-900/10",
      shadowColor: "shadow-yellow-100 dark:shadow-yellow-900/30",
    },
  },
  t1: {
    label: "中风险",
    borderColor: "border-lime-200 dark:border-lime-800",
    bgColor: "bg-lime-50 dark:bg-lime-900/10",
    badgeBg: "bg-lime-100 dark:bg-lime-900/30",
    badgeText: "text-lime-700 dark:text-lime-400",
    dotColor: "bg-lime-600 dark:bg-lime-400",
    indicatorColor:
      "from-lime-500/50 via-lime-500/30 dark:from-lime-500/60 dark:via-lime-500/30 ",
    decorationColor: "bg-lime-500 dark:bg-lime-600",
    reasonBg: "bg-lime-100 dark:bg-lime-900/30",
    reasonText: "text-lime-700 dark:text-lime-400",
    card: {
      borderColor: "border-lime-100 dark:border-lime-900/30",
      hoverBgColor: "hover:bg-lime-50/50 dark:hover:bg-lime-900/10",
      shadowColor: "shadow-lime-100 dark:shadow-lime-900/30",
    },
  },
  t0: {
    label: "低风险",
    borderColor: "border-green-200 dark:border-green-800",
    bgColor: "bg-green-50 dark:bg-green-900/10",
    badgeBg: "bg-green-100 dark:bg-green-900/30",
    badgeText: "text-green-700 dark:text-green-400",
    dotColor: "bg-green-600 dark:bg-green-400",
    indicatorColor:
      "from-green-500/50 via-green-500/30 dark:from-green-500/60 dark:via-green-500/30 ",
    decorationColor: "bg-green-400 dark:bg-green-600",
    reasonBg: "bg-green-100 dark:bg-green-900/30",
    reasonText: "text-green-700 dark:text-green-400",
    card: {
      borderColor: "border-green-100 dark:border-green-900/30",
      hoverBgColor: "hover:bg-green-50/50 dark:hover:bg-green-900/10",
      shadowColor: "shadow-green-100 dark:shadow-green-900/30",
    },
  },
  unknown: {
    label: "未知",
    borderColor: "border-gray-200 dark:border-gray-800",
    bgColor: "bg-gray-50 dark:bg-gray-900/10",
    badgeBg: "bg-gray-100 dark:bg-gray-900/30",
    badgeText: "text-gray-700 dark:text-gray-400",
    dotColor: "bg-gray-600 dark:bg-gray-400",
    indicatorColor:
      "from-gray-500/50 via-gray-500/30 dark:from-gray-500/60 dark:via-gray-500/30 ",
    decorationColor: "bg-gray-400 dark:bg-gray-600",
    reasonBg: "bg-gray-100 dark:bg-gray-900/30",
    reasonText: "text-gray-700 dark:text-gray-400",

    card: {
      borderColor: "border-gray-100 dark:border-gray-900/30",
      hoverBgColor: "hover:bg-gray-50/50 dark:hover:bg-gray-900/10",
      shadowColor: "shadow-gray-100 dark:shadow-gray-900/30",
    },
  },
};

export function Ingredients({
  ingredients,
}: {
  ingredients: FoodIngredientDetail[];
}) {
  const group = useMemo(() => {
    return AnalysisLevelSchema.options.map((level) => {
      return {
        level: level,
        label: level,
        ingredients: ingredients.filter(
          (ingredient) => ingredient.analysis?.level === level,
        ),
      };
    });
  }, [ingredients]);

  return (
    <section className="gap-3">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-lg font-semibold">配料信息</h3>
      </div>
      <div className="flex flex-col gap-3">
        {group.map(
          (group) =>
            group.ingredients.length > 0 && (
              <RiskGroupCard key={group.level} group={group} />
            ),
        )}
      </div>
    </section>
  );
}

function RiskGroupCard({ group }: { group: RiskGroup }) {
  const config = levelConfig[group.level];

  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        config.borderColor,
        config.bgColor,
      )}
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
      <div className="ingredient-scroll flex gap-3 overflow-x-auto p-1 pb-2">
        {group.ingredients.map((ingredient) => (
          <IngredientCard
            key={ingredient.id}
            ingredient={ingredient}
            config={config}
            level={group.level}
          />
        ))}
      </div>
    </div>
  );
}

function IngredientCard({
  ingredient,
  config,
  level,
}: {
  ingredient: FoodIngredientDetail;
  config: (typeof levelConfig)[AnalysisLevel];
  level: AnalysisLevel;
}) {
  const isHighRisk = level === "t4" || level === "t3" || level === "t2";

  // 根据风险等级设置边框颜色
  const borderClass = config.card.borderColor;

  const hoverBgClass = config.card.hoverBgColor;

  const shadowClass = config.card.shadowColor;

  return (
    <Link
      href={`/ingredient/${ingredient.id}`}
      className={cn(
        "group relative flex min-w-36 flex-col overflow-hidden rounded-lg border p-3.5 shadow-sm",
        borderClass,
        hoverBgClass,
        shadowClass,
      )}
    >
      {/* 风险指示条 */}
      <div
        className={cn(
          "absolute top-0 bottom-0 left-0 w-2 rounded-l-lg bg-linear-to-r to-transparent",
          config.indicatorColor,
        )}
      ></div>
      {/* 装饰背景 */}
      <div
        className={cn(
          "absolute -top-5 -right-5 h-[60px] w-[60px] rounded-full opacity-10 transition-opacity group-hover:opacity-15",
          config.decorationColor,
        )}
      ></div>
      <div className="relative flex flex-col">
        <div className="mb-1 flex items-start justify-between gap-2">
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
              {!isHighRisk && level === "t0" && (
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
              {!isHighRisk && level !== "t0" && (
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
        {ingredient.analysis &&
          level !== "unknown" &&
          level !== "t0" &&
          level !== "t1" && (
            <div
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium",
                config.reasonText,
                config.reasonBg,
              )}
            >
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              {
                (
                  ingredient.analysis as AnalysisFoodDetailWithResults<"ingredient_summary">
                ).results.result
              }
            </div>
          )}
      </div>
    </Link>
  );
}
