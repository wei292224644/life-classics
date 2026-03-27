<script setup lang="ts">
import { ref, watch } from "vue";
import { onShow, onHide } from "@dcloudio/uni-app";
import {
  fetchSearch,
  type SearchResultItem,
  type FilterType,
} from "@/services/search";
import { useInfiniteList } from "@/composables/useInfiniteList";
import DIcon from "@/components/ui/DIcon.vue";
import DButton from "@/components/ui/DButton.vue";
import TopBar from "@/components/ui/TopBar.vue";
import Empty from "@/components/ui/Empty.vue";
import SkeletonGroup from "@/components/SkeletonGroup.vue";
import ProductCard from "@/components/business/product/ProductCard.vue";
import InfiniteScrollView from "@/components/ui/InfiniteScrollView.vue";
import { cn } from "@/utils/cn";

// ── 常量 ─────────────────────────────────────────────────
const HISTORY_KEY = "search_history";
const RECENT_KEY = "search_recent";
const MAX_HISTORY = 10;
const MAX_RECENT = 10;
const HOT_KEYWORDS = [
  "阿斯巴甜",
  "反式脂肪酸",
  "防腐剂",
  "亚硝酸盐",
  "色素",
  "糖精钠",
];

// ── 状态 ─────────────────────────────────────────────────
const keyword = ref("");
const activeFilter = ref<FilterType>("all");
const searchHistory = ref<string[]>([]);
const recentViewed = ref<SearchResultItem[]>([]);

// ── 无限滚动 ──────────────────────────────────────────────
const { items, isLoading, isRefreshing, hasMore, refresh, loadMore, reset } =
  useInfiniteList<SearchResultItem>({
    fetcher: (offset, limit) =>
      fetchSearch(keyword.value, activeFilter.value, offset, limit).then(
        (r) => ({ items: r.items, has_more: r.has_more }),
      ),
    pageSize: 20,
  });

// keyword 或 filter 变化时重置并重新加载
async function triggerSearch() {
  if (!keyword.value.trim()) {
    reset();
    return;
  }
  reset();
  await refresh();
}

watch(activeFilter, () => {
  if (keyword.value.trim()) triggerSearch();
});

// ── 搜索框逻辑 ────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null;

function handleInput() {
  if (searchTimer) clearTimeout(searchTimer);
  if (!keyword.value.trim()) {
    reset();
    return;
  }
  searchTimer = setTimeout(triggerSearch, 300);
}

function handleConfirm() {
  if (searchTimer) clearTimeout(searchTimer);
  if (!keyword.value.trim()) return;
  addToHistory(keyword.value);
  triggerSearch();
}

function clearKeyword() {
  keyword.value = "";
  activeFilter.value = "all";
  reset();
}

function handleHistoryClick(kw: string) {
  keyword.value = kw;
  addToHistory(kw);
  if (searchTimer) clearTimeout(searchTimer);
  triggerSearch();
}

// ── 本地存储 ──────────────────────────────────────────────
function loadStorage() {
  try {
    const h = uni.getStorageSync(HISTORY_KEY);
    if (h) searchHistory.value = JSON.parse(h);
    const r = uni.getStorageSync(RECENT_KEY);
    if (r) recentViewed.value = JSON.parse(r);
  } catch {}
}

function saveHistory() {
  try {
    uni.setStorageSync(HISTORY_KEY, JSON.stringify(searchHistory.value));
  } catch {}
}

function addToHistory(kw: string) {
  const trimmed = kw.trim();
  if (!trimmed) return;
  searchHistory.value = [
    trimmed,
    ...searchHistory.value.filter((h) => h !== trimmed),
  ].slice(0, MAX_HISTORY);
  saveHistory();
}

function clearHistory() {
  searchHistory.value = [];
  saveHistory();
}

function addToRecent(item: SearchResultItem) {
  recentViewed.value = [
    item,
    ...recentViewed.value.filter(
      (r) => !(r.type === item.type && r.id === item.id),
    ),
  ].slice(0, MAX_RECENT);
  try {
    uni.setStorageSync(RECENT_KEY, JSON.stringify(recentViewed.value));
  } catch {}
}

// ── 生命周期 ──────────────────────────────────────────────
onShow(() => {
  loadStorage();
});

onHide(() => {
  clearKeyword();
});
</script>

