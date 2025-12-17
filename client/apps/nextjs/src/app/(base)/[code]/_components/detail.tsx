"use client";

import { useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useSuspenseQuery } from "@tanstack/react-query";
import { motion, useMotionValueEvent, useScroll } from "motion/react";

import type {
  AnalysisDetailWithResults,
  FoodNutritionDetail,
} from "@acme/api/type";
import { cn } from "@acme/ui";
import { Button } from "@acme/ui/button";
import { Carousel, CarouselContent, CarouselItem } from "@acme/ui/carousel";
import { ArrowLeftIcon, ChevronDownIcon, Share2Icon } from "@acme/ui/icons";

import { AIBadgeReason } from "~/app/_components/ai-badge";
import { AnalysisCard } from "~/app/_components/analysis-card";
import { CheckCircledIcon } from "~/app/_icons/CheckCircledIcon";
import { useTRPC } from "~/trpc/react";
import { FoodRiskLevelAnalysis } from "./food-risk-level";
import { Ingredients } from "./ingredients";

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

  const infoRows = [
    { label: "生产商", value: food.manufacturer },
    { label: "产地", value: food.origin_place },
    { label: "生产许可", value: food.production_license },
    { label: "产品分类", value: food.product_category },
    { label: "执行标准", value: food.product_standard_code },
    { label: "保质期", value: food.shelf_life },
    { label: "生产地址", value: food.production_address },
    { label: "净含量", value: food.net_content },
  ];

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

      <main className="animate-in fade-in flex-1 duration-300">
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
            <FoodRiskLevelAnalysis id={food.id} />
          </div>
        </div>

        <div className="space-y-6 px-4 py-6">
          <NutritionAnalysis nutritions={food.nutritions} />

          <Ingredients ingredients={food.ingredients} />

          <AnalysisCard<"health_summary">
            title="健康益处"
            id={food.id}
            targetType="food"
            type="health_summary"
            analysis={
              food.foodHealthSummaryAnalysis as AnalysisDetailWithResults<"health_summary">
            }
          >
            {({ analysis }) => (
              <ul className="flex list-none flex-col gap-2.5">
                {analysis.results.summaries.map((item, index: number) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-sm leading-relaxed"
                  >
                    <CheckCircledIcon className="text-primary h-5 w-5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            )}
          </AnalysisCard>

          <AnalysisCard<"usage_advice_summary">
            title="食用建议"
            id={food.id}
            targetType="food"
            type="usage_advice_summary"
            analysis={
              food.foodUsageAdviceSummaryAnalysis as AnalysisDetailWithResults<"usage_advice_summary">
            }
          >
            {({ analysis }) => (
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
            )}
          </AnalysisCard>

          <section className="space-y-2">
            <div className="text-muted-foreground flex items-baseline gap-2">
              <span className="text-foreground text-lg font-medium">
                详情信息
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

          <AIBadgeReason className="mt-20" />
        </div>
      </main>

      <div className="bg-card border-border sticky bottom-0 z-30 border-t p-4 shadow-md">
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="lg"
            className="flex-1 rounded-md font-medium"
          >
            添加到记录
          </Button>
          <Button
            size="lg"
            className="gradient-primary text-primary-foreground flex-1 rounded-md font-medium shadow-md"
          >
            咨询 AI 助手
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * 营养成分
 */
function NutritionAnalysis({
  nutritions,
}: {
  nutritions: FoodNutritionDetail[];
}) {
  const [showNutritionDetail, setShowNutritionDetail] = useState(false);

  // get top 4 nutritions
  const topNutritions = useMemo(() => {
    return nutritions.slice(0, 4);
  }, [nutritions]);

  const otherNutritions = useMemo(() => {
    return nutritions.slice(4);
  }, [nutritions]);

  return (
    <section className="gap-3">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold">营养成分</h3>
      </div>
      <div className="bg-gradient-1 border-primary/40 rounded-2xl border p-4 pb-0 shadow-sm">
        <div className="mb-4 grid grid-cols-2 gap-4">
          {topNutritions.map((item) => (
            <div key={item.id} className="flex flex-col gap-1">
              <div className="text-muted-foreground text-xs">{item.name}</div>
              <div className="text-2xl font-bold">{item.value}</div>
              <div className="text-muted-foreground -mt-2 text-xs">
                {item.value_unit}
              </div>
            </div>
          ))}
        </div>

        <div
          className={cn(
            "border-primary/20 grid max-h-[500px] grid-cols-1 gap-3 border-t pt-4 transition-all duration-200",
            showNutritionDetail
              ? "opacity-100"
              : "max-h-0 overflow-hidden pt-0 opacity-0",
          )}
        >
          {otherNutritions.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-muted-foreground">{item.name}</span>
              <span className="font-medium">
                {item.value}
                <span className="text-muted-foreground ml-2 text-xs">
                  /{item.value_unit}
                </span>
              </span>
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
  );
}
