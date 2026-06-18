import type { AiAssistantEvent } from '@/api/aiAssistant'

export type AiAssistantTimelineKind =
  | 'phase'
  | 'model'
  | 'model-output'
  | 'model-thought'
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
  const timeline: AiAssistantTimelineItem[] = []
  let modelStreamGroup: AiAssistantEvent[] = []
  for (const event of events.slice().sort((left, right) => left.sequence - right.sequence)) {
    if (event.type === 'model.stream_chunk') {
      modelStreamGroup.push(event)
      continue
    }
    flushModelStreamGroup(timeline, modelStreamGroup)
    modelStreamGroup = []
    timeline.push(eventToTimelineItem(event))
  }
  flushModelStreamGroup(timeline, modelStreamGroup)
  return timeline
}

function eventToTimelineItem(event: AiAssistantEvent): AiAssistantTimelineItem {
  return {
    id: `${event.runId}-${event.sequence}-${event.type}`,
    eventId: event.id,
    sequence: event.sequence,
    kind: eventKind(event.type),
    tone: eventTone(event),
    title: event.visibleTitle || event.type,
    summary: event.visibleSummary || '',
    payloadPreview: compactPayload(event.payload),
    approvalId: typeof event.payload?.approvalId === 'number' ? event.payload.approvalId : undefined,
  }
}

function flushModelStreamGroup(timeline: AiAssistantTimelineItem[], events: AiAssistantEvent[]) {
  if (events.length === 0) return
  const first = events[0]
  const last = events[events.length - 1]
  timeline.push({
    id: `${first.runId}-${first.sequence}-${last.sequence}-model.stream_chunk`,
    eventId: last.id,
    sequence: first.sequence,
    kind: 'model-output',
    tone: events.some((event) => event.status === 'WAITING') ? 'waiting' : 'running',
    title: '模型输出',
    summary: events.map(modelStreamChunkText).join(''),
    payloadPreview: compactPayload({
      chunkCount: events.length,
      fromSequence: first.sequence,
      toSequence: last.sequence,
      phase: first.payload?.phase,
      source: first.payload?.source,
      streaming: events.some((event) => event.payload?.streaming === true),
    }),
  })
}

function modelStreamChunkText(event: AiAssistantEvent) {
  const chunk = event.payload?.chunk
  return typeof chunk === 'string' ? chunk : event.visibleSummary || ''
}

function eventKind(type: string): AiAssistantTimelineKind {
  if (type.startsWith('orchestration.') || type === 'run.started') return 'phase'
  if (type === 'model.stream_chunk') return 'model-output'
  if (type === 'model.thought_summary') return 'model-thought'
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
  if (event.type === 'model.stream_chunk') return 'running'
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
