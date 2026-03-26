<script setup lang="ts">
import { ref } from "vue";
import DIcon from "@/components/ui/DIcon.vue";
import DButton from "@/components/ui/DButton.vue";
import TopBar from "@/components/ui/TopBar.vue";
import { cn } from "@/utils/cn";

interface Props {
  name: string;
  overallRiskLevel: string;
}

defineProps<Props>();

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
      :class="
        cn(
          ' bg-transparent pointer-events-auto transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
          isScrolled && 'bg-background  border-b border-border shadow-md',
        )
      "
    >
      <TopBar />

      <view class="flex items-center h-topbar">
        <DButton
          size="icon"
          variant="ghost"
          @click="handleBack"
          dclass="rounded-sm"
        >
          <DIcon name="arrow-left" :size="20" />
        </DButton>
        <text
          class="flex-1 text-sm leading-[1.15] font-semibold tracking-[-0.01em]"
        >
          {{ name }}
        </text>
        <DButton
          size="icon"
          variant="ghost"
          dclass="rounded-sm"
          @click="handleShare"
        >
          <DIcon name="share" :size="20" />
        </DButton>
      </view>
    </view>
  </view>
</template>
