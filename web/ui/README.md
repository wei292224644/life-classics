# web/ui — 设计说明与静态原型

本目录**不是** pnpm workspace 中的可运行应用包，而是：

- **UI/UX 文字说明**（如健康助手聊天界面结构、色板、间距等）
- **静态 HTML 原型**，便于在浏览器中快速查看布局与样式

## 文件

| 文件 | 说明 |
|------|------|
| [health-chat.html](health-chat.html) | 健康助手聊天界面原型 |
| [font-detail.html](font-detail.html) | 字体/详情相关原型 |
| [ingredient-detail.html](ingredient-detail.html) | 配料等详情原型 |

可直接用浏览器打开上述 HTML。

## 与主工程的关系

线上功能由 **`web/apps/uniapp`**（小程序/H5）与 **`web/apps/console`**（管理台）实现；本目录仅作设计与演示参考，修改此处**不会**自动同步到各应用构建产物。
