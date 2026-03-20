import type {
  Chunk,
  ChunksListResponse,
  DocumentInfo,
  KBStats,
  UpdateChunkPayload,
  AgentChatRequest,
  AgentResponse,
} from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  documents: {
    list: () => request<{ documents: DocumentInfo[]; total: number }>('/documents'),
    clearAll: () =>
      request<{
        status: string
        deleted_documents: number
        deleted_chunks: number
      }>('/documents/clear', { method: 'DELETE' }),
    upload: async (
      file: File,
      onProgress: (stage: string, status: 'active' | 'done' | 'error') => void,
    ): Promise<{ chunks_count: number }> => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('strategy', 'text')

      const res = await fetch(`${BASE}/documents`, { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? `HTTP ${res.status}`)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE 事件以 \n\n 分隔
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part.split('\n').find(l => l.startsWith('data: '))
          if (!dataLine) continue
          const payload = JSON.parse(dataLine.slice(6))

          if (payload.type === 'stage') {
            onProgress(payload.stage, payload.status)
          } else if (payload.type === 'done') {
            return { chunks_count: payload.chunks_count }
          } else if (payload.type === 'error') {
            throw new Error(payload.message)
          }
        }
      }

      throw new Error('上传流意外结束')
    },
  },
  chunks: {
    list: (params: {
      doc_id?: string
      semantic_type?: string
      limit?: number
      offset?: number
    }) => {
      const q = new URLSearchParams()
      if (params.doc_id) q.set('doc_id', params.doc_id)
      if (params.semantic_type) q.set('semantic_type', params.semantic_type)
      q.set('limit', String(params.limit ?? 20))
      q.set('offset', String(params.offset ?? 0))
      return request<ChunksListResponse>(`/chunks?${q}`)
    },
    update: (chunk_id: string, payload: UpdateChunkPayload) =>
      request<Chunk>(`/chunks/${chunk_id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
  },
  kb: {
    stats: () => request<KBStats>('/kb/stats'),
  },
  agent: {
    chat: (payload: AgentChatRequest): Promise<AgentResponse> =>
      request<AgentResponse>('/agent/chat', { method: 'POST', body: JSON.stringify(payload) }),
  },
}
