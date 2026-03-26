<template>
  <view :style="{ height: statusBarHeight + 'px' }" />
</template>

<script setup lang="ts">
import { useSystemInfo } from "@/utils/system";

const { statusBarHeight } = useSystemInfo();
</script>
