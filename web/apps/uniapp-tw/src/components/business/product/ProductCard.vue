<script setup lang="ts">
import { getRiskConfig, riskCls, type RiskLevel } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import DIcon from "@/components/ui/DIcon.vue";
import Tag from "@/components/ui/Tag.vue";
import RiskTag from "@/components/ui/RiskTag.vue";
interface Props {
  /** 食品或配料数据 */
  data: {
    type: "product" | "ingredient";
    id: number;
    barcode?: string;
    name: string;
    subtitle: string;
    imageUrl?: string | null;
    riskLevel: string;
    highRiskCount?: number | null;
  };
  click?: () => void;
}
const props = defineProps<Props>();

function handleClick() {
  console.log("handleClick", props.data);
  if (props.click) {
    props.click();
  }
  if (props.data.type === "product" && props.data.barcode) {
    uni.navigateTo({
      url: `/pages/product/index?barcode=${encodeURIComponent(props.data.barcode)}`,
    });
  } else if (props.data.type === "ingredient") {
    uni.navigateTo({
      url: `/pages/ingredient-detail/index?ingredientId=${props.data.id}`,
    });
  }
}
</script>

<template>
  <view
    @click="handleClick"
    class="flex items-center gap-2.5 p-3 bg-card border border-border rounded-2xl"
  >
    <view
      class="w-12 h-12 rounded-xl bg-background flex items-center justify-center shrink-0 overflow-hidden"
    >
      <image
        :src="data.imageUrl"
        class="w-full h-full object-cover"
        mode="aspectFill"
      />
    </view>
    <view class="flex-1 min-w-0">
      <text class="text-sm font-semibold text-foreground truncate block">
        {{ data.name }}
      </text>
      <text class="text-xs text-muted-foreground mt-0.5 block">
        {{ data.subtitle }}
      </text>
      <view class="flex gap-1 mt-1 flex-wrap">
        <Tag variant="secondary" dclass=" rounded-sm">
          {{ data.type === "product" ? "食品" : "配料" }}
        </Tag>
        <RiskTag :level="data.riskLevel as RiskLevel" size="sm" />
      </view>
    </view>
    <DIcon name="arrow-right" dclass="text-muted-foreground/40 shrink-0" />
  </view>
</template>
