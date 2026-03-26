# Empty 组件实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `Empty.vue` 空状态占位组件，支持图片或图标 + 文案布局

**Architecture:** 独立 UI 组件，挂载于 `web/apps/uniapp-tw/src/components/ui/`，与 `StateView` 正交

**Tech Stack:** Vue 3 Composition API + UniApp + Tailwind

---

## 文件结构

```
web/apps/uniapp-tw/src/components/ui/Empty.vue   # 新建
```

无现有文件修改，无测试文件（纯展示组件）。

---

## Task 1: 创建 Empty.vue 组件

**Files:**
- Create: `web/apps/uniapp-tw/src/components/ui/Empty.vue`

- [ ] **Step 1: 创建组件文件**

```vue
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
```

- [ ] **Step 2: 提交**

```bash
git add web/apps/uniapp-tw/src/components/ui/Empty.vue
git commit -m "feat(uniapp-tw): add Empty component for empty state placeholder"
```

---

## 自检清单

- [ ] Props 接口与 spec 一致（`image`、`icon`、`message`、`dclass`）
- [ ] `image` 优先渲染，`icon` 作为回退
- [ ] `DIcon` 使用 `dclass="text-[64rpx] text-muted-foreground opacity-60"`（通过 dclass 控制尺寸）
- [ ] 根容器 `gap-3`，文案 `text-xl text-muted-foreground text-center`
- [ ] `defineOptions({ virtualHost: true, addGlobalClass: true })` 与现有组件一致
- [ ] 使用 `cn` utility 合并 class
