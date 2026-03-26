# Skeleton 组件实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 Skeleton.vue 骨架屏组件，shadcn 风格，亮色/暗色自动适配

**Architecture:** 单文件 Vue 组件，使用 CSS shimmer 动画，亮暗色通过 `.dark` class 自动切换

**Tech Stack:** Vue 3 + UniApp + Tailwind CSS

---

## 文件结构

```
web/apps/uniapp-tw/src/components/ui/
└── Skeleton.vue    # 新建
```

---

## Task 1: 创建 Skeleton.vue

**文件:**
- 创建: `web/apps/uniapp-tw/src/components/ui/Skeleton.vue`

- [ ] **Step 1: 创建 Skeleton.vue**

```vue
<script setup lang="ts">
withDefaults(
  defineProps<{
    dclass?: string;
  }>(),
  {
    dclass: '',
  },
);
</script>

<template>
  <div :class="['skimmer', dclass]" />
</template>

<style lang="scss" scoped>
@keyframes skimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.skimmer {
  background: linear-gradient(
    90deg,
    theme("colors.gray.200") 25%,
    theme("colors.gray.100") 50%,
    theme("colors.gray.200") 75%
  );
  background-size: 200% 100%;
  animation: skimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
}

.dark .skimmer {
  background: linear-gradient(
    90deg,
    theme("colors.gray.800") 25%,
    theme("colors.gray.700") 50%,
    theme("colors.gray.800") 75%
  );
  background-size: 200% 100%;
}

@media (prefers-reduced-motion: reduce) {
  .skimmer {
    animation: none;
  }
}
</style>
```

**说明：**
- 使用 Tailwind dclass prop 传入宽度/高度/圆角等 class
- 亮色骨架色：`#e5e7eb` → `#f3f4f6` → `#e5e7eb`
- 暗色骨架色：`#1f2937` → `#374151` → `#1f2937`
- 动画名用 `skimmer` 避免与第三方冲突

- [ ] **Step 2: 提交**

```bash
cd /Users/wwj/Desktop/self/life-classics
git add web/apps/uniapp-tw/src/components/ui/Skeleton.vue
git commit -m "feat(uniapp-tw): add Skeleton component

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验收标准

- [ ] Skeleton.vue 已创建并位于 `components/ui/` 目录
- [ ] shimmer 动画从左向右扫过
- [ ] 暗色模式下骨架色自动切换（通过 `.dark .skeleton`）
- [ ] `prefers-reduced-motion` 环境下动画关闭
- [ ] `dclass` prop 可传入自定义 tailwind class
- [ ] git 已提交
