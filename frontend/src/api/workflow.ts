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

export function runWorkflowV2(id: number, input: Record<string, any>, idempotencyKey?: string) {
  return post<any>(`/v1/workflows/${id}/runs-v2`, {
    input,
    ...(idempotencyKey ? { idempotencyKey } : {}),
  })
}

export function getWorkflowRunDebug(id: number, runId: number) {
  return get<any>(`/v1/workflows/${id}/runs/${runId}/debug`)
}

export function runPublishedWorkflow(id: number, input: Record<string, any>) {
  return post<any>(`/v1/workflows/${id}/published-runs`, { input })
}

export function publishWorkflowVersion(id: number) {
  return post<any>(`/v1/workflows/${id}/publish`, {})
}

export function listWorkflowVersions(id: number) {
  return get<{ list: any[]; total: number }>(`/v1/workflows/${id}/versions`)
}

export function rollbackWorkflowVersion(id: number, versionId: number) {
  return post<any>(`/v1/workflows/${id}/versions/${versionId}/rollback`, {})
}

export function runWorkflowNode(id: number, nodeKey: string, input: Record<string, any>) {
  return post<any>(`/v1/workflows/${id}/nodes/${encodeURIComponent(nodeKey)}/runs`, { input })
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

export function runChatflowV2(id: number, input: Record<string, any>, idempotencyKey?: string) {
  return post<any>(`/v1/chatflows/${id}/runs-v2`, {
    input,
    ...(idempotencyKey ? { idempotencyKey } : {}),
  })
}

export function getChatflowRunDebug(id: number, runId: number) {
  return get<any>(`/v1/chatflows/${id}/runs/${runId}/debug`)
}

export function runPublishedChatflow(id: number, input: Record<string, any>) {
  return post<any>(`/v1/chatflows/${id}/published-runs`, { input })
}

export function publishChatflowVersion(id: number) {
  return post<any>(`/v1/chatflows/${id}/publish`, {})
}

export function listChatflowVersions(id: number) {
  return get<{ list: any[]; total: number }>(`/v1/chatflows/${id}/versions`)
}

export function rollbackChatflowVersion(id: number, versionId: number) {
  return post<any>(`/v1/chatflows/${id}/versions/${versionId}/rollback`, {})
}

export function resumeChatflowRun(
  id: number,
  runId: number,
  data: { eventId?: number; resumeData: Record<string, any>; idempotencyKey?: string },
) {
  return post<any>(`/v1/chatflows/${id}/runs/${runId}/resume`, data)
}

export function getChatflowSession(id: number, sessionId: string) {
  return get<any>(`/v1/chatflows/${id}/sessions/${encodeURIComponent(sessionId)}`)
}

export function listChatflowRunEvents(id: number, runId: number) {
  return get<{ list: any[]; total: number }>(`/v1/chatflows/${id}/runs/${runId}/events`)
}

export function getRuntimeV2Run(runId: number) {
  return get<any>(`/v1/runtime-runs/${runId}`)
}

export function listRuntimeV2Events(runId: number, params?: { afterSequence?: number }) {
  return get<{ list: any[]; total: number }>(`/v1/runtime-runs/${runId}/events`, params)
}

export function listRuntimeV2Nodes(runId: number) {
  return get<{ list: any[]; total: number }>(`/v1/runtime-runs/${runId}/nodes`)
}

export function listChatflowChannels(id: number) {
  return get<{ list: any[]; total: number }>(`/v1/chatflows/${id}/channels`)
}

export function updateChatflowChannel(id: number, channelId: string, data: Record<string, any>) {
  return put<any>(`/v1/chatflows/${id}/channels/${encodeURIComponent(channelId)}`, data)
}

export function testChatflowChannel(id: number, channelId: string, data: Record<string, any>) {
  return post<any>(`/v1/chatflows/${id}/channels/${encodeURIComponent(channelId)}/test`, data)
}

export function runChatflowNode(id: number, nodeKey: string, input: Record<string, any>) {
  return post<any>(`/v1/chatflows/${id}/nodes/${encodeURIComponent(nodeKey)}/runs`, { input })
}

export function deleteChatflow(id: number) {
  return del<any>(`/v1/chatflows/${id}`)
}

export function listWorkflowResources(params?: { flowType?: string }) {
  return get<{ list: any[]; total: number }>('/v1/workflow-resources', { flowType: 'WORKFLOW', ...params })
}

export interface ApiResourcePayload {
  name: string
  description?: string
  method: string
  endpoint: string
  authMode?: string
  headers?: Array<Record<string, any>> | Record<string, any>
  bodyTemplate?: string
  inputSchema?: Record<string, any>
  outputSchema?: Record<string, any>
  timeoutMs?: number
  testPayload?: Record<string, any>
  enabled?: boolean
}

export function listApiResources(params?: { page?: number; pageSize?: number; enabled?: boolean }) {
  return get<{ list: any[]; total: number; page: number; pageSize: number }>('/v1/api-resources', {
    page: 1,
    pageSize: 20,
    ...params,
  })
}

export function createApiResource(data: ApiResourcePayload) {
  return post<any>('/v1/api-resources', data)
}

export function testApiResourceCall(id: number, input: Record<string, any>) {
  return post<any>(`/v1/api-resources/${id}/test-call`, { input })
}

export interface ApiToolPayload {
  name: string
  displayName?: string
  description?: string
  adapterType: 'API_RESOURCE'
  apiResourceId: number
  inputSchema?: Record<string, any>
  outputSchema?: Record<string, any>
  modelCallable?: boolean
  enabled?: boolean
  timeoutMs?: number
  retryCount?: number
  errorBehavior?: string
}

export function listApiTools(params?: { page?: number; pageSize?: number; adapterType?: string; modelCallable?: boolean; enabled?: boolean }) {
  return get<{ list: any[]; total: number; page: number; pageSize: number }>('/v1/tools', {
    page: 1,
    pageSize: 20,
    ...params,
  })
}

export function createApiTool(data: ApiToolPayload) {
  return post<any>('/v1/tools', data)
}
