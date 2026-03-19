"use client";

import { useRouter } from "next/navigation";
import { useSuspenseQuery } from "@tanstack/react-query";

import type { AnalysisDetailWithResults } from "@acme/api/type";
import { cn } from "@acme/ui";
import { Button } from "@acme/ui/button";

import { AIBadgeReason } from "~/app/_components/ai-badge";
import { AnalysisCard } from "~/app/_components/analysis-card";
import { Header } from "~/app/_components/header";
import { levelToText } from "~/tools/level";
import { useTRPC } from "~/trpc/react";

interface IngredientDetailProps {
  id: number;
}

export function IngredientDetail(props: IngredientDetailProps) {
  const router = useRouter();
  const trpc = useTRPC();
  const { data: ingredient } = useSuspenseQuery(
    trpc.ingredient.fetchDetailById.queryOptions({ id: props.id }),
  );
  console.log(ingredient);
  async function handleShare() {
    const shareText = ingredient.name;
    if ("share" in navigator && typeof navigator.share === "function") {
      await navigator.share({ title: ingredient.name, text: shareText });
      return;
    }
    await navigator.clipboard.writeText(shareText);
  }

  const analysis =
    ingredient.analysis as AnalysisDetailWithResults<"ingredient_summary">;

  return (
    <div className="bg-background text-foreground flex min-h-screen flex-col font-sans">
      <Header
        title={ingredient.name}
        onBack={() => router.back()}
        onShare={handleShare}
      />

      {/* Main Content */}
      <main className="animate-in fade-in flex-1 pt-16 duration-300">
        <div className="space-y-6 px-4 py-6">
          {/* Ingredient Overview with Risk */}
          <section>
            <div className="bg-card border-border rounded-2xl border p-5 shadow-sm">
              {/* 风险提示 */}
              <div className="mb-4 flex items-center gap-2">
                <div
                  className={cn(
                    "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-white shadow-sm",
                    analysis.level === "t4"
                      ? "bg-red-500"
                      : analysis.level === "t3"
                        ? "bg-orange-500"
                        : analysis.level === "t2"
                          ? "bg-yellow-500"
                          : analysis.level === "t1"
                            ? "bg-lime-500"
                            : analysis.level === "t0"
                              ? "bg-green-500"
                              : "bg-gray-500",
                  )}
                >
                  {/* icon */}
                  <svg
                    className="h-4 w-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>{levelToText(analysis.level)}</span>
                </div>
                <span className="text-muted-foreground text-xs">
                  {analysis.results.result}
                </span>
              </div>

              {/* AI 分析提示 */}
              <p className="text-foreground mb-4 text-sm leading-relaxed">
                <span className="font-semibold text-red-600 dark:text-red-400">
                  AI 分析：
                </span>
                {analysis.results.reason}
              </p>

              {/* 信息标签式展示 */}
              <div className="flex flex-wrap gap-2">
                <InfoChip label="名称" value={ingredient.name} />
                {ingredient.additive_code ? (
                  <InfoChip label="代码" value={ingredient.additive_code} />
                ) : null}
                {ingredient.function_type ? (
                  <InfoChip label="功能" value={ingredient.function_type} />
                ) : null}
                {ingredient.origin_type ? (
                  <InfoChip label="来源" value={ingredient.origin_type} />
                ) : null}
              </div>

              {/* 别名信息 */}
              <div className="mt-3 flex items-center gap-2">
                <span className="text-muted-foreground text-xs">别名：</span>
                <div className="flex flex-wrap gap-1.5">
                  {ingredient.alias.length > 0 ? (
                    ingredient.alias.map((a) => (
                      <span
                        key={a}
                        className="bg-muted rounded-md px-2 py-0.5 text-xs"
                      >
                        {a}
                      </span>
                    ))
                  ) : (
                    <span className="bg-muted rounded-md px-2 py-0.5 text-xs">
                      {/* 占位，便于对齐设计稿；有数据后可删除 */}
                      暂无
                    </span>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Description */}
          <section>
            <h3 className="mb-3 text-lg font-semibold">描述</h3>
            <div className="bg-card border-border rounded-2xl border p-4">
              <p className="text-muted-foreground text-sm leading-relaxed">
                {ingredient.description}
              </p>
            </div>
          </section>

          <AnalysisCard<"risk_summary">
            title="风险分析"
            id={ingredient.id}
            targetType="ingredient"
            type="risk_summary"
          >
            {({ analysis }) => (
              <ul className="flex list-none flex-col gap-3">
                {analysis.results.summaries.map((summary, index) => (
                  <RiskItem key={index} text={summary.text} />
                ))}
              </ul>
            )}
          </AnalysisCard>

          {/* Risk Management Info */}
          <section>
            <h3 className="mb-3 text-lg font-semibold">风险管理信息</h3>
            <div className="bg-card border-border rounded-2xl border p-4">
              <div className="flex flex-col gap-3">
                <InfoRow
                  label="WHO 致癌等级"
                  value={
                    ingredient.who_level ??
                    // TODO(数据): 若 who_level 为空，按设计稿可显示“未知/未收录”
                    "未知"
                  }
                  valueClassName="text-red-700 dark:text-red-400"
                />
                <Divider />

                <InfoRow
                  label="过敏信息"
                  value={
                    ingredient.allergen_info ??
                    // TODO(数据): 若 allergen_info 为空，按设计稿可显示“未知/未收录”
                    "未知"
                  }
                />
                <Divider />
                <InfoRow
                  label="使用限量"
                  value={
                    ingredient.limit_usage ??
                    // TODO(数据): 若 limit_usage 为空，按设计稿可显示“暂无”
                    "暂无"
                  }
                />
                <Divider />
                <InfoRow
                  label="法律适用区域"
                  value={
                    ingredient.legal_region ??
                    // TODO(数据): 若 legal_region 为空，按设计稿可显示“暂无”
                    "暂无"
                  }
                />
                <Divider />
                <InfoRow
                  label="执行标准"
                  value={
                    ingredient.standard_code ??
                    // TODO(数据): 若 standard_code 为空，按设计稿可显示“暂无”
                    "暂无"
                  }
                />
              </div>
            </div>
          </section>

          {/* Usage Recommendations */}
          <AnalysisCard<"usage_advice_summary">
            title="食用建议"
            id={ingredient.id}
            targetType="ingredient"
            type="usage_advice_summary"
          >
            {({ analysis }) => (
              <ul className="flex list-none flex-col gap-2.5">
                {analysis.results.summaries.map((summary, index) => (
                  <AdviceItem key={index} text={summary.text} />
                ))}
              </ul>
            )}
          </AnalysisCard>

          <AnalysisCard<"pregnancy_safety">
            title="母婴安全分析"
            id={ingredient.id}
            targetType="ingredient"
            type="pregnancy_safety"
          >
            {({ analysis }) => (
              <ul className="flex list-none flex-col gap-2.5">
                {analysis.results.summaries.map((summary, index) => (
                  <RiskItem key={index} text={summary.text} />
                ))}
              </ul>
            )}
          </AnalysisCard>

          <AnalysisCard<"recent_risk_summary">
            title="近期风险分析"
            id={ingredient.id}
            targetType="ingredient"
            type="recent_risk_summary"
          >
            {({ analysis }) => (
              <ul className="flex list-none flex-col gap-2.5">
                {analysis.results.summaries.map((summary, index) => (
                  <RiskItem key={index} text={summary.text} />
                ))}
              </ul>
            )}
          </AnalysisCard>

          <AIBadgeReason className="mt-20" />
        </div>
      </main>

      {/* Bottom Actions（设计稿：sticky bottom，双按钮） */}
      <div className="bg-card border-border sticky bottom-0 z-30 border-t p-4">
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="lg"
            className="bg-card border-border hover:bg-muted flex-1 rounded-xl px-4 py-3 text-sm font-medium transition-colors"
            // TODO(交互): 打开 AI 助手对话（需要路由/弹窗方案）
          >
            咨询AI助手
          </Button>
          <Button
            size="lg"
            className="gradient-primary text-primary-foreground flex-1 rounded-xl px-4 py-3 text-sm font-medium shadow-md transition-all duration-150 hover:shadow-lg"
            // TODO(交互): 跳转“相关食品列表”（需要后端支持按 ingredientId 查询 foods）
          >
            查看相关食品
          </Button>
        </div>
      </div>
    </div>
  );
}

function InfoChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted flex items-center gap-1.5 rounded-lg px-3 py-1.5">
      <span className="text-muted-foreground text-xs">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

function RiskItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-3">
      <svg
        className="mt-0.5 h-5 w-5 shrink-0 text-red-600 dark:text-red-400"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
      <span className="text-sm">{text}</span>
    </li>
  );
}

function AdviceItem({
  text,
  isWarning,
}: {
  text: string;
  isWarning?: boolean;
}) {
  return (
    <li className="flex items-start gap-2.5 text-sm">
      <svg
        className={
          isWarning
            ? "text-primary mt-0.5 h-5 w-5 shrink-0"
            : "text-primary mt-0.5 h-5 w-5 shrink-0"
        }
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        {isWarning ? (
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        ) : (
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        )}
      </svg>
      <span>{text}</span>
    </li>
  );
}

function Divider() {
  return <div className="border-border border-t" />;
}

function InfoRow({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-start justify-between">
      <span className="text-muted-foreground text-sm">{label}</span>
      <span className={"text-right font-medium " + (valueClassName ?? "")}>
        {value}
      </span>
    </div>
  );
}
