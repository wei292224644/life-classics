# ingredient-detail 页面重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `ingredient-detail/index.vue` 重构为使用 `Screen` 组件 + Tailwind 类，移除 ~300 行自定义 SCSS，完美还原设计稿 `03-ingredient-detail.html`。

**Architecture:**
- 主布局：使用 `Screen` 组件（header/content/footer slots）
- Header：sticky 定位，风险等级动态背景色
- 样式：Tailwind 类 + 设计系统 CSS 变量 + 少量 scoped SCSS（所有样式内联在 index.vue 中，不修改 style.scss）

**Tech Stack:** Vue 3 + UniApp + Tailwind CSS + SCSS

---

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` | 完全重写 |

---

## Task 1: 重写 ingredient-detail/index.vue

**Files:**
- Modify: `web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue` (完全重写)

- [ ] **Step 1: 保留 script setup 部分（逻辑层不变）**

保留现有的：
- 所有 `import` 语句
- `onLoad` 逻辑
- Store 使用（`ingStore`, `productStore`, `themeStore`）
- 所有 `computed` 属性
- `goBack`, `shareToFriend`, `goToAI`, `goToSearch`, `goToProduct` 函数
- `safeResults`, `extractText` 工具函数

修改部分：
- `heroEmoji` 相关逻辑保留（用于相关产品卡片），但 Hero 卡本身不使用 emoji

- [ ] **Step 2: 重写 template 结构**

新结构：
```vue
<template>
  <Screen>
    <!-- Header Slot -->
    <template #header>
      <view class="sticky top-0 z-10 flex items-center gap-2.5 px-3.5 py-3 h-16 transition-all duration-300 ing-hdr">
        <button class="ing-hdr-btn w-[30px] h-[30px] rounded-[9px] flex items-center justify-center flex-shrink-0" @click="goBack">
          <Icon name="arrowLeft" :size="22" />
        </button>
        <view class="flex-1 flex flex-col">
          <text class="ing-hdr-title text-[14px] font-bold">
            {{ ingredient?.name ?? "配料详情" }}
          </text>
          <text class="ing-hdr-sub text-[10px] font-semibold mt-px">
            {{ headerSubtitle }}
          </text>
        </view>
        <button class="ing-hdr-btn w-[30px] h-[30px] rounded-[9px] flex items-center justify-center flex-shrink-0" @click="shareToFriend">
          <Icon name="share" :size="22" />
        </button>
      </view>
    </template>

    <!-- Content Slot -->
    <template #content>
      <view class="px-3 pt-0 bg-background">
        <!-- 加载态 -->
        <view v-if="isLoading" class="flex-1 flex items-center justify-center py-20">
          <text class="text-xl text-muted-foreground">加载中...</text>
        </view>

        <!-- 无数据错误态 -->
        <view
          v-else-if="!ingredient"
          class="flex-1 flex flex-col items-center justify-center gap-8 px-12 py-20"
        >
          <text class="text-xl text-secondary text-center">数据加载失败，请返回重试</text>
          <button class="px-12 py-5 rounded-xl bg-card border border-border text-foreground text-xl" @click="goBack">
            返回
          </button>
        </view>

        <!-- 内容区 -->
        <view v-else class="flex flex-col gap-3 pb-3">

          <!-- 1. Hero 风险卡（无 emoji） -->
          <view class="sec-card overflow-hidden">
            <view
              class="hero-top p-3"
              :class="[`hero-top-${riskConf.visualKey}`, themeStore.isDark ? 'dark' : 'light']"
            >
              <view class="flex items-start justify-between mb-2">
                <view>
                  <view class="text-[18px] font-extrabold text-foreground">
                    {{ ingredient.name }}
                  </view>
                  <view class="text-[11px] mt-0.5 text-muted-foreground">
                    {{ ingredient.additive_code || "食品添加剂" }}
                  </view>
                </view>
                <view
                  class="px-[9px] py-1 rounded-[7px] text-[11px] font-bold flex items-center gap-1 flex-shrink-0 text-white"
                  :style="{ background: `var(--color-risk-${ingredient.analysis?.level ?? 'unknown'})` }"
                >
                  <Icon name="alertTriangle" :size="12" class="text-white" />
                  {{ riskConf.badge }}
                </view>
              </view>

              <!-- 风险谱条 -->
              <view class="relative" style="margin: 4px 0 4px">
                <view class="h-[7px] rounded-full" style="background: linear-gradient(to right, #22c55e 0%, #86efac 20%, #facc15 45%, #fb923c 65%, #ef4444 82%, #dc2626 100%)" />
                <view
                  v-if="riskConf.needleLeft !== null"
                  class="absolute top-1/2 -translate-y-1/2 w-[14px] h-[14px] rounded-full bg-[var(--color-card)] border-[2.5px]"
                  :style="{
                    right: `${100 - parseFloat(riskConf.needleLeft) - 4}%`,
                    borderColor: `var(--color-risk-${ingredient.analysis?.level ?? 'unknown'})`,
                    boxShadow: '0 2px 6px rgba(220,38,38,0.35)'
                  }"
                />
              </view>
              <view class="flex justify-between text-[9px] px-0.5 text-muted-foreground">
                <span>低风险</span><span>中等</span><span>高风险</span>
              </view>
            </view>

            <!-- Chips 行 -->
            <view class="flex flex-wrap gap-[5px] p-3">
              <text v-if="ingredient.function_type" class="chip-red text-[10.5px] font-medium px-2 py-0.5 rounded-md">
                {{ ingredient.function_type }}
              </text>
              <text v-if="source" class="chip-neu text-[10.5px] font-medium px-2 py-0.5 rounded-md">
                {{ source }}
              </text>
              <text v-if="pregnancyWarning" class="chip-warn text-[10.5px] font-medium px-2 py-0.5 rounded-md">
                ⚠ {{ pregnancyWarning }}
              </text>
              <template v-if="ingredient.alias?.length">
                <text v-for="alias in ingredient.alias" :key="alias" class="chip-neu text-[10.5px] font-medium px-2 py-0.5 rounded-md">
                  别名：{{ alias }}
                </text>
              </template>
            </view>
          </view>

          <!-- 2. 描述卡片（无 AI 标签） -->
          <view v-if="summary" class="sec-card">
            <view class="flex items-center gap-2 px-3 py-[11px] border-b border-border">
              <view class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style="background: #eff6ff">
                <Icon name="info" :size="14" class="text-[#3b82f6]" />
              </view>
              <h3 class="text-[13px] font-bold text-foreground">描述</h3>
            </view>
            <view class="px-3 py-[11px]">
              <p class="text-[12px] leading-[1.7] text-secondary">
                {{ summary }}
              </p>
            </view>
          </view>

          <!-- 3. AI 风险分析卡片 -->
          <view v-if="riskFactors.length > 0" class="sec-card">
            <view class="flex items-center gap-2 px-3 py-[11px] border-b border-border">
              <view class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 risk-factor-icon">
                <Icon name="alertTriangle" :size="14" />
              </view>
              <h3 class="text-[13px] font-bold flex-1 text-foreground">AI 风险分析</h3>
              <span class="ai-label ml-auto">AI</span>
            </view>
            <view class="px-3 py-[11px] flex flex-col gap-2">
              <view v-for="(item, i) in riskFactors" :key="i" class="flex items-start gap-2">
                <view class="risk-factor-icon w-[18px] h-[18px] rounded-[5px] flex items-center justify-center flex-shrink-0 mt-px">
                  <Icon name="x" :size="12" />
                </view>
                <span class="text-[12px] leading-[1.55] flex-1 text-foreground">
                  {{ item }}
                </span>
              </view>
            </view>
          </view>

          <!-- 4. 风险管理信息卡片 -->
          <view v-if="hasRiskMgmt" class="sec-card">
            <view class="flex items-center gap-2 px-3 py-[11px] border-b border-border">
              <view class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style="background: #eff6ff">
                <Icon name="shield" :size="14" class="text-[#3b82f6]" />
              </view>
              <h3 class="text-[13px] font-bold flex-1 text-foreground">风险管理信息</h3>
            </view>
            <view class="flex flex-col">
              <view v-if="ingredient.who_level" class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">WHO 致癌等级</span>
                <span class="text-[11.5px] font-medium text-[var(--color-risk-t4)]">{{ ingredient.who_level }}</span>
              </view>
              <view v-if="maternalLevel" class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">母婴等级</span>
                <span class="text-[11.5px] font-medium text-[var(--color-risk-t4)]">{{ maternalLevel }}</span>
              </view>
              <view v-if="ingredient.allergen_info" class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">过敏信息</span>
                <span class="text-[11.5px] font-medium flex-1 text-right text-foreground">{{ ingredient.allergen_info }}</span>
              </view>
              <view v-if="usageLimit" class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">使用限量</span>
                <span class="text-[11.5px] font-medium flex-1 text-right text-foreground">{{ usageLimit }}</span>
              </view>
              <view v-if="applicableRegion" class="flex justify-between items-start py-[9px] px-3 gap-2.5 border-b border-border">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">适用区域</span>
                <span class="text-[11.5px] font-medium flex-1 text-right text-foreground">{{ applicableRegion }}</span>
              </view>
              <view v-if="ingredient.standard_code" class="flex justify-between items-start py-[9px] px-3 gap-2.5">
                <span class="text-[11.5px] flex-shrink-0 text-secondary">执行标准</span>
                <span class="text-[11.5px] font-medium flex-1 text-right text-foreground">{{ ingredient.standard_code }}</span>
              </view>
            </view>
          </view>

          <!-- 5. AI 使用建议卡片 -->
          <view v-if="suggestions.length > 0" class="sec-card">
            <view class="flex items-center gap-2 px-3 py-[11px] border-b border-border">
              <view class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style="background: rgba(236,72,153,0.15)">
                <Icon name="star" :size="14" class="text-[var(--accent-pink-light)]" />
              </view>
              <h3 class="text-[13px] font-bold flex-1 text-foreground">AI 使用建议</h3>
              <span class="ai-label ml-auto">AI</span>
            </view>
            <view class="px-3 py-[11px] flex flex-col gap-2">
              <view v-for="(s, i) in suggestions" :key="i" class="flex items-start gap-2">
                <view
                  class="w-[18px] h-[18px] rounded-[5px] flex items-center justify-center flex-shrink-0 mt-px"
                  :class="s.type === 'positive' ? 'dot-good' : 'dot-warn'"
                >
                  <Icon name="check" :size="12" />
                </view>
                <span class="text-[12px] leading-[1.55] flex-1 text-foreground">
                  {{ s.text }}
                </span>
              </view>
            </view>
          </view>

          <!-- 6. 含此配料的产品卡片 -->
          <view v-if="relatedProducts.length > 0" class="sec-card">
            <view class="flex items-center gap-2 px-3 py-[11px] border-b border-border">
              <view class="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style="background: #eff6ff">
                <Icon name="shoppingCart" :size="14" class="text-[#3b82f6]" />
              </view>
              <h3 class="text-[13px] font-bold flex-1 text-foreground">含此配料的产品</h3>
            </view>
            <scroll-view scroll-x enable-flex class="overflow-x-auto" style="scrollbar-width: none">
              <view class="flex gap-2 p-3" style="width: max-content">
                <view
                  v-for="p in relatedProducts"
                  :key="p.id"
                  class="w-[86px] flex-shrink-0 rounded-xl p-2 cursor-pointer bg-background border border-border"
                  @click="goToProduct(p.barcode)"
                >
                  <view class="w-full h-12 rounded-lg flex items-center justify-center text-[20px] mb-1.5 bg-card">
                    {{ p.emoji }}
                  </view>
                  <view class="text-[10px] font-semibold leading-[1.3] mb-1 line-clamp-2 text-foreground">
                    {{ p.name }}
                  </view>
                  <text
                    v-if="p.riskTag"
                    class="text-[9px] font-medium px-[5px] py-px rounded"
                    :class="p.riskTag === '高风险' ? 'chip-red' : 'chip-warn'"
                  >
                    {{ p.riskTag }}
                  </text>
                </view>
              </view>
            </scroll-view>
          </view>

          <!-- 底部安全距离 -->
          <view class="h-[180rpx]" />
        </view>
      </view>
    </template>

    <!-- Footer Slot -->
    <template #footer>
      <view v-if="ingredient" class="bot-bar px-3 py-2 flex gap-2 h-16">
        <button
          class="btn-out flex-1 rounded-xl py-3 text-[12px] font-semibold text-center active:scale-[0.97]"
          @click="goToAI"
        >
          咨询 AI 助手
        </button>
        <button
          class="flex-1 rounded-xl py-3 text-[12px] font-semibold text-white text-center active:scale-[0.97]"
          style="background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink)); box-shadow: 0 4px 12px rgba(225,29,72,0.3)"
          @click="goToSearch"
        >
          查看相关食品
        </button>
      </view>
    </template>
  </Screen>
