<script setup lang="ts">
import { ref, computed } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  fetchSearch,
  type SearchResultItem,
  type FilterType,
} from "@/services/search";
import DIcon from "@/components/ui/DIcon.vue";
import DButton from "@/components/ui/DButton.vue";
import Screen from "@/components/ui/Screen.vue";
import TopBar from "@/components/ui/TopBar.vue";
import Empty from "@/components/ui/Empty.vue";
import SkeletonGroup from "@/components/SkeletonGroup.vue";
import ProductCard from "@/components/business/product/ProductCard.vue";

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
const isLoading = ref(false);
const searchResults = ref<SearchResultItem[]>([]);
const searchHistory = ref<string[]>([]);
const recentViewed = ref<SearchResultItem[]>([]);

// ── Computed ─────────────────────────────────────────────
const filters = computed(() => [
  {
    key: "all" as FilterType,
    label: "全部",
    count: searchResults.value.length,
  },
  {
    key: "product" as FilterType,
    label: "食品",
    count: searchResults.value.filter((r) => r.type === "product").length,
  },
  {
    key: "ingredient" as FilterType,
    label: "配料",
    count: searchResults.value.filter((r) => r.type === "ingredient").length,
  },
]);

const filteredResults = computed(() => {
  if (activeFilter.value === "all") return searchResults.value;
  return searchResults.value.filter((r) => r.type === activeFilter.value);
});

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

// ── 搜索逻辑 ──────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null;

function handleInput() {
  if (searchTimer) clearTimeout(searchTimer);
  if (!keyword.value.trim()) {
    searchResults.value = [];
    return;
  }
  searchTimer = setTimeout(doSearch, 300);
}

function handleConfirm() {
  if (searchTimer) clearTimeout(searchTimer);
  if (!keyword.value.trim()) return;
  addToHistory(keyword.value);
  doSearch();
}

async function doSearch() {
  if (!keyword.value.trim()) return;
  isLoading.value = true;
  try {
    // 始终拉取全量结果，筛选由 filteredResults computed 在客户端完成
    searchResults.value = await fetchSearch(keyword.value, "all");
  } catch {
    // 静默失败，结果列表保持空
  } finally {
    isLoading.value = false;
  }
}

function clearKeyword() {
  keyword.value = "";
  searchResults.value = [];
  activeFilter.value = "all";
}

function handleHistoryClick(kw: string) {
  keyword.value = kw;
  addToHistory(kw);
  if (searchTimer) clearTimeout(searchTimer);
  doSearch();
}

// ── 导航 ─────────────────────────────────────────────────
function navigateToItem(item: SearchResultItem) {
  addToRecent(item);
  if (item.type === "product" && item.barcode) {
    uni.navigateTo({
      url: `/pages/product/index?barcode=${encodeURIComponent(item.barcode)}`,
    });
  } else if (item.type === "ingredient") {
    uni.navigateTo({
      url: `/pages/ingredient-detail/index?ingredientId=${item.id}`,
    });
  }
}

// ── 生命周期 ──────────────────────────────────────────────
onShow(() => {
  loadStorage();
});
</script>

<template>
  <Screen>
    <template #content>
      <view class="flex flex-col min-h-full bg-background">

        <!-- ── 吸顶头部 ───────────────────────────── -->
        <view class="sticky top-0 z-10 bg-background border-b border-border">
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
              v-for="f in filters"
              :key="f.key"
              :class="
                cn(
                  'h-7 px-3 rounded-full text-xs font-semibold flex items-center shrink-0',
                  activeFilter === f.key
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card border border-border text-foreground',
                )
              "
              @click="activeFilter = f.key"
            >
              {{ f.label
              }}{{ keyword && f.count !== undefined ? ` ${f.count}` : "" }}
            </view>
          </view>
        </view>

        <!-- ── 空状态（无搜索词）────────────────────── -->
        <view v-if="!keyword" class="flex flex-col pb-10">

          <!-- 搜索历史 -->
          <view v-if="searchHistory.length" class="mt-4">
            <view class="flex items-center justify-between px-4 mb-2">
              <text class="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
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
          <view class="mt-6 bg-muted/40 py-4">
            <view class="px-4 mb-3">
              <text class="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
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
          <template v-if="recentViewed.length">
            <view class="mt-6 px-4 mb-2">
              <text class="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
                最近查看
              </text>
            </view>
            <view class="flex flex-col gap-2 px-4">
              <view
                v-for="item in recentViewed"
                :key="`${item.type}-${item.id}`"
                class="flex items-center gap-2.5 p-3 bg-card border border-border rounded-2xl"
                @click="navigateToItem(item)"
              >
                <ProductCard :data="item" />
              </view>
            </view>
          </template>

        </view>

        <!-- ── 搜索结果 ─────────────────────────────── -->
        <view v-else class="flex flex-col pb-10">
          <!-- 加载中 -->
          <SkeletonGroup v-if="isLoading" :with-header="false" />

          <!-- 结果列表 -->
          <template v-else>
            <text class="text-xs text-muted-foreground px-4 pt-3 pb-2 block">
              找到 {{ filteredResults.length }} 条结果
            </text>
            <view class="flex flex-col gap-2 px-4">
              <view
                v-for="item in filteredResults"
                :key="`${item.type}-${item.id}`"
                class="flex items-center gap-2.5 p-3 bg-card border border-border rounded-2xl"
                @click="navigateToItem(item)"
              >
                <ProductCard :data="item" />
              </view>
            </view>

            <!-- 无结果 -->
            <Empty
              v-if="filteredResults.length === 0"
              icon="search"
              message="未找到相关结果"
              dclass="py-20"
            />
          </template>
        </view>

      </view>
    </template>
  </Screen>
</template>
