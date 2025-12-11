"use client";

import { useSuspenseQuery } from "@tanstack/react-query";

import { useTRPC } from "~/trpc/react";

export function FoodList() {
  const trpc = useTRPC();
  const { data: foods } = useSuspenseQuery(trpc.food.all.queryOptions());

  if (foods.length <= 0) {
    return (
      <p className="text-muted-foreground text-sm">暂无食品数据，稍后再试。</p>
    );
  }

  return (
    <div className="grid w-full gap-4">
      {foods.map((food) => (
        <article
          key={food.id}
          className="border-border bg-card text-card-foreground rounded-lg border p-4 shadow-sm"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <h2 className="text-lg leading-tight font-semibold">
                {food.name}
              </h2>
              <p className="text-muted-foreground text-xs">ID: {food.id}</p>
            </div>
            {food.net_content ? (
              <span className="bg-muted text-muted-foreground rounded px-2 py-1 text-xs">
                {food.net_content}
              </span>
            ) : null}
          </div>

          <dl className="mt-3 space-y-2 text-sm">
            <InfoRow label="生产商" value={food.manufacturer} />
            <InfoRow label="产地" value={food.origin_place} />
            <InfoRow label="生产许可" value={food.production_license} />
            <InfoRow label="产品分类" value={food.product_category} />
            <InfoRow label="执行标准" value={food.product_standard_code} />
            <InfoRow label="保质期" value={food.shelf_life} />
            <InfoRow label="生产地址" value={food.production_address} />
            <InfoRow
              label="配料"
              value={
                food.ingredients?.length
                  ? food.ingredients.join(", ")
                  : undefined
              }
            />
          </dl>

          {(food.created_at ?? food.updated_at) && (
            <p className="text-muted-foreground mt-3 text-xs">
              创建: {formatDate(food.created_at)} · 更新:{" "}
              {formatDate(food.updated_at)}
            </p>
          )}
        </article>
      ))}
    </div>
  );
}

function InfoRow(props: { label: string; value?: string | null }) {
  const { label, value } = props;
  if (!value) return null;

  return (
    <div className="flex gap-2">
      <span className="text-foreground min-w-20 font-medium">{label}</span>
      <span className="text-muted-foreground">{value}</span>
    </div>
  );
}

const fmt = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "UTC",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
function formatDate(value?: string | Date | null) {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : fmt.format(d);
}
