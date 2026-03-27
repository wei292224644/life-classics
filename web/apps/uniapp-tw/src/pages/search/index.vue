<script setup lang="ts">
import { ref, computed } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  fetchSearch,
  type SearchResultItem,
  type FilterType,
} from "@/services/search";
import { getRiskConfig, riskCls, type RiskLevel } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import DIcon from "@/components/ui/DIcon.vue";
import DButton from "@/components/ui/DButton.vue";
import Screen from "@/components/ui/Screen.vue";
import TopBar from "@/components/ui/TopBar.vue";
import Empty from "@/components/ui/Empty.vue";
import SkeletonGroup from "@/components/SkeletonGroup.vue";

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
        <text class="text-foreground p-4">搜索页（占位）</text>
      </view>
    </template>
  </Screen>
</template>