<template>
  <view class="bg-root border-b border-border shadow-sm">
    <TopBar />
    <!-- 页面标题 -->
    <view class="px-4 pt-3 pb-2">
      <text class="text-2xl font-extrabold tracking-tight text-foreground">
        搜索
      </text>
    </view>
    <!-- 搜索框 -->
    <view class="px-4 pb-2">
      <view
        class="flex items-center gap-2.5 bg-card border border-border rounded-2xl px-3 h-11"
      >
        <DIcon name="search" dclass="text-muted-foreground shrink-0" />
        <input
          v-model="keyword"
          class="flex-1 h-full text-sm text-foreground bg-transparent border-none outline-none"
          placeholder="搜索食品或配料名称…"
          placeholder-class="text-muted-foreground"
          confirm-type="search"
          @input="handleInput"
          @confirm="handleConfirm"
        />
        <DButton
          v-if="keyword"
          size="icon"
          variant="ghost"
          dclass="shrink-0 size-7"
          @click="clearKeyword"
        >
          <DIcon name="x" />
        </DButton>
      </view>
    </view>
    <!-- 筛选 chip -->
    <view class="flex gap-2 px-4 pb-3 overflow-x-auto">
      <view
        v-for="f in ['all', 'product', 'ingredient'] as FilterType[]"
        :key="f"
        :class="
          cn(
            'h-7 px-3 rounded-full text-xs font-semibold flex items-center shrink-0',
            activeFilter === f
              ? 'bg-primary text-primary-foreground'
              : 'bg-card border border-border text-foreground',
          )
        "
        @click="activeFilter = f"
      >
        {{ f === "all" ? "全部" : f === "product" ? "食品" : "配料" }}
      </view>
    </view>
  </view>

  <!-- ── 无搜索词：历史 / 热门 / 最近查看 ────────────────── -->
  <scroll-view
    v-if="!keyword"
    scroll-y
    class="flex-1 overflow-hidden bg-background"
  >
    <view class="flex flex-col">
      <!-- 搜索历史 -->
      <view v-if="searchHistory.length" class="mt-4">
        <view class="flex items-center justify-between px-4 mb-2">
          <text
            class="text-xs font-semibold text-muted-foreground uppercase tracking-widest"
          >
            搜索历史
          </text>
          <DButton
            variant="ghost"
            size="sm"
            dclass="text-muted-foreground h-6 text-xs"
            @click="clearHistory"
          >
            清空
          </DButton>
        </view>
        <view class="flex flex-wrap gap-2 px-4">
          <view
            v-for="(h, i) in searchHistory"
            :key="i"
            class="h-8 px-3.5 bg-card border border-border rounded-full text-sm text-foreground flex items-center"
            @click="handleHistoryClick(h)"
          >
            {{ h }}
          </view>
        </view>
      </view>

      <!-- 热门搜索 -->
      <view class="bg-muted/40 mt-4">
        <view class="px-4 mb-3">
          <text
            class="text-xs font-semibold text-muted-foreground uppercase tracking-widest"
          >
            热门搜索
          </text>
        </view>
        <view class="flex flex-wrap gap-2 px-4">
          <view
            v-for="(kw, i) in HOT_KEYWORDS"
            :key="i"
            class="h-8 px-3.5 rounded-full text-sm font-medium flex items-center bg-background border border-border text-foreground"
            @click="handleHistoryClick(kw)"
          >
            {{ kw }}
          </view>
        </view>
      </view>

      <!-- 最近查看 -->
      <view v-if="recentViewed.length" class="mt-4 mb-4">
        <view class="px-4 mb-2">
          <text
            class="text-xs font-semibold text-muted-foreground uppercase tracking-widest"
          >
            最近查看
          </text>
        </view>
        <view class="flex flex-col gap-2 px-4">
          <template
            v-for="item in recentViewed"
            :key="`${item.type}-${item.id}`"
          >
            <ProductCard :data="item" @click="addToRecent(item)" />
          </template>
        </view>
      </view>
    </view>
  </scroll-view>

  <!-- ── 搜索结果：InfiniteScrollView ────────────────────── -->
  <InfiniteScrollView
    v-else
    class="flex-1 overflow-hidden bg-background"
    :is-refreshing="isRefreshing"
    :is-loading="isLoading"
    :has-more="hasMore"
    @refresh="refresh"
    @load-more="loadMore"
  >
    <!-- 首次加载骨架屏 -->
    <SkeletonGroup
      v-if="isLoading && items.length === 0"
      :with-header="false"
    />

    <template v-else>
      <text class="text-xs text-muted-foreground px-4 pt-3 pb-2 block">
        找到 {{ items.length }} 条结果{{ hasMore ? "…" : "" }}
      </text>
      <view class="flex flex-col gap-2 px-4">
        <template v-for="item in items" :key="`${item.type}-${item.id}`">
          <ProductCard :data="item" @click="addToRecent(item)" />
        </template>
      </view>

      <!-- 无结果 -->
      <Empty
        v-if="items.length === 0"
        icon="search"
        message="未找到相关结果"
        dclass="py-20"
      />
    </template>
  </InfiniteScrollView>
</template>
