import { HydrateClient, prefetch, trpc } from "~/trpc/server";
import { IngredientDetail } from "./_components/detail";

export default async function IngredientDetailPage(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  const ingredientId = Number.parseInt(id, 10);

  if (Number.isNaN(ingredientId)) {
    return <div>无效的配料ID</div>;
  }

  prefetch(trpc.ingredient.fetchDetailById.queryOptions({ id: ingredientId }));

  return (
    <HydrateClient>
      <IngredientDetail id={ingredientId} />
    </HydrateClient>
  );
}
