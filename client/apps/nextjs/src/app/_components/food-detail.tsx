"use client";

import { useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useSuspenseQuery } from "@tanstack/react-query";
import { motion, useMotionValueEvent, useScroll } from "motion/react";

import { cn } from "@acme/ui";
import { Button } from "@acme/ui/button";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@acme/ui/carousel";
import {
  ArrowLeftIcon,
  CheckCircledIcon,
  ChevronDownIcon,
  InfoCircledIcon,
  Share2Icon,
  StarFilledIcon,
} from "@acme/ui/icons";
import { Separator } from "@acme/ui/separator";

import { useTRPC } from "~/trpc/react";

interface FoodDetailProps {
  code: string;
}

export function FoodDetail(props: FoodDetailProps) {
  const router = useRouter();
  const trpc = useTRPC();
  const { data: food } = useSuspenseQuery(
    trpc.food.getId.queryOptions({ id: props.code }),
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

  const benefits = useMemo(
    () => [
      "富含膳食纤维，有助于消化和维持肠道健康",
      "含有丰富的维生素 C，有助于增强免疫力",
      "低热量，适合作为健康零食，有助于控制体重",
      "含有抗氧化物质，有助于延缓衰老",
    ],
    [],
  );

  const suggestions = useMemo(
    () => [
      "建议每天食用 1-2 份，作为健康零食",
      "最好在餐前 30 分钟食用，有助于控制血糖",
      "建议连皮食用，以获得更多膳食纤维和营养",
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
          <div className="text-primary-foreground from-primary to-secondary absolute right-4 bottom-4 inline-flex items-center gap-1.5 rounded-xl bg-linear-to-tr px-3 py-1.5 text-sm font-medium shadow-md backdrop-blur-sm">
            <CheckCircledIcon className="h-4 w-4" />
            低风险
          </div>
        </div>

        <div className="space-y-6 px-4 py-6">
          <section className="space-y-2">
            <div className="text-muted-foreground flex items-baseline gap-2">
              <span className="text-foreground text-lg font-medium">
                {title}
              </span>
              <Separator orientation="vertical" className="h-4" />
              <span className="text-sm">{food.net_content}</span>
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
                <InfoCircledIcon className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  配料数据来自食品信息表，若存在缺失请在后台补充。我们会在未来版本中联动营养成分表做动态解析。
                </p>
              </div>
            </div>
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-lg font-semibold">健康益处</h3>
            </div>
            <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
              <ul className="flex list-none flex-col gap-3">
                {benefits.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <CheckCircledIcon className="text-primary mt-0.5 h-5 w-5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="gap-3">
            <div className="mb-3 flex items-center gap-2">
              <StarFilledIcon className="text-primary h-5 w-5" />
              <h3 className="text-lg font-semibold">食用建议</h3>
            </div>
            <div className="bg-card border-border rounded-2xl border p-4 shadow-sm">
              <ul className="flex list-none flex-col gap-2.5 text-sm">
                {suggestions.map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <CheckCircledIcon className="text-primary mt-0.5 h-5 w-5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
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
