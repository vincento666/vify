import type { AiAssistantEvent } from '@/api/aiAssistant'
import { projectRunActivities, type RunActivity } from './aiAssistantActivity'
import { buildAiAssistantTimeline, type AiAssistantTimelineItem } from './aiAssistantTimeline'

export type ActivityExpansionOverrides = Record<string, boolean>

export type RunActivityFeedItem =
  | {
      kind: 'activity'
      id: string
      sequence: number
      activity: RunActivity
    }
  | {
      kind: 'model-output'
      id: string
      sequence: number
      item: AiAssistantTimelineItem
    }

export interface SubagentPresence {
  items: RunActivity[]
  runningCount: number
  activeCount: number
  completedCount: number
}

export interface RunActivityProgress {
  current: number
  total: number
}

const ACTIVE_SUBAGENT_STATUSES = new Set<RunActivity['status']>([
  'queued',
  'running',
  'waiting_approval',
])

export function activityExpansionKey(activity: Pick<RunActivity, 'runId' | 'id'>) {
  return `run:${activity.runId}/activity:${activity.id}`
}

export function isActivityExpanded(
  activity: RunActivity,
  overrides: ActivityExpansionOverrides,
) {
  const explicit = overrides[activityExpansionKey(activity)]
  if (typeof explicit === 'boolean') return explicit
  return activity.status !== 'completed'
}

export function withActivityExpansion(
  overrides: ActivityExpansionOverrides,
  activity: RunActivity,
  expanded: boolean,
): ActivityExpansionOverrides {
  return {
    ...overrides,
    [activityExpansionKey(activity)]: expanded,
  }
}

export function buildRunActivityFeed(events: AiAssistantEvent[]): RunActivityFeedItem[] {
  const activityItems: RunActivityFeedItem[] = projectRunActivities(events)
    .filter((activity) => activity.kind !== 'subagent')
    .map((activity) => ({
      kind: 'activity',
      id: `activity:${activity.id}`,
      sequence: activity.firstSequence,
      activity,
    }))
  const modelItems: RunActivityFeedItem[] = buildAiAssistantTimeline(events)
    .filter((item) => item.kind === 'model-output' && !isFinalAnswerItem(item))
    .map((item) => ({
      kind: 'model-output',
      id: `model-output:${item.id}`,
      sequence: item.sequence,
      item,
    }))

  return [...activityItems, ...modelItems].sort(
    (left, right) => left.sequence - right.sequence || left.id.localeCompare(right.id),
  )
}

export function activityTimelineItems(
  activity: RunActivity,
  timeline: AiAssistantTimelineItem[],
) {
  const eventIds = new Set(activity.eventIds)
  return timeline.filter((item) => (
    item.kind !== 'model-output'
    && item.eventIds.some((eventId) => eventIds.has(eventId))
  ))
}

export function summarizeSubagentPresence(activities: RunActivity[]): SubagentPresence {
  const items = activities
    .filter((activity) => activity.kind === 'subagent' && Boolean(activity.executionId))
    .sort((left, right) => left.firstSequence - right.firstSequence || left.id.localeCompare(right.id))
  return {
    items,
    runningCount: items.filter((activity) => activity.status === 'running').length,
    activeCount: items.filter((activity) => ACTIVE_SUBAGENT_STATUSES.has(activity.status)).length,
    completedCount: items.filter((activity) => activity.status === 'completed').length,
  }
}

export function activityElapsedLabel(activity: RunActivity, nowMs = Date.now()) {
  const duration = activity.durationMs ?? runningDurationMs(activity, nowMs)
  if (duration < 1000) return '<1s'
  if (duration < 60_000) return `${Math.floor(duration / 1000)}s`
  const minutes = Math.floor(duration / 60_000)
  const seconds = Math.floor((duration % 60_000) / 1000)
  return `${minutes}m ${seconds}s`
}

export function activityProgress(
  activity: RunActivity,
  steps: Array<{ id: string }>,
): RunActivityProgress | undefined {
  if (activity.kind !== 'step' || steps.length === 0) return undefined
  const index = steps.findIndex((step) => activity.id === `run:${activity.runId}:step:${step.id}`)
  if (index < 0) return undefined
  return {
    current: index + 1,
    total: steps.length,
  }
}

function runningDurationMs(activity: RunActivity, nowMs: number) {
  const startedAt = Date.parse(activity.startedAt)
  if (!Number.isFinite(startedAt)) return 0
  return Math.max(0, nowMs - startedAt)
}

function isFinalAnswerItem(item: AiAssistantTimelineItem) {
  return item.phase === 'final_answer' || item.source === 'harness_final_answer'
}
