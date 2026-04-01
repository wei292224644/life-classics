import { useState, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'

interface IngredientInfo {
  id: number
  name: string
}

interface Props {
  ingredients: IngredientInfo[]
  loading: boolean
  selectedId: number | null
  onSelect: (id: number) => void
  onSearch: (name: string) => void
}

export function IngredientList({ ingredients, loading, selectedId, onSelect, onSearch }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query.trim()) return ingredients
    const q = query.toLowerCase()
    return ingredients.filter(i => i.name.toLowerCase().includes(q))
  }, [ingredients, query])

  const handleChange = (value: string) => {
    setQuery(value)
    onSearch(value)
  }

  return (
    <div className="flex flex-col h-full border-r border-border">
      <div className="p-3 border-b border-border">
        <Input
          placeholder="搜索配料..."
          value={query}
          onChange={e => handleChange(e.target.value)}
          className="h-8 text-sm bg-secondary"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-3 flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground text-center">
            {ingredients.length === 0 ? '暂无配料' : '无匹配结果'}
          </p>
        ) : (
          <div className="p-2 flex flex-col gap-1">
            {filtered.map(ing => (
              <button
                key={ing.id}
                onClick={() => onSelect(ing.id)}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm ${
                  selectedId === ing.id
                    ? 'bg-accent/20 border-l-2 border-accent'
                    : 'hover:bg-secondary'
                }`}
              >
                <span className="font-medium text-foreground break-words leading-snug">
                  {ing.name}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
