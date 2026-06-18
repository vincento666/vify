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
  details: AiAssistantTimelineDetail[]
  approvalId?: number
  phase?: string
  source?: string
}

export interface AiAssistantTimelineDetail {
  label: '调用详情' | '输入' | '输出' | '内容'
  value: string
  monospace?: boolean
  testId?: string
}

interface ToolEventGroup {
  id: string
  key: string
  events: AiAssistantEvent[]
  toolName: string
  input?: unknown
  output?: unknown
  status?: string
  completed: boolean
  firstSequence: number
  lastSequence: number
}

export function buildAiAssistantTimeline(events: AiAssistantEvent[]): AiAssistantTimelineItem[] {
  const sortedEvents = events.slice().sort((left, right) => left.sequence - right.sequence)
  const toolGroups = collectToolGroups(sortedEvents)
  const toolGroupByFirstSequence = new Map(toolGroups.map((group) => [group.firstSequence, group]))
  const toolEventSequences = new Set(toolGroups.flatMap((group) => group.events.map((event) => event.sequence)))
  const timeline: AiAssistantTimelineItem[] = []
  let modelStreamGroup: AiAssistantEvent[] = []
  let lastModelOutput = ''

  for (let index = 0; index < sortedEvents.length; index += 1) {
    const event = sortedEvents[index]
    if (event.type === 'model.stream_chunk') {
      modelStreamGroup.push(event)
      continue
    }

    lastModelOutput = flushModelStreamGroup(timeline, modelStreamGroup, lastModelOutput)
    modelStreamGroup = []

    if (toolEventSequences.has(event.sequence)) {
      const group = toolGroupByFirstSequence.get(event.sequence)
      if (group) timeline.push(toolGroupToTimelineItem(group))
      continue
    }

    if (
      event.type === 'model.thought_summary' &&
      (isDuplicateThought(event, lastModelOutput) || isDuplicateThought(event, nextModelStreamSummary(sortedEvents, index)))
    ) {
      continue
    }

    timeline.push(eventToTimelineItem(event))
  }
  flushModelStreamGroup(timeline, modelStreamGroup, lastModelOutput)
  return timeline
}

function eventToTimelineItem(event: AiAssistantEvent): AiAssistantTimelineItem {
  const kind = eventKind(event.type)
  const summary = event.visibleSummary || ''
  return {
    id: `${event.runId}-${event.sequence}-${event.type}`,
    eventId: event.id,
    sequence: event.sequence,
    kind,
    tone: eventTone(event),
    title: timelineTitle(event, kind),
    summary,
    payloadPreview: compactPayload(event.payload),
    details: eventDetails(event, kind, summary),
    approvalId: typeof event.payload?.approvalId === 'number' ? event.payload.approvalId : undefined,
  }
}

function flushModelStreamGroup(
  timeline: AiAssistantTimelineItem[],
  events: AiAssistantEvent[],
  previousModelOutput: string,
) {
  if (events.length === 0) return previousModelOutput
  const first = events[0]
  const last = events[events.length - 1]
  const summary = events.map(modelStreamChunkText).join('')
  timeline.push({
    id: `${first.runId}-${first.sequence}-${last.sequence}-model.stream_chunk`,
    eventId: last.id,
    sequence: first.sequence,
    kind: 'model-output',
    tone: modelStreamTone(events),
    title: '模型输出',
    summary,
    payloadPreview: compactPayload({
      chunkCount: events.length,
      fromSequence: first.sequence,
      toSequence: last.sequence,
      phase: first.payload?.phase,
      source: first.payload?.source,
      streaming: events.some((event) => event.payload?.streaming === true),
    }),
    details: [
      {
        label: '调用详情',
        value: `流式片段 ${events.length} 段${first.payload?.source ? ` / ${String(first.payload.source)}` : ''}`,
      },
      { label: '内容', value: summary, monospace: true },
    ],
    phase: typeof first.payload?.phase === 'string' ? first.payload.phase : undefined,
    source: typeof first.payload?.source === 'string' ? first.payload.source : undefined,
  })
  return summary
}

function modelStreamChunkText(event: AiAssistantEvent) {
  const chunk = event.payload?.chunk
  return typeof chunk === 'string' ? chunk : event.visibleSummary || ''
}

