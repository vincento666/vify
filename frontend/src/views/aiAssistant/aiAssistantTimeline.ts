import type { AiAssistantEvent } from '@/api/aiAssistant'

export type AiAssistantTimelineKind =
  | 'phase'
  | 'model'
  | 'tool'
  | 'tool-output'
  | 'approval'
  | 'sandbox'
  | 'proposed-action'
  | 'result'
  | 'error'

export interface AiAssistantTimelineItem {
  id: string
  eventId: number
  sequence: number
  kind: AiAssistantTimelineKind
  tone: 'running' | 'success' | 'waiting' | 'danger' | 'neutral'
  title: string
  summary: string
  payloadPreview: string
  approvalId?: number
}

export function buildAiAssistantTimeline(events: AiAssistantEvent[]): AiAssistantTimelineItem[] {
  return events
    .slice()
    .sort((left, right) => left.sequence - right.sequence)
    .map((event) => ({
      id: `${event.runId}-${event.sequence}-${event.type}`,
      eventId: event.id,
      sequence: event.sequence,
      kind: eventKind(event.type),
      tone: eventTone(event),
      title: event.visibleTitle || event.type,
      summary: event.visibleSummary || '',
      payloadPreview: compactPayload(event.payload),
      approvalId: typeof event.payload?.approvalId === 'number' ? event.payload.approvalId : undefined,
    }))
}

function eventKind(type: string): AiAssistantTimelineKind {
  if (type.startsWith('orchestration.') || type === 'run.started') return 'phase'
  if (type.startsWith('model.')) return 'model'
  if (type === 'tool.call_output') return 'tool-output'
  if (type.startsWith('tool.')) return 'tool'
  if (type.startsWith('approval.')) return 'approval'
  if (type === 'sandbox.denied') return 'sandbox'
  if (type.startsWith('proposed_action.')) return 'proposed-action'
  if (type === 'run.completed') return 'result'
  if (type === 'run.failed') return 'error'
  return 'phase'
}

function eventTone(event: AiAssistantEvent): AiAssistantTimelineItem['tone'] {
  if (event.type === 'run.started' || event.type.endsWith('_started')) return 'running'
  if (event.status === 'WAITING' || event.type === 'approval.required') return 'waiting'
  if (event.status === 'DENIED' || event.type === 'sandbox.denied' || event.type === 'run.failed') return 'danger'
  if (event.type === 'run.completed' || event.type.endsWith('_completed')) return 'success'
  return 'neutral'
}

function compactPayload(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload ?? {})
  if (text.length <= 180) return text
  return `${text.slice(0, 177)}...`
}
