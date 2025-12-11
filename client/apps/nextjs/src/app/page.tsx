import { HydrateClient, prefetch, trpc } from "~/trpc/server";

export default function HomePage() {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
  prefetch(trpc.food.all.queryOptions());
  return (
    <HydrateClient>
      <main className="container h-screen py-16">
        <div className="flex flex-col items-center justify-center gap-4"></div>
      </main>
    </HydrateClient>
  );
}
