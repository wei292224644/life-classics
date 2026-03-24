<template>
  <view class="index-page">
    <!-- ── 状态栏占位 ─────────────────────────── -->
    <view :style="{ height: themeStore.statusBarHeight + 'px' }" />

    <!-- ── Logo 区域 ─────────────────────────── -->
    <view class="hero">
      <view class="logo-row">
        <text class="logo-emoji">🍎</text>
        <text class="logo-title">食品安全助手</text>
      </view>
      <text class="logo-sub">扫码查配料 · 了解你吃的每一口</text>
    </view>

    <!-- ── 扫一扫 CTA ─────────────────────────── -->
    <view class="scan-cta-wrap">
      <view class="scan-cta" @click="handleScan" role="button" tabindex="0" aria-label="扫一扫">
        <view class="scan-cta-ring" aria-hidden="true"></view>
        <svg class="scan-cta-icon" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
        </svg>
        <text class="scan-cta-text">扫一扫</text>
      </view>
    </view>

    <!-- ── 最近扫描 ─────────────────────────── -->
    <view class="section-divider">
      <view class="divider-line"></view>
      <view class="section-label">
        <text class="section-label-text">最近扫描</text>
        <view class="scan-count">{{ recentScans.length }}</view>
      </view>
      <view class="divider-line"></view>
    </view>

    <view class="scan-list">
      <view
        v-for="item in recentScans"
        :key="item.barcode"
        class="scan-item"
        role="button"
        tabindex="0"
        :aria-label="`${item.name}，${formatTime(item.time)}`"
        @click="handleRecentClick(item)"
      >
        <view class="scan-icon">{{ item.emoji }}</view>
        <view class="scan-info">
          <text class="scan-name">{{ item.name }}</text>
          <text class="scan-time">{{ formatTime(item.time) }}</text>
        </view>
        <svg class="scan-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M9 18l6-6-6-6"/>
        </svg>
      </view>

      <view v-if="!recentScans.length" class="scan-empty">
        <text class="scan-empty-text">暂无扫描记录</text>
      </view>
    </view>

  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useThemeStore } from '../../store/theme'
import { scanBarcode, ScanCancelledError } from '../../utils/scanner'

// ── Types ─────────────────────────────────────────────
interface RecentScan {
  barcode: string
  name: string
  emoji: string
  time: number
}

// ── Theme Store ──────────────────────────────────────────
const themeStore = useThemeStore()

onMounted(() => {
  loadRecentScans()
})

// ── Recent Scans ───────────────────────────────────────
const RECENT_KEY = 'recent_scans'
const MAX_RECENT = 20

const recentScans = ref<RecentScan[]>([])

function loadRecentScans() {
  try {
    const data = uni.getStorageSync(RECENT_KEY)
    if (data) recentScans.value = JSON.parse(data)
  } catch {}
}

function saveRecentScans() {
  try {
    uni.setStorageSync(RECENT_KEY, JSON.stringify(recentScans.value))
  } catch {}
}

function addRecentScan(barcode: string, name: string = '待获取', emoji: string = '🥫') {
  const existing = recentScans.value.findIndex(s => s.barcode === barcode)
  if (existing !== -1) {
    recentScans.value.splice(existing, 1)
  }
  recentScans.value.unshift({ barcode, name, emoji, time: Date.now() })
  recentScans.value = recentScans.value.slice(0, MAX_RECENT)
  saveRecentScans()
}

// ── Time Format ────────────────────────────────────────
function formatTime(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)}分钟前`
  if (diff < 2 * hour) return '1小时前'
  if (diff < day) return `${Math.floor(diff / hour)}小时前`
  if (diff < 2 * day) return '昨天'
  if (diff < 7 * day) return `${Math.floor(diff / day)}天前`
  const date = new Date(timestamp)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

// ── Scan ───────────────────────────────────────────────
async function handleScan() {
  try {
    const barcode = await scanBarcode()
    addRecentScan(barcode)
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` })
  } catch (err) {
    if (err instanceof ScanCancelledError) return
    if (err && (err as any).errMsg?.includes('auth deny')) {
      uni.showToast({ title: '请允许摄像头权限', icon: 'none' })
    } else {
      uni.showToast({ title: '扫码失败', icon: 'error' })
    }
  }
}

