import { Suspense } from "react";
import { useSuspenseQuery } from "@tanstack/react-query";

import type {
  AnalysisDetailWithResults,
  AnalysisTargetType,
  AnalysisType,
} from "@acme/api/type";

import { AIBadge } from "~/app/_components/ai-badge";
import { useTRPC } from "~/trpc/react";

export function AnalysisCard<T extends AnalysisType>({
  title,
  id,
  targetType,
  type,
  analysis,
  children,
}: {
  title: string;
  id: number;
  targetType: AnalysisTargetType;
  type: AnalysisType;
  analysis?: AnalysisDetailWithResults<T> | null;
  children: ({
    analysis,
  }: {
    analysis: AnalysisDetailWithResults<T>;
  }) => React.ReactNode;
}) {
  if (!analysis) {
    return (
      <Suspense fallback={<Skeleton />}>
        <AsyncAnalysis
          id={id}
          targetType={targetType}
          type={type}
          title={title}
          children={children}
        />
      </Suspense>
    );
  }

  return (
    <AnalysisContent<T> analysis={analysis} title={title} children={children} />
  );
}

function AnalysisContent<T extends AnalysisType>({
  analysis,
  title,
  children,
}: {
  analysis?: AnalysisDetailWithResults<T> | null;
  title: string;
  children: ({
    analysis,
  }: {
    analysis: AnalysisDetailWithResults<T>;
  }) => React.ReactNode;
}) {
  if (!analysis) {
    return null;
  }

  return (
    <section className="gap-3">
      <div className="relative mb-3 inline-flex items-center gap-2">
        <AIBadge />
        <h3 className="text-foreground text-lg leading-none font-semibold">
          {title}
        </h3>
      </div>
      <div className="bg-card border-border rounded-2xl border p-4">
        <ul className="flex list-none flex-col gap-2.5">
          {children({ analysis })}
        </ul>
      </div>
    </section>
  );
}

function AsyncAnalysis<T extends AnalysisType>({
  id,
  targetType,
  type,
  title,
  children,
}: {
  id: number;
  targetType: AnalysisTargetType;
  type: AnalysisType;
  title: string;
  children: ({
    analysis,
  }: {
    analysis: AnalysisDetailWithResults<T>;
  }) => React.ReactNode;
}) {
  const trpc = useTRPC();

  const { data: analysis } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({
      targetId: id,
      type: type,
      targetType: targetType,
    }),
  );

  return (
    <AnalysisContent<T>
      analysis={analysis as AnalysisDetailWithResults<T>}
      title={title}
      children={children}
    />
  );
}

function Skeleton() {
  return (
    <ul className="flex list-none flex-col gap-3">
      <li className="flex items-start gap-3 text-sm">
        <div className="h-5 w-5 animate-pulse rounded-full bg-gray-200" />
      </li>
    </ul>
  );
}
