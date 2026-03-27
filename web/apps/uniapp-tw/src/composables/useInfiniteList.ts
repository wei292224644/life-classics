import { ref } from "vue";

interface InfiniteListOptions<T> {
  fetcher: (offset: number, limit: number) => Promise<{ items: T[]; has_more: boolean }>;
  pageSize?: number;
}

export function useInfiniteList<T>(options: InfiniteListOptions<T>) {
  const { fetcher, pageSize = 20 } = options;

  const items = ref<T[]>([]);
  const isLoading = ref(false);
  const isRefreshing = ref(false);
  const hasMore = ref(true);

  let _busy = false;

  async function refresh() {
    if (_busy) return;
    _busy = true;
    isRefreshing.value = true;
    try {
      const res = await fetcher(0, pageSize);
      items.value = res.items;
      hasMore.value = res.has_more;
    } finally {
      isRefreshing.value = false;
      _busy = false;
    }
  }

  async function loadMore() {
    if (_busy || !hasMore.value) return;
    _busy = true;
    isLoading.value = true;
    try {
      const res = await fetcher(items.value.length, pageSize);
      items.value = [...items.value, ...res.items];
      hasMore.value = res.has_more;
    } finally {
      isLoading.value = false;
      _busy = false;
    }
  }

  function reset() {
    items.value = [];
    hasMore.value = true;
    isLoading.value = false;
    isRefreshing.value = false;
    _busy = false;
  }

  return { items, isLoading, isRefreshing, hasMore, refresh, loadMore, reset };
}
