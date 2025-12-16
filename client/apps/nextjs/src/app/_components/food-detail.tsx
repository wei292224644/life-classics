"use client";

import { Suspense, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useSuspenseQuery } from "@tanstack/react-query";
import { motion, useMotionValueEvent, useScroll } from "motion/react";

import type { RiskLevel } from "@acme/api/type";
import { cn } from "@acme/ui";
import { Button } from "@acme/ui/button";
import { Carousel, CarouselContent, CarouselItem } from "@acme/ui/carousel";
import {
  ArrowLeftIcon,
  CheckCircledIcon,
  ChevronDownIcon,
  InfoCircledIcon,
  Share2Icon,
  StarFilledIcon,
} from "@acme/ui/icons";

import { useTRPC } from "~/trpc/react";

interface FoodDetailProps {
  code: string;
}

export function FoodDetail(props: FoodDetailProps) {
  const router = useRouter();
  const trpc = useTRPC();
  const { data: food } = useSuspenseQuery(
    trpc.food.fetchByBarcode.queryOptions({ barcode: props.code }),
  );

  const heroRef = useRef<HTMLDivElement | null>(null);

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  const [scrollHideImage, setScrollHideImage] = useState<boolean>(false);
  useMotionValueEvent(scrollYProgress, "change", (value) => {
    setScrollHideImage(value >= 0.5);
  });

  const [showNutritionDetail, setShowNutritionDetail] = useState(false);

  const nutritionSummary = useMemo(
    () => [
      { label: "卡路里", value: "52", unit: "kcal" },
      { label: "蛋白质", value: "0.3", unit: "g" },
      { label: "脂肪", value: "0.2", unit: "g" },
      { label: "碳水化合物", value: "14", unit: "g" },
    ],
    [],
  );

  const nutritionDetails = useMemo(
    () => [
      { label: "膳食纤维", value: "2.4g" },
      { label: "糖分", value: "10.4g" },
      { label: "维生素 C", value: "4.6mg" },
      { label: "钾", value: "107mg" },
      { label: "钙", value: "6mg" },
    ],
    [],
  );

  const infoRows = [
    { label: "生产商", value: food.manufacturer },
    { label: "产地", value: food.origin_place },
    { label: "生产许可", value: food.production_license },
    { label: "产品分类", value: food.product_category },
    { label: "执行标准", value: food.product_standard_code },
    { label: "保质期", value: food.shelf_life },
    { label: "生产地址", value: food.production_address },
    { label: "净含量", value: food.net_content },
  ].filter((item) => item.value);

  const title = food.name;
  const code = food.id;

  async function handleShare() {
    const shareText = `${title}（${code}）`;
    if ("share" in navigator && typeof navigator.share === "function") {
      await navigator.share({ title, text: shareText });
      return;
    }
    await navigator.clipboard.writeText(shareText);
  }

  return (
    <div className="bg-background text-foreground relative flex min-h-screen flex-col">
      <motion.header
        className={cn(
          "fixed inset-x-0 top-0 z-40 transition-colors",
          scrollHideImage
            ? "text-foreground bg-background shadow-sm"
            : "text-primary-foreground bg-transparent",
        )}
      >
        <div className="flex items-center gap-3 px-2 py-3">
          <Button
            size="icon"
            variant="ghost"
            aria-label="返回"
            className="hover:bg-primary/10 transition-colors"
            onClick={() => router.back()}
          >
            <ArrowLeftIcon />
          </Button>
          <motion.div className="text-base leading-tight font-semibold">
            {title}
          </motion.div>
          <div className="flex-1" />
          <Button
            size="icon"
            variant="ghost"
            aria-label="分享"
            className="hover:bg-primary/10 transition-colors"
            onClick={handleShare}
          >
            <Share2Icon />
          </Button>
        </div>
      </motion.header>

      <main className="animate-in fade-in flex-1 pb-28 duration-300">
        <div ref={heroRef} className="bg-muted relative w-full overflow-hidden">
          <Carousel>
            <CarouselContent>
              {food.image_url_list?.map((item) => (
                <CarouselItem key={item}>
                  <div className="relative h-64 w-full">
                    <Image
                      src={item}
                      alt={title}
                      fill
                      className="object-cover"
                    />
                  </div>
                </CarouselItem>
              ))}
            </CarouselContent>
          </Carousel>
          <div className="absolute right-4 bottom-4">
            <Suspense fallback={<div>AI分析中...</div>}>
              <FoodRiskLevelAnalysis id={food.id} />
            </Suspense>
          </div>
        </div>

        <div className="space-y-6 px-4 py-6">
          <section className="space-y-2">
            <div className="text-muted-foreground flex items-baseline gap-2">
              <span className="text-foreground text-lg font-medium">
                {title}
              </span>
            </div>
            {infoRows.length > 0 ? (
              <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
                <div className="grid grid-cols-1 gap-3">
                  {infoRows.map((item) => (
                    <div
                      key={item.label}
                      className="flex items-start justify-between gap-3 text-sm"
                    >
                      <span className="text-muted-foreground">
                        {item.label}
                      </span>
                      <span className="text-right font-medium">
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold">营养成分</h3>
            </div>
            <div className="from-primary/10 via-primary/5 to-secondary/20 ring-primary/15 rounded-2xl bg-linear-to-tr p-4 pb-0 shadow-sm ring-1">
              <div className="mb-4 grid grid-cols-2 gap-4">
                {nutritionSummary.map((item) => (
                  <div key={item.label} className="flex flex-col gap-1">
                    <div className="text-muted-foreground text-xs">
                      {item.label}
                    </div>
                    <div className="text-2xl font-bold">{item.value}</div>
                    <div className="text-muted-foreground text-xs">
                      {item.unit}
                    </div>
                  </div>
                ))}
              </div>

              <div
                className={cn(
                  "border-border grid max-h-[500px] grid-cols-1 gap-3 border-t pt-4 transition-all duration-200",
                  showNutritionDetail
                    ? "opacity-100"
                    : "max-h-0 overflow-hidden pt-0 opacity-0",
                )}
              >
                {nutritionDetails.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground">{item.label}</span>
                    <span className="font-medium">{item.value}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-center">
                <Button
                  variant="link"
                  className="text-muted-foreground hover:text-foreground m-0 flex size-8 items-center justify-center font-medium"
                  onClick={() => setShowNutritionDetail((prev) => !prev)}
                >
                  <ChevronDownIcon
                    className={cn(
                      "h-4 w-4 transition-transform duration-200",
                      showNutritionDetail ? "rotate-180" : "",
                    )}
                  />
                </Button>
              </div>
            </div>
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-lg font-semibold">配料信息</h3>
            </div>
            <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
              <div className="flex flex-wrap gap-2">
                {food.ingredients.length > 0 &&
                  food.ingredients.map((item) => (
                    <span
                      key={item.id + ""}
                      className="bg-muted text-muted-foreground rounded-full px-3 py-1 text-xs"
                    >
                      {item.name}
                    </span>
                  ))}
              </div>

              <div className="border-border text-muted-foreground mt-4 flex items-start gap-2 border-t pt-3 text-sm">
                <Suspense fallback={<div>AI分析中...</div>}>
                  <FoodIngredientAnalysis id={food.id} />
                </Suspense>
              </div>
            </div>
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-lg font-semibold">健康益处</h3>
            </div>
            <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
              <Suspense fallback={<div>AI分析中...</div>}>
                <FoodHealthBenefitAnalysis id={food.id} />
              </Suspense>
            </div>
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center gap-2">
              <StarFilledIcon className="text-primary h-5 w-5" />
              <h3 className="text-lg font-semibold">食用建议</h3>
            </div>
            <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
              <Suspense fallback={<div>AI分析中...</div>}>
                <FoodUsageSuggestionAnalysis id={food.id} />
              </Suspense>
            </div>
          </section>
        </div>
      </main>

      <div className="bg-card border-border sticky bottom-0 z-30 border-t p-4 shadow-md">
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1 rounded-xl px-4 py-3 text-sm font-medium"
          >
            添加到记录
          </Button>
          <Button className="from-primary to-secondary text-primary-foreground flex-1 rounded-xl bg-linear-to-tr px-4 py-3 text-sm font-medium shadow-md transition-all duration-150 hover:shadow-lg">
            咨询 AI 助手
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * 食用建议分析
 */
const FoodUsageSuggestionAnalysis = (props: { id: number }) => {
  const trpc = useTRPC();
  const { data } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({ id: props.id }),
  );

  return (
    <ul className="flex list-none flex-col gap-3">
      {/* {data.usage_suggestion_results.map((item: string) => (
        <li key={item} className="flex items-start gap-3 text-sm">
          <CheckCircledIcon className="text-primary h-5 w-5 shrink-0" />
          <span>{item}</span>
        </li>
      ))} */}
    </ul>
  );
};

/**
 * 健康益处分析
 */
const FoodHealthBenefitAnalysis = (props: { id: number }) => {
  const trpc = useTRPC();
  const { data } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({ id: props.id }),
  );

  return (
    <ul className="flex list-none flex-col gap-3">
      {/* {data.health_benefit_results.map((item: string) => (
        <li key={item} className="flex items-start gap-3 text-sm">
          <CheckCircledIcon className="text-primary h-5 w-5 shrink-0" />
          <span>{item}</span>
        </li>
      ))} */}
    </ul>
  );
};

/**
 * 配料分析
 */
const FoodIngredientAnalysis = (props: { id: number }) => {
  const trpc = useTRPC();
  const { data } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({ id: props.id }),
  );
  return (
    <ul className="flex list-none flex-col gap-3">
      {/* {data.ingredient_analysis_results.map((item: string) => (
        <li key={item} className="flex items-start gap-2 text-sm">
          <InfoCircledIcon className="mt-[2px] h-4 w-4 shrink-0" />
          <span>{item}</span>
        </li>
      ))} */}
    </ul>
  );
};

/**
 * 母婴分析
 */
const FoodPregnancyAnalysis = (props: { id: number }) => {
  const trpc = useTRPC();
  const { data } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({ id: props.id }),
  );
  return (
    <ul className="flex list-none flex-col gap-3">
      {data.pregnancy_analysis_results.map((item: string) => (
        <li key={item} className="flex items-start gap-3 text-sm">
          <CheckCircledIcon className="text-primary h-5 w-5 shrink-0" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
};

/**
 * 风险等级分析
 */
const FoodRiskLevelAnalysis = (props: { id: number }) => {
  const trpc = useTRPC();
  const { data } = useSuspenseQuery(
    trpc.analysis.advice.queryOptions({ id: props.id }),
  );
  return (
    <div className="from-chart-1 to-chart-2 text-primary-foreground flex items-center gap-1.5 rounded-md bg-linear-to-br px-3 py-1.5 text-sm font-medium shadow-md">
      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fill-rule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clip-rule="evenodd"
        />
      </svg>
      <span className="font-medium capitalize">
        {/* {getRishLevelLabel(data.risk_level)} */}
      </span>
    </div>
  );
};

const getRishLevelLabel = (riskLevel: RiskLevel) => {
  return riskLevel === "low"
    ? "低风险"
    : riskLevel === "medium"
      ? "中风险"
      : "高风险";
};
