import { get } from '@/utils/request'

export function listObserveRuns(params?: { page?: number; pageSize?: number; flowType?: string }) {
  return get<{ list: any[]; total: number; page: number; pageSize: number }>('/v1/observe/runs', {
    page: 1,
    pageSize: 20,
    ...params,
  })
}

export function getObserveRun(runId: number) {
  return get<any>(`/v1/observe/runs/${runId}`)
}

export function listObserveSessions(params?: { page?: number; pageSize?: number }) {
  return get<{ list: any[]; total: number; page: number; pageSize: number }>('/v1/observe/sessions', {
    page: 1,
    pageSize: 20,
    ...params,
  })
}

export function getObserveMetrics() {
  return get<any>('/v1/observe/metrics')
}
