<template>
  <view
    class="index-page h-screen bg-[var(--bg-base)] flex flex-col overflow-hidden"
    :class="{ 'dark': themeStore.isDark }"
    :style="{ paddingBottom: 'calc(80rpx + env(safe-area-inset-bottom))' }"
  >
    <!-- ── 状态栏占位 ─────────────────────────── -->
    <view :style="{ height: themeStore.statusBarHeight + 'px' }" />

    <!-- ── Logo 区域 ─────────────────────────── -->
    <view class="hero bg-[var(--bg-card)] py-20 px-12 pb-16 flex flex-col items-center border-b border-[var(--border-color)]">
      <view class="logo-row flex items-center gap-4 mb-2">
        <text class="logo-emoji">🍎</text>
        <text class="logo-title">食品安全助手</text>
      </view>
      <text class="logo-sub">扫码查配料 · 了解你吃的每一口</text>
    </view>

    <!-- ── 扫一扫 CTA ─────────────────────────── -->
    <view class="scan-cta-wrap flex justify-center items-center py-20 pb-16">
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
    <view class="section-divider flex items-center gap-6 px-12 pb-6">
      <view class="divider-line"></view>
      <view class="section-label flex items-center gap-4 flex-shrink-0">
        <text class="section-label-text">最近扫描</text>
        <view class="scan-count">{{ recentScans.length }}</view>
      </view>
      <view class="divider-line"></view>
    </view>

    <view class="scan-list flex-1 px-12 pb-10 flex flex-col gap-4 overflow-y-auto min-h-0">
      <view
        v-for="item in recentScans"
        :key="item.barcode"
        class="scan-item bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl py-7 px-8 flex items-center gap-6"
        role="button"
        tabindex="0"
        :aria-label="`${item.name}，${formatTime(item.time)}`"
        @click="handleRecentClick(item)"
      >
        <view class="scan-icon" style="border-radius: 20rpx">{{ item.emoji }}</view>
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
@import '@/styles/design-system.scss';

// ── Logo ────────────────────────────────────────────────
.logo-emoji {
  font-size: 52rpx;
  line-height: 1;
}

.logo-title {
  font-size: 34rpx;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.logo-sub {
  font-size: 24rpx;
  color: var(--text-muted);
}

// ── Scan CTA ───────────────────────────────────────────
.scan-cta {
  width: 280rpx;
  height: 280rpx;
  background: linear-gradient(135deg, var(--palette-pink-400) 0%, var(--palette-pink-500) 100%);
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  box-shadow: 0 16rpx 80rpx rgba(236, 72, 153, 0.4);
  cursor: pointer;
  position: relative;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;

  &:active {
    transform: scale(0.95);
  }
}

.scan-cta-ring {
  position: absolute;
  inset: -8rpx;
  border-radius: 50%;
  border: 4rpx solid rgba(236, 72, 153, 0.25);
  animation: pulse-ring 2s ease-out infinite;
  pointer-events: none;
}

.scan-cta-icon {
  width: 72rpx;
  height: 72rpx;
}

.scan-cta-text {
  color: white;
  font-size: 32rpx;
  font-weight: 700;
  letter-spacing: -0.02em;
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
.divider-line {
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.section-label-text {
  font-size: 20rpx;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.scan-count {
  background: var(--palette-red-50);
  color: var(--palette-red-500);
  font-size: 20rpx;
  font-weight: 700;
  padding: 4rpx 12rpx;
  border-radius: 9999rpx;
}

.dark-mode .scan-count {
  background: color-mix(in oklch, var(--palette-red-400) 15%, transparent);
  color: var(--palette-red-400);
}

// ── Scan Item ───────────────────────────────────────────
.scan-item {
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
  transition: transform 0.15s ease;

  &:active {
    transform: scale(0.98);
  }
}

.scan-icon {
  width: 80rpx;
  height: 80rpx;
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  flex-shrink: 0;
}

.scan-info {
  flex: 1;
  min-width: 0;
}

.scan-name {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-bottom: 4rpx;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scan-time {
  font-size: 24rpx;
  color: var(--text-muted);
}

.scan-arrow {
  width: 32rpx;
  height: 32rpx;
  color: var(--text-muted);
  opacity: 0.4;
  flex-shrink: 0;
}

.scan-empty {
  text-align: center;
  padding: 48rpx 0;
}

.scan-empty-text {
  font-size: 20rpx;
  color: var(--text-muted);
}

</style>
