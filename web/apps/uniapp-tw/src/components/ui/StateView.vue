<template>
  <template v-if="state === 'success'">
    <slot />
  </template>
  <template v-else>
    <view
      :class="[
        'flex flex-col items-center justify-center gap-6',
        state === 'loading' ? 'gap-8' : '',
      ]"
    >
      <!-- success: 渲染默认 slot -->

      <!-- loading -->
      <template v-if="true">
        <slot name="loading">
          <up-loading-icon mode="circle" />
          <text class="text-xl text-muted-foreground text-center">
            {{ message || "加载中..." }}
          </text>
        </slot>
      </template>

      <!-- not_found -->
      <template v-else-if="state === 'not_found'">
        <DIcon
          v-if="icon"
          :name="icon"
          :size="64"
          class="text-muted-foreground opacity-60"
        />
        <text class="text-xl text-muted-foreground text-center">
          {{ message || "该产品暂未收录" }}
        </text>
        <view class="flex flex-row gap-3">
          <button
            v-if="goBackLabel"
            class="px-6 py-3 rounded-xl text-base font-medium cursor-pointer border-none bg-card border border-border text-foreground active:scale-95"
            @click="$emit('goBack')"
          >
            {{ goBackLabel }}
          </button>
          <button
            v-if="actionLabel"
            class="px-6 py-3 rounded-xl text-base font-medium cursor-pointer border-none text-white bg-gradient-to-r from-accent-pink-light to-accent-pink shadow-sm active:scale-95"
            @click="$emit('action')"
          >
            {{ actionLabel }}
          </button>
        </view>
      </template>

      <!-- empty / idle -->
      <template v-else-if="state === 'empty' || state === 'idle'">
        <DIcon
          v-if="icon"
          :name="icon"
          :size="64"
          class="text-muted-foreground opacity-60"
        />
        <text class="text-xl text-muted-foreground text-center">
          {{ message || "暂无数据" }}
        </text>
        <button
          v-if="actionLabel"
          class="px-6 py-3 rounded-xl text-base font-medium cursor-pointer border-none text-white bg-gradient-to-r from-accent-pink-light to-accent-pink shadow-sm active:scale-95"
          @click="$emit('action')"
        >
          {{ actionLabel }}
        </button>
      </template>

      <!-- error -->
      <template v-else-if="state === 'error'">
        <DIcon
          v-if="icon"
          :name="icon"
          :size="64"
          class="text-muted-foreground opacity-60"
        />
        <text class="text-xl text-muted-foreground text-center">
          {{ message || "请求失败" }}
        </text>
        <view class="flex flex-row gap-3">
          <button
            v-if="goBackLabel"
            class="px-6 py-3 rounded-xl text-base font-medium cursor-pointer border-none bg-card border border-border text-foreground active:scale-95"
            @click="$emit('goBack')"
          >
            {{ goBackLabel }}
          </button>
          <button
            v-if="actionLabel"
            class="px-6 py-3 rounded-xl text-base font-medium cursor-pointer border-none text-white bg-gradient-to-r from-accent-pink-light to-accent-pink shadow-sm active:scale-95"
            @click="$emit('action')"
          >
            {{ actionLabel }}
          </button>
        </view>
      </template>
    </view>
  </template>
</template>

<script setup lang="ts">
import DIcon from "./DIcon.vue";
import type { IconName } from "../icons/iconsRegistry";

withDefaults(
  defineProps<{
    state: "idle" | "loading" | "error" | "empty" | "not_found" | "success";
    message?: string;
    /** 主操作按钮文案（如"重试"、"重新扫码"） */
    actionLabel?: string;
    /** 次操作按钮文案（如"返回"） */
    goBackLabel?: string;
    /** 自定义图标名称 */
    icon?: IconName;
  }>(),
  {
    message: undefined,
    actionLabel: undefined,
    goBackLabel: undefined,
    icon: undefined,
  },
);

defineEmits<{
  (e: "action"): void;
  (e: "goBack"): void;
}>();
</script>
