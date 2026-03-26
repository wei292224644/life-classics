<script setup lang="ts">
import { computed } from "vue";
import { cn } from "@/utils/cn";
import DIcon from "./DIcon.vue";
import type { IconName } from "../icons/iconsRegistry";

defineOptions({
  options: { virtualHost: true, addGlobalClass: true },
});

interface Props {
  /** 空状态图片 URL（优先渲染） */
  image?: string;
  /** 空状态图标（无 image 时回退） */
  icon?: IconName;
  /** 空状态文案 */
  message?: string;
  /** 根容器自定义 class */
  dclass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  image: "",
  icon: "search",
  message: "暂无数据",
  dclass: "",
});

const rootClass = computed(() =>
  cn("flex flex-col items-center justify-center gap-3", props.dclass),
);
</script>

<template>
  <view :class="rootClass">
    <!-- 图片模式 -->
    <image
      v-if="image"
      :src="image"
      mode="aspectFit"
      class="h-[200rpx]"
    />
    <!-- 图标回退模式 -->
    <DIcon
      v-else
      :name="icon"
      dclass="text-[64rpx] text-muted-foreground opacity-60"
    />
    <!-- 文案 -->
    <text class="text-xl text-muted-foreground text-center">
      {{ message }}
    </text>
  </view>
</template>
