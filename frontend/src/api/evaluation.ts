import { del, get, post, put } from '@/utils/request'

export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export interface EvalCase {
  id: number
  evalSetId: number
  input: string
  expectedOutput: string
  tags: string[]
  metadata: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface EvalSet {
  id: number
  name: string
  description: string
  caseCount: number
  createdAt: string
  updatedAt: string
}

export interface EvalSetDetail extends EvalSet {
  cases: EvalCase[]
}

export type EvaluatorType = 'EXACT_MATCH' | 'CONTAINS_KEYWORDS' | 'LLM_JUDGE'

export interface Evaluator {
  id: number
  name: string
  type: EvaluatorType
  config: Record<string, unknown>
  enabled: number
  createdAt: string
  updatedAt: string
}

export interface EvaluatorSampleResult {
  passed: boolean
  score: number
  reason: string
}

export type EvaluationTargetType = 'AGENT' | 'WORKFLOW' | 'CHATFLOW'

export interface EvaluationExperiment {
  id: number
  name: string
  targetType: EvaluationTargetType
  targetId: number
  evalSetId: number
  evaluatorIds: number[]
  status: string
  latestRunId: number | null
  createdAt: string
  updatedAt: string
}

export interface EvaluationCaseResult {
  id: number
  runId: number
  evalCaseId: number
  input: string
  expectedOutput: string
  targetOutput: string
  status: 'PASSED' | 'FAILED'
  score: number
  evaluatorResults: Array<Record<string, unknown>>
  reason: string
}

export interface EvaluationRun {
  id: number
  experimentId: number
  status: 'RUNNING' | 'COMPLETED' | 'FAILED'
  totalCases: number
  passedCases: number
  failedCases: number
  aggregateScore: number
  passRate: number
  startedAt: string | null
  finishedAt: string | null
  caseResults: EvaluationCaseResult[]
}

export interface EvaluationRunCompareCase {
  evalCaseId: number
  input: string
  baseStatus: string
  candidateStatus: string
  baseScore: number
  candidateScore: number
  baseReason: string
  candidateReason: string
}

export interface EvaluationRunCompare {
  baseRunId: number
  candidateRunId: number
  baseScore: number
  candidateScore: number
  scoreDelta: number
  basePassRate: number
  candidatePassRate: number
  passRateDelta: number
  newlyFailedCases: EvaluationRunCompareCase[]
  recoveredCases: EvaluationRunCompareCase[]
  unchangedFailures: EvaluationRunCompareCase[]
}

export const listEvalSets = (params?: { page?: number; pageSize?: number; name?: string }) =>
  get<PageResult<EvalSet>>('/v1/eval-sets', params)

export const createEvalSet = (data: { name: string; description?: string }) =>
  post<EvalSet>('/v1/eval-sets', data)

export const getEvalSet = (id: number) =>
  get<EvalSetDetail>(`/v1/eval-sets/${id}`)

export const updateEvalSet = (id: number, data: { name?: string; description?: string }) =>
  put<EvalSet>(`/v1/eval-sets/${id}`, data)

export const deleteEvalSet = (id: number) =>
  del<void>(`/v1/eval-sets/${id}`)

export const createEvalCase = (evalSetId: number, data: {
  input: string
  expectedOutput: string
  tags?: string[]
  metadata?: Record<string, unknown>
}) => post<EvalCase>(`/v1/eval-sets/${evalSetId}/cases`, data)

export const updateEvalCase = (id: number, data: {
  input: string
  expectedOutput: string
  tags?: string[]
  metadata?: Record<string, unknown>
}) => put<EvalCase>(`/v1/eval-cases/${id}`, data)

export const deleteEvalCase = (id: number) =>
  del<void>(`/v1/eval-cases/${id}`)

export const importEvalCasesCsv = (evalSetId: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return fetch(`/api/v1/eval-sets/${evalSetId}/cases/import-csv`, {
    method: 'POST',
    body: form,
  }).then(r => r.json()).then(res => {
    if (res.code !== 200) throw new Error(res.message)
    return res.data as { createdCount: number }
  })
}

export const listEvaluators = (params?: { page?: number; pageSize?: number; name?: string }) =>
  get<PageResult<Evaluator>>('/v1/evaluators', params)

export const createEvaluator = (data: { name: string; type: EvaluatorType; config: Record<string, unknown> }) =>
  post<Evaluator>('/v1/evaluators', data)

export const updateEvaluator = (
  id: number,
  data: { name: string; type: EvaluatorType; config: Record<string, unknown>; enabled?: number },
) => put<Evaluator>(`/v1/evaluators/${id}`, data)

export const deleteEvaluator = (id: number) =>
  del<void>(`/v1/evaluators/${id}`)

export const testEvaluatorDraft = (data: {
  type: EvaluatorType
  config: Record<string, unknown>
  expectedOutput?: string
  actualOutput: string
}) => post<EvaluatorSampleResult>('/v1/evaluators/test', data)

export const testEvaluator = (id: number, data: { expectedOutput?: string; actualOutput: string }) =>
  post<EvaluatorSampleResult>(`/v1/evaluators/${id}/test`, data)

export const listEvaluationExperiments = (params?: { page?: number; pageSize?: number; name?: string }) =>
  get<PageResult<EvaluationExperiment>>('/v1/evaluation-experiments', params)

export const createEvaluationExperiment = (data: {
  name: string
  targetType: EvaluationTargetType
  targetId: number
  evalSetId: number
  evaluatorIds: number[]
}) => post<EvaluationExperiment>('/v1/evaluation-experiments', data)

export const runEvaluationExperiment = (id: number) =>
  post<EvaluationRun>(`/v1/evaluation-experiments/${id}/runs`, {})

export const listEvaluationRuns = (params?: { page?: number; pageSize?: number; status?: string }) =>
  get<PageResult<EvaluationRun>>('/v1/evaluation-runs', params)

export const getEvaluationRun = (id: number, params?: { caseStatus?: string }) =>
  get<EvaluationRun>(`/v1/evaluation-runs/${id}`, params)

export const compareEvaluationRuns = (params: { baseRunId: number; candidateRunId: number }) =>
  get<EvaluationRunCompare>('/v1/evaluation-runs/compare', params)

export const rerunEvaluationCaseResult = (runId: number, caseResultId: number) =>
  post<EvaluationRun>(`/v1/evaluation-runs/${runId}/case-results/${caseResultId}/rerun`, {})

export const exportEvaluationRunCsv = async (id: number) => {
  const response = await fetch(`/api/v1/evaluation-runs/${id}/export-csv`)
  if (!response.ok) throw new Error('CSV export failed')
  return response.blob()
}
