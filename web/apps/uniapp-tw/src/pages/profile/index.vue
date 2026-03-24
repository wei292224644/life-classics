<template>
  <view class="profile-page">
    <!-- ── Header ──────────────────────────── -->
    <view class="profile-header">
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
      <view class="header-content">
        <button class="header-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <text class="header-title">我的</text>
        <view class="header-spacer" />
      </view>
    </view>

    <!-- ── Content ─────────────────────────── -->
    <scroll-view scroll-y class="content-scroll">
      <view class="content">

        <!-- 登录卡片 -->
        <view class="login-card" @click="handleLogin">
          <view class="login-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </view>
          <text class="login-text">点击登录</text>
        </view>

        <!-- 菜单列表 -->
        <view class="menu-list">
          <view class="menu-item" @click="handleScanRecord">
            <view class="menu-item-left">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 6h16M4 12h16M4 18h16"/>
              </svg>
              <text class="menu-text">扫描记录</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
              </svg>
              <text class="menu-text">家庭成员管理</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
              <text class="menu-text">收藏夹</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
              </svg>
              <text class="menu-text">设置</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>
        </view>

      </view>
    </scroll-view>

  </view>
</template>

<script setup lang="ts">
import { useThemeStore } from "../../store/theme"

const themeStore = useThemeStore()

// ── Actions ─────────────────────────────────────────────
function handleLogin() {
  uni.showToast({ title: '即将上线', icon: 'none' })
}

function handleScanRecord() {
  uni.showToast({ title: '即将上线', icon: 'none' })
}

function handleUpcoming() {
  uni.showToast({ title: '即将上线', icon: 'none' })
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
// ── Page ────────────────────────────────────────────────
.profile-page {
  @apply min-h-screen bg-background flex flex-col;
}

// ── Header ─────────────────────────────────────────────
.profile-header {
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
  margin-right: 48rpx;
}

.header-spacer {
  width: 48rpx;
}

// ── Content ─────────────────────────────────────────────
.content-scroll {
  @apply flex-1;
  height: calc(100vh - 88rpx);
}

.content {
  @apply p-6;
}

// ── Login Card ──────────────────────────────────────────
.login-card {
  @apply h-[200rpx] bg-gradient-to-br from-pink-50 to-pink-100 rounded-2xl flex flex-col items-center justify-center gap-3 mb-6;
  border: 1px solid color-mix(in oklch, oklch(93% 0.03 350) 50%, transparent);
}

.dark .login-card {
  @apply from-zinc-900 to-zinc-800;
  border-color: var(--color-border);
}

.login-avatar {
  @apply w-[100rpx] h-[100rpx] rounded-full bg-card flex items-center justify-center;
  box-shadow: var(--shadow-sm);

  svg {
    @apply w-12 h-12;
    color: var(--color-muted);
  }
}

.login-text {
  @apply text-base text-muted-foreground;
}

// ── Menu List ───────────────────────────────────────────
.menu-list {
  @apply bg-card border border-border rounded-2xl overflow-hidden;
}

.menu-item {
  @apply flex items-center justify-between h-[100rpx] px-6 border-b border-border cursor-pointer transition-colors duration-150;
  &:last-child {
    @apply border-b-0;
  }
  &:active {
    @apply bg-muted;
  }
  &.disabled {
    @apply opacity-50 pointer-events-none;
  }
}

.menu-item-left {
  @apply flex items-center gap-4;
}

.menu-icon {
  @apply w-10 h-10 text-secondary;
}

.menu-text {
  @apply text-base text-foreground;
}

.menu-arrow {
  @apply w-8 h-8 text-muted-foreground opacity-40;
}
</style>
