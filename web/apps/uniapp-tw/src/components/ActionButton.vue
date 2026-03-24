<template>
  <button
    :class="['action-btn', `action-btn--${variant}`, `action-btn--${size}`]"
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
    icon?: string;
  }>(),
  { variant: "primary", size: "lg", disabled: false, loading: false, icon: undefined }
);

defineEmits<{ (e: "click"): void }>();
</script>

<style lang="scss" scoped>
.action-btn {
  @apply inline-flex items-center justify-center gap-2 w-full border-none font-semibold cursor-pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);

  // size
  &--lg {
    @apply h-12 px-8 text-xl rounded-xl;
  }
  &--md {
    @apply h-9 px-6 text-lg rounded-lg;
  }

  // primary
  &--primary {
    @apply text-white bg-gradient-to-br from-pink-400 to-pink-500;
    box-shadow: 0 4rpx 20rpx color-mix(in oklch, var(--color-primary) 30%, transparent);

    &:active { transform: scale(0.97); }
    &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
    &:disabled { @apply opacity-50 cursor-not-allowed; transform: none; }
  }

  // secondary
  &--secondary {
    @apply bg-card border border-border text-foreground;

    &:active { background: color-mix(in oklch, var(--color-card) 90%, transparent); }
    &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
    &:disabled { @apply opacity-50 cursor-not-allowed; }
  }

  // ghost
  &--ghost {
    @apply bg-transparent text-foreground;

    &:active { background: color-mix(in oklch, var(--color-foreground) 8%, transparent); }
    &:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
    &:disabled { @apply opacity-50 cursor-not-allowed; }
  }

  &__loading,
  &__icon {
    @apply w-5 h-5;
  }
}
</style>
