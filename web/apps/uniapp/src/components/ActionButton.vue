<template>
  <button
    :class="['action-btn', `action-btn--${variant}`, `action-btn--${size}`, 'inline-flex', 'items-center', 'justify-center', 'gap-2']"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <up-loading-icon v-if="loading" class="action-btn__loading" />
    <svg v-else-if="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="action-btn__icon" aria-hidden="true">
      <path :d="icon" />
    </svg>
    <text>{{ label }}</text>
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string;
    variant?: "primary" | "secondary" | "ghost";
    size?: "md" | "lg";
    disabled?: boolean;
    loading?: boolean;
    icon?: string; // SVG path d attribute, optional
  }>(),
  { variant: "primary", size: "lg", disabled: false, loading: false, icon: undefined }
);

defineEmits<{ (e: "click"): void }>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.action-btn {
  width: 100%;
  border: none;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s $ease-spring;

  // size
  &--lg {
    height: 88rpx;
    padding: 0 32rpx;
    font-size: 28rpx;
    border-radius: 28rpx;
  }
  &--md {
    height: 72rpx;
    padding: 0 24rpx;
    font-size: 26rpx;
    border-radius: 32rpx;
  }

  // primary
  &--primary {
    background: linear-gradient(135deg, var(--accent-light), var(--accent));
    color: #fff;
    box-shadow: 0 4rpx 20rpx color-mix(in oklch, var(--accent) 30%, transparent);

    &:active { transform: scale(0.97); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  }

  // secondary
  &--secondary {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);

    &:active { background: var(--bg-card-hover); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  // ghost
  &--ghost {
    background: transparent;
    color: var(--text-primary);

    &:active { background: color-mix(in oklch, var(--text-primary) 8%, transparent); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  &__loading,
  &__icon {
    width: 28rpx;
    height: 28rpx;
  }
}
</style>
