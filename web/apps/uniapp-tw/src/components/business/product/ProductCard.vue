<script setup lang="ts">
import { getRiskConfig, riskCls, type RiskLevel } from "@/utils/riskLevel";
import { cn } from "@/utils/cn";
import DIcon from "@/components/ui/DIcon.vue";

interface Props {
  /** 食品或配料数据 */
  data: {
    type: "product" | "ingredient";
    id: number;
    name: string;
    subtitle: string;
    imageUrl?: string | null;
    riskLevel: string;
    highRiskCount?: number | null;
  };
  click?: () => void;
}

defineProps<Props>();
</script>

<template>
  <view
    class="w-12 h-12 rounded-xl bg-background flex items-center justify-center shrink-0 overflow-hidden"
    @click="click"
  >
    <image
      v-if="data.type === 'product' && data.imageUrl"
      :src="data.imageUrl"
      class="w-full h-full object-cover"
      mode="aspectFill"
    />
    <DIcon
      v-else
      :name="data.type === 'product' ? 'shopping-cart' : 'leaf'"
      dclass="text-muted-foreground"
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
      <view
        class="text-[10px] font-semibold px-1.5 py-0.5 rounded-md bg-secondary text-secondary-foreground"
      >
        {{ data.type === "product" ? "食品" : "配料" }}
      </view>
      <view
        v-if="data.type === 'ingredient' && data.riskLevel !== 'unknown'"
        :class="
          cn(
            'text-[10px] font-semibold px-1.5 py-0.5 rounded-md',
            riskCls(data.riskLevel as RiskLevel, 'bg/10 text'),
          )
        "
      >
        {{ getRiskConfig(data.riskLevel as RiskLevel).badge }}
      </view>
      <view
        v-if="data.type === 'product' && data.highRiskCount"
        class="text-[10px] font-semibold px-1.5 py-0.5 rounded-md bg-risk-t4/10 text-risk-t4"
      >
        高风险配料 ×{{ data.highRiskCount }}
      </view>
    </view>
  </view>
  <DIcon name="arrow-right" dclass="text-muted-foreground/40 shrink-0" />
</template>
