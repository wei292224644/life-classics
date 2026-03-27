<template>
  <view class="w-full">
    <view v-if="withHeader" class="h-topbar bg-root shadow-md mb-3 flex items-center px-3 gap-2">
      <Skeleton dclass="w-6 h-6" />
      <Skeleton dclass="w-12 h-6" />
    </view>
    <view class="flex flex-col gap-4 w-full px-3">
      <template v-for="i in 2" :key="i">
        <Card>
          <view class="flex items-center justify-between">
            <Skeleton dclass="w-1/2 h-6" />
            <Skeleton dclass="w-14 h-6" />
          </view>
          <Skeleton dclass="w-1/3 h-4 mt-2 " />
          <Skeleton dclass="w-2/3 h-2 mt-6 " />
          <Skeleton dclass="w-full h-4 mt-2 " />
          <Skeleton dclass="w-2/3 h-4 mt-2 " />
        </Card>
      </template>
    </view>
  </view>
</template>
<script setup lang="ts">
import Skeleton from "@/components/ui/Skeleton.vue";
import Card from "@/components/ui/card/Card.vue";

withDefaults(defineProps<{ withHeader?: boolean }>(), { withHeader: true });
</script>
