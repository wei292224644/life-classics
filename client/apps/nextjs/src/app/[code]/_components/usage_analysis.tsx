import { Suspense } from "react";
import { useSuspenseQuery } from "@tanstack/react-query";

import type {
  AnalysisDetailWithResults,
  AnalysisTargetType,
} from "@acme/api/type";

import { AIBadge } from "~/app/_components/ai-badge";
import { CheckCircledIcon } from "~/app/_icons/CheckCircledIcon";
import { useTRPC } from "~/trpc/react";

export function UsageAnalysis({
  analysis,
  id,
  targetType = "food",
}: {
  analysis?: AnalysisDetailWithResults<"ingredient_usage_advice">;
  id: number;
  targetType?: AnalysisTargetType;
}) {
  if (!analysis) {
    return (
      <Suspense fallback={<UsageAnalysisSkeleton />}>
        <UsageAsyncAnalysis id={id} targetType={targetType} />
      </Suspense>
    );
  }

  return <UsageAnalysisContent analysis={analysis} />;
}

function UsageAnalysisContent({
  analysis,
}: {
  analysis?: AnalysisDetailWithResults<"ingredient_usage_advice"> | null;
}) {
  if (!analysis) {
    return null;
  }

  return (
    <section className="gap-3">
      <div className="relative mb-3 inline-flex items-center gap-2">
        <h3 className="text-foreground text-lg leading-none font-semibold">
          食用建议
        </h3>
        <AIBadge />
      </div>
      <div className="bg-card border-border rounded-2xl border p-4">
        <ul className="flex list-none flex-col gap-2.5">
          {analysis.results.summaries.map((item, index: number) => (
            <li
              key={index}
              className="flex items-start gap-2 text-sm leading-relaxed"
            >
              <CheckCircledIcon className="h-5 w-5 shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function UsageAsyncAnalysis({
  id,
  targetType,
}: {
  id: number;
  targetType: AnalysisTargetType;
}) {
  const trpc = useTRPC();

  const { data: analysis } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({
      targetId: id,
      type: "ingredient_usage_advice",
      targetType: targetType,
    }),
  );

  return (
    <UsageAnalysisContent
      analysis={
        analysis as AnalysisDetailWithResults<"ingredient_usage_advice">
      }
    />
  );
}

function UsageAnalysisSkeleton() {
  return (
    <ul className="flex list-none flex-col gap-3">
      <li className="flex items-start gap-3 text-sm">
        <div className="h-5 w-5 animate-pulse rounded-full bg-gray-200" />
      </li>
    </ul>
  );
}
