<template>
  <view class="search-page">
    <!-- ── Header ──────────────────────────── -->
    <view class="search-header">
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
      <view class="header-content">
        <button class="header-btn" @click="goBack">
          <Icon name="arrowLeft" :size="24" />
        </button>
        <text class="header-title">搜索食品或配料</text>
        <view class="header-spacer" />
      </view>
    </view>

    <!-- ── 搜索框 ─────────────────────────── -->
    <view class="search-input-wrap">
      <view class="search-input-box">
        <Icon name="search" class="search-icon" :size="20" />
        <input
          v-model="keyword"
          class="search-input"
          type="text"
          placeholder="搜索食品或配料"
          confirm-type="search"
          @confirm="handleSearch"
          @input="handleInput"
        />
        <button v-if="keyword" class="clear-btn" @click="clearKeyword">
          <Icon name="x" :size="20" />
        </button>
      </view>
    </view>

    <!-- ── 搜索结果 ─────────────────────────── -->
    <scroll-view v-if="keyword" scroll-y class="results-scroll">
      <view class="results-content">
        <view class="results-count">搜索结果（共 {{ results.length }} 条）</view>
        <view
          v-for="item in results"
          :key="item.id"
          class="result-item"
          @click="handleResultClick(item)"
        >
          <view class="result-icon">{{ item.emoji }}</view>
          <view class="result-info">
            <view :class="['result-type-tag', item.type === 'product' ? 'type-tag--warn' : 'type-tag--risk']">
              {{ item.type === 'product' ? '食品' : '配料' }}
            </view>
            <text class="result-name">{{ item.name }}</text>
            <text class="result-desc">{{ item.description }}</text>
          </view>
          <Icon name="arrowRight" class="result-arrow" :size="20" />
        </view>
        <view v-if="results.length === 0" class="empty-results">
          <text class="empty-text">未找到相关结果</text>
        </view>
      </view>
    </scroll-view>

    <!-- ── 搜索历史 ─────────────────────────── -->
    <view v-else class="history-section">
      <view class="history-header">
        <text class="history-title">搜索历史</text>
        <button v-if="searchHistory.length" class="clear-history-btn" @click="clearHistory">清空全部</button>
      </view>
      <view class="history-tags">
        <view
          v-for="(tag, index) in searchHistory"
          :key="index"
          class="history-tag"
          @click="handleHistoryClick(tag)"
        >
          {{ tag }}
        </view>
      </view>
      <view v-if="!searchHistory.length" class="history-empty">
        <text class="history-empty-text">暂无搜索历史</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useThemeStore } from "../../store/theme"
import Icon from "@/components/ui/Icon.vue"

// ── Types ─────────────────────────────────────────────
interface SearchResult {
  type: 'product' | 'ingredient'
  id: string | number
  name: string
  description: string
  emoji?: string
}

// ── Theme Store ─────────────────────────────────────────
const themeStore = useThemeStore()

onMounted(() => {
  loadHistory()
})

// ── Search State ────────────────────────────────────────
const keyword = ref('')
const searchHistory = ref<string[]>([])
const results = ref<SearchResult[]>([])

// ── Mock Data ───────────────────────────────────────────
const mockProducts: SearchResult[] = [
  { type: 'product', id: 'p001', name: '康师傅方便面', description: '方便食品 · 高盐', emoji: '🍝' },
  { type: 'product', id: 'p002', name: '午餐肉罐头', description: '肉制加工品 · 防腐剂', emoji: '🥫' },
  { type: 'product', id: 'p003', name: '可口可乐', description: '碳酸饮料 · 高糖', emoji: '🥤' },
  { type: 'product', id: 'p004', name: '奥利奥饼干', description: '饼干类 · 食用色素', emoji: '🍪' },
]

const mockIngredients: SearchResult[] = [
  { type: 'ingredient', id: 'i001', name: '苯甲酸钠', description: '食品添加剂 · 防腐剂' },
  { type: 'ingredient', id: 'i002', name: '香兰素', description: '食品添加剂 · 香料' },
  { type: 'ingredient', id: 'i003', name: '谷氨酸钠', description: '食品添加剂 · 增味剂' },
  { type: 'ingredient', id: 'i004', name: '阿斯巴甜', description: '食品添加剂 · 甜味剂' },
]

// ── Storage ─────────────────────────────────────────────
const HISTORY_KEY = 'search_history'
const MAX_HISTORY = 10

function loadHistory() {
  try {
    const history = uni.getStorageSync(HISTORY_KEY)
    if (history) searchHistory.value = JSON.parse(history)
  } catch {}
}

function saveHistory() {
  try {
    uni.setStorageSync(HISTORY_KEY, JSON.stringify(searchHistory.value))
  } catch {}
}

function addToHistory(kw: string) {
  const trimmed = kw.trim()
  if (!trimmed) return
  searchHistory.value = [trimmed, ...searchHistory.value.filter(h => h !== trimmed)].slice(0, MAX_HISTORY)
  saveHistory()
}

