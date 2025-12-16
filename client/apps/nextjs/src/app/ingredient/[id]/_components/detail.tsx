"use client";

import { Suspense, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useSuspenseQuery } from "@tanstack/react-query";
import { motion } from "motion/react";

import { cn } from "@acme/ui";
import { Button } from "@acme/ui/button";
import { ArrowLeftIcon, Share2Icon } from "@acme/ui/icons";

import { useTRPC } from "~/trpc/react";

interface IngredientDetailProps {
  id: number;
}

export function IngredientDetail(props: IngredientDetailProps) {
  return (
    <div>
      <h1>Ingredient Detail</h1>
    </div>
  );
}
