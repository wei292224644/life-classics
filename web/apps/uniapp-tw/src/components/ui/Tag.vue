<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'
import type { IconName } from '../icons/iconsRegistry'

type TagVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'success' | 'warning'
type TagSize = 'sm' | 'md' | 'lg'

interface Props {
  variant?: TagVariant
  size?: TagSize
  removable?: boolean
  icon?: IconName
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  removable: false,
  icon: undefined,
  class: '',
})

const emit = defineEmits<{
  (e: 'remove'): void
}>()

const tagClass = computed(() => [
  'tag',
  `tag--${props.variant}`,
  `tag--${props.size}`,
  { 'tag--with-icon': props.icon },
  props.class,
])
</script>

<template>
  <view :class="tagClass">
    <Icon v-if="icon" :name="icon" class="tag__icon" />
    <text class="tag__text"><slot /></text>
    <view v-if="removable" class="tag__remove" @tap="emit('remove')">
      <Icon name="x" class="tag__remove-icon" />
    </view>
  </view>
</template>

<style lang="scss" scoped>
// ── Base Tag ────────────────────────────────────────────────
.tag {
  @apply inline-flex items-center gap-1 font-medium;
  @apply border rounded-full;
  @apply transition-all duration-150;

  // default — primary color
  &--default {
    @apply border-transparent text-white;
    background: linear-gradient(135deg, var(--accent-pink-light) 0%, var(--accent-pink) 100%);
  }

  // secondary — muted background
  &--secondary {
    @apply border-transparent text-secondary-foreground;
    background: var(--secondary);
  }

  // outline — transparent with border
  &--outline {
    @apply text-foreground border-border bg-transparent;
  }

  // ghost — fully transparent
  &--ghost {
    @apply border-transparent text-foreground bg-transparent;
  }

  // destructive — red
  &--destructive {
    @apply border-transparent text-white;
    background: var(--destructive);
  }

  // success — green
  &--success {
    @apply border-transparent text-white;
    background: var(--color-risk-t0);
  }

  // warning — orange/yellow
  &--warning {
    @apply border-transparent text-white;
    background: var(--color-risk-t2);
  }

  // ── Sizes ─────────────────────────────────────────────────

  &--sm {
    @apply px-2 py-0.5 text-xs;
    @apply gap-0.5;

    .tag__icon { @apply w-3 h-3; }
    .tag__remove-icon { @apply w-3 h-3; }
  }

  &--md {
    @apply px-3 py-1 text-xs;
    @apply gap-1;

    .tag__icon { @apply w-3.5 h-3.5; }
    .tag__remove-icon { @apply w-3.5 h-3.5; }
  }

  &--lg {
    @apply px-4 py-1.5 text-sm;
    @apply gap-1.5;

    .tag__icon { @apply w-4 h-4; }
    .tag__remove-icon { @apply w-4 h-4; }
  }

  // ── Elements ──────────────────────────────────────────────

  &__icon {
    @apply flex-shrink-0;
  }

  &__text {
    @apply leading-none;
  }

  &__remove {
    @apply flex items-center justify-center rounded-full;
    @apply -mr-0.5 p-0.5;
    @apply hover:opacity-80 active:opacity-60;
    transition: opacity 0.15s ease;

    &-icon {
      @apply opacity-70;
    }
  }
}
</style>
