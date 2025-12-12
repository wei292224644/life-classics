import { HydrateClient, prefetch, trpc } from "~/trpc/server";
import { FoodList } from "./_components/food-list";

export default function HomePage() {
  // Ensure trpc.food.getId exists and is properly typed before using
  prefetch(trpc.food.all.queryOptions());
  return (
    <HydrateClient>
      <main className="container h-screen py-16">
        <div className="flex flex-col gap-6">
          <header className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold">食品列表</h1>
            <p className="text-muted-foreground text-sm">
              以下为 food.all 查询返回的最新数据
            </p>
          </header>
          <FoodList />
        </div>
      </main>
    </HydrateClient>
  );
}