function handleRecentClick(item: RecentScan) {
  uni.navigateTo({ url: `/pages/product/index?barcode=${item.barcode}` })
}
</script>

<style lang="scss" scoped>
// ── Page ────────────────────────────────────────────────
.index-page {
  @apply h-screen bg-background flex flex-col;
  padding-bottom: calc(80rpx + env(safe-area-inset-bottom));
  overflow: hidden;
}

// ── Hero ───────────────────────────────────────────────
.hero {
  @apply bg-card px-6 pt-10 pb-8 flex flex-col items-center border-b border-border;
}

.logo-row {
  @apply flex items-center gap-2 mb-1;
}

.logo-emoji {
  @apply text-[60px] leading-none;
}

.logo-title {
  @apply text-xl font-bold text-foreground tracking-tight;
}

.logo-sub {
  @apply text-sm text-muted-foreground;
}

// ── Scan CTA ───────────────────────────────────────────
.scan-cta-wrap {
  @apply flex justify-center items-center py-10 pb-8;
}

.scan-cta {
  @apply w-[140px] h-[140px] rounded-full bg-gradient-to-br from-pink-400 to-pink-500 flex flex-col items-center justify-center gap-1.5 relative cursor-pointer;
  box-shadow: 0 16rpx 80rpx rgba(236, 72, 153, 0.4);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;

  &:active {
    @apply scale-95;
  }
}

.scan-cta-ring {
  @apply absolute inset-[-4px] rounded-full border-2 border-pink-400/30 pointer-events-none;
  animation: pulse-ring 2s ease-out infinite;
}

.scan-cta-icon {
  @apply w-9 h-9;
}

.scan-cta-text {
  @apply text-white text-base font-bold tracking-tight;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.6; }
  70% { transform: scale(1.15); opacity: 0; }
  100% { transform: scale(1.15); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .scan-cta-ring {
    animation: none;
  }
  .scan-cta {
    transition: none;
  }
}

// ── Section Divider ────────────────────────────────────
.section-divider {
  @apply flex items-center gap-3 px-6 pt-6 pb-3;
}

.divider-line {
  @apply flex-1 h-px bg-border;
}

.section-label {
  @apply flex items-center gap-2 flex-shrink-0;
}

.section-label-text {
  @apply text-[11px] font-semibold text-muted-foreground uppercase tracking-widest;
}

.scan-count {
  @apply bg-risk-t4/10 text-risk-t4 text-[10px] font-bold px-1.5 py-0.5 rounded-full;
}

.dark .scan-count {
  background: color-mix(in oklch, var(--color-risk-t4) 15%, transparent);
  color: var(--color-risk-t4);
}

// ── Scan List ───────────────────────────────────────────
.scan-list {
  @apply flex-1 px-6 pb-10 flex flex-col gap-2 overflow-y-auto;
  min-height: 0;
}

.scan-item {
  @apply bg-card border border-border rounded-xl px-4 py-3.5 flex items-center gap-3 cursor-pointer;
  box-shadow: var(--shadow-sm);
  transition: transform 0.15s ease;

  &:active {
    @apply scale-[0.98];
  }
}

.scan-icon {
  @apply w-10 h-10 rounded-lg bg-background border border-border flex items-center justify-center text-xl flex-shrink-0;
}

.scan-info {
  @apply flex-1 min-w-0;
}

.scan-name {
  @apply block text-sm font-semibold text-foreground tracking-tight mb-0.5 truncate;
}

.scan-time {
  @apply text-xs text-muted-foreground;
}

.scan-arrow {
  @apply w-4 h-4 text-muted-foreground opacity-40 flex-shrink-0;
}

.scan-empty {
  @apply text-center pt-12;
}

.scan-empty-text {
  @apply text-base text-muted-foreground;
}
</style>
