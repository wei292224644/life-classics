"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useTRPC } from "~/trpc/react";
import { RiskBadge } from "./risk-badge";

interface FoodRiskLevelAnalysisProps {
  id: number;
}

export function FoodRiskLevelAnalysis({ id }: FoodRiskLevelAnalysisProps) {
  const trpc = useTRPC();

  // 获取食品的风险分析
  const { data: riskAnalysis } = useQuery(
    trpc.analysis.advice.queryOptions({
      targetId: id,
      targetType: "food",
      type: "food_risk_summary",
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

  if (!riskAnalysis) {
    return null;
  }

  const isHighRisk = ["t2", "t3", "t4"].includes(riskAnalysis.level);

  return (
    <div className="from-primary/10 via-primary/5 to-secondary/20 ring-primary/15 rounded-xl bg-linear-to-tr px-3 py-2 shadow-sm ring-1 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <RiskBadge level={riskAnalysis.level} />
        {isHighRisk && riskReason && (
          <span className="text-primary-foreground text-xs font-medium line-clamp-1">
            {riskReason}
          </span>
        )}
      </div>
    </div>
  );
}
