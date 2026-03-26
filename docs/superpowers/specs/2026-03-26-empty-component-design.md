# Empty 组件设计规格

## 1. 组件定位

- **职责**：纯空状态占位（列表为空、搜索无结果、页面暂无数据等）
- **与其他组件关系**：与 `StateView` 正交，`StateView` 管理多状态切换，`Empty` 只负责 empty 这一单个状态的展示

## 2. Props 接口

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `image` | `string` | `""` | 空状态图片 URL（优先渲染） |
| `icon` | `IconName` | `"search"` | 空状态图标（无 image 时回退） |
| `message` | `string` | `"暂无数据"` | 空状态文案 |
| `dclass` | `string` | `""` | 根容器自定义 class |

## 3. 渲染逻辑

- 有 `image` → 渲染 uniapp `image` 标签（`mode="aspectFit"`，高度 200rpx）
- 无 `image` → 渲染 `DIcon`（`size` 64rpx，`opacity-60`）

## 4. 视觉规范

### 布局
- 根容器：`flex flex-col items-center justify-center gap-3`

### 图片
- 高度 200rpx，`mode="aspectFit"`，居中

### 图标回退
- `DIcon`，`size` 64rpx，透明度 `opacity-60`，颜色 `text-muted-foreground`

### 文案
- `text-xl text-muted-foreground text-center`

## 5. 小程序 / UniApp 适配

- 根容器用 `view`
- 文字用 `text` 节点
- 图片用 uniapp `image` 组件
- 动画仅 `transform` + `opacity`

## 6. 组件文件

- 路径：`web/apps/uniapp-tw/src/components/ui/Empty.vue`
