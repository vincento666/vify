import { get, post, put, del } from '@/utils/request'
import { hostFetch } from '@/host/request'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  enabled: number
  createdAt: string
  updatedAt: string
}

export interface KnowledgeDocument {
  id: number
  knowledgeBaseId: number
  name: string
  fileType: string
  fileSize: number
  status: 'PENDING' | 'PROCESSING' | 'DONE' | 'FAILED'
  errorMessage: string
  chunkCount: number
  createdAt: string
}

export interface ChunkVO {
  id: number
  documentId: number
  chunkIndex: number
  content: string
  tokenCount: number
}

export interface KnowledgeFaq {
  id: number
  knowledgeBaseId: number
  question: string
  answer: string
  alternativeQuestions: string[]
  keywords: string[]
  category: string
  priority: number
  enabled: boolean
  metadata: Record<string, unknown>
  source: string
  createdAt: string
  updatedAt: string
}

export interface RetrievalHit {
  sourceType: 'FAQ' | 'DOCUMENT_CHUNK' | string
  matchType: 'EXACT' | 'KEYWORD' | 'VECTOR' | 'HYBRID' | string
  score: number
  title: string
  content: string
  answer: string
  faqId: number
  documentId: number
  chunkId: number
  chunkIndex: number
  metadata: Record<string, unknown>
}

export type RetrievalMode = 'auto' | 'hybrid' | 'semantic' | 'keyword' | 'faq'

export interface RetrievalTestRequest {
  query: string
  topK?: number
  retrievalMode?: RetrievalMode
  scoreThreshold?: number
  rerank?: boolean
}

export interface RetrievalTestResult {
  query: string
  retrievalMode: RetrievalMode
  hits: RetrievalHit[]
}

export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export const createKb = (data: { name: string; description?: string }) =>
  post<KnowledgeBase>('/v1/knowledge-bases', data)

export const listKb = (params?: { page?: number; pageSize?: number; name?: string }) =>
  get<PageResult<KnowledgeBase>>('/v1/knowledge-bases', params)

export const getKb = (id: number) =>
  get<KnowledgeBase>(`/v1/knowledge-bases/${id}`)

export const updateKb = (id: number, data: { name?: string; description?: string; enabled?: number }) =>
  put<KnowledgeBase>(`/v1/knowledge-bases/${id}`, data)

export const deleteKb = (id: number) =>
  del<void>(`/v1/knowledge-bases/${id}`)

export const listDocuments = (kbId: number, params?: { page?: number; pageSize?: number }) =>
  get<PageResult<KnowledgeDocument>>(`/v1/knowledge-bases/${kbId}/documents`, params)

export const getDocument = (id: number) =>
  get<KnowledgeDocument>(`/v1/documents/${id}`)

export const deleteDocument = (id: number) =>
  del<void>(`/v1/documents/${id}`)

export const getChunks = (documentId: number) =>
  get<ChunkVO[]>(`/v1/documents/${documentId}/chunks`)

export const listFaqs = (kbId: number, params?: { page?: number; pageSize?: number }) =>
  get<PageResult<KnowledgeFaq>>(`/v1/knowledge-bases/${kbId}/faqs`, params)

export const createFaq = (kbId: number, data: Partial<KnowledgeFaq> & { question: string; answer: string }) =>
  post<KnowledgeFaq>(`/v1/knowledge-bases/${kbId}/faqs`, data)

export const updateFaq = (faqId: number, data: Partial<KnowledgeFaq>) =>
  put<KnowledgeFaq>(`/v1/knowledge-faqs/${faqId}`, data)

export const deleteFaq = (faqId: number) =>
  del<void>(`/v1/knowledge-faqs/${faqId}`)

export const retrievalTest = (kbId: number, data: RetrievalTestRequest) =>
  post<RetrievalTestResult>(`/v1/knowledge-bases/${kbId}/retrieval-test`, data)

export const uploadDocument = (kbId: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return hostFetch(`/v1/knowledge-bases/${kbId}/documents`, {
    method: 'POST',
    body: form,
  }).then(r => r.json()).then(res => {
    if (res.code !== 200) throw new Error(res.message)
    return res.data as KnowledgeDocument
  })
}

export const importFaqCsv = (kbId: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return hostFetch(`/v1/knowledge-bases/${kbId}/faqs/import-csv`, {
    method: 'POST',
    body: form,
  }).then(r => r.json()).then(res => {
    if (res.code !== 200) throw new Error(res.message)
    return res.data as { imported: number }
  })
}

export const exportFaqCsv = async (kbId: number) => {
  const response = await hostFetch(`/v1/knowledge-bases/${kbId}/faqs/export-csv`)
  if (!response.ok) throw new Error('导出失败')
  return response.text()
}
