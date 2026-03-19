export interface DocumentInfo {
  doc_id: string
  standard_no: string
  doc_type: string
  chunks_count: number
}

export interface ChunkMetadata {
  doc_id: string
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
