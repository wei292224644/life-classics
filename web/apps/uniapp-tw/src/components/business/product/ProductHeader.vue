<script setup lang="ts">
import { ref } from "vue";
import { useSystemInfo } from "@/utils/system";
import Icon from "@/components/ui/Icon.vue";
import Button from "@/components/ui/Button.vue";

interface Props {
  name: string;
  overallRiskLevel: string;
}

defineProps<Props>();

const { statusBarHeight } = useSystemInfo();
const isScrolled = ref(false);

function updateScroll(scrollTop: number) {
  isScrolled.value = scrollTop > 60;
}

defineExpose({ updateScroll });

function handleBack() {
  uni.navigateBack();
}

function handleShare() {
  uni.showShareMenu({
    withShareTicket: true,
    menus: ["shareAppMessage", "shareTimeline"],
  });
}
</script>

<template>
  <view class="fixed top-0 left-0 right-0 z-50 pointer-events-none">
    <view
      class="flex items-center px-3 py-2 bg-transparent pointer-events-auto transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      :class="{ 'header--scrolled': isScrolled }"
      :style="{ top: `${statusBarHeight}px` }"
    >
      <Button
        size="icon"
        variant="ghost"
        @click="handleBack"
        class="rounded-sm"
      >
        <Icon name="arrowLeft" :size="20" />
      </Button>
      <text
        class="flex-1 text-sm leading-[1.15] font-semibold tracking-[-0.01em]"
      >
        {{ name }}
      </text>
      <Button
        size="icon"
        variant="ghost"
        class="rounded-sm"
        @click="handleShare"
      >
        <Icon name="share" :size="20" />
      </Button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.header--scrolled {
  @apply bg-background  border-b border-border shadow-md;
}
</style>
