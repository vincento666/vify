import type { AiAssistantEvent } from '@/api/aiAssistant'

export type RunActivityKind = 'phase' | 'step' | 'tool' | 'skill' | 'approval' | 'subagent'
export type RunActivityStatus = 'queued' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled'

export interface RunActivityDetailRef {
  runId: number
  firstSequence: number
  lastSequence: number
  eventIds: number[]
}

export interface RunActivity {
  id: string
  runId: number
  kind: RunActivityKind
  status: RunActivityStatus
  title: string
  summary: string
  startedAt: string
  completedAt?: string
  durationMs?: number
  firstSequence: number
  lastSequence: number
  eventIds: number[]
  detailRef: RunActivityDetailRef
  executionId?: string
  statusRef?: string
  eventStreamRef?: string
  resultRef?: string
  parentActivityId?: string
}

interface ActivityDescriptor {
  id: string
  kind: RunActivityKind
  status: RunActivityStatus
  title: string
  summary: string
  executionId?: string
  statusRef?: string
  eventStreamRef?: string
  resultRef?: string
  parentActivityId?: string
  startedAt?: string
  completedAt?: string
}

const TERMINAL_STATUSES = new Set<RunActivityStatus>(['completed', 'failed', 'cancelled'])

export function projectRunActivities(events: AiAssistantEvent[]): RunActivity[] {
  const uniqueEvents = new Map<number, AiAssistantEvent>()
  for (const event of events) {
    if (!uniqueEvents.has(event.id)) uniqueEvents.set(event.id, event)
  }
  const orderedEvents = [...uniqueEvents.values()].sort(
    (left, right) => left.sequence - right.sequence || left.id - right.id,
  )
  const activities = new Map<string, RunActivity>()

  for (const event of orderedEvents) {
    const descriptor = describeActivity(event)
    if (!descriptor) continue
    const existing = activities.get(descriptor.id)
    if (!existing) {
      activities.set(descriptor.id, {
        ...descriptor,
        runId: event.runId,
        startedAt: descriptor.startedAt || event.createdAt,
        completedAt: terminalCompletedAt(descriptor.status, descriptor.completedAt || event.createdAt),
        durationMs: durationMs(
          descriptor.startedAt || event.createdAt,
          terminalCompletedAt(descriptor.status, descriptor.completedAt || event.createdAt),
        ),
        firstSequence: event.sequence,
        lastSequence: event.sequence,
        eventIds: [event.id],
        detailRef: {
          runId: event.runId,
          firstSequence: event.sequence,
          lastSequence: event.sequence,
          eventIds: [event.id],
        },
      })
      continue
    }
    const eventIds = [...existing.eventIds, event.id]
    const lastSequence = Math.max(existing.lastSequence, event.sequence)
    const status = mergeActivityStatus(existing.status, descriptor.status)
    const completedAt = existing.completedAt || terminalCompletedAt(
      status,
      descriptor.completedAt || event.createdAt,
    )
    activities.set(descriptor.id, {
      ...existing,
      status,
      title: descriptor.title || existing.title,
      summary: descriptor.summary || existing.summary,
      lastSequence,
      completedAt,
      durationMs: durationMs(existing.startedAt, completedAt),
      eventIds,
      detailRef: {
        runId: existing.runId,
        firstSequence: existing.firstSequence,
        lastSequence,
        eventIds,
      },
      executionId: descriptor.executionId || existing.executionId,
      statusRef: descriptor.statusRef || existing.statusRef,
      eventStreamRef: descriptor.eventStreamRef || existing.eventStreamRef,
      resultRef: descriptor.resultRef || existing.resultRef,
      parentActivityId: descriptor.parentActivityId || existing.parentActivityId,
    })
  }

  return [...activities.values()].sort(
    (left, right) => left.firstSequence - right.firstSequence || left.id.localeCompare(right.id),
  )
}

