export interface DocumentInfo {
  doc_id: string
  title: string
  standard_no: string
  doc_type: string
  chunks_count: number
}

export interface ChunkMetadata {
  doc_id: string
  title: string
  standard_no: string
  doc_type: string
  semantic_type: string
  section_path: string   // pipe-separated, e.g. "1|1.1"
  raw_content: string
}

export interface Chunk {
  id: string
  content: string
  metadata: ChunkMetadata
}

export interface ChunksListResponse {
  chunks: Chunk[]
  total: number
  limit: number
  offset: number
}

export interface KBStats {
  total_chunks: number
  total_documents: number
  semantic_types: Record<string, number>
}

export interface UpdateChunkPayload {
  content: string
  semantic_type: string
  section_path: string   // slash-separated, e.g. "1/1.1"
}

export interface ConversationMessage {
  role: string
  content: string
}

export interface AgentChatRequest {
  message: string
  conversation_history?: ConversationMessage[]
  thread_id?: string
  agent_type?: string
}

export interface SearchResult {
  id: string
  content: string
  metadata?: Record<string, unknown>
  relevance_score?: number
  relevance_reason?: string
}

export interface AgentResponse {
  content: string
  sources: SearchResult[] | null
  tool_calls: Record<string, unknown>[] | null
}

export interface UpdateDocumentPayload {
  title?: string
  standard_no?: string
  doc_type?: string
}

export interface IngredientInfo {
  id: number
  name: string
}

export interface IngredientAnalysisResult {
  analysis_type: string
  result: string
  source: string | null
  level: string
  confidence_score: number
}

export interface RelatedProductSimple {
  id: number
  name: string
  barcode: string
  image_url: string | null
  category: string | null
}

export interface IngredientResponse {
  id: number
  name: string
  alias: string[]
  description: string | null
  is_additive: boolean
  additive_code: string | null
  standard_code: string | null
  who_level: string | null
  allergen_info: string[]
  function_type: string[]
  origin_type: string | null
  limit_usage: string | null
  legal_region: string | null
  cas: string | null
  applications: string | null
  notes: string | null
  safety_info: string | null
  analyses: IngredientAnalysisResult[]
  related_products: RelatedProductSimple[]
}
