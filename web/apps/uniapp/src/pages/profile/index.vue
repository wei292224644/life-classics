<template>
  <view
    class="profile-page"
    :class="{ 'dark-mode': themeStore.isDark }"
  >
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
@import '@/styles/design-system.scss';

.profile-page {
  min-height: 100vh;
  background: var(--bg-base);
  display: flex;
  flex-direction: column;
}

// ── Header ─────────────────────────────────────────────
.profile-header {
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
    width: var(--space-9);
    height: var(--space-9);
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
  margin-right: var(--space-15);
}

.header-spacer {
  width: var(--space-15);
}

// ── Content ─────────────────────────────────────────────
.content-scroll {
  flex: 1;
  height: calc(100vh - 88rpx);
}

.content {
  padding: var(--space-6);
}

// ── Login Card ──────────────────────────────────────────
.login-card {
  height: 200rpx;
  background: linear-gradient(135deg, var(--palette-pink-50) 0%, var(--palette-pink-100) 100%);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  border: 1px solid color-mix(in oklch, var(--palette-pink-200) 50%, transparent);
}

.dark-mode .login-card {
  background: linear-gradient(135deg, #1a1018 0%, #1a1a1a 100%);
  border-color: var(--border-color);
}

.login-avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);

  svg {
    width: var(--space-12);
    height: var(--space-12);
    color: var(--text-muted);
  }
}

.login-text {
  font-size: var(--text-base);
  color: var(--text-muted);
}

// ── Menu List ───────────────────────────────────────────
.menu-list {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100rpx;
  padding: 0 var(--space-6);
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
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.menu-icon {
  width: var(--space-10);
  height: var(--space-10);
  color: var(--text-secondary);
}

.menu-text {
  font-size: var(--text-base);
  color: var(--text-primary);
}

.menu-arrow {
  width: var(--space-8);
  height: var(--space-8);
  color: var(--text-muted);
  opacity: 0.4;
}
</style>
