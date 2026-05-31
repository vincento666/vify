import { get, post, put, del } from '@/utils/request'
import type { PageResult } from '@/api/knowledge'

export interface WorkflowListItem {
  id: number
  name: string
  description: string
  flowType: string
  status: string
  createdAt: string
  updatedAt: string
}

export interface WorkflowDetail {
  id: number
  name: string
  description: string
  flowType: string
  status: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  createdAt: string
  updatedAt: string
}

export interface WorkflowNode {
  nodeKey: string
  type: string
  name: string
  config: Record<string, any>
}

export interface WorkflowEdge {
  sourceNodeKey: string
  targetNodeKey: string
  condition: string | null
}

export interface WorkflowCreateRequest {
  name: string
  description?: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export function listWorkflows(params?: { page?: number; pageSize?: number; status?: string }) {
  return get<PageResult<WorkflowListItem>>('/v1/workflows', { page: 1, pageSize: 20, ...params })
}

export function getWorkflow(id: number) {
  return get<any>(`/v1/workflows/${id}`)
}

export function createWorkflow(data: WorkflowCreateRequest) {
  return post<any>('/v1/workflows', data)
}

export function updateWorkflow(id: number, data: Partial<WorkflowCreateRequest> & { status?: string }) {
  return put<any>(`/v1/workflows/${id}`, data)
}

export function runWorkflow(id: number, input: Record<string, any>) {
  return post<any>(`/v1/workflows/${id}/runs`, { input })
}

export function deleteWorkflow(id: number) {
  return del<any>(`/v1/workflows/${id}`)
}

export function listChatflows(params?: { page?: number; pageSize?: number; status?: string }) {
  return get<PageResult<WorkflowListItem>>('/v1/chatflows', { page: 1, pageSize: 20, ...params })
}

export function getChatflow(id: number) {
  return get<any>(`/v1/chatflows/${id}`)
}

export function createChatflow(data: WorkflowCreateRequest) {
  return post<any>('/v1/chatflows', data)
}

export function updateChatflow(id: number, data: Partial<WorkflowCreateRequest> & { status?: string }) {
  return put<any>(`/v1/chatflows/${id}`, data)
}

export function runChatflow(id: number, input: Record<string, any>) {
  return post<any>(`/v1/chatflows/${id}/runs`, { input })
}

export function deleteChatflow(id: number) {
  return del<any>(`/v1/chatflows/${id}`)
}
