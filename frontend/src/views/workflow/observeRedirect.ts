export interface ObserveRedirectDetail {
  flowType?: string | null
  workflowId?: number | string | null
}

export function normalizeObserveRedirectRunId(value: unknown): number {
  const raw = Array.isArray(value) ? value[0] : value
  const runId = Number(raw || 0)
  return Number.isInteger(runId) && runId > 0 ? runId : 0
}

export function buildObserveComposerRedirect({
  runId,
  detail,
}: {
  runId: number
  detail: ObserveRedirectDetail | null | undefined
}): string {
  const ownerId = Number(detail?.workflowId || 0)
  if (!Number.isInteger(runId) || runId <= 0 || !Number.isInteger(ownerId) || ownerId <= 0) {
    return '/workflows'
  }

  const flowType = String(detail?.flowType || '').toUpperCase()
  const scope = flowType === 'CHATFLOW' ? 'chatflows' : 'workflows'
  return `/${scope}/${ownerId}/canvas?runId=${runId}&debug=1`
}
