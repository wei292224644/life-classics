import { cn } from "@acme/ui";

import type { AnalysisLevel } from "@acme/api/type";

interface RiskBadgeProps {
  level: AnalysisLevel;
  className?: string;
  showText?: boolean;
}

const levelConfig: Record<
  AnalysisLevel,
  { label: string; className: string; bgClassName: string }
> = {
  t0: {
    label: "低风险",
    className: "text-green-700 dark:text-green-400",
    bgClassName: "bg-green-100 dark:bg-green-900/30",
  },
  t1: {
    label: "中风险",
    className: "text-yellow-700 dark:text-yellow-400",
    bgClassName: "bg-yellow-100 dark:bg-yellow-900/30",
  },
  t2: {
    label: "高风险",
    className: "text-orange-700 dark:text-orange-400",
    bgClassName: "bg-orange-100 dark:bg-orange-900/30",
  },
  t3: {
    label: "中高风险",
    className: "text-red-700 dark:text-red-400",
    bgClassName: "bg-red-100 dark:bg-red-900/30",
  },
  t4: {
    label: "高风险",
    className: "text-red-800 dark:text-red-300",
    bgClassName: "bg-red-200 dark:bg-red-900/50",
  },
  unknown: {
    label: "未知",
    className: "text-gray-700 dark:text-gray-400",
    bgClassName: "bg-gray-100 dark:bg-gray-900/30",
  },
};

export function RiskBadge({
  level,
  className,
  showText = true,
}: RiskBadgeProps) {
  const config = levelConfig[level];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium",
        config.className,
        config.bgClassName,
        className,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          level === "t0"
            ? "bg-green-600 dark:bg-green-400"
            : level === "t1"
              ? "bg-yellow-600 dark:bg-yellow-400"
              : level === "t2" || level === "t3"
                ? "bg-orange-600 dark:bg-orange-400"
                : level === "t4"
                  ? "bg-red-600 dark:bg-red-400"
                  : "bg-gray-600 dark:bg-gray-400",
        )}
      />
      {showText && config.label}
    </span>
  );
}
