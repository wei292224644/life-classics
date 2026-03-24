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
    icon?: string; // SVG path d attribute, optional
  }>(),
  { variant: "primary", size: "lg", disabled: false, loading: false, icon: undefined }
);

defineEmits<{ (e: "click"): void }>();
</script>

<style lang="scss" scoped>
@import "@/styles/design-system.scss";

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  border: none;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s $ease-spring;

  // size
  &--lg {
    height: var(--btn-height-xl);
    padding: 0 var(--btn-padding-x);
    font-size: var(--text-xl);
    border-radius: var(--btn-radius);
  }
  &--md {
    height: var(--btn-height-md);
    padding: 0 var(--space-6);
    font-size: var(--text-lg);
    border-radius: var(--radius-md);
  }

  // primary
  &--primary {
    background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
    color: #fff;
    box-shadow: 0 4rpx 20rpx color-mix(in oklch, var(--accent-pink) 30%, transparent);

    &:active { transform: scale(0.97); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  }

  // secondary
  &--secondary {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);

    &:active { background: var(--bg-card-hover); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  // ghost
  &--ghost {
    background: transparent;
    color: var(--text-primary);

    &:active { background: color-mix(in oklch, var(--text-primary) 8%, transparent); }
    &:focus-visible { outline: 2px solid var(--accent-pink); outline-offset: 2px; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  &__loading,
  &__icon {
    width: var(--icon-sm);
    height: var(--icon-sm);
  }
}
</style>