function describeActivity(event: AiAssistantEvent): ActivityDescriptor | null {
  const payload = event.payload || {}
  const correlationId = stringValue(event.correlationIds?.activityId)
  const type = event.type.toLowerCase()
  if (!correlationId) return null

  if (type.startsWith('subagent.')) {
    if (!type.startsWith('subagent.execution_')) return null
    const executionId = stringValue(payload.executionId || payload.subAgentRunId)
    if (!executionId) return null
    return {
      id: correlationId,
      kind: 'subagent',
      status: statusForEvent(event),
      title: stringValue(payload.displayName) || event.visibleTitle || '子智能体',
      summary: stringValue(payload.currentSummary) || event.visibleSummary,
      executionId,
      statusRef: stringValue(payload.statusRef),
      eventStreamRef: stringValue(payload.eventStreamRef),
      resultRef: stringValue(payload.resultRef),
      parentActivityId: stringValue(event.correlationIds?.parentActivityId),
      startedAt: stringValue(payload.startedAt),
      completedAt: stringValue(payload.completedAt),
    }
  }

  if (type.startsWith('approval.')) {
    return {
      id: correlationId,
      kind: 'approval',
      status: statusForEvent(event),
      title: event.visibleTitle || '权限审批',
      summary: event.visibleSummary,
      parentActivityId: stringValue(event.correlationIds?.parentActivityId),
    }
  }

  if (type.startsWith('plan.step_')) {
    const step = objectValue(payload.step)
    return {
      id: correlationId,
      kind: 'step',
      status: statusForEvent(event),
      title: stringValue(step.title) || event.visibleTitle || '执行步骤',
      summary: event.visibleSummary,
      parentActivityId: stringValue(event.correlationIds?.parentActivityId),
    }
  }

  if (type.startsWith('tool.')) {
    const toolName = stringValue(payload.toolName)
    const isSkill = toolName === 'invoke_skill' || toolName === 'read_skill_resource' || toolName === 'run_skill_script'
    return {
      id: correlationId,
      kind: isSkill ? 'skill' : 'tool',
      status: statusForEvent(event),
      title: event.visibleTitle || (isSkill ? 'Skill 调用' : '工具调用'),
      summary: event.visibleSummary,
      parentActivityId: stringValue(event.correlationIds?.parentActivityId),
    }
  }

  if (
    type === 'run.started'
    || type === 'run.completed'
    || type === 'run.failed'
    || type === 'run.cancelled'
    || type === 'plan.created'
    || type.startsWith('task.')
    || type.startsWith('orchestration.phase_')
  ) {
    return {
      id: correlationId,
      kind: 'phase',
      status: statusForEvent(event),
      title: event.visibleTitle || '运行阶段',
      summary: event.visibleSummary,
      parentActivityId: stringValue(event.correlationIds?.parentActivityId),
    }
  }

  return null
}

function statusForEvent(event: AiAssistantEvent): RunActivityStatus {
  const type = event.type.toLowerCase()
  if (type.includes('cancel')) return 'cancelled'
  if (type.includes('failed') || type.includes('denied') || type.includes('error')) return 'failed'
  if (type.includes('completed') || type.includes('approved') || type.includes('granted')) return 'completed'
  if (type.includes('required') || type.includes('waiting') || type.includes('paused')) return 'waiting_approval'
  if (type.includes('started') || type.endsWith('_output') || type === 'task.updated') return 'running'
  return normalizeStatus(event.payload?.status || event.status)
}

function normalizeStatus(value: unknown): RunActivityStatus {
  const normalized = stringValue(value).toLowerCase()
  if (normalized === 'queued' || normalized === 'pending') return 'queued'
  if (normalized === 'running' || normalized === 'in_progress') return 'running'
  if (normalized === 'waiting' || normalized === 'waiting_approval' || normalized === 'paused') return 'waiting_approval'
  if (normalized === 'failed' || normalized === 'error' || normalized === 'timed_out') return 'failed'
  if (normalized === 'cancelled' || normalized === 'canceled') return 'cancelled'
  return 'completed'
}

function mergeActivityStatus(
  current: RunActivityStatus,
  next: RunActivityStatus,
): RunActivityStatus {
  if (TERMINAL_STATUSES.has(current)) return current
  return next
}

function terminalCompletedAt(
  status: RunActivityStatus,
  completedAt: string,
): string | undefined {
  return TERMINAL_STATUSES.has(status) ? completedAt : undefined
}

function durationMs(startedAt: string, completedAt?: string): number | undefined {
  if (!completedAt) return undefined
  const started = Date.parse(startedAt)
  const completed = Date.parse(completedAt)
  if (!Number.isFinite(started) || !Number.isFinite(completed)) return undefined
  return Math.max(0, completed - started)
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function stringValue(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value).trim()
    : ''
}
