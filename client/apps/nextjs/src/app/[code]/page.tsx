import { HydrateClient, prefetch, trpc } from "~/trpc/server";
import { FoodDetail } from "../_components/food-detail";

export default async function FoodDetailPage(props: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await props.params;
  prefetch(trpc.food.getId.queryOptions({ id: code }));
  return (
    <HydrateClient>
      <FoodDetail code={code} />
    </HydrateClient>
  );
}
