<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useThemeStore } from "../../store/theme";
import Icon from "../../components/Icon.vue";
import { scanBarcode, ScanCancelledError } from "../../utils/scanner";

// ── Types ─────────────────────────────────────────────
interface RecentScan {
  barcode: string;
  name: string;
  emoji: string;
  time: number;
}

// ── Theme Store ──────────────────────────────────────────
const themeStore = useThemeStore();

onMounted(() => {
  loadRecentScans();
});

// ── Recent Scans ───────────────────────────────────────
const RECENT_KEY = "recent_scans";
const MAX_RECENT = 20;

const recentScans = ref<RecentScan[]>([]);

function loadRecentScans() {
  try {
    const data = uni.getStorageSync(RECENT_KEY);
    if (data) {
      recentScans.value = JSON.parse(data);
    }
  } catch {}
}

function saveRecentScans() {
  try {
    uni.setStorageSync(RECENT_KEY, JSON.stringify(recentScans.value));
  } catch {}
}

function addRecentScan(
  barcode: string,
  name: string = "待获取",
  emoji: string = "🥫",
) {
  const existing = recentScans.value.findIndex((s) => s.barcode === barcode);
  if (existing !== -1) {
    recentScans.value.splice(existing, 1);
  }
  recentScans.value.unshift({ barcode, name, emoji, time: Date.now() });
  recentScans.value = recentScans.value.slice(0, MAX_RECENT);
  saveRecentScans();
}

// ── Time Format ────────────────────────────────────────
function formatTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diff < minute) {
    return "刚刚";
  }
  if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`;
  }
  if (diff < 2 * hour) {
    return "1小时前";
  }
  if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`;
  }
  if (diff < 2 * day) {
    return "昨天";
  }
  if (diff < 7 * day) {
    return `${Math.floor(diff / day)}天前`;
  }
  const date = new Date(timestamp);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

// ── Scan ───────────────────────────────────────────────
async function handleScan() {
  try {
    const barcode = await scanBarcode();
    addRecentScan(barcode);
    uni.navigateTo({ url: `/pages/product/index?barcode=${barcode}` });
  } catch (err) {
    if (err instanceof ScanCancelledError) {
      return;
    }
    if (err && (err as any).errMsg?.includes("auth deny")) {
      uni.showToast({ title: "请允许摄像头权限", icon: "none" });
    } else {
      uni.showToast({ title: "扫码失败", icon: "error" });
    }
  }
}

function handleRecentClick(item: RecentScan) {
  uni.navigateTo({ url: `/pages/product/index?barcode=${item.barcode}` });
}
</script>

<template>
  <view class="index-page flex h-screen flex-col overflow-hidden bg-background">
    <!-- ── Logo 区域 ─────────────────────────── -->
    <view
      class="flex flex-col items-center border-b border-border bg-card px-6 pb-6 pt-10"
    >
      <view class="mb-2 flex items-center gap-2">
        <text class="text-2xl leading-none">🍎</text>
        <text class="text-lg font-bold tracking-tight text-foreground">
          食品安全助手
        </text>
      </view>
      <text class="text-sm text-muted-foreground">
        扫码查配料 · 了解你吃的每一口
      </text>

      <!-- ── 扫一扫 CTA ─────────────────────────── -->
      <view class="flex items-center justify-center py-10 pb-8">
        <view
          class="scan-cta relative flex h-[140px] w-[140px] cursor-pointer flex-col items-center justify-center gap-1.5 rounded-full bg-gradient-to-br from-accent-pink-light to-accent-pink transition-all duration-200 ease-in-out active:scale-95"
          role="button"
          tabindex="0"
          aria-label="扫一扫"
          @click="handleScan"
        >
          <view
            class="scan-cta-ring pointer-events-none absolute -inset-1 rounded-full border-2 border-pink-400/30"
            aria-hidden="true"
          />
          <svg
            class="h-9 w-9"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path
              d="M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2"
            />
            <line x1="7" y1="12" x2="17" y2="12" />
          </svg>
          <text class="text-base font-bold tracking-tight text-white">
            扫一扫
          </text>
        </view>
      </view>
    </view>

    <!-- ── 最近扫描 ─────────────────────────── -->
    <view class="flex items-center gap-3 px-6 pb-3 pt-6">
      <view class="h-px flex-1 bg-border" />
      <view class="flex flex-shrink-0 items-center gap-2">
        <text
          class="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground"
        >
          最近扫描
        </text>
        <view
          class="scan-count rounded-full px-1.5 py-0.5 text-[10px] font-bold text-risk-t4"
        >
          {{ recentScans.length }}
        </view>
      </view>
      <view class="h-px flex-1 bg-border" />
    </view>

    <view class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-6 pb-10">
      <view
        v-for="item in recentScans"
        :key="item.barcode"
        class="flex cursor-pointer items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-sm transition-transform duration-150 ease-in-out active:scale-[0.98]"
        role="button"
        tabindex="0"
        :aria-label="`${item.name}，${formatTime(item.time)}`"
        @click="handleRecentClick(item)"
      >
        <view
          class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border border-border bg-background text-xl"
        >
          {{ item.emoji }}
        </view>
        <view class="min-w-0 flex-1">
          <text
            class="mb-0.5 block truncate text-sm font-semibold tracking-tight text-foreground"
          >
            {{ item.name }}
          </text>
          <text class="text-xs text-muted-foreground">
            {{ formatTime(item.time) }}
          </text>
        </view>
        <Icon name="arrowRight" class="h-4 w-4 flex-shrink-0 text-muted-foreground opacity-40" :size="16" />
      </view>

      <view v-if="!recentScans.length" class="pt-12 text-center">
        <text class="text-base text-muted-foreground">暂无扫描记录</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
// ── Page ────────────────────────────────────────────────
.index-page {
  padding-bottom: calc(80rpx + env(safe-area-inset-bottom));
}

.scan-cta {
  box-shadow: 0 16rpx 80rpx rgba(236, 72, 153, 0.4);
}

.scan-cta-ring {
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% {
    transform: scale(1);
    opacity: 0.6;
  }
  70% {
    transform: scale(1.15);
    opacity: 0;
  }
  100% {
    transform: scale(1.15);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .scan-cta-ring {
    animation: none;
  }
  .scan-cta {
    transition: none;
  }
}

.scan-count {
  background: color-mix(in oklch, var(--color-risk-t4) 10%, transparent);
}

.dark .scan-count {
  background: color-mix(in oklch, var(--color-risk-t4) 15%, transparent);
}
</style>
