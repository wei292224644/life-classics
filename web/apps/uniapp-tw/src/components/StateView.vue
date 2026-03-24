<template>
  <view :class="['state-view', `state-view--${state}`]">
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
.state-view {
  @apply flex flex-col items-center justify-center gap-8;

  &__message {
    @apply text-lg text-muted-foreground text-center;
  }

  &__action {
    @apply px-8 py-3 rounded-lg text-lg font-medium bg-card border border-border text-foreground cursor-pointer font-family-inherit;
    font-family: inherit;

    &:active { @apply bg-muted; }
  }
}
</style>
