import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { api } from '@/api/client'
import type { SearchResult } from '@/api/types'
import { useToast } from '@/hooks/use-toast'
import type { LayoutContext } from '@/components/Layout'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResult[]
}

const LS_KEY = 'kb-chat-messages'

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Message[]
    // Ensure backward compatibility: add id if missing
    return parsed.map((m, i) => ({ ...m, id: m.id ?? `legacy-${i}` }))
  } catch {
    return []
  }
}

function saveMessages(msgs: Message[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(msgs))
}

export function ChatPage() {
  const { clearChatRef } = useOutletContext<LayoutContext>()
  const { toast } = useToast()

  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Register clear callback with Layout
  useEffect(() => {
    clearChatRef.current = () => {
      setMessages([])
      localStorage.removeItem(LS_KEY)
    }
    return () => {
      clearChatRef.current = null
    }
  }, [clearChatRef])

  // Persist messages to localStorage
  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isSending) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setIsSending(true)

    try {
      const res = await api.agent.chat({
        message: text,
        conversation_history: messages.map(m => ({ role: m.role, content: m.content })),
        thread_id: 'console-test',
      })
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.content,
        sources: res.sources ?? undefined,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      toast({ description: `发送失败: ${err instanceof Error ? err.message : String(err)}`, variant: 'destructive' })
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Message List */}
      <div className="flex-1 overflow-y-auto relative">
        {messages.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-muted-foreground gap-2">
            <span className="text-4xl">💬</span>
            <p className="text-base font-medium">开始与知识库对话</p>
            <p className="text-sm">提问关于 GB 标准的任何问题</p>
          </div>
        ) : (
          <div className="px-6 py-4 flex flex-col gap-4">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'user' ? (
                  <div
                    className="max-w-[70%] bg-purple-700 text-white text-sm px-4 py-2.5"
                    style={{ borderRadius: '12px 12px 2px 12px' }}
                  >
                    {msg.content}
                  </div>
                ) : (
                  <div className="max-w-[85%] flex flex-col gap-2">
                    <div className="bg-muted border border-border rounded-xl rounded-tl-sm px-4 py-3 text-sm prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <SourcesPanel sources={msg.sources} />
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border px-6 py-4 shrink-0 flex gap-3">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          rows={1}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行…"
          className="flex-1 resize-none bg-muted border border-border rounded-lg px-3 py-2 text-sm placeholder:text-muted-foreground disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-purple-600"
          style={{ minHeight: '40px', maxHeight: '120px' }}
          onInput={e => {
            const t = e.currentTarget
            t.style.height = 'auto'
            t.style.height = `${Math.min(t.scrollHeight, 120)}px`
          }}
        />
        <button
          onClick={() => void handleSend()}
          disabled={!input.trim() || isSending}
          className="bg-purple-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-600 transition-colors shrink-0"
        >
          {isSending ? '发送中…' : '发送'}
        </button>
      </div>
    </div>
  )
}

function SourcesPanel({ sources }: { sources: SearchResult[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="text-xs border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-muted/50 hover:bg-muted text-muted-foreground"
      >
        <span>📚 召回来源 · {sources.length} 个 chunk</span>
        <span className="ml-auto">{open ? '▲' : '▶'}</span>
      </button>
      {open && (
        <div className="flex flex-col divide-y divide-border">
          {sources.map(s => (
            <div key={s.id} className="px-3 py-2 text-muted-foreground">
              <span className="text-purple-400">{(s.metadata?.doc_id as string | undefined) ?? s.id}</span>
              {s.metadata?.section_path != null && <span> / {s.metadata.section_path as string}</span>}
              {s.relevance_score != null && (
                <span className="ml-2 text-muted-foreground/60">· {s.relevance_score.toFixed(2)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
