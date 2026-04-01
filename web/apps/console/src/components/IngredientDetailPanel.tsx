import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { IngredientResponse } from '@/api/types'

interface Props {
  detail: IngredientResponse | null
  loading: boolean
  analyzing: boolean
  onTriggerAnalysis: () => void
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="text-muted-foreground shrink-0 w-28">{label}</span>
      <span className="text-foreground">{value ?? '—'}</span>
    </div>
  )
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border p-4 space-y-3">
      <h3 className="font-medium text-sm text-foreground">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

export function IngredientDetailPanel({ detail, loading, analyzing, onTriggerAnalysis }: Props) {
  if (!detail && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        选择配料查看详情
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!detail) return null

  const latestAnalysis = detail.analyses[0]

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* 基本信息 */}
      <InfoCard title="基本信息">
        <InfoRow label="名称" value={detail.name} />
        <InfoRow label="是否添加剂" value={detail.is_additive ? '是' : '否'} />
        <InfoRow label="添加剂编码" value={detail.additive_code} />
        <InfoRow label="功能类型" value={detail.function_type?.join('、')} />
        <InfoRow label="来源类型" value={detail.origin_type} />
        <InfoRow label="限用量" value={detail.limit_usage} />
        <InfoRow label="CAS 号" value={detail.cas} />
        <InfoRow label="安全信息" value={detail.safety_info} />
      </InfoCard>

      {/* 分析结果 */}
      <InfoCard title="分析结果">
        {latestAnalysis ? (
          <>
            <InfoRow label="风险等级" value={latestAnalysis.level} />
            <InfoRow label="评估结果" value={latestAnalysis.result} />
            <InfoRow label="置信度" value={latestAnalysis.confidence_score} />
            <InfoRow label="来源" value={latestAnalysis.source} />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">暂无分析数据</p>
        )}
      </InfoCard>

      {/* 触发分析 */}
      <div className="flex justify-end">
        <Button onClick={onTriggerAnalysis} disabled={analyzing}>
          {analyzing && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          触发分析
        </Button>
      </div>
    </div>
  )
}
