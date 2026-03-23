# Rpx 迁移规范 — width/height/padding/margin

> 2026-03-23

## 背景

各 .vue 组件中存在大量硬编码 rpx 值，尤其在 width、height、padding、margin 上。这些值应该统一使用 design-system.scss 中已定义的 CSS 变量，消除硬编码。

## 设计规则

### 1. Padding / Margin

**优先使用 `--space-*` 变量**（已在 design-system.scss 中定义）：

```css
--space-1: 4rpx   --space-2: 8rpx   --space-3: 12rpx   --space-4: 16rpx
--space-5: 20rpx  --space-6: 24rpx   --space-7: 28rpx   --space-8: 32rpx
--space-10: 40rpx --space-12: 48rpx  --space-14: 56rpx  --space-16: 64rpx
--space-20: 80rpx
```

### 2. Width / Height

**同样使用 `--space-*` 变量**，与 padding/margin 共用同一尺度。

### 3. 超出 `--space-*` 范围的值

**直接写 rpx 值**，不复建新变量。

当前超出 Tailwind CSS Spacing Scale（最大到 96 = 768rpx）的值：

| 值 | 场景 |
|----|------|
| `280rpx` | 配料卡片宽度 |
| `371rpx` | 某些容器宽度 |
| `520rpx` | Banner 高度（260px × 2） |
| 其他任意值 | 直接写 rpx |

### 4. 迁移示例

```scss
// Before
width: 280rpx;
height: 280rpx;
padding: 80rpx 48rpx 64rpx;

// After
width: 280rpx;  // 不在 space 列表，硬编码
height: 280rpx; // 不在 space 列表，硬编码
padding: var(--space-20) var(--space-12) var(--space-16);
```

### 5. 通用规则

- **border-width** 用 `1px`，不换算 rpx
- **`env(safe-area-inset-bottom)`** 保持原样，不转换
- **动画 transform 中的 px 值**保持原样，不影响响应式

## 实施

逐组件扫描并替换 width/height/padding/margin 中的硬编码 rpx 值，优先替换为 `--space-*`。