</template>
```

- [ ] **Step 3: 重写 scoped style（包含所有 CSS）**

删除原有的 ~300 行自定义 SCSS，替换为：

```scss
<style lang="scss" scoped>
// ── AI 标签渐变文字 ──────────────────────────────────────
.ai-label {
  font-size: 9.5px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-pink-light), var(--accent-pink));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

// ── Chips ─────────────────────────────────────────────────
.chip-red {
  .light & {
    background: #fff0f0;
    color: #dc2626;
    border: 1px solid #fecaca;
  }
  .dark & {
    background: #450a0a;
    color: #fca5a5;
    border: 1px solid transparent;
  }
}

.chip-warn {
  .light & {
    background: #fefce8;
    color: #a16207;
    border: 1px solid #fde68a;
  }
  .dark & {
    background: #3b1a00;
    color: #fcd34d;
    border: 1px solid transparent;
  }
}

.chip-neu {
  .light & {
    background: rgba(0, 0, 0, 0.04);
    color: #4b5563;
  }
  .dark & {
    background: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.6);
  }
}

// ── 建议项图标背景 ──────────────────────────────────────
.dot-good {
  .light & {
    background: #f0fdf4;
    svg { fill: #22c55e; }
  }
  .dark & {
    background: #052e16;
    svg { fill: #4ade80; }
  }
}

.dot-warn {
  .light & {
    background: #fffbeb;
    svg { fill: #f59e0b; }
  }
  .dark & {
    background: #3b1a00;
    svg { fill: #fbbf24; }
  }
}

// ── 风险因素项图标 ──────────────────────────────────────
.risk-factor-icon {
  .light & {
    background: #450a0a;
    svg { fill: #fca5a5; }
  }
  .dark & {
    background: #450a0a;
    svg { fill: #fca5a5; }
  }
}

// ── Section 卡片 ─────────────────────────────────────────
.sec-card {
  .light & {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  }
  .dark & {
    background: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    overflow: hidden;
  }
}

// ── 底部栏 ──────────────────────────────────────────────
.bot-bar {
  .light & {
    background: rgba(255, 255, 255, 0.98);
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }
  .dark & {
    background: rgba(26, 26, 26, 0.98);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
}

.btn-out {
  .light & {
    background: transparent;
    border: 1px solid rgba(0, 0, 0, 0.08);
    color: var(--foreground);
  }
  .dark & {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--foreground);
  }
}

// ── Ingredient Header ────────────────────────────────────
.ing-hdr {
  .light & {
    background: #fff4f0;
    border-bottom: 2px solid #fecaca;
  }
  .dark & {
    background: #1a0808;
    border-bottom: 2px solid #7f1d1d;
  }
}

.ing-hdr-title {
  .light & { color: #7f1d1d; }
  .dark & { color: #fca5a5; }
}

.ing-hdr-sub {
  .light & { color: #ef4444; }
  .dark & { color: #f87171; }
}

.ing-hdr-btn {
  .light & {
    background: rgba(220, 38, 38, 0.1);
    svg { stroke: #ef4444; }
  }
  .dark & {
    background: rgba(248, 113, 113, 0.15);
    svg { stroke: #f87171; }
  }
}

// ── Hero Top 渐变背景（按风险等级） ─────────────────────
.hero-top {
  min-height: 200rpx;
}

// t4 极高分险 (= critical)
.hero-top-t4,
.hero-top-critical {
  .light & {
    background: linear-gradient(135deg, rgba(255, 244, 240, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fecaca;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(26, 8, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #7f1d1d;
  }
}

// t3 高风险 (= high)
.hero-top-t3,
.hero-top-high {
  .light & {
    background: linear-gradient(135deg, rgba(255, 244, 240, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fecaca;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(26, 8, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #7f1d1d;
  }
}

// t2 中等风险
.hero-top-t2 {
  .light & {
    background: linear-gradient(135deg, rgba(255, 251, 235, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #fde68a;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(26, 20, 8, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #78350f;
  }
}

// t1 低风险
.hero-top-t1 {
  .light & {
    background: linear-gradient(135deg, rgba(240, 253, 244, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #bbf7d0;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(5, 20, 10, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #166534;
  }
}

// t0 安全
.hero-top-t0 {
  .light & {
    background: linear-gradient(135deg, rgba(240, 253, 244, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #bbf7d0;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(5, 20, 10, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #166534;
  }
}

// unknown
.hero-top-unknown {
  .light & {
    background: linear-gradient(135deg, rgba(245, 245, 245, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #e5e7eb;
  }
  .dark & {
    background: linear-gradient(135deg, rgba(20, 20, 20, 0.6) 0%, transparent 100%);
    border-bottom: 1px solid #374151;
  }
}

// ── 其他 ──────────────────────────────────────────────
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
```

- [ ] **Step 4: 验证编译**

运行: `cd web && pnpm dev:uniapp:h5`
预期: 无编译错误，页面正常显示

- [ ] **Step 5: 提交**

```bash
git add web/apps/uniapp-tw/src/pages/ingredient-detail/index.vue
git commit -m "refactor(uniapp-tw): rewrite ingredient-detail with Screen component and Tailwind"
```

---

## 验证清单

- [ ] `Screen` 组件正常渲染 header/content/footer slots
- [ ] Header sticky 定位正常，风险等级背景色动态变化
- [ ] Hero 风险卡无 emoji，渐变背景正确
- [ ] 「描述」卡片无 AI 标签
- [ ] 「AI 风险分析」「AI 使用建议」卡片有 AI 标签
- [ ] 底部栏按钮为「咨询 AI 助手」+「查看相关食品」
- [ ] 亮色/暗色模式切换正常
- [ ] 所有 Tailwind 类正确应用
- [ ] 无编译警告/错误
