<template>
  <view
    class="profile-page flex flex-col min-h-screen"
    :class="{ 'dark': themeStore.isDark }"
  >
    <!-- ── Header ──────────────────────────── -->
    <view class="profile-header">
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
      <view class="header-content flex items-center h-[88rpx] px-[32rpx] gap-[24rpx]">
        <button class="header-btn w-[60rpx] h-[60rpx] flex items-center justify-center" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <text class="header-title flex-1 text-center">我的</text>
        <view class="header-spacer w-[60rpx]" />
      </view>
    </view>

    <!-- ── Content ─────────────────────────── -->
    <scroll-view scroll-y class="content-scroll flex-1">
      <view class="content p-[48rpx]">

        <!-- 登录卡片 -->
        <view class="login-card h-[200rpx] flex flex-col items-center justify-center gap-[24rpx]" @click="handleLogin">
          <view class="login-avatar w-[100rpx] h-[100rpx] flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </view>
          <text class="login-text">点击登录</text>
        </view>

        <!-- 菜单列表 -->
        <view class="menu-list overflow-hidden">
          <view class="menu-item flex items-center justify-between h-[100rpx] px-[48rpx]" @click="handleScanRecord">
            <view class="menu-item-left flex items-center gap-[16rpx]">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 6h16M4 12h16M4 18h16"/>
              </svg>
              <text class="menu-text">扫描记录</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>

          <view class="menu-item disabled flex items-center justify-between h-[100rpx] px-[48rpx]" @click="handleUpcoming">
            <view class="menu-item-left flex items-center gap-[16rpx]">
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

          <view class="menu-item disabled flex items-center justify-between h-[100rpx] px-[48rpx]" @click="handleUpcoming">
            <view class="menu-item-left flex items-center gap-[16rpx]">
              <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
              <text class="menu-text">收藏夹</text>
            </view>
            <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </view>

          <view class="menu-item disabled flex items-center justify-between h-[100rpx] px-[48rpx]" @click="handleUpcoming">
            <view class="menu-item-left flex items-center gap-[16rpx]">
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
@import '@/styles/design-system.scss';

.profile-page {
  background: var(--bg-base);
}

// ── Header ─────────────────────────────────────────────
.profile-header {
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-color);
}

.header-btn {
  background: transparent;
  border: none;
  padding: 0;
  border-radius: 32rpx;

  svg {
    width: 36rpx;
    height: 36rpx;
    color: var(--text-primary);
  }
}

.header-title {
  font-size: 24rpx;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-right: 120rpx;
}

.header-spacer {
}

// ── Content ─────────────────────────────────────────────
.content-scroll {
}

.content {
}

// ── Login Card ──────────────────────────────────────────
.login-card {
  background: linear-gradient(135deg, var(--palette-pink-50) 0%, var(--palette-pink-100) 100%);
  border-radius: 40rpx;
  margin-bottom: 48rpx;
  border: 1px solid color-mix(in oklch, var(--palette-pink-200) 50%, transparent);
}

.dark .login-card {
  background: linear-gradient(135deg, #1a1018 0%, #1a1a1a 100%);
  border-color: var(--border-color);
}

.login-avatar {
  border-radius: 50%;
  background: var(--bg-card);
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);

  svg {
    width: 48rpx;
    height: 48rpx;
    color: var(--text-muted);
  }
}

.login-text {
  font-size: 28rpx;
  color: var(--text-muted);
}

// ── Menu List ───────────────────────────────────────────
.menu-list {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 40rpx;
}

.menu-item {
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background 0.15s ease;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: var(--bg-card-hover);
  }

  &.disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.menu-item-left {
}

.menu-icon {
  width: 80rpx;
  height: 80rpx;
  color: var(--text-secondary);
}

.menu-text {
  font-size: 28rpx;
  color: var(--text-primary);
}

.menu-arrow {
  width: 64rpx;
  height: 64rpx;
  color: var(--text-muted);
  opacity: 0.4;
}
</style>