function clearHistory() {
  searchHistory.value = []
  saveHistory()
}

// ── Search Logic ────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null

function handleInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (keyword.value.trim()) {
      const kw = keyword.value.toLowerCase()
      const filteredProducts = mockProducts.filter(p => p.name.toLowerCase().includes(kw))
      const filteredIngredients = mockIngredients.filter(i => i.name.toLowerCase().includes(kw))
      results.value = [...filteredProducts, ...filteredIngredients]
    } else {
      results.value = []
    }
  }, 300)
}

function handleSearch() {
  if (!keyword.value.trim()) return
  addToHistory(keyword.value)
  handleInput()
}

function handleHistoryClick(tag: string) {
  keyword.value = tag
  handleSearch()
}

function clearKeyword() {
  keyword.value = ''
  results.value = []
}

// ── Result Click ────────────────────────────────────────
function handleResultClick(item: SearchResult) {
  addToHistory(keyword.value)
  if (item.type === 'product') {
    uni.navigateTo({ url: `/pages/product/index?barcode=${item.id}` })
  } else {
    uni.navigateTo({ url: `/pages/ingredient-detail/index?ingredientId=${item.id}` })
  }
}

// ── Navigation ───────────────────────────────────────────
function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
// ── Page ────────────────────────────────────────────────
.search-page {
  @apply min-h-screen bg-background flex flex-col;
}

// ── Header ─────────────────────────────────────────────
.search-header {
  @apply bg-background border-b border-border;
}

.header-content {
  @apply flex items-center px-4;
  height: 88rpx;
  gap: 12rpx;
}

.header-btn {
  @apply w-12 h-12 flex items-center justify-center bg-transparent border-none p-0 rounded-lg;

  svg {
    @apply w-9 h-9;
    color: var(--color-foreground);
  }
}

.header-title {
  @apply flex-1 text-center text-base font-semibold text-foreground tracking-tight;
  margin-right: 48rpx; // balance the back button
}

.header-spacer {
  width: 48rpx;
}

// ── Search Input ───────────────────────────────────────
.search-input-wrap {
  @apply p-4 px-6 bg-background;
}

.search-input-box {
  @apply flex items-center bg-card border border-border rounded-2xl px-4;
  height: 80rpx;
  gap: 12rpx;
}

.search-icon {
  @apply w-8 h-8 text-muted-foreground flex-shrink-0;
}

.search-input {
  @apply flex-1 h-full text-base text-foreground bg-transparent border-none outline-none;
  &::placeholder {
    color: var(--color-muted);
  }
}

.clear-btn {
  @apply w-10 h-10 flex items-center justify-center bg-transparent border-none p-0;

  svg {
    @apply w-8 h-8 text-muted-foreground;
  }
}

// ── Results ────────────────────────────────────────────
.results-scroll {
  @apply flex-1;
  height: calc(100vh - 88rpx - 80rpx - 80rpx);
}

.results-content {
  @apply p-4 px-6;
}

.results-count {
  @apply text-sm text-muted-foreground mb-4;
}

.result-item {
  @apply bg-card border border-border rounded-xl px-4 py-3.5 flex items-center gap-3 mb-3;
  box-shadow: var(--shadow-sm);
}

.result-icon {
  @apply w-[72rpx] h-[72rpx] rounded-xl bg-background border border-border flex items-center justify-center text-2xl flex-shrink-0;
}

.result-info {
  @apply flex-1 min-w-0;
}

.result-type-tag {
  @apply inline-block text-xs px-2 py-0.5 rounded-full mb-0.5;
}

.type-tag--warn {
  background: color-mix(in oklch, var(--color-risk-t3) 12%, transparent);
  color: var(--color-risk-t3);
}

.type-tag--risk {
  background: color-mix(in oklch, var(--color-risk-t4) 12%, transparent);
  color: var(--color-risk-t4);
}

.result-name {
  @apply block text-base font-semibold text-foreground tracking-tight mb-0.5 truncate;
}

.result-desc {
  @apply text-sm text-muted-foreground;
}

.result-arrow {
  @apply w-8 h-8 text-muted-foreground opacity-40 flex-shrink-0;
}

.empty-results {
  @apply text-center pt-16;
}

.empty-text {
  @apply text-base text-muted-foreground;
}

// ── History ─────────────────────────────────────────────
.history-section {
  @apply p-6;
}

.history-header {
  @apply flex items-center justify-between mb-4;
}

.history-title {
  @apply text-base font-semibold text-foreground;
}

.clear-history-btn {
  @apply text-sm text-muted-foreground bg-transparent border-none p-2 pl-3;
}

.history-tags {
  @apply flex flex-wrap gap-3;
}

.history-tag {
  @apply h-14 px-6 bg-card border border-border rounded-full text-sm text-secondary flex items-center;
}

.history-empty {
  @apply text-center pt-10;
}

.history-empty-text {
  @apply text-sm text-muted-foreground;
}
</style>
