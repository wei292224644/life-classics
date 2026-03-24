<template>
  <view
    class="search-page"
    :class="{ 'dark-mode': themeStore.isDark }"
  >
    <!-- ── Header ──────────────────────────── -->
    <view class="search-header" :style="headerStyle">
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
      <view class="header-content">
        <button class="header-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <text class="header-title">搜索食品或配料</text>
        <view class="header-spacer" />
      </view>
    </view>

    <!-- ── 搜索框 ─────────────────────────── -->
    <view class="search-input-wrap">
      <view class="search-input-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
        </svg>
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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
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
            <view class="result-type-tag" :style="typeTagStyle(item.type)">{{ item.type === 'product' ? '食品' : '配料' }}</view>
            <text class="result-name">{{ item.name }}</text>
            <text class="result-desc">{{ item.description }}</text>
          </view>
          <svg class="result-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18l6-6-6-6"/>
          </svg>
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
import { ref, computed,onMounted } from 'vue'
import { useThemeStore } from "../../store/theme"

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

// ── Header Style ────────────────────────────────────────
const headerStyle = computed(() => ({
  '--header-bg': 'var(--bg-card)',
  '--header-text': 'var(--text-primary)',
}))

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
      // Mock search: filter by keyword
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

// ── Type Tag Style ───────────────────────────────────────
function typeTagStyle(type: string) {
  if (type === 'product') {
    return { background: 'var(--chip-warn-bg)', color: 'var(--chip-warn-text)' }
  }
  return { background: 'var(--chip-risk-bg)', color: 'var(--chip-risk-text)' }
}

// ── Navigation ───────────────────────────────────────────
function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
// @import '@/styles/design-system.scss';

.search-page {
  min-height: 100vh;
  background: var(--bg-base);
  display: flex;
  flex-direction: column;
}

// ── Header ─────────────────────────────────────────────
.search-header {
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-color);
}

.header-content {
  display: flex;
  align-items: center;
  height: var(--space-22);
  padding: 0 var(--space-4);
  gap: var(--space-3);
}

.header-btn {
  width: var(--space-15);
  height: var(--space-15);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  padding: 0;
  border-radius: var(--radius-md);

  svg {
    width: 36rpx;
    height: 36rpx;
    color: var(--text-primary);
  }
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-right: var(--space-15); // balance the back button
}

.header-spacer {
  width: var(--space-15);
}

// ── Search Input ───────────────────────────────────────
.search-input-wrap {
  padding: var(--space-4) var(--space-6);
  background: var(--bg-base);
}

.search-input-box {
  display: flex;
  align-items: center;
  height: var(--space-20);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 0 var(--space-4);
  gap: var(--space-3);
}

.search-icon {
  width: var(--space-8);
  height: var(--space-8);
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 100%;
  font-size: var(--text-base);
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;

  &::placeholder {
    color: var(--text-muted);
  }
}

.clear-btn {
  width: var(--space-10);
  height: var(--space-10);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  padding: 0;

  svg {
    width: var(--space-8);
    height: var(--space-8);
    color: var(--text-muted);
  }
}

// ── Results ────────────────────────────────────────────
.results-scroll {
  flex: 1;
  height: calc(100vh - var(--space-22) - var(--space-20) - var(--space-20));
}

.results-content {
  padding: var(--space-4) var(--space-6);
}

.results-count {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-4);
}

.result-item {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--card-padding-md);
  margin-bottom: var(--space-3);
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.result-icon {
  width: var(--space-18);
  height: var(--space-18);
  border-radius: var(--radius-md);
  background: var(--bg-base);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-4xl);
  flex-shrink: 0;
}

.result-info {
  flex: 1;
  min-width: 0;
}

.result-type-tag {
  display: inline-block;
  font-size: var(--text-xs);
  padding: var(--space-px) var(--space-3);
  border-radius: var(--radius-full);
  margin-bottom: var(--space-1);
}

.result-name {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-bottom: var(--space-px);
}

.result-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.result-arrow {
  width: var(--space-8);
  height: var(--space-8);
  color: var(--text-muted);
  opacity: 0.4;
  flex-shrink: 0;
}

.empty-results {
  text-align: center;
  padding: var(--space-16) 0;
}

.empty-text {
  font-size: var(--text-base);
  color: var(--text-muted);
}

// ── History ─────────────────────────────────────────────
.history-section {
  padding: var(--space-6);
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.history-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.clear-history-btn {
  font-size: var(--text-sm);
  color: var(--text-muted);
  background: transparent;
  border: none;
  padding: var(--space-2) var(--space-3);
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.history-tag {
  height: var(--space-14);
  padding: 0 var(--space-6);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
}

.history-empty {
  text-align: center;
  padding: var(--space-10) 0;
}

.history-empty-text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
</style>
