<script setup lang="ts">
import { watchEffect } from "vue";
import { useThemeStore } from "./store/theme";
import ToastContainer from "@/components/ui/ToastContainer.vue";

const themeStore = useThemeStore();

// 初始化主题 class 到 html 元素
themeStore.init();
watchEffect(() => {
  document.documentElement.classList.toggle("dark", themeStore.isDark);
});

onLaunch(() => {
  console.log("App Launch");
});
onShow(() => {
  console.log("App Show");
});
onHide(() => {
  console.log("App Hide");
});
</script>

<template>
  <ToastContainer />
</template>
