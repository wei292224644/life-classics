import { Suspense } from "react";
import { useSuspenseQuery } from "@tanstack/react-query";

import type {
  AnalysisDetailWithResults,
  AnalysisTargetType,
} from "@acme/api/type";

import { AIBadge } from "~/app/_components/ai-badge";
import { CheckCircledIcon } from "~/app/_icons/CheckCircledIcon";
import { useTRPC } from "~/trpc/react";

export function HealthAnalysis({
  analysis,
  id,
  targetType = "food",
}: {
  analysis?: AnalysisDetailWithResults<"ingredient_health_summary">;
  id: number;
  targetType?: AnalysisTargetType;
}) {
  if (!analysis) {
    return (
      <Suspense fallback={<HealthAnalysisSkeleton />}>
        <HealthAsyncAnalysis id={id} targetType={targetType} />
      </Suspense>
    );
  }

  return <HealthAnalysisContent analysis={analysis} />;
}

function HealthAnalysisContent({
  analysis,
}: {
  analysis?: AnalysisDetailWithResults<"ingredient_health_summary"> | null;
}) {
  if (!analysis) {
    return null;
  }

  return (
    <section className="gap-3">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-lg font-semibold">健康益处</h3>
        <AIBadge />
      </div>
      <div className="bg-card border-border rounded-2xl border p-4">
        <ul className="flex list-none flex-col gap-3">
          {analysis.results.summaries.map((item) => (
            <li className="flex items-start gap-2 text-sm leading-relaxed">
              <CheckCircledIcon className="text-primary h-5 w-5 shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function HealthAsyncAnalysis({
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
      type: "ingredient_health_summary",
      targetType: targetType,
    }),
  );

  return <HealthAnalysisContent analysis={analysis} />;
}

function HealthAnalysisSkeleton() {
  return (
    <ul className="flex list-none flex-col gap-3">
      <li className="flex items-start gap-3 text-sm">
        <div className="h-5 w-5 animate-pulse rounded-full bg-gray-200" />
      </li>
    </ul>
  );
}
