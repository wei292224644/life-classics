# 控制台单独删除文档 设计文档

## 背景

控制台（`web/apps/console/`）的文档列表目前只支持"清空所有文档"，无法单独删除某一个文档。后端已有 `DELETE /api/documents/{doc_id}` 接口，只需在前端实现调用。

---

## 改动一：`api/client.ts` — 新增 `delete` 方法

**文件：** `web/apps/console/src/api/client.ts`

在 `api.documents` 对象中新增：

```ts
delete: (doc_id: string) =>
  request<{ doc_id: string; errors: string[] }>(`/documents/${doc_id}`, { method: 'DELETE' }),
```

`DELETE /api/documents/{doc_id}` 后端返回 `{"doc_id": ..., "errors": []}` 或 HTTP 错误，现有 `request<T>` 函数已处理错误抛出。`errors` 数组非空时视为部分失败，`handleDeleteDoc` 中需检查并展示警告。

---

## 改动二：`DocList.tsx` — 删除按钮 + 确认弹窗

**文件：** `web/apps/console/src/components/DocList.tsx`

### Props 变更

新增 `onDelete` 回调和 `deletingDocId`：

```ts
interface Props {
  documents: DocumentInfo[]
  loading: boolean
  selectedDocId: string | null
  onSelect: (docId: string) => void
  onDelete: (docId: string) => Promise<void>   // 新增，返回 Promise 以便控制弹窗关闭
  deletingDocId: string | null                 // 新增，正在删除中的 doc_id
}
```

### UI 变更

每条文档 item 改为相对定位容器，右侧添加 `Trash2` 图标按钮：
- 默认隐藏，`group-hover` 时显示；当 `deletingDocId === doc.doc_id` 时显示 loading 旋转图标（`Loader2`）并禁用点击，防止重复触发
- 点击后弹出 `AlertDialog` 确认框（**受控模式**，每个 item 维护自己的 `open` state）：
  > 确认删除「{doc.title || doc.doc_id}」？此操作将删除该文档所有 chunks，无法撤销。
- 确认后：确认按钮进入 `disabled` 状态（防止重复点击），调用 `onDelete(doc_id)`，`onDelete` 完成后手动 `setOpen(false)` 关闭弹窗
- 取消则 `setOpen(false)`，不做任何操作

`Props` 新增 `deletingDocId: string | null`，由 `ChunksPage` 传入，用于控制 loading 状态。

确认弹窗使用 `@radix-ui/react-alert-dialog`（项目已有）。

---

## 改动三：`ChunksPage.tsx` — 实现删除逻辑

**文件：** `web/apps/console/src/pages/ChunksPage.tsx`

首先将现有 `useEffect` 内的文档加载逻辑提取为独立函数 `refreshDocuments`（静默刷新，不触发 `docsLoading`，避免列表闪烁），然后实现 `handleDeleteDoc`：

```ts
const refreshDocuments = useCallback(async () => {
  const { documents } = await api.documents.list()
  setDocuments(documents)
}, [])

const [deletingDocId, setDeletingDocId] = useState<string | null>(null)

const handleDeleteDoc = async (docId: string) => {
  setDeletingDocId(docId)
  try {
    const result = await api.documents.delete(docId)
    if (selectedDocId === docId) setSelectedDocId(null)
    await refreshDocuments()
    if (result.errors.length > 0) {
      toast({ title: '部分删除失败', description: result.errors.join('; '), variant: 'destructive' })
    } else {
      toast({ title: '已删除' })
    }
  } catch (e) {
    toast({ title: '删除失败', description: (e as Error).message, variant: 'destructive' })
  } finally {
    setDeletingDocId(null)
  }
}
```

将 `handleDeleteDoc` 和 `deletingDocId` 分别作为 `onDelete`、`deletingDocId` prop 传给 `<DocList>`。

---

## 不在范围内

- 批量选择删除
- 删除前展示 chunk 数量预览（AlertDialog 里只显示文档标题）
- 后端接口变更（已有 `DELETE /api/documents/{doc_id}`）
