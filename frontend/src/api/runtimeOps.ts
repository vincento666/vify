import { get, post } from '@/utils/request'

export interface RuntimeOpsRunListQuery {
  ownerType?: string
  state?: string
  tenantId?: string
  createdFrom?: string
  createdTo?: string
  page?: number
  pageSize?: number
}

export interface RuntimeOpsRunListResponse {
  list: Record<string, any>[]
  total: number
  page?: number
  pageSize?: number
}

export interface RuntimeOpsJobListQuery {
  ownerType?: string
  status?: string
  tenantId?: string
  page?: number
  pageSize?: number
}

export interface RuntimeOpsJobListResponse {
  list: Record<string, any>[]
  total: number
  page?: number
  pageSize?: number
}

export function listRuntimeOpsRuns(params: RuntimeOpsRunListQuery) {
  return get<RuntimeOpsRunListResponse>('/v1/runtime-runs', params)
}

export function listRuntimeOpsJobs(params: RuntimeOpsJobListQuery) {
  return get<RuntimeOpsJobListResponse>('/v1/runtime-jobs', params)
}

export function listRuntimeOpsDlq(params: RuntimeOpsJobListQuery) {
  return get<RuntimeOpsJobListResponse>('/v1/runtime-jobs/dlq', params)
}

export function retryRuntimeOpsDlqJob(jobId: number) {
  return post<Record<string, any>>(`/v1/runtime-jobs/${jobId}/retry`)
}

export function reopenRuntimeOpsDlqJob(jobId: number, reason = 'operator reopened') {
  return post<Record<string, any>>(`/v1/runtime-jobs/${jobId}/reopen`, { reason })
}

export function ignoreRuntimeOpsDlqJob(jobId: number, reason = 'operator ignored') {
  return post<Record<string, any>>(`/v1/runtime-jobs/${jobId}/ignore`, { reason })
}

export function markRuntimeOpsDlqJobResolved(jobId: number, reason = 'operator marked resolved') {
  return post<Record<string, any>>(`/v1/runtime-jobs/${jobId}/mark-resolved`, { reason })
}

export function getRuntimeOpsRun(runId: number) {
  return get<Record<string, any>>(`/v1/runtime-runs/${runId}`)
}

export function cancelRuntimeOpsRun(runId: number, reason = 'operator cancel', deadlineMs = 1000) {
  return post<Record<string, any>>(`/v1/runtime-runs/${runId}/cancel`, { reason, deadlineMs })
}

export function resumeRuntimeOpsRun(runId: number, resumeData: Record<string, any> = {}) {
  return post<Record<string, any>>(`/v1/runtime-runs/${runId}/resume`, {
    resumeData,
    idempotencyKey: `runtime-ops-resume-${runId}-${Date.now()}`,
  })
}

export function listRuntimeOpsRunNodes(runId: number) {
  return get<{ list: Record<string, any>[]; total: number }>(`/v1/runtime-runs/${runId}/nodes`)
}

export function listRuntimeOpsRunEvents(runId: number, params?: { afterSequence?: number }) {
  return get<{ list: Record<string, any>[]; total: number }>(`/v1/runtime-runs/${runId}/events`, params)
}
