import { get, post } from '@/utils/request'

export interface RuntimeLabSession {
  id: number
  status?: string
  activeTaskId?: number | null
  version?: number
  createdAt?: string | null
  updatedAt?: string | null
}

export interface RuntimeLabTask {
  id: number
  sessionId?: number
  sopId: string
  status: string
  currentStep?: string | null
  checkpointId?: string | null
  parentTaskId?: number | null
  resumeSummary?: string | null
  businessRefs?: Record<string, unknown>
  suspendedAt?: string | null
  completedAt?: string | null
  createdAt?: string | null
  updatedAt?: string | null
}

export interface RuntimeLabEvent {
  id: number
  sessionId: number
  sequence: number
  eventType: string
  payload: Record<string, unknown>
  createdAt: string | null
}

export interface RuntimeLabRouteDecision {
  action: string
  reason?: string | null
  targetSopId?: string | null
  activeTaskId?: number | null
  matchedKeyword?: string | null
  candidates?: unknown[]
  candidateSources?: string[]
  policyGate?: Record<string, unknown> | null
  classifierRequest?: Record<string, unknown> | null
  classifierResult?: Record<string, unknown> | null
  finalDecision?: Record<string, unknown> | null
}

export interface RuntimeLabResumeOffer {
  taskId?: number
  sopId?: string
  prompt?: string
  [key: string]: unknown
}

export interface RuntimeLabTurn {
  reply: string
  routeDecision: RuntimeLabRouteDecision
  activeTask: RuntimeLabTask | null
  suspendedTasks: RuntimeLabTask[]
  resumeOffer: RuntimeLabResumeOffer | null
  events?: RuntimeLabEvent[]
}

export interface RuntimeLabListResult<T> {
  list: T[]
  total: number
}

export const createRuntimeLabSession = () =>
  post<RuntimeLabSession>('/v1/runtime-lab/sessions')

export const postRuntimeLabMessage = (
  sessionId: number,
  payload: { message: string; idempotencyKey?: string },
) => post<RuntimeLabTurn>(`/v1/runtime-lab/sessions/${sessionId}/messages`, payload)

export const listRuntimeLabTasks = (sessionId: number) =>
  get<RuntimeLabListResult<RuntimeLabTask>>(`/v1/runtime-lab/sessions/${sessionId}/tasks`)

export const listRuntimeLabEvents = (sessionId: number) =>
  get<RuntimeLabListResult<RuntimeLabEvent>>(`/v1/runtime-lab/sessions/${sessionId}/events`)
