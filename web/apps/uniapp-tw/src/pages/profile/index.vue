<template>
  <view class="profile-page">
    <!-- ── Header ──────────────────────────── -->
    <view class="profile-header">
      <view :style="{ height: themeStore.statusBarHeight + 'px' }" />
      <view class="header-content">
        <button class="header-btn" @click="goBack">
          <Icon name="arrowLeft" :size="24" />
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
            <Icon name="user" :size="48" />
          </view>
          <text class="login-text">点击登录</text>
        </view>

        <!-- 菜单列表 -->
        <view class="menu-list">
          <view class="menu-item" @click="handleScanRecord">
            <view class="menu-item-left">
              <Icon name="menu" class="menu-icon" :size="20" />
              <text class="menu-text">扫描记录</text>
            </view>
            <Icon name="arrowRight" class="menu-arrow" :size="20" />
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <Icon name="users" class="menu-icon" :size="20" />
              <text class="menu-text">家庭成员管理</text>
            </view>
            <Icon name="arrowRight" class="menu-arrow" :size="20" />
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <Icon name="bookmark" class="menu-icon" :size="20" />
              <text class="menu-text">收藏夹</text>
            </view>
            <Icon name="arrowRight" class="menu-arrow" :size="20" />
          </view>

          <view class="menu-item disabled" @click="handleUpcoming">
            <view class="menu-item-left">
              <Icon name="settings" class="menu-icon" :size="20" />
              <text class="menu-text">设置</text>
            </view>
            <Icon name="arrowRight" class="menu-arrow" :size="20" />
          </view>
        </view>

      </view>
    </scroll-view>

  </view>
</template>

<script setup lang="ts">
import { useThemeStore } from "../../store/theme"
import Icon from "@/components/ui/Icon.vue"

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
    @apply w-6 h-6;
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
