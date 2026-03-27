<template>
  <scroll-view
    scroll-y
    :show-scrollbar="false"
    :refresher-enabled="true"
    :refresher-triggered="isRefreshing"
    :lower-threshold="80"
    v-bind="$attrs"
    @refresherrefresh="$emit('refresh')"
    @refresherrestore="$emit('refresherrestore')"
    @scrolltolower="onScrollToLower"
  >
    <slot />
    <!-- 底部状态 -->
    <view class="flex items-center justify-center py-4">
      <text v-if="isLoading" class="text-xs text-muted-foreground">加载中…</text>
      <text v-else-if="!hasMore" class="text-xs text-muted-foreground">— 到底了 —</text>
    </view>
  </scroll-view>
</template>

<script setup lang="ts">
defineOptions({ inheritAttrs: false });

defineProps<{
  isRefreshing?: boolean;
  isLoading?: boolean;
  hasMore?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  refresherrestore: [];
  loadMore: [];
}>();

function onScrollToLower() {
  emit("loadMore");
}
</script>
