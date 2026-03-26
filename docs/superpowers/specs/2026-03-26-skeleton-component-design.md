# Skeleton 组件设计

## 1. 背景

当前 `StateView` 组件使用中心 Spinner 展示加载态，页面完全空白，用户感知差。
需要新增 Skeleton 骨架屏组件，提前渲染内容结构占位符，数据回来后渐变过渡。

## 2. 设计方案

### 2.1 组件清单

| 组件 | 文件 | 说明 |
|------|------|------|
| `Skeleton` | `components/ui/Skeleton.vue` | 基础骨架单元 |
| `SkeletonBlock` | `components/ui/SkeletonBlock.vue` | 整块骨架区（Card 内使用） |
| `SkeletonText` | `components/ui/SkeletonText.vue` | 文本行骨架，支持多行 |

### 2.2 Skeleton（基础单元）

**Props：**

| prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | `string \| number` | `'100%'` | 宽度 |
| `height` | `string \| number` | `16` | 高度（px） |
| `radius` | `string \| number` | `6` | 圆角（px） |
| `dclass` | `string` | `''` | 自定义 tailwind class |

**行为：**
- 灰色占位块 + 微光动画（shimmer）
- 亮色/暗色自动适配

### 2.3 SkeletonText（文本骨架）

**Props：**

| prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lines` | `number` | `3` | 行数 |
| `lastLineWidth` | `string \| number` | `'60%'` | 最后一行宽度 |

**行为：**
- 渲染 `lines` 个 Skeleton，最后一行宽度缩小
- 常用于段落描述区域

### 2.4 SkeletonBlock（卡片骨架）

**Props：**

| prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dclass` | `string` | `''` | 自定义 tailwind class |

**行为：**
- 模拟 `Card` 组件的内边距和结构
- 内含 Hero 骨架 + 描述区骨架 + 分析区骨架

### 2.5 动画规范

```css
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    var(--muted) 25%,
    var(--secondary) 50%,
    var(--muted) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
```

- 曲线：`ease-in-out`
- 时长：1.5s
- 尊重 `prefers-reduced-motion`

### 2.6 暗色模式

| Token | 亮色 | 暗色 |
|-------|------|------|
| 骨架底色 | `#e5e7eb` | `#1f2937` |
| 骨架动画色 | `#f3f4f6` | `#374151` |

### 2.7 StateView 扩展（后续）

`StateView` 后续增加 `skeleton` 状态，内部渲染 SkeletonBlock 而非 Spinner。
本次不实现，留作后续任务。

## 3. 实施范围（本期）

1. `Skeleton.vue` — 基础骨架单元
2. `SkeletonText.vue` — 文本行骨架
3. `SkeletonBlock.vue` — 卡片内容骨架
4. 设计 spec 写入 `docs/superpowers/specs/`
5. ingredient-detail 页面接入 SkeletonBlock 演示（可选）

## 4. 设计稿（亮色 / 暗色并排）

```
┌──────────────────┬──────────────────┐
│   亮色模式        │   暗色模式        │
├──────────────────┼──────────────────┤
│ [██████████████] │ [██████████████] │
│ [███      ████]  │ [███      ████]  │
│ [███      ████]  │ [███      ████]  │
│ [██████████████] │ [██████████████] │
│ [██████        ] │ [██████        ] │
└──────────────────┴──────────────────┘
```

（骨架块带 shimmer 动画，从左向右扫过）

## 5. 文件结构

```
components/ui/
├── Skeleton.vue        # 基础骨架单元
├── SkeletonText.vue    # 文本行骨架
├── SkeletonBlock.vue   # 卡片内容骨架
└── StateView.vue       # [后续] 增加 skeleton 状态
```

## 6. 验收标准

- [ ] Skeleton 组件亮色/暗色均有正确视觉
- [ ] shimmer 动画流畅，不卡顿
- [ ] 尊重 `prefers-reduced-motion`（关闭动画）
- [ ] 与现有 `Card` 组件结构对齐
- [ ] 组件可被 `StateView` 后续调用
