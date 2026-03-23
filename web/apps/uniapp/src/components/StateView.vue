<template>
  <view :class="['state-view flex flex-col items-center justify-center gap-8', `state-view--${state}`]">
    <template v-if="state === 'loading'">
      <up-loading-icon mode="circle" />
      <text class="state-view__message">{{ message || "加载中..." }}</text>
    </template>
    <template v-else-if="state === 'empty'">
      <text class="state-view__message">{{ message || "暂无数据" }}</text>
    </template>
    <template v-else-if="state === 'error'">
      <text class="state-view__message">{{ message || "请求失败" }}</text>
      <button
        v-if="actionLabel"
        class="state-view__action"
        @click="$emit('retry')"
      >
        {{ actionLabel }}
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    state: "loading" | "error" | "empty";
    message?: string;
    actionLabel?: string;
  }>(),
  { message: undefined, actionLabel: undefined }
);

defineEmits<{ (e: "retry"): void }>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.state-view {
  &__message {
    font-size: 26rpx;
    color: var(--text-muted);
    text-align: center;
  }

  &__action {
    padding: 12rpx 32rpx;
    border-radius: 32rpx;
    font-size: 26rpx;
    font-weight: 500;
    font-family: inherit;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    cursor: pointer;

    &:active { background: var(--bg-card-hover); }
  }
}
</style>