function modelStreamTone(events: AiAssistantEvent[]): AiAssistantTimelineItem['tone'] {
  if (events.some((event) => event.status === 'WAITING')) return 'waiting'
  if (events.some((event) => event.status === 'RUNNING')) return 'running'
  return 'success'
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

function timelineTitle(event: AiAssistantEvent, kind: AiAssistantTimelineKind) {
  if (kind === 'model-thought') return '思考'
  return event.visibleTitle || event.type
}

function eventDetails(
  event: AiAssistantEvent,
  kind: AiAssistantTimelineKind,
  summary: string,
): AiAssistantTimelineDetail[] {
  if (kind === 'model-output' || kind === 'model-thought') {
    return summary ? [{ label: '内容', value: summary, monospace: true }] : []
  }
  const rows: AiAssistantTimelineDetail[] = []
  if (summary) rows.push({ label: '调用详情', value: summary })
  if (event.payload && Object.keys(event.payload).length > 0) {
    rows.push({ label: '输入', value: prettyPayload(event.payload), monospace: true })
  }
  return rows
}

function collectToolGroups(events: AiAssistantEvent[]) {
  const groups: ToolEventGroup[] = []
  const activeGroups = new Map<string, ToolEventGroup>()
  for (const event of events) {
    if (!event.type.startsWith('tool.')) continue
    const key = toolEventKey(event)
    let group = activeGroups.get(key)
    if (event.type === 'tool.call_started' || !group) {
      group = createToolGroup(event, key)
      groups.push(group)
      activeGroups.set(key, group)
    }
    if (!group.events.some((item) => item.id === event.id)) group.events.push(event)
    group.lastSequence = Math.max(group.lastSequence, event.sequence)
    mergeToolEvent(group, event)
    if (event.type === 'tool.call_completed') {
      group.completed = true
      activeGroups.delete(key)
    }
  }
  return groups
}

function createToolGroup(event: AiAssistantEvent, key: string): ToolEventGroup {
  const toolName = payloadString(event, 'toolName') || 'tool'
  return {
    id: `${event.runId}-${event.sequence}-${key}-tool-call`,
    key,
    events: [],
    toolName,
    completed: false,
    firstSequence: event.sequence,
    lastSequence: event.sequence,
  }
}

function mergeToolEvent(group: ToolEventGroup, event: AiAssistantEvent) {
  group.toolName = payloadString(event, 'toolName') || group.toolName
  if ('input' in event.payload) group.input = event.payload.input
  if ('output' in event.payload) group.output = event.payload.output
  if ('status' in event.payload && typeof event.payload.status === 'string') group.status = event.payload.status
}

function toolGroupToTimelineItem(group: ToolEventGroup): AiAssistantTimelineItem {
  const first = group.events[0]
  const last = group.events[group.events.length - 1]
  return {
    id: group.id,
    eventId: last.id,
    sequence: group.firstSequence,
    kind: 'tool',
    tone: toolGroupTone(group),
    title: toolLabel(group.toolName),
    summary: '',
    payloadPreview: compactPayload({
      toolName: group.toolName,
      status: group.status,
      hasInput: group.input !== undefined,
      hasOutput: group.output !== undefined,
      fromSequence: group.firstSequence,
      toSequence: group.lastSequence,
    }),
    details: [
      {
        label: '调用详情',
        value: `${toolLabel(group.toolName)}${group.status ? ` / ${statusLabel(group.status)}` : ''}`,
      },
      {
        label: '输入',
        value: group.input === undefined ? prettyPayload(first.payload) : prettyPayload(group.input),
        monospace: true,
        testId: 'ai-assistant-tool-detail-input',
      },
      {
        label: '输出',
        value: group.output === undefined ? '等待工具输出' : prettyPayload(group.output),
        monospace: true,
        testId: 'ai-assistant-tool-detail-output',
      },
    ],
  }
}

function toolGroupTone(group: ToolEventGroup): AiAssistantTimelineItem['tone'] {
  if (group.status === 'FAILED') return 'danger'
  if (group.completed || group.output !== undefined) return 'success'
  return 'running'
}

function toolEventKey(event: AiAssistantEvent) {
  const scheduler = event.payload?.scheduler ?? event.correlationIds?.scheduler
  if (scheduler) return `${payloadString(event, 'toolName')}:${JSON.stringify(scheduler)}`
  if (event.toolCallId) return `tool-call:${event.toolCallId}`
  return payloadString(event, 'toolName') || `tool-sequence:${event.sequence}`
}

function payloadString(event: AiAssistantEvent, key: string) {
  const value = event.payload?.[key]
  return typeof value === 'string' ? value : ''
}

function isDuplicateThought(event: AiAssistantEvent, lastModelOutput: string) {
  const summary = String(event.payload?.summary || event.visibleSummary || '')
  return normalizeText(summary) !== '' && normalizeText(summary) === normalizeText(lastModelOutput)
}

function nextModelStreamSummary(events: AiAssistantEvent[], currentIndex: number) {
  const chunks: string[] = []
  for (let index = currentIndex + 1; index < events.length; index += 1) {
    const event = events[index]
    if (event.type !== 'model.stream_chunk') break
    chunks.push(modelStreamChunkText(event))
  }
  return chunks.join('')
}

function normalizeText(value: string) {
  return value.replace(/\s+/g, '').trim()
}

function compactPayload(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload ?? {})
  if (text.length <= 180) return text
  return `${text.slice(0, 177)}...`
}

function prettyPayload(payload: unknown) {
  if (payload === undefined || payload === null) return ''
  if (typeof payload === 'string') return payload
  return JSON.stringify(payload, null, 2)
}

function toolLabel(toolName: string) {
  return (
    {
      echo_context: '上下文回显',
      update_customer_profile: '客户资料变更',
      run_shell: '终端',
      customer_assistant_subagent_bridge: '客服助手子任务桥接',
      read_workspace_file: '读取工作区文件',
      write_workspace_file: '写入工作区文件',
      invoke_skill: '技能调用',
      search_knowledge_base: '知识库检索',
    }[toolName] ?? toolName
  )
}

function statusLabel(status: string) {
  return (
    {
      OK: '已完成',
      COMPLETED: '已完成',
      RUNNING: '执行中',
      FAILED: '失败',
      PENDING: '待处理',
      WAITING_APPROVAL: '等待审批',
    }[status] ?? status
  )
}
