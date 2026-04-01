import { useState, useEffect, useCallback } from 'react'
import { IngredientList } from '@/components/IngredientList'
import { IngredientDetailPanel } from '@/components/IngredientDetailPanel'
import { api } from '@/api/client'
import type { IngredientInfo, IngredientResponse } from '@/api/types'
import { useToast } from '@/hooks/use-toast'

export function IngredientsPage() {
  const [ingredients, setIngredients] = useState<IngredientInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<IngredientResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const { toast } = useToast()

  const fetchList = useCallback(async (name?: string) => {
    const res = await api.ingredients.list({ name, limit: 100, offset: 0 })
    setIngredients(res.items)
  }, [])

  const fetchDetail = useCallback(async (id: number) => {
    setDetailLoading(true)
    try {
      const res = await api.ingredients.get(id)
      setDetail(res)
    } catch {
      toast({ title: '获取详情失败', variant: 'destructive' })
    } finally {
      setDetailLoading(false)
    }
  }, [toast])

  useEffect(() => {
    api.ingredients.list({ limit: 100, offset: 0 })
      .then(res => setIngredients(res.items))
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = (id: number) => {
    setSelectedId(id)
    fetchDetail(id)
  }

  const handleSearch = (name: string) => {
    fetchList(name)
  }

  const handleTriggerAnalysis = async () => {
    if (!selectedId) return
    setAnalyzing(true)
    try {
      await api.ingredients.triggerAnalysis(selectedId)
      toast({ title: '分析任务已加入队列' })
    } catch (e) {
      toast({ title: '触发分析失败', description: (e as Error).message, variant: 'destructive' })
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-[360px] shrink-0 flex flex-col min-h-0">
        <IngredientList
          ingredients={ingredients}
          loading={loading}
          selectedId={selectedId}
          onSelect={handleSelect}
          onSearch={handleSearch}
        />
      </aside>
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <IngredientDetailPanel
          detail={detail}
          loading={detailLoading}
          analyzing={analyzing}
          onTriggerAnalysis={handleTriggerAnalysis}
        />
      </main>
    </div>
  )
}
